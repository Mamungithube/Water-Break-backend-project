import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from teamapp.models import Team, TeamMember
from .models import TeamChatMessage
from django.contrib.auth.models import AnonymousUser


class TeamChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            self.user = self.scope.get("user")
            self.team_id = self.scope["url_route"]["kwargs"]["team_id"]
            self.group_name = f"team_{self.team_id}"

            # User check
            if not self.user or isinstance(self.user, AnonymousUser):
                print("❌ User not authenticated")
                await self.close(code=4001)
                return

            # Team member check
            is_allowed = await self.is_team_member()
            if not is_allowed:
                print(f"❌ User {self.user.email} is not a team member of team {self.team_id}")
                await self.close(code=4003)
                return

            # Add to group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
            print(f"✅ User {self.user.email} connected to team {self.team_id}")
            
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            import traceback
            traceback.print_exc()
            await self.close(code=4000)

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            print(f"User disconnected from {self.group_name}")
        except Exception as e:
            print(f"Disconnect error: {str(e)}")

    async def receive(self, text_data):
        try:
            try:
                data = json.loads(text_data)
                message = data.get("message")
            except json.JSONDecodeError:
                message = text_data

            if not message:
                print("⚠️ No message content found.")
                return
            saved = await self.save_message(message)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "sender": self.user.email,
                    "message": message,
                }
            )

            try:
                member_ids = await self.get_team_member_user_ids()
                notification_payload = {
                    "type": "send_notification",
                    "data": {
                        "notification_type": "team_message",
                        "team_id": saved.get("team_id"),
                        "team_name": saved.get("team_name"),
                        "message_id": saved.get("id"),
                        "message": saved.get("message"),
                        "sender_id": saved.get("sender_id"),
                        "sender_email": getattr(self.user, "email", None),
                        "created_at": saved.get("created_at"),
                    },
                }

                for uid in member_ids:
                    await self.channel_layer.group_send(f"user_{uid}", notification_payload)
            except Exception as e:
                print(f"❌ Notification send error: {str(e)}")
        except Exception as e:
            print(f"❌ Receive logic error: {str(e)}")
    async def chat_message(self, event):
        message = event.get("message")
        sender = event.get("sender")

        await self.send(text_data=json.dumps({
            "message": message,
            "sender": sender
        }))
    # ---------- DB helpers ----------

    @database_sync_to_async
    def is_team_member(self):
        try:
            team = Team.objects.get(id=self.team_id)

            if team.coach == self.user:
                return True

            return TeamMember.objects.filter(
                team=team,
                member=self.user,
                is_role_approved=True
            ).exists()
        except Team.DoesNotExist:
            print(f"❌ Team {self.team_id} does not exist")
            return False
        except Exception as e:
            print(f"❌ is_team_member error: {str(e)}")
            return False
    
    @database_sync_to_async
    def save_message(self, message):
        try:
            # সরাসরি আইডি ব্যবহার করা নিরাপদ
            msg = TeamChatMessage.objects.create(
                team_id=self.team_id,
                sender=self.user,
                message=message
            )
            print(f"✅ Success: Message saved for Team {self.team_id}")
            return {
                "id": msg.id,
                "team_id": msg.team_id,
                "team_name": getattr(msg.team, "name", None),
                "sender_id": msg.sender_id,
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
        except Exception as e:
            print(f"❌ DB Save Error: {str(e)}")
            return {}

    @database_sync_to_async
    def get_team_member_user_ids(self):
        try:
            team = Team.objects.get(id=self.team_id)
            member_ids = list(TeamMember.objects.filter(team=team, is_role_approved=True).values_list("member_id", flat=True))
            # include coach if present
            if getattr(team, "coach_id", None) and team.coach_id not in member_ids:
                member_ids.append(team.coach_id)
            # exclude sender
            sender_id = getattr(self.user, "id", None)
            return [uid for uid in member_ids if uid != sender_id]
        except Team.DoesNotExist:
            print(f"❌ Team {self.team_id} does not exist (get_team_member_user_ids)")
            return []
        except Exception as e:
            print(f"❌ get_team_member_user_ids error: {str(e)}")
            return []


from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
        else:
            self.group_name = f"user_{user.id}"
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_notification(self, event):
        await self.send_json(event["data"])
