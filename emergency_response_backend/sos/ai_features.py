from django.utils import timezone

from users.models import UserProfile


def _user_node(user, node_type='USER'):
    profile = getattr(user, 'userprofile', None)
    return {
        'id': f'user:{user.id}',
        'type': node_type,
        'label': user.get_username(),
        'properties': {
            'user_id': user.id,
            'role': getattr(profile, 'role', None),
            'society_id': getattr(profile, 'society_id', None),
            'is_available': getattr(profile, 'is_available', None),
            'latitude': float(profile.latitude) if profile and profile.latitude is not None else None,
            'longitude': float(profile.longitude) if profile and profile.longitude is not None else None,
        },
    }


def build_knowledge_graph(incident):
    """Build an explainable graph from existing incident relationships."""
    nodes = {}
    edges = []
    edge_keys = set()

    def add_node(node):
        nodes.setdefault(node['id'], node)

    def add_edge(source, target, relation, properties=None):
        key = (source, target, relation)
        if key not in edge_keys:
            edge_keys.add(key)
            edges.append({
                'source': source,
                'target': target,
                'relation': relation,
                'properties': properties or {},
            })

    incident_id = f'incident:{incident.id}'
    add_node({
        'id': incident_id,
        'type': 'INCIDENT',
        'label': f'Incident #{incident.id}',
        'properties': {
            'status': incident.status,
            'category': incident.category.code,
            'category_name': incident.category.name,
            'created_at': incident.created_at.isoformat(),
        },
    })
    add_node(_user_node(incident.user, 'RESIDENT'))
    add_edge(incident_id, f'user:{incident.user_id}', 'REPORTED_BY')

    if incident.latitude is not None and incident.longitude is not None:
        location_id = f'location:incident:{incident.id}'
        add_node({
            'id': location_id,
            'type': 'LOCATION',
            'label': f'Incident location #{incident.id}',
            'properties': {
                'latitude': float(incident.latitude),
                'longitude': float(incident.longitude),
                'accuracy': incident.accuracy,
            },
        })
        add_edge(incident_id, location_id, 'OCCURRED_AT')

    for relationship in incident.user.guardian_relationships.filter(is_active=True).select_related('guardian'):
        add_node(_user_node(relationship.guardian, 'GUARDIAN'))
        add_edge(
            f'user:{relationship.resident_id}',
            f'user:{relationship.guardian_id}',
            'GUARDED_BY',
            {'relationship_type': relationship.relationship_type},
        )

    for response in incident.responses.select_related('responder'):
        add_node(_user_node(response.responder, 'RESPONDER'))
        add_edge(
            f'user:{response.responder_id}',
            incident_id,
            'RESPONDED_TO',
            {'response_message': response.response_message},
        )

    for message in incident.chat_messages.select_related('sender'):
        add_node(_user_node(message.sender, 'PARTICIPANT'))
        add_edge(
            f'user:{message.sender_id}',
            incident_id,
            'MESSAGED',
            {'message_type': message.message_type, 'created_at': message.created_at.isoformat()},
        )

    for history in incident.history.select_related('actor'):
        if history.actor_id:
            add_node(_user_node(history.actor, 'PARTICIPANT'))
            add_edge(
                f'user:{history.actor_id}',
                incident_id,
                'ACTED_ON',
                {'event': history.event, 'created_at': history.created_at.isoformat()},
            )

    owner_society = getattr(getattr(incident.user, 'userprofile', None), 'society_id', None)
    available_responders = UserProfile.objects.filter(
        role__in=['VOLUNTEER', 'SECURITY'],
        is_available=True,
    ).select_related('user')
    if owner_society is not None:
        available_responders = available_responders.filter(society_id=owner_society)
    for profile in available_responders:
        add_node(_user_node(profile.user, 'AVAILABLE_RESPONDER'))
        add_edge(f'user:{profile.user_id}', incident_id, 'AVAILABLE_FOR', {'same_society': True})

    recommendations = []
    responder_count = sum(1 for node in nodes.values() if node['type'] == 'AVAILABLE_RESPONDER')
    if responder_count:
        recommendations.append({
            'action': 'ASSIGN_NEAREST_AVAILABLE_RESPONDER',
            'reason': f'{responder_count} available responder(s) are connected to this incident.',
        })
    else:
        recommendations.append({
            'action': 'ESCALATE_GUARDIAN_CHAIN',
            'reason': 'No available responder is currently connected to this incident.',
        })
    if incident.status in {'OPEN', 'NOTIFICATIONS_SENT', 'ESCALATED'}:
        recommendations.append({
            'action': 'MONITOR_RESPONSE_TIMEOUT',
            'reason': 'The incident is still awaiting a completed response.',
        })

    return {
        'graph_version': '1.0',
        'generated_at': timezone.now().isoformat(),
        'nodes': list(nodes.values()),
        'edges': edges,
        'recommendations': recommendations,
        'summary': {
            'node_count': len(nodes),
            'edge_count': len(edges),
            'available_responder_count': responder_count,
            'explainability': 'Built from stored users, relationships, responses, messages, and incident history.',
        },
    }


