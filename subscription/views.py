from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Subscription, SubscriptionPlan
from .serializers import SubscriptionSerializer, SubscriptionPlanSerializer


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_limits(self, request):
        """Get current user's subscription limits"""
        try:
            subscription = request.user.subscription
            
            can_team, team_msg = subscription.can_create_team()
            can_drill, drill_msg = subscription.can_create_drill()
            can_plan, plan_msg = subscription.can_create_practice_plan()
            
            return Response({
                "plan": subscription.plan.name,
                "status": subscription.status,
                "teams": {
                    "can_create": can_team,
                    "current": subscription.number_of_teams,
                    "max": subscription.plan.max_teams_allowed,
                    "message": team_msg
                },
                "drills": {
                    "can_create": can_drill,
                    "current": subscription.number_of_drills,
                    "max": subscription.plan.max_drills,
                    "message": drill_msg
                },
                "practice_plans": {
                    "can_create": can_plan,
                    "current": subscription.number_of_practice_plans,
                    "max": subscription.plan.max_practice_plans,
                    "message": plan_msg
                }
            })
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND
            )


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """List available plans"""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]