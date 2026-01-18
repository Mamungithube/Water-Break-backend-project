from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
# Create your views here.
from rest_framework import viewsets
from .models import privacy_policy, termsandconditions, aboutus
from .serializers import PrivacyPolicySerializer, TermsAndConditionsSerializer, AboutUsSerializer


class PrivacyPolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = privacy_policy.objects.all().order_by('-updated_at')
    serializer_class = PrivacyPolicySerializer


class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = termsandconditions.objects.all().order_by('-updated_at')
    serializer_class = TermsAndConditionsSerializer


class AboutUsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = aboutus.objects.all().order_by('-updated_at')
    serializer_class = AboutUsSerializer
