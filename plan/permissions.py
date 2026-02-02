from rest_framework import permissions
from teamapp.models import TeamMember

class IsCoachOrAssistant(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        # চেক: ইউজার কি কোনো টিমে 'assistant' হিসেবে আছে?
        is_assistant = TeamMember.objects.filter(
            member=user, 
            role='assistant', 
            is_role_approved=True
        ).exists()

        # কোচ অথবা অ্যাসিস্ট্যান্ট হলে পারমিশন পাবে
        return user.role == 'coach' or is_assistant

    def has_object_permission(self, request, view, obj):
        # এডিট বা ডিলিট করার সময় চেক করবে সে ওই অবজেক্টের মালিক কি না
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.create_By == request.user or (hasattr(obj, 'assistant_coach') and obj.assistant_coach == request.user)