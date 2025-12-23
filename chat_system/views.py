from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TeamChatMessage

class TeamChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, team_id):
        messages = TeamChatMessage.objects.filter(
            team_id=team_id
        ).order_by('-created_at')[:50]
        
        data = [{
            'id': msg.id,
            'sender': msg.sender.email,
            'message': msg.message,
            'created_at': msg.created_at
        } for msg in messages]
        
        return Response(data)