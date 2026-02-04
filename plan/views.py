from django.shortcuts import render
from django.http import Http404
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status, viewsets
from .models import Drill, Block, Plan
from .serializers import DrillSerializer, BlockSerializer, planSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsCoachOrAssistant
from datetime import datetime
from django.db.models import Q
from rest_framework.decorators import action

class DrillViewSet(viewsets.ModelViewSet):
    queryset = Drill.objects.all()
    serializer_class = DrillSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAssistant]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        queryset = Drill.objects.all()

        # 🔐 Role based visibility
        if user.role == 'coach':
            queryset = queryset.filter(create_By=user)

        elif user.role == 'assistant':
            queryset = queryset.filter(
                Q(assistant_coach=user) | Q(create_By=user)
            ).distinct()

        else:
            queryset = queryset.filter(assigned_members=user).distinct()

        # 🔍 Filters start here

        if params.get('id'):
            queryset = queryset.filter(id=params.get('id'))

        if params.get('create_By'):
            queryset = queryset.filter(create_By_id=params.get('create_By'))

        if params.get('assistant_coach'):
            queryset = queryset.filter(assistant_coach_id=params.get('assistant_coach'))

        if params.get('assign_team'):
            queryset = queryset.filter(assign_team__id=params.get('assign_team'))

        if params.get('assigned_members'):
            queryset = queryset.filter(assigned_members__id=params.get('assigned_members'))

        if params.get('name'):
            queryset = queryset.filter(name__icontains=params.get('name'))

        if params.get('category'):
            queryset = queryset.filter(category__icontains=params.get('category'))

        if params.get('description'):
            queryset = queryset.filter(description__icontains=params.get('description'))

        if params.get('date_created'):
            queryset = queryset.filter(date_created__date=params.get('date_created'))

        if params.get('date_modified'):
            queryset = queryset.filter(date_modified__date=params.get('date_modified'))

        return queryset.distinct()

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
        user = self.request.user

        if user.role in ['coach', 'assistant']:
            # ✅ CHANGE - Coach sees their own blocks, assistant sees blocks of assigned drills
            if user.role == 'coach':
                return Block.objects.filter(drill__create_By=user)
            else:  # assistant
                return Block.objects.filter(drill__assistant_coach=user) | Block.objects.filter(drill__create_By=user)
        else:
            # ✅ CHANGE - Regular members can see blocks of their assigned drills
            return Block.objects.filter(drill__assigned_members=user).distinct()

    def perform_create(self, serializer):
        serializer.save()

    def list(self, request, *args, **kwargs):
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
        try:
            block_id = kwargs.get('pk')

            if not Block.objects.filter(id=block_id).exists():
                return Response({
                    'status': 'error',
                    'message': f'Block with ID {block_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

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

            if not Block.objects.filter(id=block_id).exists():
                return Response({
                    'status': 'error',
                    'message': f'Block with ID {block_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

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

            if not Block.objects.filter(id=block_id).exists():
                return Response({
                    'status': 'error',
                    'message': f'Block with ID {block_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

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
    queryset = Plan.objects.all()
    serializer_class = planSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAssistant]

    def get_queryset(self):
        user = self.request.user
        queryset = Plan.objects.select_related('create_By').prefetch_related(
            'Plan_Block',
            'Plan_Block__drill'
        )

        # ✅ CHANGE - Based on Role-based filtering
        if user.role in ['coach', 'assistant']:
            if user.role == 'coach':
                queryset = queryset.filter(create_By=user)
            else:  # assistant
                # Assistant can see plans of their assigned drills
                queryset = queryset.filter(
                    Plan_Block__drill__assistant_coach=user).distinct()
        else:
            # Regular members can see plans of their assigned drills
            queryset = queryset.filter(
                Plan_Block__drill__assigned_members=user).distinct()

        # Apply date filtering if provided
        date_param = self.request.query_params.get('date', None)
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                queryset = queryset.filter(
                    start_practice_time__date=filter_date)
            except ValueError:
                pass

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        """Override list to provide custom response format with date filtering"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)

            date_param = request.query_params.get('date', None)
            message = 'Plans retrieved successfully'
            if date_param:
                message = f'Plans for {date_param} retrieved successfully'

            return Response({
                'status': 'success',
                'message': message,
                'count': queryset.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to fetch plans',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        # Permission check
        if request.user.role not in ['coach', 'assistant']:
            return Response({
                'status': 'error',
                'message': 'Only coaches and assistants can create plans'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                plan_instance = serializer.save()
                
                response_data = {
                    "status": "success",
                    "message": "Plan created successfully with drills and blocks",
                    "data": planSerializer(plan_instance, context={'request': request}).data
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
            
            return Response({
                "status": "error",
                "message": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                "status": "error",
                "message": "Something went wrong",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        # Permission check
        if request.user.role not in ['coach', 'assistant']:
            return Response({
                'status': 'error',
                'message': 'Only coaches and assistants can update plans'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                serializer.save()
                
                return Response({
                    "status": "success",
                    "message": "Plan updated successfully with drills and blocks",
                    "data": planSerializer(instance, context={'request': request}).data
                }, status=status.HTTP_200_OK)
            
            return Response({
                "status": "error",
                "message": "Update failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Http404:
            return Response({
                "status": "error",
                "message": "Plan not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "error",
                "message": "Update failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance_id = instance.id
            instance.delete()
            return Response({
                "status": "success",
                "message": "Plan deleted successfully",
                "data": {"id": instance_id}
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                "status": "error",
                "message": "Plan not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "error",
                "message": "Failed to delete plan",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def available_members(self, request, pk=None):
        plan_obj = self.get_object()
        serializer = planSerializer(plan_obj, context={'request': request})
        return Response({
            "status": "success",
            "available_members": serializer.data.get('available_members', [])
        })
    
    @action(detail=True, methods=['get'])
    def available_assistants(self, request, pk=None):
        plan_obj = self.get_object()
        serializer = planSerializer(plan_obj, context={'request': request})
        return Response({
            "status": "success",
            "available_assistants": serializer.data.get('available_assistants', [])
        })