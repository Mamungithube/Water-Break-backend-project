from re import search
from django.conf import settings
import requests
from rest_framework import (
    status
)
from .serializers import (
    UserSerializer, 
    GoogleAuthSerializer,
    RegistrationSerializer
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

from django.core.mail import EmailMessage
User = get_user_model()

from .google_auth import get_or_create_google_user, generate_jwt_for_user
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


class GoogleLoginAPIView(APIView):
    """
    Receives Google id_token from frontend and returns JWT tokens.
    """
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or get user
        user = serializer.create_or_login_user()
        
        # ✅ AUTO DJANGO ACTIVE - Session Login
        login(request, user)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "email": user.email,
                "name": user.Fullname,
                "id": user.id
            }
        }, status=status.HTTP_200_OK)




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
        return Response(serializers.error_messages,status=status.HTTP_400_BAD_REQUEST)
    



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

