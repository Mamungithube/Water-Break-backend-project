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
    drill_details = DrillSerializer(source='drill', read_only=True)
    
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
            'practice_plan',  # ← এটা যোগ করা হয়েছে
            'title', 
            'color_code',
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
        drill_data = validated_data.pop('drill', None)
        
        instance.title = validated_data.get('title', instance.title)
        instance.color_code = validated_data.get('color_code', instance.color_code)
        instance.start_time = validated_data.get('start_time', instance.start_time)
        instance.end_time = validated_data.get('end_time', instance.end_time)
        instance.practice_plan = validated_data.get('practice_plan', instance.practice_plan)
        instance.save()
        
        if drill_data:
            drill = instance.drill
            user = self.context['request'].user
            
            if drill.create_By != user:
                raise serializers.ValidationError(
                    "You can only edit drills that you created."
                )
            
            drill.name = drill_data.get('name', drill.name)
            drill.category = drill_data.get('category', drill.category)
            drill.description = drill_data.get('description', drill.description)
            
            if 'assign_team' in drill_data:
                assign_teams = drill_data.get('assign_team', [])
                
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