from rest_framework import serializers

from account.models import Profile
from .models import TeamMember, InvitationToken , Team
from django.contrib.auth import get_user_model
User = get_user_model()

# ==================== Invitation Token Serializer ====================
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


# ==================== Team Serializer ====================
class teamserializers(serializers.ModelSerializer):
    coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='coach'), 
        required=False,
        allow_null=True
    )
    active_invitation_token = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()  # ✅ নতুন ফিল্ড
    
    class Meta:
        model = Team
        fields = [
            'id', 'coach', 'name', 'team_profile_pic',
            'created_at', 'updated_at', 'active_invitation_token', 
            'members_count', 'members'  # ✅ fields-এ যোগ করুন
        ]
        read_only_fields = ['coach', 'created_at', 'updated_at']
    
    def get_active_invitation_token(self, obj):
        token = obj.get_active_token()
        if token:
            return InvitationTokenSerializer(token, context=self.context).data
        return None
    
    def get_members_count(self, obj):
        return obj.memberships.filter(is_role_approved=True).count()
    
    def get_members(self, obj):  # ✅ নতুন method
        memberships = obj.memberships.filter(is_role_approved=True).select_related('member__profile')
        return TeamMemberSerializer(memberships, many=True, context=self.context).data
    
    def create(self, validated_data):
        validated_data['coach'] = self.context['request'].user
        team = super().create(validated_data)
        InvitationToken.objects.create(
            team=team,
            coach=self.context['request'].user
        )
        return team


# ==================== Team Member Serializer ====================
class TeamMemberSerializer(serializers.ModelSerializer):
    member_email = serializers.EmailField(source='member.email', read_only=True)
    member_name = serializers.SerializerMethodField()
    member_profile_picture = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            'id', 'team_position', 'team', 'team_name', 'member', 'member_email', 'member_name',
            'member_profile_picture', 'role', 'role_display', 'is_role_approved', 'joined_at'
        ]
        read_only_fields = ['is_role_approved', 'joined_at', 'member_email']
        
        # এখানে team_position কে স্পষ্টভাবে রিকোয়ার্ড করে দিন
        extra_kwargs = {
            'team_position': {
                'required': True,
                'allow_blank': False,
                'error_messages': {
                    'required': 'Position is required.',
                    'blank': 'Position cannot be empty.'
                }
            }
        }

    def get_member_profile_picture(self, obj):
        try:
            # member (User) থেকে তার প্রোফাইলে যেতে হবে, তারপর পিকচার
            if obj.member.profile and obj.member.profile.profile_picture:
                request = self.context.get('request')
                image_url = obj.member.profile.profile_picture.url
                if request:
                    return request.build_absolute_uri(image_url)
                return image_url
        except (AttributeError, Profile.DoesNotExist):
            # যদি কোনো ইউজারের প্রোফাইল ক্রিয়েট করা না থাকে তবে এরর না দিয়ে None আসবে
            return None
        return None

    def get_member_name(self, obj):
        return f"{obj.member.first_name} {obj.member.last_name}".strip() or obj.member.email

    def validate(self, attrs):
        # আপনার বর্তমান ভ্যালিডেশন কোড...
        team = attrs.get('team')
        member = attrs.get('member')
        team_position = attrs.get('team_position')

        if not team_position:
            raise serializers.ValidationError({"team_position": "This field is required."})

        if team and member and team.coach == member:
            raise serializers.ValidationError("Coach cannot join their own team as a member.")
        
        if team and member:
            if TeamMember.objects.filter(team=team, member=member).exists():
                raise serializers.ValidationError("This member is already part of the team.")
        
        return attrs


# ==================== Join Team Serializer ====================
class JoinTeamSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=10)
    role = serializers.ChoiceField(choices=TeamMember.ROLE_CHOICES)
    
    # এখানে পরিবর্তন করুন:
    team_position = serializers.CharField(
        max_length=25, 
        required=False,     # এটি এখন আর বাধ্যতামূলক নয়
        allow_blank=True,   # খালি স্ট্রিংও গ্রহণ করবে
        allow_null=True     # নাল ভ্যালুও গ্রহণ করবে
    )

    def validate_token(self, value):
        # ... আপনার আগের কোড ...
        pass

    def save(self, user):
        token = self.validated_data['token']
        role = self.validated_data['role']
        
        # .get() ব্যবহার করুন যাতে ডাটা না পাঠালে এরর না খায়
        team_position = self.validated_data.get('team_position', None) 
        
        invitation = InvitationToken.objects.get(token=token)
        
        if invitation.team.coach == user:
            raise serializers.ValidationError("Coach cannot join their own team.")
        
        if TeamMember.objects.filter(team=invitation.team, member=user).exists():
            raise serializers.ValidationError("You are already requested to be a member of this team.")
        
        team_member = TeamMember.objects.create(
            team=invitation.team,
            member=user,
            role=role,
            team_position=team_position,
            is_role_approved=False
        )
        
        return team_member
