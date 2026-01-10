
from rest_framework import serializers
from .utils import generate_otp
from django.core.mail import send_mail, EmailMessage
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from .models import User, Profile, TeamMember,Team, Notification
from django.contrib.auth import get_user_model,password_validation
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

from rest_framework import serializers
from .models import Team, TeamMember, InvitationToken
from django.contrib.auth import get_user_model

User = get_user_model()

class InvitationTokenSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    coach_email = serializers.CharField(source='coach.email', read_only=True)
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = InvitationToken
        fields = [
            'id', 'team', 'team_name', 'coach', 'coach_email', 
            'token', 'expires_at', 'created_at', 'is_active', 'is_valid'
        ]
        read_only_fields = ['token', 'coach', 'created_at']
    
    def get_is_valid(self, obj):
        return obj.is_valid()


"""=============================Team serializers=========================`"""


class teamserializers(serializers.ModelSerializer):
    coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='coach'), 
        required=False,
        allow_null=True
    )
    active_invitation_token = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            'id', 'coach', 'name', 'team_profile_pic',
            'created_at', 'updated_at', 'active_invitation_token', 'members_count'
        ]
        read_only_fields = ['coach', 'created_at', 'updated_at']
    
    def get_active_invitation_token(self, obj):
        token = obj.get_active_token()
        if token:
            return InvitationTokenSerializer(
                token,
                context = self.context,
            ).data
        return None
    
    def get_members_count(self, obj):
        return obj.memberships.filter(is_role_approved=True).count()
    
    def create(self, validated_data):
        # স্বয়ংক্রিয়ভাবে বর্তমান ইউজারকে কোচ হিসেবে সেট করুন
        validated_data['coach'] = self.context['request'].user
        team = super().create(validated_data)
        
        # Automatically create invitation token
        InvitationToken.objects.create(
            team=team,
            coach=self.context['request'].user
        )
        
        return team


"""=============================Team Member serializers========================="""
class TeamMemberSerializer(serializers.ModelSerializer):
    member_email = serializers.EmailField(source='member.email', read_only=True)
    member_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            'id', 'team', 'team_name', 'member', 'member_email', 'member_name',
            'role', 'role_display', 'is_role_approved', 'joined_at'
        ]
        read_only_fields = ['is_role_approved', 'joined_at', 'member_email']
    
    def get_member_name(self, obj):
        return f"{obj.member.first_name} {obj.member.last_name}".strip() or obj.member.email

    def validate(self, attrs):
        team = attrs.get('team')
        member = attrs.get('member')
        
        # Check if coach is trying to join their own team
        if team and member and team.coach == member:
            raise serializers.ValidationError(
                "Coach cannot join their own team as a member."
            )
        
        # Check if member already exists in team
        if team and member:
            if TeamMember.objects.filter(team=team, member=member).exists():
                raise serializers.ValidationError(
                    "This member is already part of the team."
                )
        
        return attrs


"""=============================Join Team with Token Serializer========================="""
class JoinTeamSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=10)
    role = serializers.ChoiceField(choices=TeamMember.ROLE_CHOICES)
    
    def validate_token(self, value):
        try:
            invitation = InvitationToken.objects.get(token=value.upper())
            if not invitation.is_valid():
                raise serializers.ValidationError("This invitation token has expired or is inactive.")
            return value.upper()
        except InvitationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token.")
    
    def save(self, user):
        token = self.validated_data['token']
        role = self.validated_data['role']
        
        invitation = InvitationToken.objects.get(token=token)
        
        # Check if user is the coach
        if invitation.team.coach == user:
            raise serializers.ValidationError("Coach cannot join their own team.")
        
        # Check if already a member
        if TeamMember.objects.filter(team=invitation.team, member=user).exists():
            raise serializers.ValidationError("You are already a member of this team.")
        
        # Create team member (pending approval)
        team_member = TeamMember.objects.create(
            team=invitation.team,
            member=user,
            role=role,
            is_role_approved=False  # Needs coach approval
        )
        
        return team_member

"""=============================Notification Serializer========================="""

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


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
    fullname = serializers.CharField(source='user.Fullname', required=False)

    class Meta:
        model = Profile
        fields = ['fullname', 'profile_picture']

    def update(self, instance, validated_data):
        # Update User Fullname
        user_data = validated_data.pop('user', {})
        if 'Fullname' in user_data:
            instance.user.Fullname = user_data['Fullname']
            instance.user.save()
        
        # Update Profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance