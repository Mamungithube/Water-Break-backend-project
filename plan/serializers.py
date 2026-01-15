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
        
        # Get teams created by this coach (using 'coach' field instead of 'created_by')
        coach_teams = Team.objects.filter(coach=user)
        
        for team in value:
            if team not in coach_teams:
                raise serializers.ValidationError(
                    f"You can only assign teams that you created. Team '{team.name}' is not your team."
                )
        
        return value


class BlockSerializer(serializers.ModelSerializer):
    # Nested drill serializer for editing drill details through block
    drill_details = DrillSerializer(source='drill', read_only=False, required=False)
    
    # Keep drill ID field for creating new blocks
    drill = serializers.PrimaryKeyRelatedField(
        queryset=Drill.objects.all(),
        required=False
    )
    
    class Meta:
        model = Block
        fields = [
            'id', 
            'drill',  # For creating new blocks
            'drill_details',  # For editing drill details
            'title', 
            'start_time', 
            'end_time', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_drill(self, value):
        """Validate that the drill belongs to the current user"""
        user = self.context['request'].user
        if value and value.create_By != user:
            raise serializers.ValidationError(
                "You can only create blocks for your own drills."
            )
        return value

    def update(self, instance, validated_data):
        """Allow updating drill details through block"""
        drill_data = validated_data.pop('drill', None)
        
        # Update block fields
        instance.title = validated_data.get('title', instance.title)
        instance.start_time = validated_data.get('start_time', instance.start_time)
        instance.end_time = validated_data.get('end_time', instance.end_time)
        instance.save()
        
        # Update drill fields if drill_details is provided
        if drill_data:
            drill = instance.drill
            user = self.context['request'].user
            
            # Security check: only drill creator can edit
            if drill.create_By != user:
                raise serializers.ValidationError(
                    "You can only edit drills that you created."
                )
            
            # Update drill fields
            drill.name = drill_data.get('name', drill.name)
            drill.category = drill_data.get('category', drill.category)
            drill.description = drill_data.get('description', drill.description)
            
            # Handle assign_team if provided
            if 'assign_team' in drill_data:
                assign_teams = drill_data.get('assign_team', [])
                
                # Validate teams belong to coach (using 'coach' field)
                from teamapp.models import Team
                coach_teams = Team.objects.filter(coach=user)
                
                for team in assign_teams:
                    if team not in coach_teams:
                        raise serializers.ValidationError(
                            f"You can only assign teams that you created. Team '{team.name}' is not your team."
                        )
                
                drill.assign_team.set(assign_teams)
            
            drill.save()
        
        return instance

    def to_representation(self, instance):
        """Include drill details in response"""
        representation = super().to_representation(instance)
        representation['drill_details'] = DrillSerializer(instance.drill).data
        return representation


class planSerializer(serializers.ModelSerializer):
    class Meta:
        model = plan
        fields = ['id', 'plan_title', 'Plan_Block', 'prectice_time', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']