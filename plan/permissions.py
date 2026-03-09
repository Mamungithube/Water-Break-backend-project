from rest_framework import permissions
from teamapp.models import TeamMember


def is_assistant(user):
    return TeamMember.objects.filter(
        member=user,
        role='assistant',
        is_role_approved=True
    ).exists()


# ✅ শুধু Coach এর জন্য
class IsCoachOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role == 'coach'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role == 'coach' and obj.create_By == request.user


# ✅ Coach + Assistant Block এর জন্য
class IsCoachOrAssistantForBlock(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        # Coach অথবা Assistant উভয়ই Block write করতে পারবে
        return user.role == 'coach' or is_assistant(user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.role == 'coach':
            return obj.drill.create_By == user
        if is_assistant(user):
            return obj.drill.assistant_coach == user
        return False