import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { acceptIncident, cancelIncident, clearSession, createSOSIncident, getCategories, getDigitalTwin, getGuardianRelationships, getIncidentChat, getIncidentSharedLocation, getIncidents, getKnowledgeGraph, getLocation, getMe, getNearbyIncidents, getNotifications, getResponderAvailability, hasSession, login, logout, markAllNotificationsRead, markNotificationRead, register, rejectIncident, resolveIncident, respondToGuardianIncident, searchOpenStreetMap, sendIncidentMessage, setResponderAvailability as setResponderAvailabilityApi, updateLocation, updateProfile } from './api'
import type { ApiAIData, ApiChatMessage, ApiGuardianRelationship, ApiIncident, ApiLocation, ApiNotification, ApiProfile, ApiSharedLocation, ApiSharedParticipant, RegisterPayload } from './api'
import './App.css'

type Role = 'resident' | 'guardian' | 'volunteer' | 'security' | 'subadmin' | 'platform'
type DesignModel = 'mcc' | 'workbench' | 'cockpit'
type WorkspaceSection = 'Overview' | 'Incidents' | 'Communication' | 'AI command center' | 'Community' | 'Settings' | 'Help center' | 'Offline queue' | 'My profile'

type RoleMeta = {
  label: string
  title: string
  subtitle: string
  avatar: string
  accent: string
}

function uiRoleFromApi(role: string): Role {
  const normalized = role.toUpperCase().replace('-', '_').replace(' ', '_')
  if (normalized === 'GUARDIAN') return 'guardian'
  if (normalized === 'VOLUNTEER') return 'volunteer'
  if (normalized === 'SECURITY') return 'security'
  if (normalized === 'SUB_ADMIN' || normalized === 'SOCIETY_ADMIN') return 'subadmin'
  if (normalized === 'ADMIN' || normalized === 'PLATFORM_ADMIN') return 'platform'
  return 'resident'
}

function LoginScreen({ onLogin, onRegister, initialError = '' }: { onLogin: (username: string, password: string) => Promise<void>; onRegister: () => void; initialError?: string }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(initialError)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onLogin(username, password)
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Unable to sign in.')
    } finally {
      setBusy(false)
    }
  }

  return <div className="auth-shell"><section className="auth-card"><div className="brand auth-brand"><div className="brand-mark">✦</div><div><strong>SafeCircle</strong><span>Community response</span></div></div><div className="auth-tabs"><button className="active" onClick={() => undefined}>Login</button><button onClick={onRegister}>Register</button></div><span className="eyebrow">Protected workspace</span><h1>Welcome back</h1><p>Login to connect incidents, SOS alerts, guardians, responders, and notifications to your account.</p><form onSubmit={submit} className="auth-form"><label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label><label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required /></label>{error && <div className="auth-error" role="alert">{error}</div>}<button className="primary-button auth-submit" disabled={busy}>{busy ? 'Connecting…' : 'Login securely'}</button></form><div className="auth-links"><button className="link-button" onClick={onRegister}>New here? Register first</button></div><small className="auth-note">API session · JWT tokens refresh automatically · role permissions come from Django.</small></section></div>
}

function RegisterScreen({ onRegister, onLogin, initialError = '' }: { onRegister: (payload: RegisterPayload) => Promise<void>; onLogin: () => void; initialError?: string }) {
  const [form, setForm] = useState<RegisterPayload>({ name: '', location: '', society_name: '', flat_number: '', phone: '', email: '', username: '', password: '', role: 'RESIDENT' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(initialError)
  const setField = (field: keyof RegisterPayload, value: string) => setForm((current) => ({ ...current, [field]: value }))
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try { await onRegister(form) } catch (registerError) { setError(registerError instanceof Error ? registerError.message : 'Unable to create your account.') } finally { setBusy(false) }
  }
  return <div className="auth-shell"><section className="auth-card register-card"><div className="brand auth-brand"><div className="brand-mark">✦</div><div><strong>SafeCircle</strong><span>Community response</span></div></div><div className="auth-tabs"><button onClick={onLogin}>Login</button><button className="active" onClick={() => undefined}>Register</button></div><span className="eyebrow">Resident onboarding</span><h1>Create your account</h1><p>Register your household first, then use the Login option to enter the protected workspace.</p><form onSubmit={submit} className="auth-form register-form" autoComplete="off"><div className="auth-form-grid"><label>Full name<input value={form.name} onChange={(event) => setField('name', event.target.value)} autoComplete="off" required /></label><label>Contact number<input value={form.phone} onChange={(event) => setField('phone', event.target.value)} type="tel" autoComplete="off" required /></label><label>Location<input value={form.location} onChange={(event) => setField('location', event.target.value)} autoComplete="off" placeholder="Area, city or address" required /></label><label>Society name<input value={form.society_name} onChange={(event) => setField('society_name', event.target.value)} autoComplete="off" required /></label><label>Flat number<input value={form.flat_number} onChange={(event) => setField('flat_number', event.target.value)} autoComplete="off" required /></label><label>Email<input value={form.email} onChange={(event) => setField('email', event.target.value)} type="email" autoComplete="off" required /></label><label>Username<input value={form.username} onChange={(event) => setField('username', event.target.value)} autoComplete="off" required /></label><label>Password<input value={form.password} onChange={(event) => setField('password', event.target.value)} type="password" autoComplete="new-password" minLength={5} required /><small className="field-hint">Minimum 5 characters</small></label></div>{error && <div className="auth-error" role="alert">{error}</div>}<button className="primary-button auth-submit" disabled={busy}>{busy ? 'Creating account…' : 'Create resident account'}</button></form><div className="auth-links"><button className="link-button" onClick={onLogin}>Already registered? Login</button></div><small className="auth-note">Your account is created as a resident. Society and flat records can be linked later by an administrator.</small></section></div>
}

const roles: Record<Role, RoleMeta> = {
  resident: { label: 'Resident', title: 'Resident Dashboard', subtitle: 'Good morning, Ravi. Your community is ready to help.', avatar: 'RK', accent: 'blue' },
  guardian: { label: 'Guardian', title: 'Guardian Dashboard', subtitle: 'Stay close when your family needs you.', avatar: 'GR', accent: 'green' },
  volunteer: { label: 'Volunteer', title: 'Volunteer Dashboard', subtitle: 'Your quick response can change everything.', avatar: 'VO', accent: 'orange' },
  security: { label: 'Security', title: 'Security Dashboard', subtitle: 'Coordinate a fast, visible response.', avatar: 'SE', accent: 'purple' },
  subadmin: { label: 'Society admin', title: 'Society Admin Dashboard', subtitle: 'Manage your society, users, and incidents.', avatar: 'SA', accent: 'teal' },
  platform: { label: 'Platform admin', title: 'Platform Admin Dashboard', subtitle: 'See platform-wide safety, analytics, and configuration.', avatar: 'PA', accent: 'pink' },
}

const navItems = [
  { icon: '⌂', label: 'Overview' },
  { icon: '◉', label: 'Incidents' },
  { icon: '◌', label: 'Communication' },
  { icon: '⌖', label: 'AI command center' },
  { icon: '♧', label: 'Community' },
]

const designModels: { id: DesignModel; label: string; short: string; description: string }[] = [
  { id: 'mcc', label: 'Mission Control Center', short: 'Model 1', description: 'Map-first command surface for live operations.' },
  { id: 'workbench', label: 'Role-Adaptive Workbench', short: 'Model 2', description: 'A tailored workspace for every role.' },
  { id: 'cockpit', label: 'AI Decision Cockpit', short: 'Model 3', description: 'Digital Twin and Knowledge Graph at the center.' },
]

function StatusPill({ children, tone = 'blue' }: { children: string; tone?: string }) {
  return <span className={`status-pill ${tone}`}>{children}</span>
}

function MetricCard({ icon, label, value, trend, tone }: { icon: string; label: string; value: string; trend: string; tone: string }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-icon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span className="metric-trend">{trend}</span>
      </div>
    </article>
  )
}

function Timeline() {
  return (
    <div className="timeline">
      <div className="timeline-item done"><span className="timeline-dot">✓</span><div><strong>SOS created</strong><small>Today, 10:30 AM</small></div></div>
      <div className="timeline-item done"><span className="timeline-dot">✓</span><div><strong>Guardian notified</strong><small>Primary guardian responded</small></div></div>
      <div className="timeline-item active"><span className="timeline-dot">•</span><div><strong>Community response</strong><small>Volunteer is on the way · ETA 5 min</small></div></div>
      <div className="timeline-item pending"><span className="timeline-dot">○</span><div><strong>Assistance completed</strong><small>Waiting for resolution update</small></div></div>
    </div>
  )
}

type MapMarker = {
  id: string
  label: string
  kind: 'incident' | 'responder' | 'location'
  latitude?: number | null
  longitude?: number | null
  x?: number
  y?: number
  status?: string
  icon?: string
}

function OpenStreetMapLayer({ location, markers = [], sharedParticipants = [], zoom = 13 }: { location?: ApiLocation | null; markers?: MapMarker[]; sharedParticipants?: ApiSharedParticipant[]; zoom?: number }) {
  const latitude = location?.latitude != null ? Number(location.latitude) : 17.385
  const longitude = location?.longitude != null ? Number(location.longitude) : 78.4867
  const tileCount = 2 ** zoom
  const centerX = ((longitude + 180) / 360) * tileCount * 256
  const centerY = ((1 - Math.asinh(Math.tan((latitude * Math.PI) / 180)) / Math.PI) / 2) * tileCount * 256
  const baseTileX = Math.floor(centerX / 256)
  const baseTileY = Math.floor(centerY / 256)
  const centerTileX = centerX - baseTileX * 256
  const centerTileY = centerY - baseTileY * 256
  const tiles = [-1, 0, 1].flatMap((dx) => [-1, 0, 1].map((dy) => {
    const tileX = (baseTileX + dx + tileCount) % tileCount
    const tileY = Math.min(tileCount - 1, Math.max(0, baseTileY + dy))
    return { tileX, tileY, dx, dy }
  }))

  const markerPositions = markers.map((marker, index) => {
    if (marker.latitude != null && marker.longitude != null) {
      const markerX = ((Number(marker.longitude) + 180) / 360) * tileCount * 256
      const markerY = ((1 - Math.asinh(Math.tan((Number(marker.latitude) * Math.PI) / 180)) / Math.PI) / 2) * tileCount * 256
      let deltaX = markerX - centerX
      if (deltaX > (tileCount * 256) / 2) deltaX -= tileCount * 256
      if (deltaX < -(tileCount * 256) / 2) deltaX += tileCount * 256
      return { marker, style: { left: `calc(50% + ${deltaX}px)`, top: `calc(50% + ${markerY - centerY}px)` } }
    }
    const fallbackPositions = [{ x: 28, y: 31 }, { x: 67, y: 24 }, { x: 81, y: 72 }, { x: 54, y: 61 }]
    const fallback = marker.x != null && marker.y != null ? { x: marker.x, y: marker.y } : fallbackPositions[index % fallbackPositions.length]
    return { marker, style: { left: `${fallback.x}%`, top: `${fallback.y}%` } }
  })

  const sharedParticipantPositions = sharedParticipants.filter((participant) => participant.latitude != null && participant.longitude != null).map((participant) => {
    const participantX = ((Number(participant.longitude) + 180) / 360) * tileCount * 256
    const participantY = ((1 - Math.asinh(Math.tan((Number(participant.latitude) * Math.PI) / 180)) / Math.PI) / 2) * tileCount * 256
    let deltaX = participantX - centerX
    if (deltaX > (tileCount * 256) / 2) deltaX -= tileCount * 256
    if (deltaX < -(tileCount * 256) / 2) deltaX += tileCount * 256
    return { participant, x: Math.max(8, Math.min(92, 50 + (deltaX / (3 * 256)) * 100)), y: Math.max(10, Math.min(86, 50 + ((participantY - centerY) / (3 * 256)) * 100)) }
  })
  const sharedRoutePositions = sharedParticipantPositions.filter(({ participant }) => participant.accepted)

  return <div className="osm-map-layer" aria-label="OpenStreetMap location view">{tiles.map(({ tileX, tileY, dx, dy }) => <img key={`${tileX}-${tileY}-${dx}-${dy}`} src={`https://tile.openstreetmap.org/${zoom}/${tileX}/${tileY}.png`} alt="" style={{ left: `calc(50% - ${centerTileX}px + ${dx * 256}px)`, top: `calc(50% - ${centerTileY}px + ${dy * 256}px)` }} />)}{sharedRoutePositions.length > 0 && <svg className="shared-route-overlay" viewBox="0 0 100 100" aria-hidden="true">{sharedRoutePositions.map(({ participant, x, y }) => <line key={`route-${participant.id}`} x1="50" y1="50" x2={x} y2={y} />)}</svg>}{markerPositions.map(({ marker, style }) => <span className={`osm-marker ${marker.kind} ${marker.status ?? ''}`} key={marker.id} style={style} title={marker.label}><span>{marker.icon ?? (marker.kind === 'responder' ? 'R' : marker.kind === 'location' ? 'You' : '!')}</span><small>{marker.label}</small></span>)}{sharedParticipantPositions.map(({ participant, x, y }) => <span className={`osm-marker shared-participant ${participant.accepted ? 'accepted' : 'waiting'}`} key={`participant-${participant.id}`} style={{ left: `${x}%`, top: `${y}%` }} title={`${participant.role} · ${participant.distance_km ?? '—'} km · ${participant.accepted ? `ETA ${participant.estimated_arrival_minutes ?? '—'} min` : 'waiting for acceptance'}`}><span>{participant.role === 'security' ? 'S' : participant.role === 'guardian' ? 'G' : 'V'}</span><small>{participant.role} · {participant.accepted ? `ETA ${participant.estimated_arrival_minutes ?? '—'} min` : 'waiting'}</small></span>)}</div>
}

function MissionControlView({ onOpenAI, incidents, location, isPreview }: { onOpenAI: () => void; incidents: ApiIncident[]; location?: ApiLocation | null; isPreview: boolean }) {
  const [mapZoom, setMapZoom] = useState(13)
  const activeIncidents = incidents.filter((incident) => !['resolved', 'closed', 'cancelled'].includes(incident.status))
  const mapIncidentMarkers: MapMarker[] = (activeIncidents.length ? activeIncidents.slice(0, 6) : isPreview ? [{ id: 0, incident_id: 'preview-incident', category: 'medical', category_name: 'Medical emergency', status: 'active', created_at: '', updated_at: '' } as ApiIncident] : []).map((incident, index) => ({
    id: `incident-${incident.id}`,
    label: `${incident.category_name} · ${incident.status}`,
    kind: 'incident',
    latitude: incident.location?.latitude ?? incident.latitude,
    longitude: incident.location?.longitude ?? incident.longitude,
    x: 28 + (index * 17) % 50,
    y: 31 + (index * 13) % 42,
    status: incident.status,
    icon: incident.category_name.toLowerCase().includes('fire') ? '♨' : incident.category_name.toLowerCase().includes('fall') ? '!' : incident.category_name.toLowerCase().includes('accident') ? '⌖' : '✚',
  }))
  const mapMarkers: MapMarker[] = [...mapIncidentMarkers, { id: 'current-location', label: 'Current location', kind: 'location', latitude: location?.latitude, longitude: location?.longitude, icon: 'You' }, { id: 'responder-network', label: 'Responder network', kind: 'responder', x: 57, y: 66, icon: 'R' }]
  return <section className="mcc-view">
    <div className="mcc-banner"><div><StatusPill tone="soft-red">Live operations</StatusPill><h2>Mission Control Center</h2><p>Coordinate every incident, responder, and escalation from one calm surface.</p></div><div className="mcc-status"><span className="pulse" /> All systems operational<strong>24 active incidents</strong></div></div>
    <div className="mcc-metrics"><MetricCard icon="◉" label="Active incidents" value="24" trend="+3 this hour" tone="blue" /><MetricCard icon="⌖" label="Responders online" value="18" trend="72% available" tone="green" /><MetricCard icon="◷" label="Average response" value="4.2m" trend="18% faster" tone="orange" /><MetricCard icon="✦" label="AI confidence" value="92%" trend="High confidence" tone="purple" /></div>
    <div className="mcc-grid"><article className="panel ops-map-panel"><div className="panel-heading"><div><span className="eyebrow">Live geospatial view · OpenStreetMap</span><h2>Community response map</h2></div><StatusPill tone="green">{`${activeIncidents.length} live incidents`}</StatusPill></div><div className="ops-map"><OpenStreetMapLayer location={location} markers={mapMarkers} zoom={mapZoom} /><div className="map-controls"><button onClick={() => setMapZoom((current) => Math.min(17, current + 1))} aria-label="Zoom in">＋</button><button onClick={() => setMapZoom((current) => Math.max(10, current - 1))} aria-label="Zoom out">−</button><button onClick={() => setMapZoom(13)} aria-label="Reset map zoom">⌖</button></div><div className="map-attribution">© OpenStreetMap contributors</div></div><div className="map-legend wide"><span><i className="critical-dot" /> Incident</span><span><i className="responder-dot" /> Responder</span><span><i className="location-dot" /> Current location</span></div></article><article className="panel mcc-queue"><div className="panel-heading"><div><span className="eyebrow">Priority queue</span><h2>Needs attention</h2></div><button className="text-button">View all →</button></div>{['Medical emergency · Tower A','Security concern · Gate 2','Fall alert · Tower B','Guardian escalation · Flat 204'].map((item, index) => <div className="mcc-queue-row" key={item}><span className={`priority-marker p-${index}`}>{index + 1}</span><div><strong>{item}</strong><small>{['Responder accepted · ETA 5 min','Awaiting assignment','Guardian notified','Secondary guardian next'][index]}</small></div><StatusPill tone={index === 1 ? 'amber' : index === 3 ? 'purple' : 'green'}>{index === 1 ? 'Action' : index === 3 ? 'Escalate' : 'Active'}</StatusPill></div>)}</article><article className="panel lifecycle-panel"><div className="panel-heading"><div><span className="eyebrow">Incident lifecycle</span><h2>Response pipeline</h2></div><button className="text-button">Open board →</button></div><div className="lifecycle-lanes"><div><span>REPORTED</span><strong>08</strong><small>New SOS alerts</small></div><div><span>DISPATCHED</span><strong>06</strong><small>Responders assigned</small></div><div><span>ON SCENE</span><strong>04</strong><small>Assistance active</small></div><div><span>RESOLVED</span><strong>12</strong><small>Closed today</small></div></div></article><article className="panel mcc-ai"><div><span className="eyebrow">AI operations layer</span><h2>See relationships. Simulate response.</h2><p>Connect the Knowledge Graph to the Digital Twin before the next decision.</p><button className="primary-button" onClick={onOpenAI}>Open AI decision cockpit →</button></div><div className="mini-graph"><span className="mini-node center">AI</span><span className="mini-node one">R</span><span className="mini-node two">I</span><span className="mini-node three">V</span></div></article></div>
  </section>
}

