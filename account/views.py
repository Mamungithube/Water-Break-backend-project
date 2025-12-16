from re import search
from django.conf import settings
import requests
from rest_framework import (
    status
)
from .serializers import (
    UserSerializer, 
    RegistrationSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    LoginSerializer
)
from .models import Profile
from rest_framework import viewsets
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import EmailMultiAlternatives,send_mail
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from .utils import generate_otp
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from django.contrib.auth import get_user_model
from rest_framework import status
from django.db.models import Q  # For search
from rest_framework.decorators import action
from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework.permissions import AllowAny
User = get_user_model()

import requests

class UserAPIView(APIView):
    # permission_classes = [IsAdminUser]

    def get(self, request, pk=None):
        if pk:
            user = get_object_or_404(User, pk=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data)

        users = User.objects.all()

        # Query params
        email = request.GET.get('email')
        search = request.GET.get('search')

        if email:
            users = users.filter(email__icontains=email)

        if search:
            users = users.filter(
                Q(Fullname__icontains=search) |
                Q(email__icontains=search)
            )

        # ✅ Pagination parameters
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


from django.contrib.auth import get_user_model, login
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, serializers
from django.conf import settings
from django.shortcuts import redirect
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
import os

User = get_user_model()

class GoogleLoginInitView(APIView):
    """
    Step 1: Generate Google OAuth URL and redirect user
    """
    def get(self, request):
        # Google OAuth Flow তৈরি করুন
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
        
        # Authorization URL তৈরি করুন
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # প্রতিবার consent চাইবে
        )
        
        # State session এ save করুন (CSRF protection)
        request.session['google_auth_state'] = state
        
        return Response({
            'authorization_url': authorization_url
        }, status=status.HTTP_200_OK)


class GoogleCallbackView(APIView):
    """
    Step 2: Handle Google callback and create/login user
    """
    def get(self, request):
        # Authorization code এবং state পান
        code = request.GET.get('code')
        state = request.GET.get('state')
        
        # State verification (CSRF protection)
        saved_state = request.session.get('google_auth_state')
        if not state or state != saved_state:
            return Response(
                {'error': 'Invalid state parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # OAuth flow complete করুন
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
            
            # Authorization code দিয়ে token পান
            flow.fetch_token(code=code)
            
            # Credentials থেকে ID token verify করুন
            credentials = flow.credentials
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                settings.GOOGLE_OAUTH2_CLIENT_ID
            )
            
            # User তথ্য extract করুন
            email = id_info.get('email')
            name = id_info.get('name', '')
            picture = id_info.get('picture', '')
            
            if not email:
                return Response(
                    {'error': 'Email not found in token'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # User তৈরি বা খুঁজে আনুন
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "Fullname": name,
                    "social_auth_provider": "google",
                    "is_active": True,
                }
            )
            
            # Profile তৈরি বা update করুন
            from .models import Profile  # আপনার Profile model import করুন
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    "social_auth_provider": "google",
                    "is_verified": True,
                }
            )
            
            # Django session login
            login(request, user)
            
            # JWT tokens generate করুন
            refresh = RefreshToken.for_user(user)
            
            # Frontend এ redirect করুন tokens সহ
            frontend_url = f"http://localhost:3000/auth/callback?access={str(refresh.access_token)}&refresh={str(refresh)}"
            
            return redirect(frontend_url)
            
            # অথবা JSON response পাঠান (যদি API হিসেবে ব্যবহার করতে চান)
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
from rest_framework.permissions import AllowAny

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
