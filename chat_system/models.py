from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from account.models import Team

User = get_user_model()

class TeamChatMessage(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="chat_messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.email} → {self.team.name}"
