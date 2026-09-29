from rest_framework.permissions import BasePermission


# Public API role names are ADMIN/SUB_ADMIN. Keep the older long names as
# accepted aliases so existing tokens and registrations remain compatible.
PLATFORM_ADMIN_ROLES = {"ADMIN", "PLATFORM_ADMIN"}
SOCIETY_ADMIN_ROLES = {"SUB_ADMIN", "SOCIETY_ADMIN"}
RESPONDER_ROLES = {"GUARDIAN", "VOLUNTEER", "SECURITY"}
SUPPORTED_ROLES = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {"RESIDENT"} | RESPONDER_ROLES

# Canonical role capabilities exposed to clients and used as the single
# source of truth for the role matrix documented in Postman.
ROLE_PERMISSIONS = {
    "ADMIN": {
        "permission_level": "FULL_SYSTEM_ACCESS",
        "capabilities": [
            "manage_all_societies",
            "manage_all_users",
            "manage_system_configuration",
            "manage_emergency_categories",
            "view_all_incidents",
            "view_reports_and_analytics",
            "view_audit_logs",
        ],
    },
    "SUB_ADMIN": {
        "permission_level": "SOCIETY_LEVEL_ACCESS",
        "capabilities": [
            "manage_assigned_society",
            "manage_blocks_and_towers",
            "manage_flats",
            "manage_residents",
            "manage_guardians",
            "manage_security_personnel",
            "view_society_incidents",
            "view_society_reports",
            "configure_society_emergency_settings",
        ],
    },
    "RESIDENT": {
        "permission_level": "OWN_DATA_AND_OWN_INCIDENT_ACCESS",
        "capabilities": [
            "manage_own_profile",
            "manage_own_guardians",
            "manage_own_emergency_contacts",
            "configure_sos_settings",
            "trigger_sos",
            "view_own_incidents",
            "track_responders",
            "use_emergency_chat",
            "cancel_or_resolve_own_incident_when_permitted",
        ],
    },
    "GUARDIAN": {
        "permission_level": "ASSIGNED_INCIDENT_ACCESS",
        "capabilities": [
            "receive_emergency_alerts",
            "view_assigned_incidents",
            "accept_emergency_requests",
            "track_incidents",
            "use_emergency_chat",
            "provide_response_updates",
        ],
    },
    "VOLUNTEER": {
        "permission_level": "AVAILABLE_NEARBY_INCIDENT_ACCESS",
        "capabilities": [
            "manage_availability",
            "share_current_location",
            "receive_nearby_emergency_alerts",
            "view_nearby_incidents",
            "accept_or_reject_incidents",
            "provide_response_updates",
            "use_emergency_chat",
        ],
    },
    "SECURITY": {
        "permission_level": "SOCIETY_INCIDENT_ACCESS",
        "capabilities": [
            "receive_society_emergency_alerts",
            "view_active_society_incidents",
            "accept_emergency_incidents",
            "update_response_status",
            "coordinate_assistance",
            "use_emergency_chat",
        ],
    },
}


def get_role(user):
    # Normalize legacy values such as ``SUB ADMIN`` and ``SUB-ADMIN`` so
    # existing accounts receive the same permissions as ``SUB_ADMIN``.
    raw_role = str(getattr(getattr(user, "userprofile", None), "role", "")).strip().upper()
    return "_".join(part for part in raw_role.replace("-", "_").replace(" ", "_").split("_") if part)


def canonical_role(user):
    role = get_role(user)
    if role in PLATFORM_ADMIN_ROLES:
        return "ADMIN"
    if role in SOCIETY_ADMIN_ROLES:
        return "SUB_ADMIN"
    return role


def get_role_permissions(user):
    role = canonical_role(user)
    permissions = ROLE_PERMISSIONS.get(role, {"permission_level": "NO_ACCESS", "capabilities": []})
    return {
        "role": role,
        "permission_level": permissions["permission_level"],
        "capabilities": list(permissions["capabilities"]),
    }


def is_platform_admin(user):
    return get_role(user) in PLATFORM_ADMIN_ROLES


def is_society_admin(user):
    return get_role(user) in SOCIETY_ADMIN_ROLES


def is_admin(user):
    return is_platform_admin(user) or is_society_admin(user)


def _role(request):
    return get_role(getattr(request, "user", None))


class RolePermission(BasePermission):
    allowed_roles = set()

    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_authenticated", False)) and _role(request) in self.allowed_roles


class IsPlatformAdmin(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES


class IsPlatformOrSocietyAdmin(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES


class IsResident(RolePermission):
    allowed_roles = {"RESIDENT"}


class IsResidentOrPlatformAdmin(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES | {"RESIDENT"}


class IsGuardian(RolePermission):
    allowed_roles = {"GUARDIAN"}


class IsVolunteer(RolePermission):
    allowed_roles = {"VOLUNTEER"}


class IsSecurity(RolePermission):
    allowed_roles = {"SECURITY"}


class IsResponder(RolePermission):
    allowed_roles = RESPONDER_ROLES


class IsLocationParticipant(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {"RESIDENT"} | RESPONDER_ROLES


class IsResidentOrIncidentAdministrator(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {"RESIDENT"}


# Backwards-compatible names used by the existing views.
class IsAdminRole(IsPlatformAdmin):
    pass


class IsSubAdminRole(IsPlatformOrSocietyAdmin):
    pass


class IsSecurityRole(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES | {"SECURITY"}


class IsResidentRole(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES | {"RESIDENT"}


class IsAdminOrSubAdmin(IsPlatformOrSocietyAdmin):
    pass


class IsSubAdminOrSecurity(RolePermission):
    allowed_roles = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES | {"SECURITY"}
