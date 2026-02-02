from rest_framework import serializers
from .models import Subscription, SubscriptionPlan

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    number_of_teams = serializers.IntegerField(read_only=True)
    number_of_drills = serializers.IntegerField(read_only=True)
    number_of_practice_plans = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'plan', 'plan_details', 'status',
            'revenue_cat_id', 'is_active',
            'number_of_teams', 'number_of_drills', 'number_of_practice_plans',
            'current_period_start', 'current_period_end'
        ]
        read_only_fields = ['user', 'status', 'revenue_cat_id']