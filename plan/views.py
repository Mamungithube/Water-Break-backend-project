from django.shortcuts import render
from rest_framework.viewsets import ViewSetMixin
from django.template.context_processors import request
# Create your views here.
from plan.models import Block
from rest_framework import response, status, viewsets
from .models import Drill, Block, plan
from .serializers import DrillSerializer,BlockSerializer,planSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class DrillViewSet(viewsets.ModelViewSet):
    queryset = Drill.objects.all()
    serializer_class = DrillSerializer
    permission_classes = [IsAuthenticated] 

    def perform_create(self, serializer):
        serializer.save(create_By=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        data = response.data or {}
        data['message'] = 'Drill created successfully'
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        data = response.data or {}
        data['message'] = 'Drill deleted successfully'
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        data = response.data or {}
        data['message'] = 'Drill updated successfully'
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_200_OK)
    


class BlockViewSet(viewsets.ModelViewSet):
    queryset = Block.objects.all()
    serializer_class = BlockSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        data = response.data or {}
        data['message'] = 'Block created successfully'
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        data = response.data or {}
        data['message'] = 'Block deleted successfully'
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        data = response.data or {}
        data['message'] = 'Block updated successfully'
        return Response({
            'status': "success",
            'data': data
        }, status=status.HTTP_200_OK)
    

class PlanViewSet(viewsets.ModelViewSet):
    queryset = plan.objects.all()
    serializer_class = planSerializer
    permission_classes = [IsAuthenticated]

    def create(self,request,*args, **kwargs):
        response = super().create(request,*args, **kwargs)
        data = response.data or {}
        data['message'] = 'Plan created successfully'
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_201_CREATED)
    
    def destroy(self,request,*args, **kwargs):
        response = super().destroy(request,*args,**kwargs)
        data = response.data or {}
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_200_OK)
    
    def update(self,request,*args, **kwargs):
        response = super().update(request, *args, **kwargs)
        data = response.data or {}
        return Response({
            'status': 'success',
            'data': data
        }, status=status.HTTP_200_OK)