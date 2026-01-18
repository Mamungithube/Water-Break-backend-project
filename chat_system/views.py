
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import TeamChatMessage
from teamapp.models import Team, TeamMember
from account.models import Notification


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
        



# views.py

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # All User unread notifications
            notifications = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).select_related('sender', 'team', 'related_message').order_by('-created_at')[:50]
            
            data = [
                {
                    "id": n.id,
                    "notification_type": n.notification_type,
                    "message": n.message,
                    "sender": {
                        "id": n.sender.id,
                        "email": n.sender.email,
                        "fullname": getattr(n.sender, 'Fullname', n.sender.email)
                    },
                    "team": {
                        "id": n.team.id,
                        "name": n.team.name
                    } if n.team else None,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat()
                }
                for n in notifications
            ]
            
            return Response({
                "success": True,
                "unread_count": notifications.count(),
                "notifications": data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=request.user
            )
            notification.is_read = True
            notification.save()
            
            return Response({
                "success": True,
                "message": "Notification marked as read"
            }, status=status.HTTP_200_OK)
            
        except Notification.DoesNotExist:
            return Response({
                "success": False,
                "message": "Notification not found"
            }, status=status.HTTP_404_NOT_FOUND)