from rest_framework import permissions

class IsCoachOrAssistant(permissions.BasePermission):
    """
    Permission to allow only Coach and Assistant Coach to create/update/delete
    """
    def has_permission(self, request, view):
        # Read permissions are allowed for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        return (
            request.user 
            and request.user.is_authenticated 
            and request.user.role in ['coach', 'assistant']
        )

    def has_object_permission(self, request, view, obj):
        # Read permissions - check if user is in assigned team
        if request.method in permissions.SAFE_METHODS:
            return self._can_view_object(request.user, obj)
        
        # Write permissions - only creator coach or assistant
        if request.user.role in ['coach', 'assistant']:
            return self._is_creator_or_related(request.user, obj)
        
        return False

    def _can_view_object(self, user, obj):
        """Check if user can view this object"""
        from .models import Drill, Block, plan
        from teamapp.models import Team
        
        if isinstance(obj, Drill):
            # Check if user is creator
            if obj.create_By == user:
                return True
            # Check if user is in assigned teams
            user_teams = Team.objects.filter(members=user)
            return obj.assign_team.filter(id__in=user_teams).exists()
        
        elif isinstance(obj, Block):
            # Check through drill
            drill = obj.drill
            if drill.create_By == user:
                return True
            user_teams = Team.objects.filter(members=user)
            return drill.assign_team.filter(id__in=user_teams).exists()
        
        elif isinstance(obj, plan):
            # Check if user is in any of the drill's assigned teams
            for block in obj.Plan_Block.all():
                drill = block.drill
                if drill.create_By == user:
                    return True
                user_teams = Team.objects.filter(members=user)
                if drill.assign_team.filter(id__in=user_teams).exists():
                    return True
            return False
        
        return False

    def _is_creator_or_related(self, user, obj):
        """Check if user is creator or related to the object"""
        from .models import Drill, Block, plan
        
        if isinstance(obj, Drill):
            return obj.create_By == user
        
        elif isinstance(obj, Block):
            return obj.drill.create_By == user
        
        elif isinstance(obj, plan):
            # Check if user created any of the drills in the plan
            for block in obj.Plan_Block.all():
                if block.drill.create_By == user:
                    return True
            return False
        
        return False