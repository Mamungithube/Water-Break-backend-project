from rest_framework import permissions
from teamapp.models import TeamMember

class IsCoachOrAssistant(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        # Check: Is the user an 'assistant' in any team?
        is_assistant = TeamMember.objects.filter(
            member=user, 
            role='assistant', 
            is_role_approved=True
        ).exists()

        # Permission granted if the user is a coach or an assistant
        return user.role == 'coach' or is_assistant

    def has_object_permission(self, request, view, obj):
        # Check if the user is the owner of the object during edit or delete
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.create_By == request.user or (hasattr(obj, 'assistant_coach') and obj.assistant_coach == request.user)