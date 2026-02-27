# subscription/permissions.py
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class CanCreateDrill(BasePermission):
    def has_permission(self, request, view):
        if view.action != 'create':
            return True
        try:
            can_create, message = request.user.subscription.can_create_drill()
            if not can_create:
                raise PermissionDenied(detail=message)
            return True
        except AttributeError:
            raise PermissionDenied(detail="No active subscription found.")

class CanCreatePlan(BasePermission):
    def has_permission(self, request, view):
        if view.action != 'create':
            return True
        try:
            can_create, message = request.user.subscription.can_create_practice_plan()
            if not can_create:
                raise PermissionDenied(detail=message)
            return True
        except AttributeError:
            raise PermissionDenied(detail="No active subscription found.")

class CanCreateTeam(BasePermission):
    def has_permission(self, request, view):
        if view.action != 'create':
            return True
        try:
            can_create, message = request.user.subscription.can_create_team()
            if not can_create:
                raise PermissionDenied(detail=message)
            return True
        except AttributeError:
            raise PermissionDenied(detail="No active subscription found.")