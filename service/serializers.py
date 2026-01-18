from rest_framework import serializers
from .models import  privacy_policy, termsandconditions, aboutus


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = privacy_policy
        fields = '__all__'


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = termsandconditions
        fields = '__all__'


class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = aboutus
        fields = '__all__'
