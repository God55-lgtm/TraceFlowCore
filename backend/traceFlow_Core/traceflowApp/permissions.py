from rest_framework.permissions import BasePermission

class IsAuditor(BasePermission):
    """Permite acceso solo a usuarios en el grupo 'auditor'."""
    def has_permission(self, request, view):
        return request.user.groups.filter(name='auditor').exists()

class IsAdmin(BasePermission):
    """Permite acceso solo a usuarios en el grupo 'admin'."""
    def has_permission(self, request, view):
        return request.user.groups.filter(name='admin').exists()

class IsAuditorOrAdmin(BasePermission):
    """Permite acceso a usuarios en grupo 'auditor' o 'admin'."""
    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=['auditor', 'admin']).exists()

class IsDeveloper(BasePermission):
    """Permite acceso solo a usuarios en el grupo 'developer'."""
    def has_permission(self, request, view):
        return request.user.groups.filter(name='developer').exists()