function AICockpitView({ incident, graph, twin, onRefresh }: { incident?: ApiIncident; graph?: ApiAIData | null; twin?: ApiAIData | null; onRefresh: (scenario?: string) => void }) {
  const [scenario, setScenario] = useState('Current response')
  const scenarios = ['Current response', 'Fire spread · 30 min', 'Flood evacuation · 60 min', 'Crowd density · 120 min']
  const graphEntityCount = Array.isArray(graph?.nodes) ? graph.nodes.length : graph ? Object.keys(graph).length : 0
  const twinStatus = typeof twin?.status === 'string' ? twin.status : twin ? 'Generated from API' : 'Waiting for an incident'

  return <section className="cockpit-view"><div className="cockpit-banner"><div><StatusPill tone="purple">AI decision layer</StatusPill><h2>AI Emergency Decision Cockpit</h2><p>{incident ? `${incident.category_name} · ${incident.status} · ${incident.incident_id}` : 'Select an incident to generate live AI context.'}</p></div><div className="confidence-ring"><strong>{graph ? 'API' : '—'}</strong><span>{twinStatus}</span></div></div><div className="scenario-bar"><span className="eyebrow">Simulation scenario</span>{scenarios.map((item) => <button key={item} className={scenario === item ? 'scenario active' : 'scenario'} onClick={() => { setScenario(item); onRefresh(item) }}>{item}</button>)}<span className="freshness">● {scenario} · {graph || twin ? 'data fresh' : 'not loaded'}</span></div><div className="cockpit-grid"><article className="panel twin-panel"><div className="panel-heading"><div><span className="eyebrow">Digital Twin</span><h2>Emergency simulation space</h2></div><button className="text-button" onClick={() => onRefresh(scenario)}>↻ Refresh</button></div><div className="twin-canvas"><div className="twin-building building-a"><span>{incident?.category_name ?? 'Tower A'}</span><i /></div><div className="twin-building building-b"><span>{incident?.status ?? 'Tower B'}</span><i /></div><div className="twin-road" /><div className="risk-wave wave-one" /><div className="risk-wave wave-two" /><span className="twin-alert">!</span><div className="twin-label label-one">Live twin: {twinStatus}</div><div className="twin-label label-two">Human approval required</div><div className="twin-controls"><button>−</button><button>+</button><button>◷</button></div></div><div className="twin-footer"><span><i className="risk-red" /> Risk projection</span><span><i className="route-green" /> Recommended route</span><span><i className="people-blue" /> People coverage</span></div></article><article className="panel graph-panel"><div className="panel-heading"><div><span className="eyebrow">Knowledge Graph</span><h2>Connected entities</h2></div><button className="text-button" onClick={() => onRefresh()}>Refresh →</button></div><div className="knowledge-graph"><div className="graph-connection c-one" /><div className="graph-connection c-two" /><div className="graph-connection c-three" /><div className="graph-connection c-four" /><span className="kg-node kg-center">{incident ? 'INC' : '—'}<br /><small>{graphEntityCount || 'API'}</small></span><span className="kg-node kg-resident">R</span><span className="kg-node kg-guardian">G</span><span className="kg-node kg-volunteer">V</span><span className="kg-node kg-location">⌖</span></div><div className="entity-list"><span><i className="entity blue" /> {incident ? '1 incident' : 'No incident selected'}</span><span><i className="entity green" /> {graphEntityCount || 0} API entities</span><span><i className="entity purple" /> Human review</span><span><i className="entity orange" /> Live location</span></div></article><article className="panel recommendation-panel"><div className="panel-heading"><div><span className="eyebrow">Recommended actions</span><h2>Human-approved next steps</h2></div><StatusPill tone="green">API context</StatusPill></div>{['Dispatch nearest volunteer', 'Notify guardian escalation', 'Keep safe zone open'].map((item, index) => <div className="recommendation" key={item}><span>{index + 1}</span><div><strong>{item}</strong><small>{incident ? `Based on ${incident.category_name} · review before action` : 'Waiting for live incident context'}</small></div><button onClick={() => onRefresh(scenario)}>Review</button></div>)}</article><article className="panel ai-summary"><div className="summary-icon">✦</div><div><span className="eyebrow">AI summary</span><h2>{incident ? 'Response context loaded' : 'Waiting for incident data'}</h2><p>{graph ? 'Knowledge graph and digital twin snapshots are connected to the selected incident.' : 'Open an incident from the API feed to generate AI context.'}</p><button className="ghost-button" onClick={() => onRefresh()}>View explanation</button></div></article></div></section>
}

type IncidentAction = 'accept' | 'reject' | 'resolve' | 'cancel'
type WorkspaceRow = { title: string; detail: string; action?: string; incident?: ApiIncident; notification?: ApiNotification }

function ProfileSectionView({ profile, busy, onSave }: { profile: ApiProfile; busy: boolean; onSave: (payload: Partial<ApiProfile>) => void }) {
  const [form, setForm] = useState({ name: profile.name ?? '', location: profile.location ?? '', society_name: profile.society_name ?? '', flat_number: profile.flat_number ?? '', phone: profile.phone ?? '', email: profile.email ?? '', username: profile.username ?? '' })
  const setField = (field: keyof typeof form, value: string) => setForm((current) => ({ ...current, [field]: value }))
  return <section className="workspace-section-view"><article className="workspace-hero teal"><div><StatusPill tone="teal">Account details</StatusPill><h2>My profile</h2><p>Keep your household information current so responders can reach the right person and location.</p></div><div className="workspace-hero-mark">◎</div></article><article className="panel profile-panel"><div className="profile-panel-heading"><div className="profile-large-avatar">{(form.name || form.username).slice(0, 2).toUpperCase()}</div><div><span className="eyebrow">Resident account</span><h2>{form.name || form.username}</h2><p>{roles[uiRoleFromApi(profile.role)].label} · {form.email}</p></div></div><div className="profile-form-grid">{([['name', 'Full name'], ['location', 'Location'], ['society_name', 'Society name'], ['flat_number', 'Flat number'], ['phone', 'Contact number'], ['email', 'Email'], ['username', 'Username']] as const).map(([field, label]) => <label key={field}>{label}<input value={form[field]} onChange={(event) => setField(field, event.target.value)} required /></label>)}</div><div className="profile-actions"><button className="primary-button" disabled={busy} onClick={() => onSave(form)}>{busy ? 'Saving…' : 'Save profile'}</button><small>Role and permissions are managed securely by Django.</small></div></article></section>
}

function OfflineQueueView({ onRetry }: { onRetry: () => void }) {
  const [items, setItems] = useState([{ id: 1, title: 'Location update', detail: 'Waiting for a connection', status: 'Queued' }, { id: 2, title: 'Emergency contact sync', detail: 'Will retry automatically', status: 'Queued' }, { id: 3, title: 'Notification receipt', detail: 'Created from preview mode', status: 'Ready' }])
  const [syncing, setSyncing] = useState(false)
  const retrySync = () => {
    if (syncing || !items.length) return
    setSyncing(true)
    onRetry()
    setItems((current) => current.map((item) => ({ ...item, detail: 'Synced just now', status: 'Synced' })))
    window.setTimeout(() => {
      setItems([])
      setSyncing(false)
    }, 700)
  }
  return <section className="workspace-section-view"><article className="workspace-hero orange"><div><StatusPill tone="orange">Resilient mode</StatusPill><h2>Offline queue</h2><p>Your important actions stay safe on the device and sync when the connection returns.</p></div><div className="workspace-hero-mark">⌁</div></article><div className="offline-queue-layout"><article className="panel queue-status-panel"><span className="offline-big-icon">⌁</span><span className="eyebrow">Connection status</span><h2>{syncing ? 'Syncing queue' : items.length ? 'Ready to sync' : 'Queue synced'}</h2><p>SafeCircle keeps emergency updates, location changes, and notification receipts in order.</p><div className="queue-progress"><span style={{ width: `${Math.max(20, 100 - items.length * 14)}%` }} /></div><small>{syncing ? 'Sending queued actions now…' : `${items.length} item${items.length === 1 ? '' : 's'} waiting · automatic retry enabled`}</small><button className="primary-button" disabled={syncing || !items.length} onClick={retrySync}>{syncing ? 'Syncing…' : items.length ? 'Retry sync now' : 'Queue synced'}</button></article><article className="panel workspace-list-panel"><div className="panel-heading"><div><span className="eyebrow">Device queue</span><h2>Pending actions</h2></div><button className="text-button" onClick={() => setItems([])}>Clear completed</button></div>{items.length ? items.map((item) => <div className="workspace-list-row" key={item.id}><span className="workspace-row-icon orange">{item.id}</span><span className="workspace-row-copy"><strong>{item.title}</strong><small>{item.detail}</small></span><StatusPill tone={item.status === 'Ready' || item.status === 'Synced' ? 'green' : 'amber'}>{item.status}</StatusPill></div>) : <div className="queue-empty">The queue is clear. New actions will appear here while offline.</div>}</article></div></section>
}

