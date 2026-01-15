from django.shortcuts import render
from rest_framework.viewsets import ViewSetMixin
from django.template.context_processors import request
from django.http import Http404
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db.models import Q
from rest_framework import response, status, viewsets
from .models import Drill, Block, plan
from .serializers import DrillSerializer, BlockSerializer, planSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsCoachOrAssistant


class DrillViewSet(viewsets.ModelViewSet):
    queryset = Drill.objects.all()
    serializer_class = DrillSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAssistant]

    def get_queryset(self):
        """
        Filter drills based on user role:
        - Coach/Assistant: Only their created drills
        - Player: Drills assigned to their teams
        """
        user = self.request.user
        
        if user.role in ['coach', 'assistant']:
            return Drill.objects.filter(create_By=user)
        else:
            from teamapp.models import Team
            user_teams = Team.objects.filter(members=user)
            return Drill.objects.filter(assign_team__in=user_teams).distinct()

    def perform_create(self, serializer):
        serializer.save(create_By=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            data = response.data or {}
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
    permission_classes = [IsAuthenticated, IsCoachOrAssistant]

    def get_queryset(self):
        """
        Filter blocks based on user role:
        - Coach/Assistant: Blocks from their drills
        - Player: Blocks from drills assigned to their teams
        """
        user = self.request.user
        
        if user.role in ['coach', 'assistant']:
            return Block.objects.filter(drill__create_By=user)
        else:
            from teamapp.models import Team
            user_teams = Team.objects.filter(members=user)
            return Block.objects.filter(
                drill__assign_team__in=user_teams
            ).distinct()

    def perform_create(self, serializer):
        serializer.save()

    def list(self, request, *args, **kwargs):
        """List all blocks with better error handling"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'status': 'success',
                'count': queryset.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to fetch blocks',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve single block with better error handling"""
        try:
            block_id = kwargs.get('pk')
            
            # Check if block exists
            if not Block.objects.filter(id=block_id).exists():
                return Response({
                    'status': 'error',
                    'message': f'Block with ID {block_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check permission
            try:
                instance = self.get_object()
            except Http404:
                return Response({
                    'status': 'error',
                    'message': 'Access denied',
                    'detail': 'You do not have permission to view this block'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(instance)
            return Response({
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve block',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            data = response.data or {}
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
            block_id = kwargs.get('pk')
            
            # Check if block exists
            if not Block.objects.filter(id=block_id).exists():
                return Response({
                    'status': 'error',
                    'message': f'Block with ID {block_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check permission
            try:
                block = self.get_object()
            except Http404:
                return Response({
                    'status': 'error',
                    'message': 'Access denied',
                    'detail': 'You do not have permission to delete this block'
                }, status=status.HTTP_403_FORBIDDEN)
            
            super().destroy(request, *args, **kwargs)
            return Response({
                'status': 'success',
                'message': 'Block deleted successfully',
                'data': {'id': block.id}
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to delete block',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        try:
            block_id = kwargs.get('pk')
            
            # Check if block exists
            if not Block.objects.filter(id=block_id).exists():
                return Response({
                    'status': 'error',
                    'message': f'Block with ID {block_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check permission
            try:
                block = self.get_object()
            except Http404:
                return Response({
                    'status': 'error',
                    'message': 'Access denied',
                    'detail': 'You do not have permission to update this block'
                }, status=status.HTTP_403_FORBIDDEN)
            
            response = super().update(request, *args, **kwargs)
            data = response.data or {}
            return Response({
                'status': 'success',
                'message': 'Block updated successfully',
                'data': data
            }, status=status.HTTP_200_OK)
            
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
    permission_classes = [IsAuthenticated, IsCoachOrAssistant]

    def get_queryset(self):
        """
        Filter plans based on user role:
        - Coach/Assistant: Plans containing their blocks
        - Player: Plans containing blocks from drills assigned to their teams
        """
        user = self.request.user
        
        if user.role in ['coach', 'assistant']:
            return plan.objects.filter(
                Plan_Block__drill__create_By=user
            ).distinct()
        else:
            from teamapp.models import Team
            user_teams = Team.objects.filter(members=user)
            return plan.objects.filter(
                Plan_Block__drill__assign_team__in=user_teams
            ).distinct()

    def perform_create(self, serializer):
        # Validate that all blocks belong to drills created by current user
        blocks = serializer.validated_data.get('Plan_Block', [])
        for block in blocks:
            if block.drill.create_By != self.request.user:
                raise DRFValidationError({
                    'Plan_Block': f'Block "{block.title}" belongs to a drill you did not create.'
                })
        serializer.save()

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            data = response.data or {}
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