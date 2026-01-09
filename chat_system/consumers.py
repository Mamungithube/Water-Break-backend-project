import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from account.models import Team, TeamMember
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

            # ডাটাবেসে সেভ করা (অবশ্যই await দিবেন)
            await self.save_message(message)

            # অন্য মেম্বারদের মেসেজটি পাঠানো
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "sender": self.user.email,
                    "message": message,
                }
            )
        except Exception as e:
            print(f"❌ Receive logic error: {str(e)}")
    async def chat_message(self, event):
        # গ্রুপ থেকে আসা মেসেজটি রিসিভ করা
        message = event.get("message")
        sender = event.get("sender")

        # ক্লায়েন্ট বা পোস্টম্যানের কাছে মেসেজটি পাঠানো
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
            TeamChatMessage.objects.create(
                team_id=self.team_id,
                sender=self.user,
                message=message
            )
            print(f"✅ Success: Message saved for Team {self.team_id}")
        except Exception as e:
            print(f"❌ DB Save Error: {str(e)}")




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
