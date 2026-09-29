from users.permissions import (
    IsResident as _IsResident,
    IsResponder as _IsResponder,
    IsGuardian as _IsGuardian,
    IsResidentOrIncidentAdministrator as _IsResidentOrIncidentAdministrator,
    IsPlatformOrSocietyAdmin,
    get_role,
    PLATFORM_ADMIN_ROLES,
    RESPONDER_ROLES,
    SOCIETY_ADMIN_ROLES,
)
from rest_framework.permissions import BasePermission


class IsResident(_IsResident):
    """Only a resident may trigger and manage their own SOS settings."""


class IsResponder(_IsResponder):
    """Guardian, volunteer, and security response actions."""


class IsGuardian(_IsGuardian):
    """Guardian-specific incident actions."""


class IsResidentOrIncidentAdministrator(_IsResidentOrIncidentAdministrator):
    pass


class IsIncidentAdministrator(IsPlatformOrSocietyAdmin):
    """Administrative incident actions, scoped by the view where necessary."""


class IsGuardianResponseParticipant(BasePermission):
    """Guardians and incident administrators may acknowledge guardian alerts."""

    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {'GUARDIAN'}
    message = 'Only ADMIN, SUB_ADMIN, or GUARDIAN users may respond to a guardian escalation.'

    def has_permission(self, request, view):
        user = request.user
        if not bool(getattr(user, 'is_authenticated', False)):
            return False
        if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
            return True
        return get_role(user) in self.allowed_roles


class IsGuardianRelationshipParticipant(BasePermission):
    """Residents, guardians, and administrators may view guardian links."""

    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {'RESIDENT', 'GUARDIAN'}
    message = 'Only residents, guardians, or administrators may manage guardian relationships.'

    def has_permission(self, request, view):
        user = request.user
        return bool(getattr(user, 'is_authenticated', False)) and (
            getattr(user, 'is_staff', False)
            or getattr(user, 'is_superuser', False)
            or get_role(user) in self.allowed_roles
        )


class IsGuardianWorkflowManager(BasePermission):
    """Residents and administrators may start guardian notification."""

    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {'RESIDENT'}

    def has_permission(self, request, view):
        user = request.user
        return bool(getattr(user, 'is_authenticated', False)) and (
            getattr(user, 'is_staff', False)
            or getattr(user, 'is_superuser', False)
            or get_role(user) in self.allowed_roles
        )


class IsSOSResponder(BasePermission):
    """Roles that may accept/reject/respond to an SOS; ADMIN is excluded."""

    allowed_roles = SOCIETY_ADMIN_ROLES | RESPONDER_ROLES

    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_authenticated", False)) and get_role(request.user) in self.allowed_roles


class IsNonResident(BasePermission):
    """Any authenticated role except RESIDENT."""

    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_authenticated", False)) and get_role(request.user) != "RESIDENT"
