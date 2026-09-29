export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export type ApiProfile = {
  id: number
  username: string
  email: string
  phone?: string | null
  name?: string | null
  location?: string | null
  society_name?: string | null
  flat_number?: string | null
  role: string
  permissions?: { role: string; permission_level: string; capabilities: string[] }
  society_id?: number | null
  flat_id?: number | null
}

export type ApiIncident = {
  id: number
  incident_id: string
  category: string
  category_name: string
  message?: string | null
  location?: { latitude?: number | null; longitude?: number | null; accuracy?: number | null }
  latitude?: number | null
  longitude?: number | null
  accuracy?: number | null
  status: string
  created_at: string
  updated_at: string
}

export type ApiNotification = {
  id: number
  title: string
  message: string
  notification_type?: string
  is_read: boolean
  created_at: string
}

export type ApiLocation = {
  latitude?: number | null
  longitude?: number | null
  accuracy?: number | null
  location_updated_at?: string | null
}

export type ApiCategory = { id: number; code: string; name: string; is_active: boolean }
export type ApiGuardianRelationship = { id: number; resident_id: number; guardian_id: number; relationship_type: string; is_active: boolean; created_at: string }
export type ApiSharedParticipant = { id: number; username: string; role: 'guardian' | 'volunteer' | 'security' | string; is_primary_guardian: boolean; accepted: boolean; accepted_eta_minutes?: number | null; response_message?: string | null; latitude?: number | null; longitude?: number | null; accuracy?: number | null; distance_km?: number | null; estimated_arrival_minutes?: number | null; route_url?: string | null; location_available: boolean }
export type ApiSharedLocation = { incident_id: number; incident_status: string; resident: { id: number; username: string }; location?: { latitude?: number | null; longitude?: number | null; accuracy?: number | null; google_maps_url?: string | null } | null; participants: ApiSharedParticipant[]; shared_with_count: number; accepted_count: number; updated_at: string }
export type ApiChatMessage = { id: number; incident: number; sender: number; sender_name: string; message_type: 'TEXT' | 'VOICE'; message: string; audio_url?: string | null; download_url?: string | null; duration_seconds?: number | null; created_at: string }
export type ApiAIData = Record<string, unknown>
type ApiError = { message?: string; detail?: string; errors?: Record<string, string[] | string> }

const readJson = async (response: Response) => response.json().catch(() => ({})) as Promise<ApiError>

function saveTokens(access: string, refresh?: string) {
  localStorage.setItem('access_token', access)
  if (refresh) localStorage.setItem('refresh_token', refresh)
}

