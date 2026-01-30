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
        
        # ✅ CHANGE - Write permissions logic পরিবর্তন
        # Old: creator coach or assistant
        # New: creator coach OR drill's assistant_coach
        if request.user.role == 'coach':
            return self._is_creator(request.user, obj)
        elif request.user.role == 'assistant':
            return self._is_drill_assistant(request.user, obj)
        
        return False

    def _can_view_object(self, user, obj):
        """Check if user can view this object"""
        from .models import Drill, Block, plan
        from teamapp.models import Team
        
        if isinstance(obj, Drill):
            # ✅ CHANGE - Creator, assistant_coach, এবং assigned_members দেখতে পারবে
            if obj.create_By == user:
                return True
            if obj.assistant_coach == user:
                return True
            if obj.assigned_members.filter(id=user.id).exists():
                return True
            # Team members ও দেখতে পারবে (যদি আপনি চান)
            user_teams = Team.objects.filter(members=user)
            return obj.assign_team.filter(id__in=user_teams).exists()
        
        elif isinstance(obj, Block):
            # ✅ CHANGE - Drill এর permissions অনুসারে
            drill = obj.drill
            if drill:
                if drill.create_By == user:
                    return True
                if drill.assistant_coach == user:
                    return True
                if drill.assigned_members.filter(id=user.id).exists():
                    return True
                user_teams = Team.objects.filter(members=user)
                return drill.assign_team.filter(id__in=user_teams).exists()
            return False
        
        elif isinstance(obj, plan):
            # ✅ CHANGE - Plan creator এবং drills এর assistant_coach/assigned_members
            if obj.create_By == user:
                return True
            
            for block in obj.Plan_Block.all():
                drill = block.drill
                if drill:
                    if drill.assistant_coach == user:
                        return True
                    if drill.assigned_members.filter(id=user.id).exists():
                        return True
                    user_teams = Team.objects.filter(members=user)
                    if drill.assign_team.filter(id__in=user_teams).exists():
                        return True
            return False
        
        return False

    # ✅ NEW METHOD - শুধু creator check করার জন্য
    def _is_creator(self, user, obj):
        """Check if user is the creator of the object"""
        from .models import Drill, Block, plan
        
        if isinstance(obj, Drill):
            return obj.create_By == user
        
        elif isinstance(obj, Block):
            return obj.drill.create_By == user if obj.drill else False
        
        elif isinstance(obj, plan):
            return obj.create_By == user
        
        return False

    # ✅ NEW METHOD - drill এর assistant_coach কিনা check করার জন্য
    def _is_drill_assistant(self, user, obj):
        """Check if user is the assistant_coach of the drill"""
        from .models import Drill, Block, plan
        
        if isinstance(obj, Drill):
            return obj.assistant_coach == user
        
        elif isinstance(obj, Block):
            return obj.drill.assistant_coach == user if obj.drill else False
        
        elif isinstance(obj, plan):
            # ✅ Plan এর কোনো block এর drill এর assistant_coach হলে edit করতে পারবে
            # তবে এটা আপনার requirement অনুসারে adjust করতে পারেন
            # এখন: assistant শুধু তার নিজের drill edit করতে পারবে, পুরো plan edit করতে পারবে না
            return False
        
        return False

    # ✅ REMOVED - _is_creator_or_related method আর দরকার নেই