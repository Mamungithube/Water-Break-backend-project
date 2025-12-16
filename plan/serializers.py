from rest_framework import serializers
from .models import Drill
from account.serializers import UserSerializer
class DrillSerializer(serializers.ModelSerializer):
    create_By = UserSerializer(read_only=True)
    class Meta:
        model = Drill
        fields = ['id', 'create_By', 'name', 'category', 'description', 'date_created', 'date_modified']
        read_only_fields = ['date_created', 'date_modified']
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['create_By'] = request.user
        return super().create(validated_data)
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    

    