export function clearSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return null
  const response = await fetch(`${API_BASE_URL}/v1/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!response.ok) return null
  const data = await response.json() as { access?: string }
  if (!data.access) return null
  saveTokens(data.access)
  return data.access
}

export async function apiRequest<T>(path: string, options: RequestInit = {}, canRefresh = true): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = localStorage.getItem('access_token')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  if (response.status === 401 && canRefresh && await refreshAccessToken()) return apiRequest<T>(path, options, false)
  if (!response.ok) {
    const error = await readJson(response)
    const fieldErrors = error.errors ? Object.values(error.errors).flat().join(' ') : ''
    throw new Error(error.message ?? error.detail ?? fieldErrors ?? `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function login(username: string, password: string) {
  const data = await apiRequest<{ access: string; refresh: string }>('/v1/auth/login/', {
    method: 'POST', body: JSON.stringify({ username, password }),
  }, false)
  saveTokens(data.access, data.refresh)
  return getMe()
}

export type RegisterPayload = {
  name: string
  location: string
  society_name: string
  flat_number: string
  phone: string
  email: string
  username: string
  password: string
  role?: 'RESIDENT'
}

export const register = (payload: RegisterPayload) => apiRequest<{ success: boolean; message: string }>('/v1/auth/register/', {
  method: 'POST',
  body: JSON.stringify({ ...payload, role: payload.role ?? 'RESIDENT' }),
}, false)

export const updateProfile = (payload: Partial<Pick<ApiProfile, 'username' | 'email' | 'phone' | 'name' | 'location' | 'society_name' | 'flat_number'>>) => apiRequest<ApiProfile>('/v1/auth/profile/update/', {
  method: 'PUT',
  body: JSON.stringify(payload),
})

export const logout = clearSession
export const hasSession = () => Boolean(localStorage.getItem('access_token'))
export const getMe = () => apiRequest<ApiProfile>('/v1/auth/me/')

export async function getIncidents() {
  const response = await apiRequest<{ data: ApiIncident[] }>('/v1/incidents/my/')
  return response.data ?? []
}

export async function createSOSIncident(payload: { category: string; message?: string; latitude?: number | null; longitude?: number | null; accuracy?: number | null }) {
  return apiRequest<{ data: ApiIncident; incident?: ApiIncident }>('/v1/incidents/', {
    method: 'POST', body: JSON.stringify(payload),
  })
}

export async function getNotifications() {
  const response = await apiRequest<{ data: { unread_count: number; results: ApiNotification[] } }>('/v1/notifications/')
  return response.data ?? { unread_count: 0, results: [] }
}

export const markAllNotificationsRead = () => apiRequest('/v1/notifications/read-all/', { method: 'PATCH' })
export const markNotificationRead = (notificationId: number) => apiRequest(`/v1/notifications/${notificationId}/read/`, { method: 'PATCH' })
export const getCategories = async () => (await apiRequest<{ data: ApiCategory[] }>('/v1/emergency-categories/')).data ?? []
export const getLocation = () => apiRequest<ApiLocation>('/v1/me/location/get/')
export const updateLocation = (location: ApiLocation) => apiRequest('/v1/me/location/', { method: 'POST', body: JSON.stringify(location) })
export const getGuardianRelationships = () => apiRequest<{ data: ApiGuardianRelationship[] }>('/v1/guardians/relationships/')
export const getIncidentSharedLocation = (incidentId: number) => apiRequest<{ data: ApiSharedLocation }>(`/v1/incidents/${incidentId}/shared-location/`)
export const getResponderAvailability = () => apiRequest<{ data: { is_available: boolean } }>('/v1/responders/me/availability/')
export const setResponderAvailability = (is_available: boolean) => apiRequest('/v1/responders/me/availability/', { method: 'PATCH', body: JSON.stringify({ is_available }) })
export const getNearbyIncidents = (location?: ApiLocation | null) => {
  const query = new URLSearchParams()
  if (location?.latitude != null) query.set('latitude', String(location.latitude))
  if (location?.longitude != null) query.set('longitude', String(location.longitude))
  query.set('radius_km', '10')
  return apiRequest<{ data: ApiIncident[]; count: number }>(`/v1/responders/incidents/nearby/?${query.toString()}`)
}
export const getKnowledgeGraph = (incidentId: number) => apiRequest<{ data: ApiAIData }>(`/v1/incidents/${incidentId}/ai/knowledge-graph/`)
export const getDigitalTwin = (incidentId: number, scenario?: string) => scenario
  ? apiRequest<{ data: ApiAIData }>(`/v1/incidents/${incidentId}/ai/digital-twin/`, { method: 'POST', body: JSON.stringify({ scenario }) })
  : apiRequest<{ data: ApiAIData }>(`/v1/incidents/${incidentId}/ai/digital-twin/`)
const dashboardRoleHeaders = (dashboardRole?: string) => dashboardRole
  ? { 'X-SafeCircle-Dashboard-Role': dashboardRole.toUpperCase() }
  : undefined

export const acceptIncident = (incidentId: number, estimatedArrivalMinutes?: number, dashboardRole?: string) => apiRequest<{ data: { status: string } }>(`/v1/incidents/${incidentId}/accept/`, { method: 'POST', headers: dashboardRoleHeaders(dashboardRole), body: JSON.stringify(estimatedArrivalMinutes == null ? {} : { estimated_arrival_minutes: estimatedArrivalMinutes }) })
export const respondToGuardianIncident = (incidentId: number, estimatedArrivalMinutes?: number, dashboardRole?: string) => apiRequest<{ data: { status: string; estimated_arrival_minutes?: number | null } }>(`/v1/incidents/${incidentId}/guardian/respond/`, { method: 'POST', headers: dashboardRoleHeaders(dashboardRole), body: JSON.stringify(estimatedArrivalMinutes == null ? {} : { estimated_arrival_minutes: estimatedArrivalMinutes }) })
export const rejectIncident = (incidentId: number, reason?: string, dashboardRole?: string) => apiRequest(`/v1/incidents/${incidentId}/reject/`, { method: 'POST', headers: dashboardRoleHeaders(dashboardRole), body: JSON.stringify({ reason: reason ?? 'Not available' }) })
export const resolveIncident = (incidentId: number, resolution?: string, dashboardRole?: string) => apiRequest<{ data: ApiIncident }>(`/v1/incidents/${incidentId}/resolve/`, { method: 'POST', headers: dashboardRoleHeaders(dashboardRole), body: JSON.stringify({ resolution: resolution ?? 'Resolved from SafeCircle workspace.' }) })
export const cancelIncident = (incidentId: number, reason?: string) => apiRequest(`/v1/incidents/${incidentId}/cancel/`, { method: 'POST', body: JSON.stringify({ reason: reason ?? 'Cancelled by resident.' }) })
export const getIncidentChat = (incidentId: number) => apiRequest<{ data: { messages: ApiChatMessage[] } }>(`/v1/incidents/${incidentId}/chat/`)
export const sendIncidentMessage = (incidentId: number, message: string) => apiRequest<{ data: ApiChatMessage }>(`/v1/incidents/${incidentId}/chat/messages/`, { method: 'POST', body: JSON.stringify({ message_type: 'TEXT', message }) })

export async function searchOpenStreetMap(query: string) {
  const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${encodeURIComponent(query)}`, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Location search is temporarily unavailable.')
  const results = await response.json() as Array<{ lat: string; lon: string; display_name: string }>
  const result = results[0]
  if (!result) throw new Error('No matching location found.')
  return { latitude: Number(result.lat), longitude: Number(result.lon), label: result.display_name }
}
