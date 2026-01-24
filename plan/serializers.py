from rest_framework import serializers
from .models import Drill, Block, plan
from account.serializers import UserSerializer


class DrillSerializer(serializers.ModelSerializer):
    create_By = UserSerializer(read_only=True)
    
    class Meta:
        model = Drill
        fields = ['id', 'create_By', 'assign_team', 'name', 'category', 'description', 'date_created', 'date_modified']
        read_only_fields = ['date_created', 'date_modified']

    def create(self, validated_data):
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['create_By'] = user 
        return super().create(validated_data)

    def validate_assign_team(self, value):
        """Validate that coach can only assign their own teams"""
        user = self.context['request'].user
        from teamapp.models import Team
        
        coach_teams = Team.objects.filter(coach=user)
        
        for team in value:
            if team not in coach_teams:
                raise serializers.ValidationError(
                    f"You can only assign teams that you created. Team '{team.name}' is not your team."
                )
        
        return value


class BlockSerializer(serializers.ModelSerializer):
    drill_details = serializers.SerializerMethodField()  # ✅ Changed to SerializerMethodField
    
    drill = serializers.PrimaryKeyRelatedField(
        queryset=Drill.objects.all(),
        required=False
    )
    
    # Practice plan field - can be null
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
        return DrillSerializer(obj.drill).data

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

    def update(self, instance, validated_data):
        """Allow updating drill details through block"""
        request = self.context.get('request')
        user = request.user if request else None
        
        # Get drill_details from request data (not validated_data)
        drill_details_data = request.data.get('drill_details', None) if request else None
        
        # Update block fields
        instance.title = validated_data.get('title', instance.title)
        instance.color_code = validated_data.get('color_code', instance.color_code)
        instance.start_time = validated_data.get('start_time', instance.start_time)
        instance.end_time = validated_data.get('end_time', instance.end_time)
        instance.practice_plan = validated_data.get('practice_plan', instance.practice_plan)
        instance.save()
        
        # Update drill fields if drill_details is provided
        if drill_details_data and user:
            drill = instance.drill
            
            # Security check: only drill creator can edit
            if drill.create_By != user:
                raise serializers.ValidationError(
                    "You can only edit drills that you created."
                )
            
            # Update drill fields
            if 'name' in drill_details_data:
                drill.name = drill_details_data['name']
            
            if 'category' in drill_details_data:
                drill.category = drill_details_data['category']
            
            if 'description' in drill_details_data:
                drill.description = drill_details_data['description']
            
            # Handle assign_team if provided
            if 'assign_team' in drill_details_data:
                team_ids = drill_details_data['assign_team']
                
                # Validate teams belong to coach
                from teamapp.models import Team
                coach_teams = Team.objects.filter(coach=user)
                coach_team_ids = list(coach_teams.values_list('id', flat=True))
                
                # Check each team
                for team_id in team_ids:
                    if team_id not in coach_team_ids:
                        raise serializers.ValidationError(
                            f"You can only assign teams that you created. Team ID {team_id} is not your team."
                        )
                
                # Set the teams
                drill.assign_team.set(team_ids)
            
            drill.save()
        
        return instance


class planSerializer(serializers.ModelSerializer):
    create_By = serializers.PrimaryKeyRelatedField(read_only=True)
    creator_name = serializers.CharField(source='create_By.username', read_only=True)
    
    plan_blocks_detail = BlockSerializer(source='Plan_Block', many=True, read_only=True)
    
    Plan_Block = serializers.PrimaryKeyRelatedField(
        queryset=Block.objects.all(),
        many=True,
        required=False
    )
    
    class Meta:
        model = plan
        fields = [
            'id', 'create_By', 'creator_name', 'plan_title', 
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