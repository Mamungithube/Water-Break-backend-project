# urls.py
from django.urls import path
from .views import (
    TeamChatHistoryView,
    NotificationListView,
    MarkNotificationReadView
)

urlpatterns = [
    path('team/<int:team_id>/chat/history/', TeamChatHistoryView.as_view(), name='team_chat_history'),
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:notification_id>/read/', MarkNotificationReadView.as_view(), name='mark_notification_read'),
]