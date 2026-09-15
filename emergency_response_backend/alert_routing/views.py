from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import AlertRoute
from .serializers import AlertRouteSerializer


# ============================================================
# 1. ALERT ROUTING
# ============================================================

class AlertRoutingView(APIView):

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

    def get(self, request):

        incident_id = request.query_params.get("incident_id")

        if incident_id:

            routes = AlertRoute.objects.filter(
                incident_id=incident_id
            )

        else:

            routes = AlertRoute.objects.all()

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

        delivery_status = request.data.get(
            "delivery_status"
        )

        if delivery_status not in [
            "PENDING",
            "DELIVERED",
            "FAILED"
        ]:

            return Response(
                {
                    "success": False,
                    "error": "Invalid delivery status"
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