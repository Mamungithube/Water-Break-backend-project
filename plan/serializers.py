from requests import Response
from rest_framework import serializers
from django.contrib.auth import get_user_model

from teamapp.models import Team, TeamMember
from teamapp.serializers import TeamMemberSerializer
from .models import Drill, Block, Plan
from account.serializers import UserSerializer


User = get_user_model()


class DrillSerializer(serializers.ModelSerializer):
    create_By = UserSerializer(read_only=True)

    assigned_users = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        write_only=True,
        required=False
    )

    assigned_data = serializers.SerializerMethodField()

    class Meta:
        model = Drill
        fields = [
            'id', 'create_By', 'assign_team', 'assign_team_name',
            'assistant_coach',
            'assigned_users', 'assigned_data',
            'name', 'category', 'description',
            'date_created', 'date_modified'
        ]
        read_only_fields = ['date_created', 'date_modified']

    def get_assigned_data(self, obj):
        assigned_user_ids = obj.assigned_members.values_list('id', flat=True)

        team_memberships = TeamMember.objects.filter(
            member_id__in=assigned_user_ids
        ).select_related('member', 'member__profile').distinct('member_id')

        return {
            "players": TeamMemberSerializer(
                team_memberships.filter(role='player'),
                many=True,
                context=self.context
            ).data,
            "assistant_coaches": TeamMemberSerializer(
                team_memberships.filter(role='assistant'),
                many=True,
                context=self.context
            ).data
        }

    def create(self, validated_data):
        assigned_users = validated_data.pop('assigned_users', [])

        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['create_By'] = user

        drill = super().create(validated_data)

        if assigned_users:
            drill.assigned_members.set(assigned_users)

        return drill

    def validate_assign_team(self, value):
        user = self.context['request'].user
        coach_teams = Team.objects.filter(coach=user)

        for team in value:
            if team not in coach_teams:
                raise serializers.ValidationError(
                    f"You can only assign teams that you created. Team '{team.name}' is not your team."
                )

        return value

    def validate_assistant_coach(self, value):
        if value and value.role != 'assistant':
            raise serializers.ValidationError(
                "Only users with 'assistant' role can be assigned as assistant coach."
            )
        return value