function WorkspaceSectionView({ section, role, incidents, notifications, relationships, availability, profile, busy, onMarkAllRead, onToggleAvailability, onIncidentAction, onOpenChat, onNotificationRead, onSectionAction, onProfileSave }: { section: WorkspaceSection; role: Role; incidents: ApiIncident[]; notifications: ApiNotification[]; relationships: ApiGuardianRelationship[]; availability: boolean | null; profile?: ApiProfile | null; busy: boolean; onMarkAllRead: () => void; onToggleAvailability: () => void; onIncidentAction: (incidentId: number, action: IncidentAction) => void; onOpenChat: (incidentId: number) => void; onNotificationRead: (notificationId: number) => void; onSectionAction: (action: string) => void; onProfileSave: (payload: Partial<ApiProfile>) => void }) {
  if (section === 'Offline queue') return <OfflineQueueView onRetry={() => onSectionAction('retry-queue')} />
  if (section === 'My profile') {
    const previewProfile: ApiProfile = profile ?? { id: 0, username: roles[role].label.toLowerCase().replace(/\s+/g, '.'), email: 'Login to connect your email', phone: '', name: roles[role].label, location: 'Preview location', society_name: 'Preview society', flat_number: '—', role: role.toUpperCase() }
    return <ProfileSectionView key={previewProfile.username} profile={previewProfile} busy={busy} onSave={onProfileSave} />
  }
  const sectionContent = {
    Incidents: { eyebrow: 'Live response queue', title: 'Incidents needing attention', description: 'Review active alerts, assign responders, and keep every response moving.', tone: 'blue' },
    Communication: { eyebrow: 'Response inbox', title: 'Messages ready to sync', description: 'Keep guardians, residents, and responders aligned across every channel.', tone: 'green' },
    Community: { eyebrow: 'People and places', title: 'Community network', description: 'See who is available nearby and how your response coverage is changing.', tone: 'teal' },
    Settings: { eyebrow: 'Workspace preferences', title: 'Make SafeCircle fit your team', description: 'Notification rules, role preferences, and offline behavior are ready to configure.', tone: 'purple' },
    'Help center': { eyebrow: 'Need a hand?', title: 'Help center', description: 'Find guidance for emergency workflows, guardian escalation, and responder coordination.', tone: 'orange' },
  } as const
  const content = sectionContent[section as keyof typeof sectionContent]

  if (!content) return null

  const incidentRows: WorkspaceRow[] = incidents.slice(0, 5).map((incident) => ({ title: `${incident.category_name} · ${incident.incident_id}`, detail: `${incident.status} · ${new Date(incident.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`, incident }))
  const notificationRows: WorkspaceRow[] = notifications.slice(0, 5).map((notification) => ({ title: notification.title, detail: notification.message, notification }))
  const communityRows: WorkspaceRow[] = [
    `${relationships.length} guardian relationship${relationships.length === 1 ? '' : 's'} linked`,
    availability === null ? 'Responder availability not applicable' : `Responder availability: ${availability ? 'available' : 'offline'}`,
    `${incidents.filter((incident) => !['resolved', 'closed', 'cancelled'].includes(incident.status)).length} active incidents visible to this role`,
  ].map((title) => ({ title, detail: 'Synced from Django API' }))
  const settingsRows: WorkspaceRow[] = [
    { title: 'Notification preferences', detail: 'Choose which response updates should reach you', action: 'notifications' },
    { title: 'Offline queue & sync', detail: 'Review actions waiting for a connection', action: 'offline' },
    { title: 'Profile & household details', detail: 'Update contact, society, flat, and location details', action: 'profile' },
  ]
  const helpRows: WorkspaceRow[] = [
    { title: 'Activate an SOS alert', detail: 'Choose medical, accident, fire, or fall alert', action: 'sos' },
    { title: 'Share live location', detail: 'Use the location control on the overview screen', action: 'location' },
    { title: 'Review role permissions', detail: 'Access is controlled by Django permissions', action: 'profile' },
    { title: 'Offline mode and queue', detail: 'Understand how updates sync after reconnecting', action: 'offline' },
  ]
  const rows: WorkspaceRow[] = section === 'Incidents' ? incidentRows : section === 'Communication' ? notificationRows : section === 'Community' ? communityRows : section === 'Settings' ? settingsRows : helpRows
  const visibleRows: WorkspaceRow[] = rows.length ? rows : [{ title: 'No API records yet', detail: 'This section will update when data is created.' }]
  const activeCount = incidents.filter((incident) => !['resolved', 'closed', 'cancelled'].includes(incident.status)).length

  return <section className="workspace-section-view"><article className={`workspace-hero ${content.tone}`}><div><StatusPill tone={content.tone}>{content.eyebrow}</StatusPill><h2>{content.title}</h2><p>{content.description}</p></div><div className="workspace-hero-mark">{section === 'Communication' ? '◌' : section === 'Community' ? '♧' : section === 'Help center' ? '?' : '◉'}</div></article><div className="workspace-summary-grid"><MetricCard icon="◉" label={section === 'Communication' ? 'Unread messages' : 'Active incidents'} value={section === 'Communication' ? String(notifications.filter((notification) => !notification.is_read).length) : String(activeCount)} trend="Synced just now" tone="blue" /><MetricCard icon="♧" label="Guardian links" value={String(relationships.length)} trend="From API" tone="green" /><MetricCard icon="◷" label="Notifications" value={String(notifications.length)} trend={availability === null ? 'All roles' : availability ? 'Responder online' : 'Responder offline'} tone="orange" /></div><article className="panel workspace-list-panel"><div className="panel-heading"><div><span className="eyebrow">{role === 'resident' ? 'Your workspace' : roles[role].label}</span><h2>{section === 'Settings' ? 'Preferences' : section === 'Help center' ? 'Popular guidance' : 'Recent activity'}</h2></div>{section === 'Communication' ? <button className="text-button" onClick={onMarkAllRead}>Mark all read</button> : section === 'Community' && availability !== null ? <button className="text-button" onClick={onToggleAvailability}>{availability ? 'Go offline' : 'Go available'}</button> : <StatusPill tone="green">Live API</StatusPill>}</div>{visibleRows.map((row, index) => {
    const incident = row.incident
    const isTerminal = incident ? ['resolved', 'closed', 'cancelled'].includes(incident.status) : true
    const canRespond = Boolean(incident && ['guardian', 'volunteer', 'security'].includes(role) && !isTerminal)
    const canChat = Boolean(incident && ['guardian', 'volunteer', 'security'].includes(role))
    const canResolve = Boolean(incident && ['guardian', 'volunteer', 'security', 'subadmin', 'platform'].includes(role) && ['active_response', 'response_received', 'on_scene', 'notifications_sent'].includes(incident.status))
    const canCancel = Boolean(incident && role === 'resident' && !isTerminal)
    return <div className="workspace-list-row" key={`${row.title}-${index}`}><span className={`workspace-row-icon ${content.tone}`}>{index + 1}</span><span className="workspace-row-copy"><strong>{row.title}</strong><small>{row.detail}</small></span>{incident && <span className="workspace-row-actions">{canRespond && <><button disabled={busy} onClick={() => onIncidentAction(incident.id, 'accept')}>Accept</button><button disabled={busy} className="subtle-danger" onClick={() => onIncidentAction(incident.id, 'reject')}>Reject</button></>}{canResolve && <button disabled={busy} onClick={() => onIncidentAction(incident.id, 'resolve')}>Resolve</button>}{canCancel && <button disabled={busy} className="subtle-danger" onClick={() => onIncidentAction(incident.id, 'cancel')}>Cancel</button>}{canChat && <button disabled={busy} className="subtle-button" onClick={() => onOpenChat(incident.id)}>Chat</button>}</span>}{row.notification && !row.notification.is_read && <button className="subtle-button" onClick={() => onNotificationRead(row.notification!.id)}>Mark read</button>}{row.action && <button className="subtle-button" onClick={() => onSectionAction(row.action!)}>Open →</button>}{!incident && !row.notification && !row.action && <span className="workspace-row-arrow">→</span>}</div>
  })}</article></section>
}

function LocationInterface({ onOpenCommunity, onSyncLocation, location }: { onOpenCommunity: () => void; onSyncLocation: () => void; location?: ApiLocation | null }) {
  const [query, setQuery] = useState('Green Valley Apartments')
  const [locationStatus, setLocationStatus] = useState('Your location is active')
  const [mapLocation, setMapLocation] = useState<ApiLocation | null>(location ?? null)
  const [searchBusy, setSearchBusy] = useState(false)

  const searchLocation = async () => {
    if (!query.trim()) return
    setSearchBusy(true)
    try {
      const result = await searchOpenStreetMap(query.trim())
      setMapLocation({ latitude: result.latitude, longitude: result.longitude })
      setLocationStatus(result.label)
    } catch (error) {
      setLocationStatus(error instanceof Error ? error.message : 'Location search failed.')
    } finally {
      setSearchBusy(false)
    }
  }

  const locationLabel = mapLocation?.latitude != null && mapLocation?.longitude != null ? `${Number(mapLocation.latitude).toFixed(4)}, ${Number(mapLocation.longitude).toFixed(4)}` : 'Green Valley Apartments'
  return <article className="network-card location-card"><div className="card-heading"><div><span className="eyebrow">Location interface</span><h3>Nearby response network</h3></div><button className="more-button" onClick={onOpenCommunity} aria-label="Open community">•••</button></div><div className="location-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void searchLocation() }} aria-label="Search location" /><button onClick={() => void searchLocation()} disabled={searchBusy}>{searchBusy ? 'Searching…' : 'Search'}</button></div><div className="location-map"><OpenStreetMapLayer location={mapLocation} /><span className="location-marker resident-marker">You</span><span className="location-marker responder-marker">R</span><span className="location-marker guardian-marker">G</span><div className="location-map-controls"><button onClick={() => setLocationStatus('Zoomed in')}>＋</button><button onClick={() => setLocationStatus('Zoomed out')}>−</button><button onClick={() => { setLocationStatus('Requesting your device location'); onSyncLocation() }} aria-label="Center on my location">⌖</button></div><div className="location-map-label"><strong>{mapLocation ? `Live location · ${locationLabel}` : locationStatus}</strong><small>{location?.accuracy != null ? `Accuracy ${Math.round(Number(location.accuracy))} m · synced` : 'Search or center the map'} · © OpenStreetMap</small></div></div><div className="location-bottom-sheet"><div><span className="location-pulse" /><div><strong>4 responders nearby</strong><small>1 guardian · 450 m away</small></div></div><button onClick={onOpenCommunity}>View people →</button></div></article>
}

function MobilePreviewGallery({ onChoose, onClose }: { onChoose: (design: DesignModel) => void; onClose: () => void }) {
  const previews: { id: DesignModel; number: string; title: string; description: string }[] = [
    { id: 'mcc', number: '01', title: 'Mission Control', description: 'Best for security teams and society admins.' },
    { id: 'workbench', number: '02', title: 'Resident Home', description: 'Best for everyday residents and guardians.' },
    { id: 'cockpit', number: '03', title: 'AI Cockpit', description: 'Best for advanced response coordination.' },
  ]

  return <div className="mobile-gallery-backdrop" role="presentation"><section className="mobile-gallery" role="dialog" aria-modal="true" aria-labelledby="mobile-gallery-title"><div className="mobile-gallery-heading"><div><span className="eyebrow">Android app directions</span><h2 id="mobile-gallery-title">Choose your mobile home screen</h2><p>Three touch-first SafeCircle interfaces for the Android app.</p></div><button className="modal-close" onClick={onClose} aria-label="Close preview">×</button></div><div className="phone-gallery">{previews.map((preview) => <article className="phone-option" key={preview.id}><div className={`phone-frame phone-${preview.id}`}><div className="phone-speaker" /><div className="phone-status"><span>9:41</span><span>● ▰</span></div>{preview.id === 'mcc' && <><div className="phone-appbar"><span>SafeCircle</span><b>⌖</b></div><div className="phone-greeting"><small>LIVE OPERATIONS</small><h3>Community watch</h3></div><div className="phone-map"><span className="phone-pin red">✚</span><span className="phone-pin amber">!</span><span className="phone-pin blue">R</span><div className="phone-map-label">24 active incidents</div></div><div className="phone-stat-row"><span><b>18</b><small>online</small></span><span><b>4.2m</b><small>response</small></span></div><div className="phone-alert-row"><span>✚</span><div><b>Medical emergency</b><small>Tower A · ETA 5 min</small></div><i>›</i></div></>}{preview.id === 'workbench' && <><div className="phone-appbar"><span>Good morning, Ravi</span><b>♧</b></div><div className="phone-sos-card"><small>NEED HELP?</small><h3>Alert your network</h3><button>SOS</button><span>Guardians + nearby responders</span></div><div className="phone-section-title"><b>Your response network</b><span>See all</span></div><div className="phone-network"><span className="phone-avatar green">G</span><span className="phone-avatar blue">V</span><span className="phone-avatar orange">S</span><div><b>4 people available</b><small>1 guardian connected</small></div></div><div className="phone-timeline"><span>✓</span><div><b>Volunteer is on the way</b><small>ETA 5 minutes · Tower A</small></div></div></>}{preview.id === 'cockpit' && <><div className="phone-appbar dark"><span>AI command center</span><b>✦</b></div><div className="phone-ai-ring"><strong>92%</strong><small>AI confidence</small></div><div className="phone-ai-card"><small>ACTIVE INCIDENT · 005</small><h3>Response is stable</h3><p>Guardian confirmed. Volunteer dispatched.</p><span>Digital Twin synced · 12 sec ago</span></div><div className="phone-section-title light"><b>Recommended next steps</b><span>3</span></div><div className="phone-recommendation"><span>1</span><b>Keep safe zone open</b><i>›</i></div><div className="phone-recommendation"><span>2</span><b>Monitor Tower A</b><i>›</i></div></>}<div className="phone-bottom-nav"><span className="active">⌂<small>Home</small></span><span>◉<small>Alerts</small></span><span>♧<small>People</small></span><span>☷<small>More</small></span></div></div><div className="phone-option-copy"><div><span>Model {preview.number}</span><h3>{preview.title}</h3></div><p>{preview.description}</p><button className="phone-choose" onClick={() => onChoose(preview.id)}>Choose this interface →</button></div></article>)}</div></section></div>
}

function ResponseTrackingModal({ incident, shared, onClose }: { incident: ApiIncident; shared: ApiSharedLocation; onClose: () => void }) {
  const acceptedParticipants = shared.participants.filter((participant) => participant.accepted)
  const fastestEta = acceptedParticipants.map((participant) => participant.estimated_arrival_minutes).filter((eta): eta is number => eta != null).sort((left, right) => left - right)[0]
  const roleLabel = (role: string) => role === 'security' ? 'Security' : role === 'guardian' ? 'Guardian' : 'Volunteer'
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><section className="response-tracking-modal" role="dialog" aria-modal="true" aria-labelledby="response-tracking-title" onClick={(event) => event.stopPropagation()}><div className="panel-heading"><div><span className="eyebrow">Resident ↔ accepted responder</span><h2 id="response-tracking-title">Private response route</h2><p className="tracking-subtitle">SOS {incident.incident_id} · only the resident and accepted responder are shown</p></div><button className="modal-close" onClick={onClose} aria-label="Close response tracking">×</button></div><div className="tracking-status-row"><div><span className="tracking-live-dot" /> Location is shared only after an acceptor accepts this incident.</div><StatusPill tone="soft-red">{shared.incident_status}</StatusPill></div><div className="tracking-map"><OpenStreetMapLayer location={shared.location} markers={[{ id: 'sos-location', label: 'Resident SOS location', kind: 'location', status: 'injured', icon: 'SOS' }]} sharedParticipants={shared.participants} zoom={14} /><div className="tracking-map-key"><span><i className="tracking-route-line" /> Resident ↔ accepted responder route</span><span><i className="tracking-sos-dot" /> Resident</span><span><i className="tracking-team-dot" /> Accepted responder</span></div></div>{!shared.location && <div className="tracking-warning">The resident location is unavailable. Share the resident device location to draw the private route and calculate ETA.</div>}{shared.location && shared.accepted_count === 0 && <div className="tracking-warning">The resident location is ready. The blue route and ETA will appear when a responder accepts.</div>}<div className="tracking-summary"><MetricCard icon="♧" label="Notified" value={String(shared.shared_with_count)} trend="Notifications only" tone="blue" /><MetricCard icon="✓" label="Accepted" value={String(shared.accepted_count ?? acceptedParticipants.length)} trend="Private route active" tone="green" /><MetricCard icon="◷" label="Fastest ETA" value={fastestEta != null ? `${fastestEta}m` : '—'} trend="Accepted responder" tone="orange" /></div><div className="tracking-participants"><div className="panel-heading"><div><span className="eyebrow">Private response map</span><h3>Accepted responder</h3></div>{shared.location?.google_maps_url && <a className="text-button" href={shared.location.google_maps_url} target="_blank" rel="noreferrer">Open resident location ↗</a>}</div>{shared.participants.length ? shared.participants.map((participant) => <div className="tracking-participant" key={participant.id}><span className={`tracking-avatar ${participant.role} ${participant.accepted ? 'accepted' : 'waiting'}`}>{participant.role === 'security' ? 'S' : participant.role === 'guardian' ? 'G' : 'V'}</span><div><strong>{participant.username} · {roleLabel(participant.role)}</strong><small>{participant.accepted ? participant.location_available ? `${participant.distance_km} km away · resident route highlighted blue · ETA ${participant.estimated_arrival_minutes ?? '—'} min` : `Accepted · waiting for responder location${participant.accepted_eta_minutes != null ? ` · ETA ${participant.accepted_eta_minutes} min` : ''}` : 'Not accepted · location hidden'}</small></div>{participant.accepted && participant.route_url ? <a href={participant.route_url} target="_blank" rel="noreferrer">Route ↗</a> : <StatusPill tone="amber">{participant.accepted ? 'Accepted' : 'Waiting'}</StatusPill>}</div>) : <div className="tracking-empty">The resident location is private until a responder accepts. No responder location is displayed yet.</div>}</div><button className="primary-button tracking-close" onClick={onClose}>Keep tracking in workspace</button></section></div>
}

