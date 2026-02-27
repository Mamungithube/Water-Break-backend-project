from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
from .models import TeamMember, InvitationToken, Team
from .serializers import TeamMemberSerializer, InvitationTokenSerializer, JoinTeamSerializer, teamserializers
from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from account.models import Notification
from django.db.models import Q
from plan.permissions import IsCoachOrAssistant
from subscription.permissions import CanCreateTeam

# Create your views here.
"""=============================Team view set==========================================="""


class teamviewset(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = teamserializers
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Create action শুধুমাত্র Coach বা Assistant করতে পারবে
        অন্যান্য action-এ শুধু IsAuthenticated যথেষ্ট
        """
        if self.action == 'create':
            return [IsAuthenticated(), IsCoachOrAssistant() , CanCreateTeam()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter teams based on user role"""
        user = self.request.user
        if user.role == 'coach':
            return Team.objects.filter(coach=user)
        return Team.objects.filter(members=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    

    # ========================== 🔑 Invitation Token ==========================
    @action(detail=True, methods=['get'])
    def invitation_token(self, request, pk=None):
        team = self.get_object()

        if request.user != team.coach:
            return Response(
                {"detail": "Only the team coach can view invitation tokens."},
                status=status.HTTP_403_FORBIDDEN
            )

        token = team.get_active_token()
        if not token:
            return Response(
                {"detail": "No active invitation token found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = InvitationTokenSerializer(token)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_token_expiry(self, request, pk=None):
        team = self.get_object()

        if request.user != team.coach:
            return Response(
                {"detail": "Only the team coach can update token expiry."},
                status=status.HTTP_403_FORBIDDEN
            )

        expiry_days = request.data.get('expiry_days')
        expiry_date = request.data.get('expiry_date')

        if not expiry_days and not expiry_date:
            return Response(
                {"detail": "Provide expiry_days or expiry_date."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = team.get_active_token()
        if not token:
            return Response(
                {"detail": "No active invitation token found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if expiry_days:
            token.expires_at = timezone.now() + timedelta(days=int(expiry_days))
        else:
            from django.utils.dateparse import parse_datetime
            parsed_date = parse_datetime(expiry_date)
            if not parsed_date or parsed_date <= timezone.now():
                return Response(
                    {"detail": "Invalid expiry date."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            token.expires_at = parsed_date

        token.save()
        return Response(InvitationTokenSerializer(token).data)

    # ==========================🚪 Join With Token==========================
    @action(detail=False, methods=['post'])
    def join_with_token(self, request):
        serializer = JoinTeamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team_member = serializer.save(user=request.user)
        coach = team_member.team.coach

        Notification.objects.create(
            recipient=coach,
            sender=request.user,
            team=team_member.team,
            notification_type='join_request',
            message=f"{request.user.email} wants to join your team {team_member.team.name}."
            f"{team_member.team.name} as {team_member.get_role_display()}."
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{coach.id}",
            {
                "type": "send_notification",
                "data": {
                    "type": "join_request",
                    "team": team_member.team.name,
                    "user": request.user.email,
                    "role": team_member.role,
                    "role_display": team_member.get_role_display(),
                    "message": (
                        f"{request.user.email} wants to join as "
                        f"{team_member.get_role_display()}"
                    )
                }
            }
        )

        send_mail(
            subject="New Team Join Request",
            message=(
                f"{request.user.email} wants to join your team "
                f"'{team_member.team.name}' as "
                f"{team_member.get_role_display()}.\n\n"
                "Please login to approve or reject the request."
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[coach.email],
            fail_silently=True,
        )

        return Response(
            {"detail": "Join request sent. Waiting for coach approval."},
            status=status.HTTP_201_CREATED
        )

    # ========================== ⏳ Pending Members   =========================="""
    @action(detail=False, methods=['get'], url_path='pending_members')
    def pending_members(self, request):

        if request.user.role != 'coach':
            return Response(
                {"detail": "Only the team coach can view pending members."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            pending_qs = TeamMember.objects.filter(
                team__coach=request.user, 
                is_role_approved=False
            ).select_related('team', 'member')

            serializer = TeamMemberSerializer(
                pending_qs, many=True, context={"request": request}
            )
            return Response(
                {"count": pending_qs.count(), "pending_members": serializer.data}, 
                status=status.HTTP_200_OK
            )
        except Exception as exc:
            return Response(
                {"detail": "Failed to fetch pending members.", "error": str(exc)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

"""================================Team Member View set=================================="""


class TeamMemberViewSet(viewsets.ModelViewSet):
    # queryset = TeamMember.objects.all()
    queryset = TeamMember.objects.select_related('member__profile', 'team').all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated ,]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        
        # Performance optimization: select_related ব্যবহার করা হয়েছে
        queryset = TeamMember.objects.select_related('member__profile', 'team').all()

        # ১. বেস ফিল্টারিং (কে কতটুকু ডাটা দেখতে পারবে)
        
        # ইউজার যদি কোনো টিমে 'assistant' হয় (approved)
        is_assistant_anywhere = TeamMember.objects.filter(
            member=user, role='assistant', is_role_approved=True
        ).exists()

        if user.role == 'coach':
            # কোচ তার নিজের টিমের সব মেম্বার দেখবে (approved + pending)
            queryset = queryset.filter(team__coach=user)
        elif is_assistant_anywhere:
            # অ্যাসিস্ট্যান্ট তার নিজের টিমের মেম্বার এবং অন্যান্য অ্যাপ্রুভড মেম্বারদের দেখবে
            # (লজিক আপনার প্রয়োজন অনুযায়ী ছোট-বড় করতে পারেন)
            queryset = queryset.filter(
                Q(team__memberships__member=user, team__memberships__role='assistant') | 
                Q(is_role_approved=True)
            ).distinct()
        else:
            # সাধারণ প্লেয়াররা শুধু অ্যাপ্রুভড মেম্বারদের দেখবে
            queryset = queryset.filter(is_role_approved=True)

        # ২. ডাইনামিক ফিল্টারিং (Query Params)
        team_param = params.get('team')
        team_name = params.get('team_name')
        role = params.get('role')
        team_position = params.get('team_position')
        is_role_approved = params.get('is_role_approved')
        
        
        if team_param:
            team_ids = team_param.split(',')
            queryset = queryset.filter(team_id__in=team_ids)

        if team_name:
            queryset = queryset.filter(team__name__icontains=team_name)

        if role:
            queryset = queryset.filter(role=role)

        if team_position:
            queryset = queryset.filter(team_position__icontains=team_position)

        if is_role_approved is not None:
            queryset = queryset.filter(is_role_approved=is_role_approved.lower() == 'true')

        return queryset.distinct()

    @action(detail=False, methods=['post'], url_path='handle_request')
    def handle_request(self, request):
        membership_id = request.query_params.get('id')
        action = request.data.get('action')  # 'approve' or 'reject'
    
        if not membership_id:
            return Response(
                {"detail": "Query param 'id' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        if action not in ['approve', 'reject']:
            return Response(
                {"detail": "action must be 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        try:
            membership = TeamMember.objects.get(pk=membership_id)
        except TeamMember.DoesNotExist:
            return Response(
                {"detail": "Membership not found."},
                status=status.HTTP_404_NOT_FOUND
            )
    
        if request.user != membership.team.coach:
            return Response(
                {"detail": f"You are not the coach of team '{membership.team.name}'."},
                status=status.HTTP_403_FORBIDDEN
            )
    
        if membership.is_role_approved:
            return Response(
                {"detail": "Member is already approved."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        if action == 'approve':
            membership.is_role_approved = True
            membership.save()
            return Response(
                {"detail": f"Approved successfully in team '{membership.team.name}'."},
                status=status.HTTP_200_OK
            )
    
        elif action == 'reject':
            membership.delete()
            return Response(
                {"detail": "Join request rejected."},
                status=status.HTTP_200_OK
            )


"""================================Invitation Token ViewSet=================================="""


class InvitationTokenViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InvitationToken.objects.all()
    serializer_class = InvitationTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Coach can only see their own tokens"""
        user = self.request.user
        if user.role == 'coach':
            return InvitationToken.objects.filter(coach=user)
        return InvitationToken.objects.none()
