from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.conf import settings
from .serializers import (
    UserSerializer,
    RegistrationSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    NotificationSerializer,
    DeviceTokenSerializer,
)
from .models import Profile, Notification
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

            # print(f"Saving user: {email}, Name: {name}")
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
        
        except Exception as e:
            print(f"Google OAuth error: {str(e)}")
            return Response(
                {'error': f'Authentication failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


""" ----------------Registration view------------------- """

class RegisterApiView(APIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        # Validate input
        if not request.data:
            return Response(
                {"success": False, "message": "Request body cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(data=request.data)
        
        # Check serializer validity
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Validation failed. Please check your input.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Attempt to save user and send OTP
        try:
            user = serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Registration successful! An OTP verification code has been sent to your email. Please check your inbox.",
                    "data": {
                        "user_id": user.id,
                        "email": user.email,
                        "message": "Please verify your email with the OTP to activate your account.",
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            # Handle duplicate email or other model errors
            error_message = str(e)
            if "email" in error_message.lower() or "unique" in error_message.lower():
                return Response(
                    {
                        "success": False,
                        "message": "An account with this email already exists. Please log in or use a different email.",
                        "errors": {"email": ["Email already registered."]},
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            
            # Generic server error for unexpected exceptions
            return Response(
                {
                    "success": False,
                    "message": "An error occurred during registration. Please try again later.",
                    "errors": {"detail": [str(e)]},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


""" ----------------verify OTP API view------------------- """

class VerifyOTPApiView(APIView):
    """OTP verification endpoint.
    
    Expects `email` and `otp` in the request body.
    Activates user account after successful OTP verification.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Validate request body is not empty
        if not request.data:
            return Response(
                {"success": False, "message": "Request body cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract and validate email
        email = request.data.get('email', '').strip()
        if not email:
            return Response(
                {
                    "success": False,
                    "message": "Email is required.",
                    "errors": {"email": ["Email field cannot be empty."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract and validate OTP
        otp = request.data.get('otp', '').strip()
        if not otp:
            return Response(
                {
                    "success": False,
                    "message": "OTP is required.",
                    "errors": {"otp": ["OTP field cannot be empty."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "No account found with this email address.",
                    "errors": {"email": ["User not registered."]},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user is already active
        if user.is_active:
            return Response(
                {
                    "success": False,
                    "message": "This account is already activated.",
                    "errors": {"detail": ["Account already verified."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if profile exists
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "User profile not found. Please contact support.",
                    "errors": {"detail": ["Profile does not exist."]},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Check if OTP exists in profile
        if not profile.otp:
            return Response(
                {
                    "success": False,
                    "message": "No OTP found for this account. Please request a new OTP.",
                    "errors": {"otp": ["OTP has expired or not set."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify OTP (case-insensitive for safety)
        if profile.otp.strip().upper() != otp.upper():
            return Response(
                {
                    "success": False,
                    "message": "The OTP you entered is incorrect.",
                    "errors": {"otp": ["Invalid OTP. Please try again."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # OTP is valid — activate the user account
        try:
            user.is_active = True
            user.save(update_fields=['is_active'])
            
            profile.otp = None
            profile.save(update_fields=['otp'])

            return Response(
                {
                    "success": True,
                    "message": "Account activated successfully. You can now log in.",
                    "data": {
                        "user_id": user.id,
                        "email": user.email,
                        "is_active": user.is_active,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": "Failed to activate account. Please try again later.",
                    "errors": {"detail": [str(e)]},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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

            return Response({'Message': "OTP has been Resend To Your email. please check your email inbox"}, status=status.HTTP_200_OK)

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
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"success": False, "message": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.get_serializer(data=request.data, context={"request": request})

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            return Response(
                {"success": False, "message": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        old_password = serializer.validated_data.get("old_password")
        new_password = serializer.validated_data.get("new_password")

        if not user.check_password(old_password):
            return Response(
                {"success": False, "message": "The provided current password is incorrect.", "errors": {"old_password":"Incorrect password.please try again."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the new password against Django validators
        try:
            from django.contrib.auth import password_validation

            password_validation.validate_password(new_password, user)
        except Exception as exc:
            # password_validation raises ValidationError with a list of messages
            return Response(
                {"success": False, "message": "New password did not meet requirements.", "errors": exc.messages if hasattr(exc, 'messages') else [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Everything OK — change the password
        try:
            user.set_password(new_password)
            user.save()
        except Exception as exc:
            return Response(
                {"success": False, "message": "Failed to update password. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"success": True, "message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


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




"""------------------------Profile Detail View-----------------------------------"""

class ProfileDetailsView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = Profile.objects.get_or_create(
            user=self.request.user)
        return profile

"""------------------------Notification view--------------------------- """

class DeviceTokenViewSet(viewsets.ModelViewSet):
    """Register/unregister device tokens for the authenticated user."""
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.device_tokens.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter notifications for the current user, ordered by most recent."""
        try:
            return Notification.objects.filter(
                recipient=self.request.user
            ).order_by('-created_at')
        except Exception as e:
            # Return empty queryset on error instead of crashing
            return Notification.objects.none()

    def list(self, request, *args, **kwargs):
        """Retrieve all notifications for the authenticated user."""
        try:
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            
            # Validate pagination parameters
            if page < 1:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid page number.",
                        "errors": {"page": ["Page must be greater than 0."]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            if page_size < 1 or page_size > 100:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid page size.",
                        "errors": {"page_size": ["Page size must be between 1 and 100."]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Get filter by notification type (optional)
            notification_type = request.GET.get('notification_type', '').strip()
            
            # Get base queryset
            queryset = self.get_queryset()
            
            # Apply type filter if provided
            if notification_type:
                queryset = queryset.filter(notification_type=notification_type)
            
            # Get unread only filter (optional)
            unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
            if unread_only:
                queryset = queryset.filter(is_read=False)
            
            # Calculate pagination
            total_count = queryset.count()
            start = (page - 1) * page_size
            end = start + page_size
            paginated_notifications = queryset[start:end]
            
            # Serialize
            serializer = self.get_serializer(paginated_notifications, many=True)
            
            return Response(
                {
                    "success": True,
                    "message": "Notifications retrieved successfully.",
                    "data": {
                        "total": total_count,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (total_count + page_size - 1) // page_size,
                        "notifications": serializer.data,
                    },
                },
                status=status.HTTP_200_OK,
            )
        
        except ValueError:
            return Response(
                {
                    "success": False,
                    "message": "Invalid pagination parameters.",
                    "errors": {"detail": ["Page and page_size must be valid integers."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": "Failed to retrieve notifications. Please try again later.",
                    "errors": {"detail": [str(e)]},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Retrieve a single notification by ID."""
        try:
            # Get the notification
            notification = self.get_queryset().get(pk=pk)
            
            # Mark as read
            if not notification.is_read:
                notification.is_read = True
                notification.save(update_fields=['is_read'])
            
            serializer = self.get_serializer(notification)
            
            return Response(
                {
                    "success": True,
                    "message": "Notification retrieved successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        
        except Notification.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Notification not found.",
                    "errors": {"id": ["Notification with this ID does not exist."]},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": "Failed to retrieve notification. Please try again later.",
                    "errors": {"detail": [str(e)]},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
    
