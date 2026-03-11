from rest_framework import permissions
from teamapp.models import TeamMember

def get_assistant_team_ids(user):
    return TeamMember.objects.filter(
        member=user,
        role='assistant',
        is_role_approved=True
    ).values_list('team_id', flat=True)

def is_assistant(user):
    return TeamMember.objects.filter(
        member=user,
        role='assistant',
        is_role_approved=True
    ).exists()


# ✅ Only for Coach
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


# ✅ For Coach + Assistant Block
class IsCoachOrAssistantForBlock(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        # Coach or approved assistant on any team
        return user.role == 'coach' or is_assistant(user)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.method in permissions.SAFE_METHODS:
            return True

        # Coach block of your own drill or plan
        if user.role == 'coach':
            if obj.drill:
                return obj.drill.create_By == user
            if obj.practice_plan:
                return obj.practice_plan.create_By == user
            return obj.create_By == user

        # Assistant If in plan's assign_team
        if is_assistant(user):
            assistant_team_ids = get_assistant_team_ids(user)

            if obj.practice_plan:
                plan_team_ids = obj.practice_plan.assign_team.values_list('id', flat=True)
                return TeamMember.objects.filter(
                    member=user,
                    team_id__in=plan_team_ids,
                    role='assistant',
                    is_role_approved=True
                ).exists()

            # Even if it's an assistant_coach for the drill, it will work.
            if obj.drill and obj.drill.assistant_coach == user:
                return True

        return False