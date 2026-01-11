from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import TeamChatMessage
from teamapp.models import Team, TeamMember

class TeamChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, team_id):
        # Validate team_id is provided and is a valid integer
        if not team_id:
            return Response(
                {
                    "success": False,
                    "message": "Team ID is required.",
                    "errors": {"team_id": ["Team ID cannot be empty."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            team_id = int(team_id)
        except (ValueError, TypeError):
            return Response(
                {
                    "success": False,
                    "message": "Invalid team ID format.",
                    "errors": {"team_id": ["Team ID must be a valid integer."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if team exists
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": f"Team with ID {team_id} does not exist.",
                    "errors": {"team_id": ["Team not found."]},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify user has permission to view team chat
        user = request.user
        is_coach = user == team.coach
        is_member = TeamMember.objects.filter(
            team=team,
            member=user,
            is_role_approved=True
        ).exists()

        if not (is_coach or is_member):
            return Response(
                {
                    "success": False,
                    "message": "You do not have permission to view this team's chat history.",
                    "errors": {"permission": ["Access denied."]},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve chat messages
        try:
            messages = TeamChatMessage.objects.filter(
                team_id=team_id
            ).order_by('-created_at')[:50]

            # Serialize messages
            data = [
                {
                    "id": msg.id,
                    "sender": {
                        "id": msg.sender.id,
                        "email": msg.sender.email,
                        "fullname": msg.sender.Fullname or msg.sender.email,
                    },
                    "message": msg.message,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ]

            return Response(
                {
                    "success": True,
                    "message": "Chat history retrieved successfully.",
                    "data": {
                        "team_id": team.id,
                        "team_name": team.name,
                        "message_count": len(data),
                        "messages": data,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": "Failed to retrieve chat history. Please try again later.",
                    "errors": {"detail": [str(e)]},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )