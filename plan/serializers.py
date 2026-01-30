from rest_framework import serializers
from django.contrib.auth import get_user_model

from teamapp.models import Team
from .models import Drill, Block, plan
from account.serializers import UserSerializer

User = get_user_model()  # ✅ Import User model


class DrillSerializer(serializers.ModelSerializer):
    create_By = UserSerializer(read_only=True)
    
    # ✅ BEST FIX - সরাসরি User.objects.all() দিয়ে দিন
    assigned_members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),  # ✅ Direct queryset
        required=False,
        allow_empty=True
    )
    assistant_coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='assistant'),  # ✅ Filtered queryset
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Drill
        fields = [
            'id', 'create_By', 'assign_team', 
            'assigned_members', 'assistant_coach',
            'name', 'category', 'description', 
            'date_created', 'date_modified'
        ]
        read_only_fields = ['date_created', 'date_modified']

    def create(self, validated_data):
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['create_By'] = user 
        return super().create(validated_data)

    def validate_assign_team(self, value):
        """Validate that coach can only assign their own teams"""
        user = self.context['request'].user
        
        coach_teams = Team.objects.filter(coach=user)
        
        for team in value:
            if team not in coach_teams:
                raise serializers.ValidationError(
                    f"You can only assign teams that you created. Team '{team.name}' is not your team."
                )
        
        return value

    def validate_assistant_coach(self, value):
        """Validate that assistant_coach has 'assistant' role"""
        if value and value.role != 'assistant':
            raise serializers.ValidationError(
                "Only users with 'assistant' role can be assigned as assistant coach."
            )
        return value


class BlockSerializer(serializers.ModelSerializer):
    drill_details = serializers.SerializerMethodField()
    
    drill = serializers.PrimaryKeyRelatedField(
        queryset=Drill.objects.all(),
        required=False
    )
    
    practice_plan = serializers.PrimaryKeyRelatedField(
        queryset=plan.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Block
        fields = [
            'id', 
            'drill',
            'drill_details',
            'practice_plan',
            'title', 
            'color_code',
            'start_time', 
            'end_time', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_drill_details(self, obj):
        """Get drill details for display"""
        if obj.drill:
            return DrillSerializer(obj.drill, context=self.context).data
        return None

    def validate_drill(self, value):
        """Validate that the drill belongs to the current user"""
        user = self.context['request'].user
        if value and value.create_By != user:
            raise serializers.ValidationError(
                "You can only create blocks for your own drills."
            )
        return value

    def validate_practice_plan(self, value):
        """Validate that the practice plan belongs to the current user"""
        if value:
            user = self.context['request'].user
            if value.create_By != user:
                raise serializers.ValidationError(
                    "You can only assign blocks to your own practice plans."
                )
        return value

    def validate(self, attrs):
        """
        Cross-field validation:
        - Check if drill's assigned_members are from practice_plan's assigned teams
        """
        drill = attrs.get('drill') or (self.instance.drill if self.instance else None)
        practice_plan = attrs.get('practice_plan') or (self.instance.practice_plan if self.instance else None)
        
        if drill and practice_plan:
            # Get all members from plan's assigned teams
            plan_team_members = set()
            for team in practice_plan.assign_team.all():
                plan_team_members.update(team.members.all())
            
            # Check if all drill's assigned_members are in plan's teams
            for member in drill.assigned_members.all():
                if member not in plan_team_members:
                    raise serializers.ValidationError({
                        'drill': f"Assigned member '{member.email}' is not in the practice plan's teams."
                    })
        
        return attrs

    def update(self, instance, validated_data):
        """Allow updating drill details through block"""
        request = self.context.get('request')
        user = request.user if request else None
        
        drill_details_data = request.data.get('drill_details', None) if request else None
        
        instance.title = validated_data.get('title', instance.title)
        instance.color_code = validated_data.get('color_code', instance.color_code)
        instance.start_time = validated_data.get('start_time', instance.start_time)
        instance.end_time = validated_data.get('end_time', instance.end_time)
        instance.practice_plan = validated_data.get('practice_plan', instance.practice_plan)
        instance.save()
        
        if drill_details_data and user:
            drill = instance.drill
            
            if not drill:
                return instance
            
            if drill.create_By != user:
                raise serializers.ValidationError(
                    "You can only edit drills that you created."
                )
            
            if 'name' in drill_details_data:
                drill.name = drill_details_data['name']
            
            if 'category' in drill_details_data:
                drill.category = drill_details_data['category']
            
            if 'description' in drill_details_data:
                drill.description = drill_details_data['description']
            
            if 'assign_team' in drill_details_data:
                team_ids = drill_details_data['assign_team']
                
                coach_teams = Team.objects.filter(coach=user)
                coach_team_ids = list(coach_teams.values_list('id', flat=True))
                
                for team_id in team_ids:
                    if team_id not in coach_team_ids:
                        raise serializers.ValidationError(
                            f"You can only assign teams that you created. Team ID {team_id} is not your team."
                        )
                
                drill.assign_team.set(team_ids)
            
            # Handle assigned_members update
            if 'assigned_members' in drill_details_data:
                member_ids = drill_details_data['assigned_members']
                
                # Validate that members are from practice_plan's teams
                if instance.practice_plan:
                    plan_team_members = set()
                    for team in instance.practice_plan.assign_team.all():
                        plan_team_members.update(team.members.values_list('id', flat=True))
                    
                    for member_id in member_ids:
                        if member_id not in plan_team_members:
                            raise serializers.ValidationError(
                                f"Member ID {member_id} is not in the practice plan's teams."
                            )
                
                drill.assigned_members.set(member_ids)
            
            # Handle assistant_coach update
            if 'assistant_coach' in drill_details_data:
                assistant_id = drill_details_data['assistant_coach']
                if assistant_id:
                    try:
                        assistant = User.objects.get(id=assistant_id)
                        if assistant.role != 'assistant':
                            raise serializers.ValidationError(
                                "Only users with 'assistant' role can be assigned."
                            )
                        drill.assistant_coach = assistant
                    except User.DoesNotExist:
                        raise serializers.ValidationError(
                            f"User with ID {assistant_id} does not exist."
                        )
                else:
                    drill.assistant_coach = None
            
            drill.save()
        
        return instance


class planSerializer(serializers.ModelSerializer):
    create_By = serializers.PrimaryKeyRelatedField(read_only=True)
    
    plan_blocks_detail = BlockSerializer(source='Plan_Block', many=True, read_only=True)
    
    Plan_Block = serializers.PrimaryKeyRelatedField(
        queryset=Block.objects.all(),
        many=True,
        required=False
    )
    assign_team = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Team.objects.all()
    )
    
    class Meta:
        model = plan
        fields = [
            'id', 'create_By', 'assign_team', 'plan_title', 
            'Plan_Block', 'plan_blocks_detail', 'start_practice_time', 'end_practice_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'create_By']

    def update(self, instance, validated_data):
        blocks = validated_data.pop('Plan_Block', None)
        instance = super().update(instance, validated_data)
        
        if blocks is not None:
            for block in blocks:
                block.practice_plan = instance
                block.save()
        return instance