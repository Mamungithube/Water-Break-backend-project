from django.shortcuts import render
from django.http import Http404
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status, viewsets
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
    queryset = plan.objects.all()
    serializer_class = planSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAssistant]

    def get_queryset(self):
        user = self.request.user
        queryset = plan.objects.select_related('create_By').prefetch_related(
            'Plan_Block',
            'Plan_Block__drill'
        )
        if user.role in ['coach', 'assistant']:
            return queryset.filter(create_By=user).distinct()
        else:
            from teamapp.models import Team
            user_teams = Team.objects.filter(members=user)
            return queryset.filter(Plan_Block__drill__assign_team__in=user_teams).distinct()

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                blocks = serializer.validated_data.get('Plan_Block', [])
                
                for block in blocks:
                    if block.drill.create_By != request.user:
                        return Response({
                            "status": "error",
                            "message": f"Block '{block.title}' belongs to a drill you did not create."
                        }, status=status.HTTP_400_BAD_REQUEST)

                plan_instance = serializer.save(create_By=request.user)
                
                for block in blocks:
                    block.practice_plan = plan_instance
                    block.save()

                # Clean response format
                return Response({
                    "status": "success",
                    "message": "Plan created successfully",
                    "data": {
                        "id": plan_instance.id,
                        "plan_title": plan_instance.plan_title,
                        "start_practice_time": plan_instance.start_practice_time.strftime("%Y-%m-%d %H:%M:%S") if plan_instance.start_practice_time else None,
                        "end_practice_time": plan_instance.end_practice_time.strftime("%Y-%m-%d %H:%M:%S") if plan_instance.end_practice_time else None,
                        "created_at": plan_instance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": plan_instance.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                }, status=status.HTTP_201_CREATED)

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
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                blocks = serializer.validated_data.get('Plan_Block', [])
                for block in blocks:
                    if block.drill.create_By != request.user:
                        return Response({
                            "status": "error",
                            "message": f"Block '{block.title}' is unauthorized."
                        }, status=status.HTTP_403_FORBIDDEN)

                serializer.save()
                
                # Clean response format
                return Response({
                    "status": "success",
                    "message": "Plan updated successfully",
                    "data": {
                        "id": instance.id,
                        "plan_title": instance.plan_title,
                        "start_practice_time": instance.start_practice_time.strftime("%Y-%m-%d %H:%M:%S") if instance.start_practice_time else None,
                        "end_practice_time": instance.end_practice_time.strftime("%Y-%m-%d %H:%M:%S") if instance.end_practice_time else None,
                        "created_at": instance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": instance.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
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