from django.shortcuts import render
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from .models import Privacy_Policy, TermsAndConditions, AboutUs
from .serializers import PrivacyPolicySerializer, TermsAndConditionsSerializer, AboutUsSerializer


class PrivacyPolicyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Privacy_Policy.objects.all().order_by('-updated_at')
    serializer_class = PrivacyPolicySerializer


class TermsAndConditionsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = TermsAndConditions.objects.all().order_by('-updated_at')
    serializer_class = TermsAndConditionsSerializer


class AboutUsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = AboutUs.objects.all().order_by('-updated_at')
    serializer_class = AboutUsSerializer