class BlockSerializer(serializers.ModelSerializer):
    drill_details = serializers.SerializerMethodField()

    drill = serializers.PrimaryKeyRelatedField(
        queryset=Drill.objects.all(),
        required=False
    )

    practice_plan = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Block
        fields = [
            'id',
            'drill',
            'drill_details',
            'practice_plan',
            'title',
            'color_code',
            'start_time',
            'end_time',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_drill_details(self, obj):
        if obj.drill:
            return DrillSerializer(obj.drill, context=self.context).data
        return None

    def validate_drill(self, value):
        user = self.context['request'].user
        if value:
            if value.create_By == user:
                return value
            if value.assistant_coach == user:
                return value
            # Assistant হলে drill এর team এ থাকলেও চলবে
            from teamapp.models import TeamMember
            drill_team_ids = value.assign_team.values_list('id', flat=True)
            is_assistant = TeamMember.objects.filter(
                member=user,
                team_id__in=drill_team_ids,
                role='assistant',
                is_role_approved=True
            ).exists()
            if not is_assistant:
                raise serializers.ValidationError(
                    "You can only create blocks for your own drills."
                )
        return value


    def validate_practice_plan(self, value):
        if value:
            user = self.context['request'].user
            from teamapp.models import TeamMember
    
            if user.role == 'coach':
                if value.create_By != user:
                    raise serializers.ValidationError(
                        "You can only assign blocks to your own practice plans."
                    )
            else:
                # Assistant — plan এর assign_team এ থাকলেই চলবে
                plan_team_ids = value.assign_team.values_list('id', flat=True)
                is_assistant = TeamMember.objects.filter(
                    member=user,
                    team_id__in=plan_team_ids,
                    role='assistant',
                    is_role_approved=True
                ).exists()
    
                if not is_assistant:
                    raise serializers.ValidationError(
                        "You can only assign blocks to practice plans of your team."
                    )
        return value

    def validate(self, attrs):
        drill = attrs.get('drill') or (
            self.instance.drill if self.instance else None)
        practice_plan = attrs.get('practice_plan') or (
            self.instance.practice_plan if self.instance else None)

        if drill and practice_plan:
            plan_team_members = set()
            for team in practice_plan.assign_team.all():
                plan_team_members.update(team.members.all())

            for member in drill.assigned_members.all():
                if member not in plan_team_members:
                    raise serializers.ValidationError({
                        'drill': f"Assigned member '{member.email}' is not in the practice plan's teams."
                    })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['create_By'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user if request else None

        drill_details_data = request.data.get(
            'drill_details', None) if request else None

        instance.title = validated_data.get('title', instance.title)
        instance.color_code = validated_data.get(
            'color_code', instance.color_code)
        instance.start_time = validated_data.get(
            'start_time', instance.start_time)
        instance.end_time = validated_data.get('end_time', instance.end_time)
        instance.practice_plan = validated_data.get(
            'practice_plan', instance.practice_plan)
        instance.save()

        if drill_details_data and user:
            drill = instance.drill

            if not drill:
                return instance

            if drill.create_By != user:
                raise serializers.ValidationError(
                    "You can only edit drills that you created."
                )

            if 'name' in drill_details_data:
                drill.name = drill_details_data['name']

            if 'category' in drill_details_data:
                drill.category = drill_details_data['category']

            if 'description' in drill_details_data:
                drill.description = drill_details_data['description']

            if 'assign_team' in drill_details_data:
                team_ids = drill_details_data['assign_team']

                coach_teams = Team.objects.filter(coach=user)
                coach_team_ids = list(coach_teams.values_list('id', flat=True))

                for team_id in team_ids:
                    if team_id not in coach_team_ids:
                        raise serializers.ValidationError(
                            f"You can only assign teams that you created. Team ID {team_id} is not your team."
                        )

                drill.assign_team.set(team_ids)

            if 'assigned_members' in drill_details_data:
                member_ids = drill_details_data['assigned_members']

                if instance.practice_plan:
                    plan_team_members = set()
                    for team in instance.practice_plan.assign_team.all():
                        plan_team_members.update(
                            team.members.values_list('id', flat=True))

                    for member_id in member_ids:
                        if member_id not in plan_team_members:
                            raise serializers.ValidationError(
                                f"Member ID {member_id} is not in the practice plan's teams."
                            )

                drill.assigned_members.set(member_ids)

            if 'assistant_coach' in drill_details_data:
                assistant_id = drill_details_data['assistant_coach']
                if assistant_id:
                    try:
                        assistant = User.objects.get(id=assistant_id)
                        if assistant.role != 'assistant':
                            raise serializers.ValidationError(
                                "Only users with 'assistant' role can be assigned."
                            )
                        drill.assistant_coach = assistant
                    except User.DoesNotExist:
                        raise serializers.ValidationError(
                            f"User with ID {assistant_id} does not exist."
                        )
                else:
                    drill.assistant_coach = None

            drill.save()

        return instance


class planSerializer(serializers.ModelSerializer):
    create_By = serializers.PrimaryKeyRelatedField(read_only=True)

    plan_blocks_detail = serializers.SerializerMethodField()

    blocks_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of blocks with drill details"
    )

    assign_team = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Team.objects.all()
    )

    available_members = serializers.SerializerMethodField()
    available_assistants = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'id', 'create_By', 'assign_team', 'plan_title',
            'available_members', 'available_assistants',
            'plan_blocks_detail', 'blocks_data',
            'start_practice_time', 'end_practice_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'create_By']

    def get_plan_blocks_detail(self, obj):
        """Get blocks sorted by start_time (practice schedule order)"""
        blocks = obj.Plan_Block.all().order_by('start_time')
        return BlockSerializer(blocks, many=True, context=self.context).data

    def get_available_members(self, obj):
        """Filter only 'player' role members from the TeamMember model"""
        team_ids = obj.assign_team.values_list('id', flat=True)

        memberships = TeamMember.objects.filter(
            team_id__in=team_ids,
            role='player'
        ).select_related('member')

        members_list = []
        for entry in memberships:
            members_list.append({
                'id': entry.member.id,
                'email': entry.member.email,
                'first_name': entry.member.first_name,
                'last_name': entry.member.last_name,
                'role': entry.role,
                'position': entry.team_position
            })

        unique_members = {m['id']: m for m in members_list}
        return list(unique_members.values())

    def get_available_assistants(self, obj):
        """Filter only 'assistant' role members from the TeamMember model"""
        team_ids = obj.assign_team.values_list('id', flat=True)

        assistants = TeamMember.objects.filter(
            team_id__in=team_ids,
            role='assistant'
        ).select_related('member')

        assistant_list = []
        for entry in assistants:
            assistant_list.append({
                'id': entry.member.id,
                'email': entry.member.email,
                'first_name': entry.member.first_name,
                'last_name': entry.member.last_name,
                'role': entry.role
            })

        unique_assistants = {a['id']: a for a in assistant_list}
        return list(unique_assistants.values())

    def create(self, validated_data):
        blocks_data = validated_data.pop('blocks_data', [])
        assign_teams = validated_data.pop('assign_team', [])

        user = self.context['request'].user

        # Create plan
        plan = Plan.objects.create(create_By=user, **validated_data)
        plan.assign_team.set(assign_teams)

        # Create drills and blocks
        for block_item in blocks_data:
            drill_data = block_item.pop('drill_details', None)

            if drill_data:
                # Create drill
                drill_serializer = DrillSerializer(
                    data=drill_data, context=self.context)
                if drill_serializer.is_valid(raise_exception=True):
                    drill = drill_serializer.save(create_By=user)

                    # Create block
                    block_item['drill'] = drill.id
                    block_item['practice_plan'] = plan.id

                    block_serializer = BlockSerializer(
                        data=block_item, context=self.context)
                    if block_serializer.is_valid(raise_exception=True):
                        block_serializer.save()

        return plan

    def update(self, instance, validated_data):
        blocks_data = validated_data.pop('blocks_data', None)
        assign_teams = validated_data.pop('assign_team', None)

        # Update plan fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if assign_teams is not None:
            instance.assign_team.set(assign_teams)

        # Update/Create blocks and drills
        if blocks_data is not None:
            for block_item in blocks_data:
                block_id = block_item.get('id', None)
                drill_data = block_item.pop('drill_details', None)

                if block_id:
                    # Update existing block
                    try:
                        block = Block.objects.get(
                            id=block_id, practice_plan=instance)

                        # Update drill if provided
                        if drill_data and block.drill:
                            drill = block.drill
                            for attr, value in drill_data.items():
                                if attr == 'assigned_users':
                                    drill.assigned_members.set(value)
                                elif attr == 'assign_team':
                                    drill.assign_team.set(value)
                                elif attr == 'assistant_coach':
                                    drill.assistant_coach_id = value
                                else:
                                    setattr(drill, attr, value)
                            drill.save()

                        # Update block
                        for attr, value in block_item.items():
                            if attr not in ['id', 'drill_details', 'create_By']:
                                setattr(block, attr, value)
                        block.save()

                    except Block.DoesNotExist:
                        pass
                else:
                    # Create new block with drill
                    if drill_data:
                        drill_serializer = DrillSerializer(
                            data=drill_data, context=self.context)
                        if drill_serializer.is_valid(raise_exception=True):
                            drill = drill_serializer.save(
                                create_By=self.context['request'].user)

                            block_item['drill'] = drill.id
                            block_item['practice_plan'] = instance.id

                            block_serializer = BlockSerializer(
                                data=block_item, context=self.context)
                            if block_serializer.is_valid(raise_exception=True):
                                block_serializer.save()

        return instance
