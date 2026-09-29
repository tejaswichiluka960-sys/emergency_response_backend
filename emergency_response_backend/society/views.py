from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import (
    IsPlatformAdmin,
    IsPlatformOrSocietyAdmin,
    is_platform_admin,
    is_society_admin,
)
from .models import Flat, Society


def _assigned_society_id(user):
    return getattr(getattr(user, "userprofile", None), "society_id", None)


def _society_allowed(user, society_id):
    return is_platform_admin(user) or (is_society_admin(user) and _assigned_society_id(user) == society_id)


def _flat_society_id(flat):
    return Society.objects.filter(society_name=flat.society_name).values_list("id", flat=True).first()


class SocietyView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def post(self, request):
        society = Society.objects.create(
            society_name=request.data.get("society_name"),
            owner_name=request.data.get("owner_name"),
            incharge=request.data.get("incharge"),
            address=request.data.get("address"),
        )
        return Response({"id": society.id, "message": "Society Added Successfully"}, status=status.HTTP_201_CREATED)


class SocietyListView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def get(self, request):
        societies = Society.objects.all()
        if is_society_admin(request.user):
            society_id = _assigned_society_id(request.user)
            societies = societies.filter(id=society_id) if society_id else societies.none()
        return Response(societies.values())


class GetSocietyView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def get(self, request, pk):
        society = get_object_or_404(Society, id=pk)
        if not _society_allowed(request.user, society.id):
            return Response({"message": "Society is outside your assignment."}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            "id": society.id,
            "society_name": society.society_name,
            "owner_name": society.owner_name,
            "incharge": society.incharge,
            "address": society.address,
        })


class UpdateSocietyView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def put(self, request, pk):
        society = get_object_or_404(Society, id=pk)
        if not _society_allowed(request.user, society.id):
            return Response({"message": "Society is outside your assignment."}, status=status.HTTP_403_FORBIDDEN)
        for field in ("society_name", "owner_name", "incharge", "address"):
            if field in request.data:
                setattr(society, field, request.data[field])
        society.save()
        return Response({"message": "Society Updated Successfully"})


class DeleteSocietyView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def delete(self, request, pk):
        society = get_object_or_404(Society, id=pk)
        if not _society_allowed(request.user, society.id):
            return Response({"message": "Society is outside your assignment."}, status=status.HTTP_403_FORBIDDEN)
        society.delete()
        return Response({"message": "Society Deleted Successfully"})


class InviteUserView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def post(self, request):
        email = str(request.data.get("email") or "").strip()
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "A valid email address is required."}, status=status.HTTP_400_BAD_REQUEST)

        from_email = (
            getattr(settings, "DEFAULT_FROM_EMAIL", "")
            or getattr(settings, "EMAIL_HOST_USER", "")
        ).strip()
        if (
            not getattr(settings, "EMAIL_SMTP_CONFIGURED", False)
            and not getattr(settings, "EMAIL_BACKEND", "").endswith("console.EmailBackend")
        ):
            return Response(
                {"error": "SMTP email is not configured. Set a valid sender email, EMAIL_HOST_PASSWORD, and SMTP settings."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not from_email:
            return Response(
                {"error": "Email service is not configured. Set DEFAULT_FROM_EMAIL or EMAIL_HOST_USER."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            send_mail(
                subject="Invitation to Gated Society",
                message="You have been invited to join Gated Society.",
                from_email=from_email,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            return Response(
                {"error": "Invitation email could not be sent. Check the SMTP configuration."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if getattr(settings, "EMAIL_BACKEND", "").endswith("console.EmailBackend"):
            return Response({"message": "Invitation generated; configure SMTP to deliver it by email."})
        return Response({"message": "Invitation sent successfully"})


class FlatView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def post(self, request):
        society_name = request.data.get("society_name")
        society = Society.objects.filter(society_name=society_name).first()
        if not society:
            return Response({"message": "Society not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _society_allowed(request.user, society.id):
            return Response({"message": "Society is outside your assignment."}, status=status.HTTP_403_FORBIDDEN)
        flat = Flat.objects.create(
            flat_number=request.data.get("flat_number"),
            owner_name=request.data.get("owner_name"),
            floor=request.data.get("floor"),
            society_name=society_name,
        )
        return Response({"id": flat.id, "message": "Flat Added Successfully"}, status=status.HTTP_201_CREATED)


class FlatListView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def get(self, request):
        flats = Flat.objects.all()
        if is_society_admin(request.user):
            society_id = _assigned_society_id(request.user)
            society_name = Society.objects.filter(id=society_id).values_list("society_name", flat=True).first()
            flats = flats.filter(society_name=society_name) if society_name else flats.none()
        return Response(flats.values())


class UpdateFlatView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def put(self, request, pk):
        flat = get_object_or_404(Flat, id=pk)
        if not is_platform_admin(request.user) and _flat_society_id(flat) != _assigned_society_id(request.user):
            return Response({"message": "Flat is outside your assignment."}, status=status.HTTP_403_FORBIDDEN)
        for field in ("flat_number", "owner_name", "floor", "society_name"):
            if field in request.data:
                setattr(flat, field, request.data[field])
        flat.save()
        return Response({"message": "Flat Updated Successfully"})


class DeleteFlatView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def delete(self, request, pk):
        flat = get_object_or_404(Flat, id=pk)
        if not is_platform_admin(request.user) and _flat_society_id(flat) != _assigned_society_id(request.user):
            return Response({"message": "Flat is outside your assignment."}, status=status.HTTP_403_FORBIDDEN)
        flat.delete()
        return Response({"message": "Flat Deleted Successfully"})


class GetFlatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        flat = get_object_or_404(Flat, id=pk)
        role = getattr(getattr(request.user, "userprofile", None), "role", "").upper()
        profile = getattr(request.user, "userprofile", None)
        allowed = is_platform_admin(request.user) or (
            is_society_admin(request.user) and _flat_society_id(flat) == _assigned_society_id(request.user)
        ) or (role == "RESIDENT" and getattr(profile, "flat_id", None) == flat.id)
        if not allowed:
            return Response({"message": "Flat is outside your access scope."}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            "id": flat.id,
            "flat_number": flat.flat_number,
            "owner_name": flat.owner_name,
            "floor": flat.floor,
            "society_name": flat.society_name,
        })
