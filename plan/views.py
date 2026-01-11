from django.shortcuts import render
from rest_framework.viewsets import ViewSetMixin
from django.template.context_processors import request
from django.http import Http404
from rest_framework.exceptions import ValidationError as DRFValidationError
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
        try:
            response = super().create(request, *args, **kwargs)
            data = response.data or {}
            data['message'] = 'Drill created successfully'
            return Response({
                'status': 'success',
                'message': 'Drill created successfully',
                'data': data
            }, status=status.HTTP_201_CREATED)
        except DRFValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation error',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to create drill',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        try:
            drill = self.get_object()
            super().destroy(request, *args, **kwargs)
            return Response({
                'status': 'success',
                'message': 'Drill deleted successfully',
                'data': {'id': drill.id}
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'status': 'error',
                'message': 'Drill not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to delete drill',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            data = response.data or {}
            data['message'] = 'Drill updated successfully'
            return Response({
                'status': 'success',
                'message': 'Drill updated successfully',
                'data': data
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'status': 'error',
                'message': 'Drill not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except DRFValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation error',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to update drill',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


class BlockViewSet(viewsets.ModelViewSet):
    queryset = Block.objects.all()
    serializer_class = BlockSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()
    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            data = response.data or {}
            data['message'] = 'Block created successfully'
            return Response({
                'status': 'success',
                'message': 'Block created successfully',
                'data': data
            }, status=status.HTTP_201_CREATED)
        except DRFValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation error',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to create block',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        try:
            block = self.get_object()
            super().destroy(request, *args, **kwargs)
            return Response({
                'status': 'success',
                'message': 'Block deleted successfully',
                'data': {'id': block.id}
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'status': 'error',
                'message': 'Block not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to delete block',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            data = response.data or {}
            data['message'] = 'Block updated successfully'
            return Response({
                'status': 'success',
                'message': 'Block updated successfully',
                'data': data
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'status': 'error',
                'message': 'Block not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except DRFValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation error',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to update block',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class PlanViewSet(viewsets.ModelViewSet):
    queryset = plan.objects.all()
    serializer_class = planSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            data = response.data or {}
            data['message'] = 'Plan created successfully'
            return Response({
                'status': 'success',
                'message': 'Plan created successfully',
                'data': data
            }, status=status.HTTP_201_CREATED)
        except DRFValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation error',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to create plan',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        try:
            plan_obj = self.get_object()
            super().destroy(request, *args, **kwargs)
            return Response({
                'status': 'success',
                'message': 'Plan deleted successfully',
                'data': {'id': plan_obj.id}
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'status': 'error',
                'message': 'Plan not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to delete plan',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            data = response.data or {}
            data['message'] = 'Plan updated successfully'
            return Response({
                'status': 'success',
                'message': 'Plan updated successfully',
                'data': data
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'status': 'error',
                'message': 'Plan not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except DRFValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation error',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to update plan',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)