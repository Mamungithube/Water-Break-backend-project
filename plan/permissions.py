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
        return user.role == 'coach' or is_assistant(user)

    def has_object_permission(self, request, view, obj):
        user = request.user

        # ✅ সবাই GET করতে পারবে
        if request.method in permissions.SAFE_METHODS:
            return True

        # ✅ Coach — নিজের drill এর block edit করতে পারবে
        if user.role == 'coach':
            if obj.drill:
                return obj.drill.create_By == user
            return obj.create_By == user

        # ✅ Assistant — নিজের team এর plan এর block edit করতে পারবে
        if is_assistant(user):
            from teamapp.models import TeamMember

            # drill এর assistant_coach হলে
            if obj.drill and obj.drill.assistant_coach == user:
                return True

            # অথবা plan এর team এ assistant হলে
            if obj.practice_plan:
                plan_team_ids = obj.practice_plan.assign_team.values_list(
                    'id', flat=True
                )
                return TeamMember.objects.filter(
                    member=user,
                    team_id__in=plan_team_ids,
                    role='assistant',
                    is_role_approved=True
                ).exists()

            return False

        return False