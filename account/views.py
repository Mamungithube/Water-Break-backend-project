from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from django.shortcuts import redirect
from django.contrib.auth import get_user_model, login
from django.conf import settings
from .serializers import (
    UserSerializer,
    RegistrationSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    teamserializers,
    TeamMemberSerializer
)
from .models import Profile,Team,TeamMember
from rest_framework import viewsets,status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from .utils import generate_otp
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser,AllowAny
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

    def post(self,request):
        serializers = self.serializer_class(data = request.data)
        if serializers.is_valid():
            user = serializers.save()
            return Response({
                "detail" : "Registration Successful! Check your email for OTP verification."
            },status=status.HTTP_201_CREATED)
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
    def post(self,request,*args, **kwargs):
        email = request.data.get('email')
        user = get_object_or_404(User,email=email)
        otp_code = generate_otp()
        user.profile.otp = otp_code
        user.profile.save()

        html_content = render_to_string('send_code.html',{'otp':otp_code,'user':user})

        try:
            msg = EmailMessage(
                subject='Your New OTP Code',
                body=html_content,
                from_email=settings.EMAIL_HOST_USER,
                to = [email],
            )
            msg.content_subtype = "html"
            msg.send()

            return Response({'Message':"OTP has been Resend To Your email"},status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"Error":f'Failed to send email: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        serializer = self.get_serializer(data=request.data, context={"request": request})

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

"""=========================deleted account/views.py code========================="""
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

    def perform_create(self, serializer):
        serializer.save(coach=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
"""================================Team Member View set=================================="""
class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        team_id = self.request.query_params.get('team_id')
        if team_id:
            return self.queryset.filter(team_id=team_id)
        return self.queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Custom endpoint to approve a team member"""
        member = self.get_object()
        
        if request.user != member.team.coach:
            return Response(
                {"detail": "Only the team coach can approve members."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        member.is_role_approved = True
        member.save()
        return Response({'status': 'member approved'})








# from rest_framework import generics, status
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from django.shortcuts import get_object_or_404
# from django.db import transaction

# from .models import User, InvitationToken, TeamMember
# from .serializers import (
#     InvitationTokenCreateSerializer, 
#     InvitationTokenDetailsSerializer, 
#     TeamMemberJoinSerializer
# )

# # --- 1. Coach creates the Invitation Token ---
# class InvitationCreateView(generics.CreateAPIView):
#     serializer_class = InvitationTokenCreateSerializer
#     permission_classes = [IsAuthenticated]

#     def perform_create(self, serializer):
#         # Ensure only a 'coach' can create an invitation
#         if self.request.user.role != 'coach':
#             # Customize this error message/status as needed
#             raise serializers.ValidationError("Only coaches can create invitation tokens.")
            
#         # The coach is the authenticated user
#         instance = serializer.save(coach=self.request.user)
        
#         # You can construct the deep link/URL here if needed for the response
#         # Example: instance.token will be the UUID

# # --- 2. Verify Invitation Token and Fetch Coach Info ---
# class InvitationVerifyView(generics.RetrieveAPIView):
#     serializer_class = InvitationTokenDetailsSerializer
#     # This view is publicly accessible, even before login/signup
#     authentication_classes = [] 
#     permission_classes = []
#     lookup_field = 'token'

#     def get_object(self):
#         # Retrieves the token object and ensures it is valid
#         token_uuid = self.kwargs.get(self.lookup_field)
#         invitation = get_object_or_404(InvitationToken, token=token_uuid)

#         if not invitation.is_valid():
#             # You might want to return a different status or a specific error message
#             raise serializers.ValidationError({"detail": "Invitation token is expired or already used."})
        
#         return invitation

# # --- 3. User joins the Team (Final Step) ---
# class TeamJoinView(generics.GenericAPIView):
#     serializer_class = TeamMemberJoinSerializer
#     permission_classes = [IsAuthenticated] # User must be logged in/signed up

#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         token_uuid = serializer.validated_data['token']
#         selected_role = serializer.validated_data['selected_role']
#         member_user = request.user # The user performing the join operation

#         try:
#             with transaction.atomic():
#                 # Get and lock the token to prevent race conditions
#                 invitation = InvitationToken.objects.select_for_update().get(token=token_uuid)
                
#                 # Double-check validation
#                 if not invitation.is_valid():
#                     return Response({"detail": "Invitation token is expired or already used."}, 
#                                     status=status.HTTP_400_BAD_REQUEST)
                
#                 coach_user = invitation.coach

#                 # 1. Create the TeamMember instance (Role is set by the joining user)
#                 team_member, created = TeamMember.objects.get_or_create(
#                     coach=coach_user,
#                     member=member_user,
#                     defaults={
#                         'role': selected_role,
#                         'is_role_approved': False # Pending approval as per your requirement
#                     }
#                 )

#                 if not created:
#                     return Response({"detail": "You are already a member of this team."}, 
#                                     status=status.HTTP_400_BAD_REQUEST)
                
#                 # 2. Mark the token as used
#                 invitation.is_used = True
#                 invitation.save(update_fields=['is_used'])

#                 # 3. Notification Logic (Placeholder for your system)
#                 # notification_system.send_notification(coach_user, f"New member {member_user.Fullname} joined. Role: {selected_role}")

#                 return Response({
#                     "message": "Successfully joined the team! Approval pending from coach.",
#                     "team_member_id": team_member.id
#                 }, status=status.HTTP_201_CREATED)

#         except InvitationToken.DoesNotExist:
#             return Response({"detail": "Invalid invitation token."}, 
#                             status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             # General error handling
#             return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)