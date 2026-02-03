from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
# Create your views here.
from rest_framework import viewsets
from .models import Privacy_Policy, TermsAndConditions, AboutUs
from .serializers import PrivacyPolicySerializer, TermsAndConditionsSerializer, AboutUsSerializer


class PrivacyPolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Privacy_Policy.objects.all().order_by('-updated_at')
    serializer_class = PrivacyPolicySerializer


class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = TermsAndConditions.objects.all().order_by('-updated_at')
    serializer_class = TermsAndConditionsSerializer


class AboutUsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AboutUs.objects.all().order_by('-updated_at')
    serializer_class = AboutUsSerializer
