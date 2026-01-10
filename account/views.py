from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from django.shortcuts import redirect
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.conf import settings
from .serializers import (
    UserSerializer,
    RegistrationSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    teamserializers,
    TeamMemberSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    InvitationTokenSerializer,
    JoinTeamSerializer,
    NotificationSerializer
)
from .models import InvitationToken, Profile, Team, TeamMember, Notification
from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from .utils import generate_otp
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db.models import Q  # For search
from rest_framework.decorators import action
from django.conf import settings
from django.core.mail import EmailMessage
User = get_user_model()


class UserAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk=None):
        if pk:
            user = get_object_or_404(User, pk=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data)

        users = User.objects.all()

        email = request.GET.get('email')
        search = request.GET.get('search')

        if email:
            users = users.filter(email__icontains=email)

        if search:
            users = users.filter(
                Q(Fullname__icontains=search) |
                Q(email__icontains=search)
            )
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        paginated_users = users[start:end]

        serializer = UserSerializer(paginated_users, many=True)
        total_users = users.count()

        return Response({
            'total': total_users,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_users + page_size - 1) // page_size,
            'results': serializer.data
        })

    def post(self, request):
        is_many = isinstance(request.data, list)
        serializer = UserSerializer(data=request.data, many=is_many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


""" ----------------Gooooooooooogle auth  view------------------- """


class GoogleLoginInitView(APIView):
    """
    Step 1: Generate Google OAuth URL and redirect user
    """

    def get(self, request):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_OAUTH2_REDIRECT_URI],
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )

        flow.redirect_uri = settings.GOOGLE_OAUTH2_REDIRECT_URI

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        request.session['google_auth_state'] = state
        return Response({
            'authorization_url': authorization_url
        }, status=status.HTTP_200_OK)


