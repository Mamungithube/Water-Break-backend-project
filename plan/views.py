from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Drill   
from .serializers import DrillSerializer
class DrillViewSet(viewsets.ModelViewSet):
    queryset = Drill.objects.all()
    serializer_class = DrillSerializer

        