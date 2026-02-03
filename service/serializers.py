from rest_framework import serializers
from .models import  Privacy_Policy, TermsAndConditions, AboutUs


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Privacy_Policy
        fields = '__all__'


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = '__all__'


class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUs
        fields = '__all__'
