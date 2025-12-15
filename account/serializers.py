
from rest_framework import serializers
from .utils import generate_otp
from .models import Profile
from django.core.mail import send_mail, EmailMessage
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework import serializers
from .models import User, Profile, User
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.template.loader import render_to_string
from django.conf import settings
User = get_user_model()

""" ----------------User Serializer------------------- """
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'Fullname', 'email', 'date_joined', 'is_active']
        extra_kwargs = {
            'Fullname': {'required': False},
            'email': {'required': False}
        }
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance



""" ----------------Google Auth Serializer------------------- """



from rest_framework import serializers
import requests
from django.conf import settings
from .models import User, Profile

class GoogleAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()  # Changed from id_token

    def validate(self, attrs):
        token = attrs.get("access_token")
        print("Validating Google access token:", token[:50] + "...")
        
        try:
            # Use access token to get user info
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise serializers.ValidationError("Invalid Google token")
            
            user_info = response.json()
            
            if "email" not in user_info:
                raise serializers.ValidationError("Email not found in token")

            attrs["email"] = user_info["email"]
            attrs["name"] = user_info.get("name", "")
            attrs["picture"] = user_info.get("picture", "")
            return attrs

        except requests.RequestException as e:
            print(f"Token validation error: {e}")
            raise serializers.ValidationError("Failed to validate Google token")

    def create_or_login_user(self):
        email = self.validated_data["email"]
        name = self.validated_data["name"]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "Fullname": name,
                "social_auth_provider": "google",
                "is_active": True,
            }
        )

        Profile.objects.get_or_create(
            user=user,
            defaults={
                "social_auth_provider": "google",
                "is_verified": True,
            }
        )

        return user