from rest_framework import serializers
from .models import Drill, Block , plan
from account.serializers import UserSerializer
class DrillSerializer(serializers.ModelSerializer):
    create_By = UserSerializer(read_only=True)
    class Meta:
        model = Drill
        fields = ['id', 'create_By', 'name', 'category', 'description', 'date_created', 'date_modified']
        read_only_fields = ['date_created', 'date_modified']

    def create(self, validated_data):
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['create_By'] = user 
        
        return super().create(validated_data)


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ['id',  'title', 'start_time', 'end_time', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class planSerializer(serializers.ModelSerializer):
    class Meta:
        model = plan
        fields = ['id', 'plan_title', 'Drill', 'prectice_time', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']