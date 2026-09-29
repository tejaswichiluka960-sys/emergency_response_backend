from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import AlertRoute
from .serializers import AlertRouteSerializer
from sos.models import GuardianRelationship, SOSIncident, SOSResponse
from users.permissions import (
    IsPlatformOrSocietyAdmin,
    IsResponder,
    PLATFORM_ADMIN_ROLES,
    SOCIETY_ADMIN_ROLES,
    RESPONDER_ROLES,
    get_role,
    is_platform_admin,
    is_society_admin,
)


class IsAlertDeliveryParticipant(BasePermission):
    """Roles allowed to update delivery records for routed alerts."""

    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {'RESIDENT', 'GUARDIAN', 'VOLUNTEER', 'SECURITY'}

    def has_permission(self, request, view):
        return bool(getattr(request.user, 'is_authenticated', False)) and get_role(request.user) in self.allowed_roles


class IsAlertResponseParticipant(BasePermission):
    """Roles allowed to update alert response status; ADMIN remains excluded."""

    allowed_roles = RESPONDER_ROLES | {'RESIDENT'}

    def has_permission(self, request, view):
        return bool(getattr(request.user, 'is_authenticated', False)) and get_role(request.user) in self.allowed_roles


def _same_society(user, incident):
    actor_society = getattr(getattr(user, 'userprofile', None), 'society_id', None)
    owner_society = getattr(getattr(incident.user, 'userprofile', None), 'society_id', None)
    return actor_society is not None and actor_society == owner_society


def _can_access_incident(user, incident):
    if is_platform_admin(user) or incident.user_id == user.id:
        return True
    if is_society_admin(user) or get_role(user) in {'VOLUNTEER', 'SECURITY'}:
        return _same_society(user, incident)
    if get_role(user) == 'GUARDIAN':
        return GuardianRelationship.objects.filter(
            resident=incident.user, guardian=user, is_active=True
        ).exists()
    return SOSResponse.objects.filter(incident=incident, responder=user).exists()


def _accessible_routes(user, routes):
    if is_platform_admin(user):
        return routes
    accessible_ids = [
        incident.id for incident in SOSIncident.objects.all()
        if _can_access_incident(user, incident)
    ]
    return routes.filter(incident_id__in=accessible_ids)


# ============================================================
# 1. ALERT ROUTING
# ============================================================

class AlertRoutingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        incident_id = request.data.get("incident_id")
        emergency_type = request.data.get("emergency_type")

        if not incident_id:
            return Response(
                {
                    "success": False,
                    "error": "incident_id is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            incident = SOSIncident.objects.get(id=incident_id)
        except SOSIncident.DoesNotExist:
            return Response({'success': False, 'error': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _can_access_incident(request.user, incident):
            return Response({'success': False, 'error': 'You do not have access to this incident'}, status=status.HTTP_403_FORBIDDEN)

        if not emergency_type:
            return Response(
                {
                    "success": False,
                    "error": "emergency_type is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        emergency_type = emergency_type.lower()

        # ----------------------------------------------------
        # Decide who receives the alert
        # ----------------------------------------------------

        if emergency_type == "medical":

            recipients = [
                ("GUARDIAN", 1, 1),
                ("SECURITY", 2, 2),
                ("VOLUNTEER", 3, 3),
                ("VOLUNTEER", 4, 4),
            ]

        elif emergency_type == "fire":

            recipients = [
                ("SECURITY", 2, 1),
                ("GUARDIAN", 1, 2),
                ("VOLUNTEER", 3, 3),
                ("COMMUNITY", 4, 4),
            ]

        elif emergency_type == "security":

            recipients = [
                ("SECURITY", 2, 1),
                ("GUARDIAN", 1, 2),
            ]

        else:

            recipients = [
                ("GUARDIAN", 1, 1),
                ("SECURITY", 2, 2),
                ("VOLUNTEER", 3, 3),
            ]

        routes = []

        # ----------------------------------------------------
        # Create AlertRoute records
        # ----------------------------------------------------

        for recipient_type, recipient_id, priority in recipients:

            route = AlertRoute.objects.create(

                incident_id=incident_id,

                recipient_id=recipient_id,

                recipient_type=recipient_type,

                priority=priority,

                # IMPORTANT:
                # Model uses delivery_status, NOT status
                delivery_status="PENDING",

                response_status="NO_RESPONSE"
            )

            routes.append(route)

        serializer = AlertRouteSerializer(
            routes,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": "SOS alert routed successfully",
                "incident_id": incident_id,
                "emergency_type": emergency_type,
                "recipients": serializer.data
            },
            status=status.HTTP_201_CREATED
        )


# ============================================================
# 2. GET ALERT ROUTES
# ============================================================

class AlertRoutingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        incident_id = request.query_params.get("incident_id")

        routes = AlertRoute.objects.all()
        if incident_id:
            routes = routes.filter(incident_id=incident_id)
        routes = _accessible_routes(request.user, routes)

        serializer = AlertRouteSerializer(
            routes,
            many=True
        )

        return Response(
            {
                "success": True,
                "count": routes.count(),
                "routes": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# 3. ALERT MONITORING
# ============================================================

class AlertMonitoringView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        incident_id = request.query_params.get("incident_id")

        if not incident_id:

            return Response(
                {
                    "success": False,
                    "error": "incident_id is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            incident = SOSIncident.objects.get(id=incident_id)
        except SOSIncident.DoesNotExist:
            return Response({'success': False, 'error': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)
        routes = AlertRoute.objects.filter(
            incident_id=incident_id
        )

        if not routes.exists():

            return Response(
                {
                    "success": False,
                    "error": "No alert routes found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ----------------------------------------------------
        # Delivery Tracking
        # ----------------------------------------------------

        delivered = routes.filter(
            delivery_status="DELIVERED"
        ).count()

        failed = routes.filter(
            delivery_status="FAILED"
        ).count()

        pending = routes.filter(
            delivery_status="PENDING"
        ).count()

        # ----------------------------------------------------
        # Response Tracking
        # ----------------------------------------------------

        responded = routes.filter(
            response_status__in=[
                "RESPONDED",
                "RESPONDING",
                "RESOLVED"
            ]
        ).count()

        # ----------------------------------------------------
        # Overall Alert Status
        # ----------------------------------------------------

        if responded > 0:

            alert_status = "RESPONSE_RECEIVED"

        elif delivered > 0 or failed > 0:

            alert_status = "NOTIFICATIONS_SENT"

        else:

            alert_status = "OPEN"

        serializer = AlertRouteSerializer(
            routes,
            many=True
        )

        return Response(
            {
                "success": True,

                "incident_id": incident_id,

                "alert_status": alert_status,

                "notification_delivery": {

                    "delivered": delivered,

                    "failed": failed,

                    "pending": pending
                },

                "response_monitoring": {

                    "someone_responded": responded > 0,

                    "responses_received": responded
                },

                "routes": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# 4. UPDATE DELIVERY STATUS
# ============================================================

class UpdateDeliveryStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAlertDeliveryParticipant]

    def patch(self, request, route_id):

        try:

            route = AlertRoute.objects.get(
                id=route_id
            )

        except AlertRoute.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "error": "Alert route not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Volunteers may update only volunteer delivery routes. Other roles
        # retain the broader delivery-management access already granted.
        if get_role(request.user) == 'VOLUNTEER' and route.recipient_type != 'VOLUNTEER':
            return Response(
                {
                    "success": False,
                    "error": "Volunteers may update only volunteer delivery routes"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        raw_delivery_status = request.data.get("delivery_status")
        delivery_status = (
            str(raw_delivery_status).strip().upper()
            if raw_delivery_status is not None
            else None
        )

        if delivery_status not in [
            "PENDING",
            "DELIVERED",
            "FAILED"
        ]:

            return Response(
                {
                    "success": False,
                    "error": "Invalid delivery status. Use PENDING, DELIVERED, or FAILED."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        route.delivery_status = delivery_status

        route.save()

        serializer = AlertRouteSerializer(
            route
        )

        return Response(
            {
                "success": True,
                "message": "Delivery status updated",
                "route": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# 5. UPDATE RESPONSE STATUS
# ============================================================

class UpdateResponseStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAlertResponseParticipant]

    def patch(self, request, route_id):

        try:

            route = AlertRoute.objects.get(
                id=route_id
            )

        except AlertRoute.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "error": "Alert route not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        response_status = request.data.get(
            "response_status"
        )

        if response_status not in [
            "NO_RESPONSE",
            "RESPONDED",
            "RESPONDING",
            "RESOLVED"
        ]:

            return Response(
                {
                    "success": False,
                    "error": "Invalid response status"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        route.response_status = response_status

        route.save()

        serializer = AlertRouteSerializer(
            route
        )

        return Response(
            {
                "success": True,
                "message": "Response status updated",
                "route": serializer.data
            },
            status=status.HTTP_200_OK
        )
