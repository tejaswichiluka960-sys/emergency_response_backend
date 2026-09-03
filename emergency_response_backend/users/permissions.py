from rest_framework.permissions import BasePermission
from .models import UserProfile

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role == "ADMIN"


class IsSubAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role == "SUB_ADMIN"


class IsSecurityRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role == "SECURITY"


class IsResidentRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role == "RESIDENT"
    
class IsAdminOrSubAdmin(BasePermission):
    def has_permission(self, request, view):
        role = request.user.userprofile.role
        return role in ["ADMIN", "SUB_ADMIN"] 
    
class IsSecurity(BasePermission):
    def has_permission(self, request, view):

        role = request.user.userprofile.role

        if role == "SECURITY":
            return request.method in ["GET", "PUT", "PATCH"]

        return False
    
from rest_framework.permissions import BasePermission

class IsSubAdminOrSecurity(BasePermission):
    def has_permission(self, request, view):
        role = request.user.userprofile.role
        return role in ["SUB_ADMIN", "SECURITY"] 
    
