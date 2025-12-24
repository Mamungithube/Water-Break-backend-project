
from rest_framework import serializers
from .utils import generate_otp
from django.core.mail import send_mail, EmailMessage
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from .models import User, Profile, TeamMember,Team
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.template.loader import render_to_string
from django.conf import settings
from django.forms import fields
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




""" ----------------registation Serializer------------------- """


class RegistrationSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only = True)

    class Meta :
        model = User 
        fields = ['email','password','confirm_password']
        extra_kwargs = {
            'password':{'write_only' : True},
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
        Profile.objects.create(user=user, otp=otp)
        # Send OTP via email
        subject = 'Your OTP Code - Verify Your Account'
        html_content = render_to_string('send_code.html', {'otp': otp, 'user': user}) 
        
        try:
            msg = EmailMessage(
                subject=subject, 
                body=html_content, 
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email], 
            )
            msg.content_subtype = "html" 
            msg.send()

        except Exception as e:         
            print(f"Failed to send email to {user.email}: {str(e)}")
            pass 
            
        return user
    

"""----------------------------reset password serializer---------------------------"""


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField() 
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    



""" ----------------Change Password Serializer------------------- """


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context['request'].user)
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "New password and confirm password do not match."})
        return data
    

""" ----------------Login view------------------- """


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


""" ----------------User Login view------------------- """
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


"""=============================Team serializers========================="""

class teamserializers(serializers.ModelSerializer):
    coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='coach'), 
        required=False,  # required=False যাতে ফ্রন্টএন্ড থেকে পাঠাতে না হয়
        allow_null=True
    )
    
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ['coach']  # শুধু রিড অনলি করলে হবে না
    
    def create(self, validated_data):
        # স্বয়ংক্রিয়ভাবে বর্তমান ইউজারকে কোচ হিসেবে সেট করুন
        validated_data['coach'] = self.context['request'].user
        return super().create(validated_data)
    
"""=============================Team Member serializers========================="""
class TeamMemberSerializer(serializers.ModelSerializer):
    member_email = serializers.EmailField(source='member.email', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            'id', 'team', 'member', 'member_email', 
            'role', 'role_display', 'is_role_approved', 'joined_at'
        ]
        read_only_fields = ['is_role_approved', 'joined_at']

    def validate(self, attrs):
        instance = TeamMember(**attrs)
        try:
            instance.clean()
        except serializers.ValidationError as e:
            raise serializers.ValidationError(e.message)
        return attrs
    



"""========================================profile serializers=============================="""

class ProfileSerializer(serializers.ModelSerializer):
    fullname = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['fullname', 'email', 'profile_picture']

    def get_fullname(self, obj):
        return getattr(getattr(obj, 'user', None), 'Fullname', '') or ''

    def get_email(self, obj):
        return getattr(getattr(obj, 'user', None), 'email', '') or ''


"""==============================================profile update serializers========================="""

class ProfileUpdateSerializer(serializers.ModelSerializer):
    # expose frontend-friendly `fullname` but map to `user.Fullname` on save
    fullname = serializers.CharField(source='user.Fullname', required=False, allow_blank=True)

    class Meta:
        model = Profile
        fields = ['fullname', 'profile_picture']

    def update(self, instance, validated_data):
        # handle nested user data (source='user.Fullname')
        user_data = validated_data.pop('user', {})
        if 'Fullname' in user_data:
            setattr(instance.user, 'Fullname', user_data['Fullname'])
            instance.user.save()

        # update remaining profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