def build_digital_twin(incident):
    """Return a live, explainable digital representation of an incident."""
    now = timezone.now()
    elapsed_seconds = max(0, int((now - incident.created_at).total_seconds()))
    status = incident.status
    if status in {'OPEN', 'NOTIFICATIONS_SENT'}:
        risk_level = 'HIGH' if elapsed_seconds > 120 else 'MEDIUM'
        next_actions = ['Monitor guardian and responder acknowledgement.', 'Escalate if the response timeout expires.']
        predicted_next_status = 'ESCALATED' if elapsed_seconds > 120 else 'ACTIVE_RESPONSE'
    elif status == 'ESCALATED':
        risk_level = 'HIGH'
        next_actions = ['Assign an available responder.', 'Keep guardians and responders updated.']
        predicted_next_status = 'ACTIVE_RESPONSE'
    elif status in {'RESPONSE_RECEIVED', 'ACTIVE_RESPONSE'}:
        risk_level = 'MEDIUM'
        next_actions = ['Track responder arrival.', 'Collect assistance updates and evidence.']
        predicted_next_status = 'RESOLVED'
    elif status == 'RESOLVED':
        risk_level = 'LOW'
        next_actions = ['Capture the resolution note.', 'Close the incident with documentation.']
        predicted_next_status = 'CLOSED'
    else:
        risk_level = 'LOW'
        next_actions = ['Review the incident history.']
        predicted_next_status = status

    responders = [
        {
            'responder_id': response.responder_id,
            'response_message': response.response_message,
            'created_at': response.created_at.isoformat(),
        }
        for response in incident.responses.select_related('responder')
    ]
    timeline = [
        {
            'event': history.event,
            'message': history.message,
            'created_at': history.created_at.isoformat(),
            'actor_id': history.actor_id,
        }
        for history in incident.history.select_related('actor')
    ]
    return {
        'twin_version': '1.0',
        'generated_at': now.isoformat(),
        'incident': {
            'id': incident.id,
            'status': status,
            'category': incident.category.code,
            'category_name': incident.category.name,
            'latitude': float(incident.latitude) if incident.latitude is not None else None,
            'longitude': float(incident.longitude) if incident.longitude is not None else None,
            'elapsed_seconds': elapsed_seconds,
        },
        'response_state': {
            'risk_level': risk_level,
            'predicted_next_status': predicted_next_status,
            'next_actions': next_actions,
            'responder_count': len(responders),
            'message_count': incident.chat_messages.count(),
            'escalation_count': incident.guardian_escalations.count(),
        },
        'responders': responders,
        'timeline': timeline,
        'safety_note': 'This is an explainable planning aid. Authorized humans approve emergency actions.',
    }


def simulate_digital_twin(incident, scenario):
    scenario = str(scenario or 'NO_RESPONSE').strip().upper().replace('-', '_').replace(' ', '_')
    base = build_digital_twin(incident)
    scenarios = {
        'NO_RESPONSE': {
            'description': 'No responder accepts within the response window.',
            'projected_status_path': [incident.status, 'ESCALATED', 'ACTIVE_RESPONSE'],
            'recommended_action': 'Notify the next escalation level and assign the nearest available responder.',
        },
        'RESPONDER_ACCEPTS': {
            'description': 'A responder accepts and begins assistance.',
            'projected_status_path': [incident.status, 'ACTIVE_RESPONSE'],
            'recommended_action': 'Share location and keep the incident chat updated.',
        },
        'ASSISTANCE_COMPLETED': {
            'description': 'Assistance is completed and documented.',
            'projected_status_path': [incident.status, 'RESOLVED', 'CLOSED'],
            'recommended_action': 'Record the resolution and closure documentation.',
        },
    }
    selected = scenarios.get(scenario)
    if not selected:
        selected = {
            'description': 'Unknown scenario.',
            'projected_status_path': [incident.status],
            'recommended_action': 'Choose NO_RESPONSE, RESPONDER_ACCEPTS, or ASSISTANCE_COMPLETED.',
        }
    base['simulation'] = {'scenario': scenario, **selected}
    return base
