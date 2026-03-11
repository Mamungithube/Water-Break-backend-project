from rest_framework import serializers
from .utils import generate_otp
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile, Notification, DeviceToken
from django.contrib.auth import get_user_model, password_validation
from .tasks import send_otp_email_task
from django.utils import timezone 

User = get_user_model()

# ==================== User Serializer ====================


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


# ==================== Registration Serializer ====================
class RegistrationSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        password_validation.validate_password(data['password'])
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        user.is_active = False
        user.save()
        otp = generate_otp()
        Profile.objects.create(user=user, otp=otp, otp_created_at=timezone.now())

        send_otp_email_task.delay(user.email, otp)

        return user

# ==================== Reset Password Serializer ====================


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data


# ==================== Change Password Serializer ====================
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        password_validation.validate_password(
            value, self.context['request'].user)
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "New password and confirm password do not match."})
        return data


# ==================== Login Serializer ====================
class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


# ==================== User Login Serializer ====================
class UserLoginSerializer(serializers.ModelSerializer):
    tokens = serializers.SerializerMethodField()

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    class Meta:
        model = User
        fields = ['email', 'tokens']


# ==================== Notification Serializer ====================
class NotificationSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    sender_fullname = serializers.CharField(
        source='sender.Fullname', read_only=True)
    team_name = serializers.CharField(
        source='team.name', read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'sender_email', 'sender_fullname',
            'team', 'team_name', 'notification_type', 'message',
            'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at']


# ==================== DeviceToken Serializer ====================

class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['id', 'token', 'platform', 'created_at']
        read_only_fields = ['id', 'created_at']


# ==================== Profile Serializer ====================
class ProfileSerializer(serializers.ModelSerializer):
    fullname = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = Profile
        fields = ['fullname', 'email', 'profile_picture', 'role']

    def get_fullname(self, obj):
        return getattr(getattr(obj, 'user', None), 'Fullname', '') or ''

    def get_email(self, obj):
        return getattr(getattr(obj, 'user', None), 'email', '') or ''


class ProfileUpdateSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='user.Fullname', required=False)

    class Meta:
        model = Profile
        fields = ['fullname', 'profile_picture']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if 'Fullname' in user_data:
            instance.user.Fullname = user_data['Fullname']
            instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
