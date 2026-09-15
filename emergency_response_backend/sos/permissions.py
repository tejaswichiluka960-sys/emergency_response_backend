from rest_framework.permissions import BasePermission


class IsResident(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'RESIDENT'
        )


from rest_framework.permissions import BasePermission

class IsResponder(BasePermission):
    def has_permission(self, request, view):

        role = request.user.userprofile.role

        print("USER:", request.user)
        print("ROLE:", role)

        return (
            request.user.is_authenticated
            and role in [
                "RESIDENT",
                "GUARDIAN",
                "SECURITY",
                "VOLUNTEER"
            ]
        )