class GoogleCallbackView(APIView):
    """
    Step 2: Handle Google callback and create/login user
    """

    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')

        saved_state = request.session.get('google_auth_state')
        if not state or state != saved_state:
            return Response(
                {'error': 'Invalid state parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                        "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [settings.GOOGLE_OAUTH2_REDIRECT_URI],
                    }
                },
                scopes=[
                    'openid',
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile'
                ]
            )

            flow.redirect_uri = settings.GOOGLE_OAUTH2_REDIRECT_URI

            flow.fetch_token(code=code)
            credentials = flow.credentials
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                settings.GOOGLE_OAUTH2_CLIENT_ID
            )

            email = id_info.get('email')
            name = id_info.get('name', '')
            picture = id_info.get('picture', '')

            if not email:
                return Response(
                    {'error': 'Email not found in token'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user, created = User.objects.get_or_create(email=email)

            print(f"Saving user: {email}, Name: {name}")
            user.Fullname = name
            user.social_auth_provider = "google"
            user.is_active = True
            user.save()
            profile, p_created = Profile.objects.get_or_create(user=user)
            profile.social_auth_provider = "google"
            profile.is_verified = True

            if picture:
                profile.profile_image = picture
            profile.save()

            login(request, user)

            refresh = RefreshToken.for_user(user)

            frontend_url = f"http://localhost:3000/auth/callback?access={str(refresh.access_token)}&refresh={str(refresh)}"

            return redirect(frontend_url)

            # return Response({
            #     "refresh": str(refresh),
            #     "access": str(refresh.access_token),
            #     "user": {
            #         "email": user.email,
            #         "name": user.Fullname,
            #         "id": user.id
            #     }
            # }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Google OAuth error: {str(e)}")
            return Response(
                {'error': f'Authentication failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


""" ----------------Registration view------------------- """


class RegisterApiView(APIView):
    serializer_class = RegistrationSerializer

    def post(self, request):
        serializers = self.serializer_class(data=request.data)
        if serializers.is_valid():
            user = serializers.save()
            return Response({
                "detail": "Registration Successful! Check your email for OTP verification."
            }, status=status.HTTP_201_CREATED)
        return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)


""" ----------------verify OTP API view------------------- """


class VerifyOTPApiView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        otp = request.data.get('otp')

        user = get_object_or_404(User, email=email)
        profile = user.profile

        if profile.otp == otp:
            user.is_active = True
            user.save(update_fields=['is_active'])
            profile.otp = None
            profile.save(update_fields=['otp'])
            return Response({'Message': 'Account Activate Successfully'}, status=status.HTTP_200_OK)
        return Response({'Error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)


""" ----------------Resend OTP API view------------------- """


class ResendOTPApiView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        user = get_object_or_404(User, email=email)
        otp_code = generate_otp()
        user.profile.otp = otp_code
        user.profile.save()

        html_content = render_to_string(
            'send_code.html', {'otp': otp_code, 'user': user})

        try:
            msg = EmailMessage(
                subject='Your New OTP Code',
                body=html_content,
                from_email=settings.EMAIL_HOST_USER,
                to=[email],
            )
            msg.content_subtype = "html"
            msg.send()

            return Response({'Message': "OTP has been Resend To Your email"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"Error": f'Failed to send email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


""" ----------------Forgot Password view------------------- """


class ForgotPasswordAPIView(APIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'detail': 'Email not registered. Please sign up.'}, status=status.HTTP_404_NOT_FOUND)

            user.set_password(password)
            user.save()

            return Response({'detail': 'Password has been reset successfully'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


""" -------------------Change Password view----------------------- """


class ChangePasswordViewSet(viewsets.GenericViewSet):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        user = request.user
        serializer = self.get_serializer(
            data=request.data, context={"request": request})

        if serializer.is_valid():
            if not user.check_password(serializer.validated_data["old_password"]):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response({"message": "Password changed successfully!"}, status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


""" ----------------Login view------------------- """


class LoginAPIView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(email=email, password=password)

            if user:
                if not user.is_active:
                    return Response(
                        {'error': 'Account not activated. Verify OTP first!'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                login(request, user)

                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)

                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'Fullname': user.Fullname,
                        'is_staff': user.is_staff,
                        "role": user.role
                    }
                }, status=status.HTTP_200_OK)

            return Response(
                {'error': 'Email and password do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BaseResponseMixin:
    def success_response(self, message, data=None, status_code=status.HTTP_200_OK):
        response = {
            "success": True,
            "message": message,
            "data": data
        }
        return Response(response, status=status_code)

    def error_response(self, message, data=None, status_code=status.HTTP_400_BAD_REQUEST):
        response = {
            "success": False,
            "message": message,
            "data": data
        }
        return Response(response, status=status_code)


"""========================= deleted account/views.py code========================="""


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        user.delete()
        return Response(
            {"message": "Account deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


"""=============================Team view set==========================================="""


class teamviewset(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = teamserializers
    permission_classes = [IsAuthenticated]

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
    @action(detail=True, methods=['get'])
    def pending_members(self, request, pk=None):
        team = self.get_object()

        if request.user != team.coach:
            return Response(
                {"detail": "Only the team coach can view pending members."},
                status=status.HTTP_403_FORBIDDEN
            )

        pending = TeamMember.objects.filter(
            team=team,
            is_role_approved=False
        )
        serializer = TeamMemberSerializer(pending, many=True)
        return Response(serializer.data)


"""================================Team Member View set=================================="""


class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        team_id = self.request.query_params.get('team_id')

        if user.role == 'coach':
            if team_id:
                return TeamMember.objects.filter(team_id=team_id, team__coach=user)

            return TeamMember.objects.filter(team__coach=user)

        queryset = TeamMember.objects.filter(is_role_approved=True)
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        return queryset

    @action(detail=True, methods=['post'])
    def approve_member(self, request, pk=None):
        try:
            membership = TeamMember.objects.get(pk=pk)
        except TeamMember.DoesNotExist:
            return Response({"detail": "Membership request not found."}, status=404)

        if request.user != membership.team.coach:
            return Response(
                {"detail": f"You are not the coach of team '{membership.team.name}'."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        if membership.is_role_approved:
            return Response(
                {"detail": f"Member already approved in team '{membership.team.name}'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        membership.is_role_approved = True
        membership.save()

        return Response(
            {"detail": f"Approved for team '{membership.team.name}' successfully."}, 
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def reject_member(self, request, pk=None):
        membership_obj = self.get_object()
        team = membership_obj.team

        if request.user != team.coach:
            return Response(
                {"detail": "Only coach can reject members."},
                status=status.HTTP_403_FORBIDDEN
            )
    
        # Reject/delete the membership targeted by this detail route
        membership = membership_obj
        if membership.is_role_approved:
            return Response({"detail": "Cannot reject an already approved member."}, status=status.HTTP_400_BAD_REQUEST)

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


"""------------------------Profile Detail View-----------------------------------"""


class ProfileDetailsView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = Profile.objects.get_or_create(
            user=self.request.user)
        return profile


"""------------------------Notification view--------------------------- """


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')


""" ------------------------Profile UpdateView view--------------------------- """


class ProfileUpdateView(generics.UpdateAPIView):
    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Get or create profile for the current user
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile  

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return full profile data after update
        profile_serializer = ProfileSerializer(instance, context=self.get_serializer_context())
        return Response(profile_serializer.data)