function IncidentChatModal({ incident, messages, draft, busy, error, onDraftChange, onSend, onClose }: { incident?: ApiIncident; messages: ApiChatMessage[]; draft: string; busy: boolean; error: string; onDraftChange: (value: string) => void; onSend: () => void; onClose: () => void }) {
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><section className="chat-modal" role="dialog" aria-modal="true" aria-labelledby="chat-title" onClick={(event) => event.stopPropagation()}><div className="panel-heading"><div><span className="eyebrow">Incident communication</span><h2 id="chat-title">{incident?.category_name ?? 'Incident'} chat</h2></div><button className="modal-close" onClick={onClose} aria-label="Close chat">×</button></div><div className="chat-message-list">{messages.length ? messages.map((message) => <div className="chat-message" key={message.id}><strong>{message.sender_name}</strong><p>{message.message}</p><small>{new Date(message.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</small></div>) : <div className="chat-empty">No messages yet. Start the response conversation.</div>}</div>{error && <div className="auth-error" role="alert">{error}</div>}<div className="chat-compose"><input value={draft} onChange={(event) => onDraftChange(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') onSend() }} placeholder="Write a response update…" aria-label="Chat message" /><button className="primary-button" onClick={onSend} disabled={busy || !draft.trim()}>{busy ? 'Sending…' : 'Send'}</button></div></section></div>
}

function App() {
  const [role, setRole] = useState<Role>('resident')
  const [previewMode, setPreviewMode] = useState(false)
  const [authUser, setAuthUser] = useState<ApiProfile | null>(null)
  const [authLoading, setAuthLoading] = useState(() => hasSession())
  const [authError, setAuthError] = useState('')
  const [authView, setAuthView] = useState<'login' | 'register'>('register')
  const [incidents, setIncidents] = useState<ApiIncident[]>([])
  const [notificationsUnread, setNotificationsUnread] = useState(0)
  const [notifications, setNotifications] = useState<ApiNotification[]>([])
  const [relationships, setRelationships] = useState<ApiGuardianRelationship[]>([])
  const [responderAvailability, setResponderAvailability] = useState<boolean | null>(null)
  const [nearbyIncidents, setNearbyIncidents] = useState<ApiIncident[]>([])
  const [aiGraph, setAiGraph] = useState<ApiAIData | null>(null)
  const [aiTwin, setAiTwin] = useState<ApiAIData | null>(null)
  const [apiLocation, setApiLocation] = useState<ApiLocation | null>(null)
  const [categories, setCategories] = useState<{ id: number; code: string; name: string; is_active: boolean }[]>([])
  const [design, setDesign] = useState<DesignModel>('workbench')
  const [activeNav, setActiveNav] = useState<WorkspaceSection>('Overview')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [mobileGalleryOpen, setMobileGalleryOpen] = useState(false)
  const [sosOpen, setSosOpen] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState('Medical emergency')
  const [alertSent, setAlertSent] = useState(false)
  const [alertError, setAlertError] = useState('')
  const [workspaceMessage, setWorkspaceMessage] = useState('')
  const [workspaceError, setWorkspaceError] = useState('')
  const [workspaceBusy, setWorkspaceBusy] = useState(false)
  const [chatIncidentId, setChatIncidentId] = useState<number | null>(null)
  const [chatMessages, setChatMessages] = useState<ApiChatMessage[]>([])
  const [chatDraft, setChatDraft] = useState('')
  const [chatBusy, setChatBusy] = useState(false)
  const [chatError, setChatError] = useState('')
  const [responseTracking, setResponseTracking] = useState<{ incident: ApiIncident; shared: ApiSharedLocation } | null>(null)
  const [offlineCount] = useState(3)
  const meta = roles[role]
  const latestIncident = incidents[0]
  const selectedCategoryCode = categories.find((category) => category.name.toLowerCase() === selectedAlert.toLowerCase())?.code
    ?? ({ 'Medical emergency': 'medical', 'Accident emergency': 'accident', 'Fire emergency': 'fire', 'Fall alert': 'fall' }[selectedAlert] ?? 'medical')

  const loadApiData = async (profile = authUser) => {
    const [incidentResult, notificationResult, locationResult, categoryResult] = await Promise.allSettled([
      getIncidents(), getNotifications(), getLocation(), getCategories(),
    ])
    if (incidentResult.status === 'fulfilled') setIncidents(incidentResult.value)
    if (notificationResult.status === 'fulfilled') {
      setNotificationsUnread(notificationResult.value.unread_count)
      setNotifications(notificationResult.value.results)
    }
    if (locationResult.status === 'fulfilled') setApiLocation(locationResult.value)
    if (categoryResult.status === 'fulfilled') setCategories(categoryResult.value)
    const loadedLocation = locationResult.status === 'fulfilled' ? locationResult.value : null
    const loadedRole = profile ? uiRoleFromApi(profile.role) : role
    if (['resident', 'guardian', 'subadmin'].includes(loadedRole)) {
      const relationshipResult = await getGuardianRelationships().catch(() => ({ data: [] }))
      setRelationships(relationshipResult.data)
    }
    if (['volunteer', 'security'].includes(loadedRole)) {
      const availabilityResult = await getResponderAvailability().catch(() => ({ data: { is_available: false } }))
      setResponderAvailability(availabilityResult.data.is_available)
      const nearbyResult = await getNearbyIncidents(loadedLocation).catch(() => ({ data: [] }))
      setNearbyIncidents(nearbyResult.data)
    } else {
      setResponderAvailability(null)
      setNearbyIncidents([])
    }
  }

  const loadAIData = async (scenario?: string) => {
    const incident = incidents[0]
    if (!authUser || !incident) {
      setAiGraph(null)
      setAiTwin(null)
      return
    }
    const [graphResult, twinResult] = await Promise.allSettled([getKnowledgeGraph(incident.id), getDigitalTwin(incident.id, scenario)])
    if (graphResult.status === 'fulfilled') setAiGraph(graphResult.value.data)
    if (twinResult.status === 'fulfilled') setAiTwin(twinResult.value.data)
  }

  useEffect(() => {
    if (!hasSession()) return
    getMe().then((profile) => {
      setAuthUser(profile)
      setRole(uiRoleFromApi(profile.role))
      setPreviewMode(false)
      return loadApiData(profile)
    }).catch((error: unknown) => {
      clearSession()
      setAuthError(error instanceof Error ? error.message : 'Your session expired. Please sign in again.')
      setPreviewMode(false)
    }).finally(() => setAuthLoading(false))
  // The initial session restore intentionally runs once on mount.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleLogin = async (username: string, password: string) => {
    const profile = await login(username, password)
    setAuthUser(profile)
    setRole(uiRoleFromApi(profile.role))
    setPreviewMode(false)
    setAuthError('')
    await loadApiData(profile)
  }

  const handleRegister = async (payload: RegisterPayload) => {
    await register(payload)
    setAuthView('login')
    setAuthError('Registration complete. Use your username and password to login.')
  }

  const handleLogout = () => {
    logout()
    setAuthUser(null)
    setPreviewMode(false)
    setAuthError('')
    setAuthView('login')
  }

  const syncBrowserLocation = () => {
    if (!authUser) return
    if (!navigator.geolocation) {
      setWorkspaceError('This browser does not provide device location. Use a browser with location enabled to trace the route.')
      return
    }
    navigator.geolocation.getCurrentPosition((position) => {
      const nextLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude, accuracy: position.coords.accuracy }
      setApiLocation(nextLocation)
      void updateLocation(nextLocation)
        .then(() => setWorkspaceMessage('Resident device location synced. New accepted routes can now be traced.'))
        .catch(() => setWorkspaceError('Location was read but could not be synced. Please try again.'))
    }, () => {
      setWorkspaceError('Location permission is required. Allow device location, then select Center on my location again.')
    }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 })
  }

  const readBrowserLocation = () => new Promise<ApiLocation>((resolve, reject) => {
    if (!navigator.geolocation) { reject(new Error('Device location is unavailable.')); return }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude, accuracy: position.coords.accuracy }),
      () => reject(new Error('Location permission was not granted.')),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 },
    )
  })

  const sendAlert = async () => {
    if (!authUser) {
      setSosOpen(false)
      setAlertSent(true)
      return
    }
    setAlertError('')
    try {
      let sharedLocation = apiLocation
      if (sharedLocation?.latitude == null || sharedLocation.longitude == null) {
        try {
          sharedLocation = await readBrowserLocation()
          setApiLocation(sharedLocation)
          await updateLocation(sharedLocation).catch(() => undefined)
        } catch {
          sharedLocation = apiLocation
        }
      }
      const response = await createSOSIncident({ category: selectedCategoryCode, message: `${selectedAlert} reported from the SafeCircle mobile app.`, latitude: sharedLocation?.latitude, longitude: sharedLocation?.longitude, accuracy: sharedLocation?.accuracy })
      if (response.data) {
        setIncidents((current) => [response.data, ...current])
        const sharedResult = await getIncidentSharedLocation(response.data.id).catch(() => null)
        const trackingData = sharedResult?.data ?? {
          incident_id: response.data.id,
          incident_status: response.data.status,
          resident: { id: authUser.id, username: authUser.username },
          location: sharedLocation?.latitude != null && sharedLocation.longitude != null ? { latitude: sharedLocation.latitude, longitude: sharedLocation.longitude, accuracy: sharedLocation.accuracy } : null,
          participants: [],
          shared_with_count: 0,
          accepted_count: 0,
          updated_at: new Date().toISOString(),
        }
        setResponseTracking({ incident: response.data, shared: trackingData })
      }
      setSosOpen(false)
      setAlertSent(true)
      await loadApiData()
    } catch (error) {
      setAlertError(error instanceof Error ? error.message : 'Unable to activate the emergency alert.')
    }
  }

  useEffect(() => {
    const incidentId = responseTracking?.incident.id
    if (incidentId == null) return undefined
    const refreshSharedLocation = async () => {
      const result = await getIncidentSharedLocation(incidentId).catch(() => null)
      if (result?.data) setResponseTracking((current) => current?.incident.id === incidentId ? { ...current, shared: result.data } : current)
    }
    const intervalId = window.setInterval(() => void refreshSharedLocation(), 10000)
    return () => window.clearInterval(intervalId)
  }, [responseTracking?.incident.id])

  const aiCopy = useMemo(() => {
    if (role === 'platform') return { label: 'AI platform insight', title: 'Response time is improving', body: 'Across 3 communities, average response time is down 18% this month.' }
    if (role === 'volunteer' || role === 'security') return { label: 'AI assignment insight', title: 'You are a strong match', body: 'You are the closest available responder for 2 active incidents nearby.' }
    return { label: 'AI emergency insight', title: 'Your response network is ready', body: 'Primary guardian is connected, and 4 nearby responders are available.' }
  }, [role])

  const navigate = (nextNav: WorkspaceSection) => {
    setActiveNav(nextNav)
    setMobileMenuOpen(false)
    if (nextNav === 'AI command center') { setDesign('cockpit'); void loadAIData() }
    if (nextNav !== 'Overview' && nextNav !== 'AI command center') setDesign('workbench')
    if (nextNav === 'Overview' && design === 'cockpit') setDesign('workbench')
  }

  const chooseRole = (nextRole: Role) => {
    setRole(nextRole)
    navigate('Overview')
    if (authUser && nextRole !== uiRoleFromApi(authUser.role)) {
      setWorkspaceMessage(`Dashboard switched to ${roles[nextRole].label}. Development preview actions are enabled for this dashboard.`)
    }
  }

  const chooseDesign = (nextDesign: DesignModel) => {
    setDesign(nextDesign)
    setActiveNav(nextDesign === 'cockpit' ? 'AI command center' : 'Overview')
    if (nextDesign === 'cockpit') void loadAIData()
  }

  const handleMarkAllRead = async () => {
    if (!authUser) return
    await markAllNotificationsRead()
    setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true })))
    setNotificationsUnread(0)
  }

  const handleToggleAvailability = async () => {
    if (responderAvailability === null) return
    const nextValue = !responderAvailability
    setWorkspaceError('')
    try {
      await setResponderAvailabilityApi(nextValue)
      setResponderAvailability(nextValue)
      setWorkspaceMessage(`You are now ${nextValue ? 'available' : 'offline'} for nearby response.`)
    } catch (error) {
      setWorkspaceError(error instanceof Error ? error.message : 'Unable to update availability.')
    }
  }

  const handleIncidentAction = async (incidentId: number, action: IncidentAction) => {
    if (!authUser) {
      setWorkspaceError('Sign in to update incidents.')
      return
    }
    setWorkspaceBusy(true)
    setWorkspaceError('')
    try {
      if (action === 'accept') {
        const signedInRole = uiRoleFromApi(authUser.role)
        if (signedInRole === 'guardian' && role === 'guardian') {
          try {
            await respondToGuardianIncident(incidentId, 5)
          } catch (error) {
            // Some existing incidents were created before a GuardianEscalation
            // row was generated. The relationship-scoped accept endpoint keeps
            // those valid guardian incidents actionable.
            if (!(error instanceof Error) || !error.message.toLowerCase().includes('no pending guardian escalation')) throw error
            await acceptIncident(incidentId, 5, role)
          }
        } else {
          await acceptIncident(incidentId, 5, role)
        }
        const acceptedIncident = incidents.find((incident) => incident.id === incidentId)
        const sharedResult = await getIncidentSharedLocation(incidentId).catch(() => null)
        if (acceptedIncident && sharedResult?.data) setResponseTracking({ incident: acceptedIncident, shared: sharedResult.data })

        // Open tracking immediately after acceptance. Location permission can
        // take several seconds, so capture the acceptor position in the
        // background and refresh the same private resident -> acceptor view.
        try {
          const responderLocation = await readBrowserLocation()
          setApiLocation(responderLocation)
          await updateLocation(responderLocation)
          const refreshedSharedResult = await getIncidentSharedLocation(incidentId).catch(() => null)
          if (acceptedIncident && refreshedSharedResult?.data) setResponseTracking({ incident: acceptedIncident, shared: refreshedSharedResult.data })
        } catch {
          // The modal remains open and explains that a responder location is
          // still needed when the browser declines location access.
        }
      }
      if (action === 'reject') await rejectIncident(incidentId, undefined, role)
      if (action === 'resolve') await resolveIncident(incidentId, undefined, role)
      if (action === 'cancel') await cancelIncident(incidentId)
      await loadApiData()
      setWorkspaceMessage(`Incident ${action === 'accept' ? 'accepted' : action === 'reject' ? 'rejected' : action === 'resolve' ? 'resolved' : 'cancelled'} successfully.`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to update the incident.'
      setWorkspaceError(message.includes('assigned guardian') && uiRoleFromApi(authUser.role) !== 'guardian'
        ? 'This is a Guardian dashboard preview, but the signed-in account is not a Guardian. Login with an assigned Guardian account to accept this incident.'
        : message)
    } finally {
      setWorkspaceBusy(false)
    }
  }

  const handleNotificationRead = async (notificationId: number) => {
    if (!authUser) return
    try {
      await markNotificationRead(notificationId)
      setNotifications((current) => current.map((notification) => notification.id === notificationId ? { ...notification, is_read: true } : notification))
      setNotificationsUnread((current) => Math.max(0, current - 1))
    } catch (error) {
      setWorkspaceError(error instanceof Error ? error.message : 'Unable to mark notification as read.')
    }
  }

  const openIncidentChat = async (incidentId: number) => {
    if (!authUser) {
      setWorkspaceError('Sign in to open incident chat.')
      return
    }
    setChatIncidentId(incidentId)
    setChatMessages([])
    setChatDraft('')
    setChatError('')
    setChatBusy(true)
    try {
      const response = await getIncidentChat(incidentId)
      setChatMessages(response.data.messages ?? [])
    } catch (error) {
      setChatError(error instanceof Error ? error.message : 'Unable to load incident chat.')
    } finally {
      setChatBusy(false)
    }
  }

  const sendChatMessage = async () => {
    if (!chatIncidentId || !chatDraft.trim()) return
    setChatBusy(true)
    setChatError('')
    try {
      const response = await sendIncidentMessage(chatIncidentId, chatDraft.trim())
      if (response.data) setChatMessages((current) => [...current, response.data])
      setChatDraft('')
    } catch (error) {
      setChatError(error instanceof Error ? error.message : 'Unable to send chat message.')
    } finally {
      setChatBusy(false)
    }
  }

  const handleSectionAction = (action: string) => {
    if (action === 'offline' || action === 'retry-queue') { navigate('Offline queue'); if (action === 'retry-queue') setWorkspaceMessage('Queue sync started. Pending actions are being retried now.'); return }
    if (action === 'profile') { navigate('My profile'); return }
    if (action === 'notifications') { navigate('Communication'); return }
    if (action === 'location') { navigate('Overview'); setWorkspaceMessage('Use the location control on the overview to share your live position.'); return }
    if (action === 'sos') { navigate('Overview'); setSosOpen(true); return }
  }

  const handleProfileSave = async (payload: Partial<ApiProfile>) => {
    if (!authUser) { setWorkspaceError('Login to update your profile.'); return }
    setWorkspaceBusy(true)
    setWorkspaceError('')
    try {
      const updated = await updateProfile(payload)
      setAuthUser((current) => ({ ...current, ...updated }))
      setWorkspaceMessage('Your profile was updated successfully.')
    } catch (error) { setWorkspaceError(error instanceof Error ? error.message : 'Unable to update your profile.') } finally { setWorkspaceBusy(false) }
  }

  if (authLoading) return <div className="auth-shell"><section className="auth-card"><div className="brand auth-brand"><div className="brand-mark">✦</div><div><strong>SafeCircle</strong><span>Community response</span></div></div><p className="auth-loading">Restoring your secure session…</p></section></div>
  if (!authUser && !previewMode) return authView === 'register' ? <RegisterScreen onRegister={handleRegister} onLogin={() => { setAuthView('login'); setAuthError('') }} initialError={authError} /> : <LoginScreen onLogin={handleLogin} onRegister={() => { setAuthView('register'); setAuthError('') }} initialError={authError} />

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">✦</div><div><strong>SafeCircle</strong><span>Community response</span></div></div>
        <div className="live-indicator"><span /> System operational</div>
        <nav className="side-nav" aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          {navItems.map((item) => <button key={item.label} className={activeNav === item.label ? 'nav-item active' : 'nav-item'} onClick={() => navigate(item.label as WorkspaceSection)}><span>{item.icon}</span>{item.label}{item.label === 'Communication' && <em>3</em>}</button>)}
          <p className="nav-label lower">Manage</p>
          <button className={activeNav === 'Settings' ? 'nav-item active' : 'nav-item'} onClick={() => navigate('Settings')}><span>⚙</span>Settings</button>
          <button className={activeNav === 'Help center' ? 'nav-item active' : 'nav-item'} onClick={() => navigate('Help center')}><span>?</span>Help center</button>
          <button className={activeNav === 'Offline queue' ? 'nav-item active' : 'nav-item'} onClick={() => navigate('Offline queue')}><span>⌁</span>Offline queue<em>{offlineCount}</em></button>
          <button className={activeNav === 'My profile' ? 'nav-item active' : 'nav-item'} onClick={() => navigate('My profile')}><span>◎</span>My profile</button>
        </nav>
        <div className="sidebar-bottom"><div className="support-card"><span>♧</span><div><strong>Community support</strong><small>Someone is always nearby.</small></div></div><div className="mini-profile"><div className={`avatar ${meta.accent}`}>{meta.avatar}</div><div><strong>{meta.label}</strong><small>Online now</small></div><span>•••</span></div></div>
      </aside>

      <main className="main-area">
        <header className="topbar"><button className="mobile-menu" aria-label="Open menu" aria-expanded={mobileMenuOpen} onClick={() => setMobileMenuOpen((open) => !open)}>☰</button><div className="breadcrumb"><span>{meta.label}</span><b>/</b><strong>{activeNav === 'Offline queue' ? 'Offline queue' : activeNav === 'My profile' ? 'My profile' : designModels.find((model) => model.id === design)?.label}</strong></div><div className="top-actions"><button className="offline-chip offline-chip-button" onClick={() => navigate('Offline queue')}><span className="offline-dot" /> Offline queue <strong>{offlineCount}</strong></button><button className="icon-button" aria-label={`${notificationsUnread} unread notifications`} onClick={() => navigate('Communication')}>♧{notificationsUnread > 0 && <i />}</button>{!authUser && previewMode && <><button className="ghost-button session-button" onClick={() => { setPreviewMode(false); setAuthView('login') }}>Login</button><button className="primary-button session-button" onClick={() => { setPreviewMode(false); setAuthView('register') }}>Register</button></>}<select value={design} onChange={(event) => chooseDesign(event.target.value as DesignModel)} aria-label="Choose interface model">{designModels.map((model) => <option key={model.id} value={model.id}>{model.short} · {model.label}</option>)}</select><select value={role} onChange={(event) => chooseRole(event.target.value as Role)} aria-label="Switch dashboard">{(Object.keys(roles) as Role[]).map((key) => <option key={key} value={key}>{roles[key].label} dashboard</option>)}</select>{authUser && <button className="ghost-button session-button" onClick={handleLogout}>Logout</button>}<button className={`avatar ${meta.accent} avatar-button`} onClick={() => navigate('My profile')} aria-label="Open my profile">{authUser?.username?.slice(0, 2).toUpperCase() ?? meta.avatar}</button></div></header>

        {mobileMenuOpen && <div className="mobile-menu-panel"><p className="nav-label">Workspace</p>{navItems.map((item) => <button key={item.label} className={activeNav === item.label ? 'mobile-menu-item active' : 'mobile-menu-item'} onClick={() => navigate(item.label as WorkspaceSection)}><span>{item.icon}</span>{item.label}</button>)}<p className="nav-label">Manage</p><button className="mobile-menu-item" onClick={() => navigate('Settings')}><span>⚙</span>Settings</button><button className="mobile-menu-item" onClick={() => navigate('Help center')}><span>?</span>Help center</button><button className="mobile-menu-item" onClick={() => navigate('Offline queue')}><span>⌁</span>Offline queue</button><button className="mobile-menu-item" onClick={() => navigate('My profile')}><span>◎</span>My profile</button></div>}

        <div className="page-content">
          <section className="welcome-row"><div><p className="eyebrow">{meta.label} · {designModels.find((model) => model.id === design)?.short}</p><h1>{meta.title}</h1><p className="subheading">{meta.subtitle}</p></div><div className="welcome-actions"><button className="outline-button" onClick={() => setMobileGalleryOpen(true)}>▣ Android previews</button><div className="model-switcher" role="tablist" aria-label="Interface design models">{designModels.map((model) => <button key={model.id} className={design === model.id ? 'selected' : ''} onClick={() => chooseDesign(model.id)}>{model.short}</button>)}</div></div></section>

          {design === 'mcc' && activeNav === 'Overview' ? <MissionControlView onOpenAI={() => navigate('AI command center')} incidents={incidents} location={apiLocation} isPreview={!authUser} /> : design === 'cockpit' && activeNav === 'AI command center' ? <AICockpitView incident={latestIncident} graph={aiGraph} twin={aiTwin} onRefresh={(scenario) => void loadAIData(scenario)} /> : activeNav !== 'Overview' && activeNav !== 'AI command center' ? <WorkspaceSectionView section={activeNav} role={role} profile={authUser} incidents={[...nearbyIncidents, ...incidents.filter((incident) => !nearbyIncidents.some((nearby) => nearby.id === incident.id))]} notifications={notifications} relationships={relationships} availability={responderAvailability} busy={workspaceBusy} onMarkAllRead={() => void handleMarkAllRead()} onToggleAvailability={() => void handleToggleAvailability()} onIncidentAction={(incidentId, action) => void handleIncidentAction(incidentId, action)} onOpenChat={(incidentId) => void openIncidentChat(incidentId)} onNotificationRead={(notificationId) => void handleNotificationRead(notificationId)} onSectionAction={handleSectionAction} onProfileSave={(payload) => void handleProfileSave(payload)} /> : role === 'resident' ? <>
            <section className="hero-grid"><article className="sos-card"><div className="sos-copy"><StatusPill tone="soft-red">Emergency access</StatusPill><h2>Need help right now?</h2><p>Alert your guardians and nearby responders with your location.</p><button className="sos-button" onClick={() => { setAlertSent(false); setSosOpen(true) }}><span className="sos-ring">SOS</span><span>Get help now</span></button></div><div className="sos-decoration"><span>⌁</span><span>⌁</span><span>⌁</span></div></article><LocationInterface key={`${apiLocation?.latitude ?? ''}:${apiLocation?.longitude ?? ''}`} onOpenCommunity={() => navigate('Community')} onSyncLocation={syncBrowserLocation} location={apiLocation} /></section>
            <section className="metrics-grid"><MetricCard icon="◉" label="Active incidents" value={String(incidents.filter((incident) => !['resolved', 'closed', 'cancelled'].includes(incident.status)).length)} trend={authUser ? 'From Django API' : 'Preview data'} tone="blue" /><MetricCard icon="♧" label="Responders nearby" value={authUser ? String(nearbyIncidents.length || 0) : '4'} trend={authUser ? 'From location service' : '+2 available now'} tone="green" /><MetricCard icon="◌" label="Unread notifications" value={String(authUser ? notificationsUnread : offlineCount)} trend={authUser ? 'Synced from API' : 'Preview queue'} tone="orange" /></section>
            <section className="content-grid"><article className="panel incident-panel"><div className="panel-heading"><div><span className="eyebrow">{authUser ? 'Live response · API' : 'Live response · preview'}</span><h2>{latestIncident?.category_name ?? 'Medical emergency'} <StatusPill tone="amber">{latestIncident?.status ?? 'Active'}</StatusPill></h2></div><button className="text-button" onClick={() => navigate('Incidents')}>View details →</button></div><div className="incident-meta"><span>⌖ {latestIncident?.location?.latitude && latestIncident?.location?.longitude ? `${latestIncident.location.latitude.toFixed(4)}, ${latestIncident.location.longitude.toFixed(4)}` : 'Tower A · Flat 101'}</span><span>◷ {latestIncident ? new Date(latestIncident.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '10:30 AM'}</span><span>♧ 3 responders</span></div><Timeline /><div className="panel-actions"><button className="primary-button" onClick={() => navigate('Communication')}>Open incident chat</button><button className="ghost-button" onClick={() => navigate('Incidents')}>See full timeline</button></div></article><article className="panel ai-panel"><div className="ai-orb"><span>✦</span></div><div className="ai-content"><span className="eyebrow">{aiCopy.label}</span><h2>{aiCopy.title}</h2><p>{aiCopy.body}</p><div className="ai-links"><button onClick={() => navigate('AI command center')}>Explore knowledge graph <span>↗</span></button><button onClick={() => navigate('AI command center')}>Open digital twin <span>↗</span></button></div></div></article></section>
          </> : <section className="command-grid"><article className="command-hero"><div><StatusPill tone={meta.accent}>Live operations</StatusPill><h2>{meta.title}</h2><p>{meta.subtitle} AI-assisted recommendations and real-time incident tracking are ready.</p></div><div className="command-number"><strong>{role === 'platform' ? '24' : role === 'subadmin' ? '12' : '02'}</strong><span>active now</span></div></article><div className="command-metrics"><MetricCard icon="◉" label="Active incidents" value={role === 'platform' ? '24' : role === 'subadmin' ? '12' : '02'} trend="View live queue" tone="blue" /><MetricCard icon="⌖" label="Responders online" value="18" trend="72% available" tone="green" /><MetricCard icon="◷" label="Avg response" value="4.2m" trend="18% faster" tone="orange" /></div><article className="panel queue-panel"><div className="panel-heading"><div><span className="eyebrow">Operations queue</span><h2>Incidents needing attention</h2></div><button className="text-button" onClick={() => navigate('Incidents')}>View all →</button></div>{['Medical emergency · Tower A', 'Accident emergency · Gate 2', 'Fall alert · Tower B'].map((item, index) => <div className="queue-row" key={item}><span className={`queue-icon q-${index}`}>{index === 0 ? '✚' : index === 1 ? '⌖' : '♧'}</span><div><strong>{item}</strong><small>{index === 0 ? 'Responder accepted · ETA 5 min' : index === 1 ? 'Awaiting assignment' : 'Guardian notified'}</small></div><StatusPill tone={index === 1 ? 'amber' : 'green'}>{index === 1 ? 'Needs action' : 'In progress'}</StatusPill></div>)}</article><article className="panel ai-command-panel"><div className="graph-preview"><div className="graph-line gl-one" /><div className="graph-line gl-two" /><span className="graph-node gn-center">AI</span><span className="graph-node gn-one">R</span><span className="graph-node gn-two">G</span><span className="graph-node gn-three">V</span></div><div><span className="eyebrow">AI command center</span><h2>Understand. Simulate. Act.</h2><p>Use the Knowledge Graph to see relationships and the Digital Twin to test the next response.</p><button className="primary-button" onClick={() => navigate('AI command center')}>Open AI workspace</button></div></article></section>}

          {(workspaceError || workspaceMessage) && <div className={workspaceError ? 'workspace-feedback error' : 'workspace-feedback'} role="status"><span>{workspaceError ? '!' : '✓'}</span><div><strong>{workspaceError ? 'Action needs attention' : 'Workspace updated'}</strong><small>{workspaceError || workspaceMessage}</small></div><button onClick={() => { setWorkspaceError(''); setWorkspaceMessage('') }} aria-label="Dismiss workspace message">×</button></div>}
          <section className="feature-strip"><div><span className="feature-icon">⌁</span><strong>Offline-ready</strong><small>Keep communicating even without a connection.</small></div><div><span className="feature-icon violet">✦</span><strong>AI-assisted</strong><small>Clear recommendations with human approval.</small></div><div><span className="feature-icon green">✓</span><strong>People-first</strong><small>Every action is built for calmer response.</small></div></section>
        </div>
        <nav className="mobile-nav">{navItems.slice(0, 4).map((item) => <button key={item.label} className={activeNav === item.label ? 'active' : ''} onClick={() => navigate(item.label as WorkspaceSection)}><span>{item.icon}</span><small>{item.label.split(' ')[0]}</small></button>)}</nav>
      </main>

      {alertSent && <div className="toast" role="status"><span>✓</span><div><strong>{authUser ? 'Emergency alert activated' : 'Emergency alert queued'}</strong><small>{selectedAlert} · {authUser ? 'responders and guardians notified' : 'will sync when connected'}</small></div><button onClick={() => setAlertSent(false)} aria-label="Dismiss alert confirmation">×</button></div>}
      {sosOpen && <div className="modal-backdrop" role="presentation" onClick={() => setSosOpen(false)}><div className="sos-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><button className="modal-close" onClick={() => setSosOpen(false)}>×</button><div className="modal-signal">SOS</div><span className="eyebrow">Emergency activation</span><h2>What happened?</h2><p>Choose the emergency type so the right responders can act quickly.</p><div className="alert-options"><button className={selectedAlert === 'Medical emergency' ? 'selected' : ''} onClick={() => setSelectedAlert('Medical emergency')}><span>✚</span> Medical emergency</button><button className={selectedAlert === 'Accident emergency' ? 'selected' : ''} onClick={() => setSelectedAlert('Accident emergency')}><span>🚗</span> Accident emergency</button><button className={selectedAlert === 'Fire emergency' ? 'selected' : ''} onClick={() => setSelectedAlert('Fire emergency')}><span>♨</span> Fire emergency</button><button className={selectedAlert === 'Fall alert' ? 'selected' : ''} onClick={() => setSelectedAlert('Fall alert')}><span>⚠</span> Fall alert</button></div>{alertError && <div className="auth-error" role="alert">{alertError}</div>}<button className="confirm-sos" onClick={() => void sendAlert()}>Send emergency alert</button><button className="cancel-action" onClick={() => setSosOpen(false)}>Cancel</button></div></div>}
      {responseTracking && <ResponseTrackingModal incident={responseTracking.incident} shared={responseTracking.shared} onClose={() => setResponseTracking(null)} />}
      {chatIncidentId !== null && <IncidentChatModal incident={incidents.find((incident) => incident.id === chatIncidentId)} messages={chatMessages} draft={chatDraft} busy={chatBusy} error={chatError} onDraftChange={setChatDraft} onSend={() => void sendChatMessage()} onClose={() => setChatIncidentId(null)} />}
      {mobileGalleryOpen && <MobilePreviewGallery onClose={() => setMobileGalleryOpen(false)} onChoose={(nextDesign) => { chooseDesign(nextDesign); setMobileGalleryOpen(false) }} />}
    </div>
  )
}

export default App
