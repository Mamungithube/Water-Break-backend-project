from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import teamviewset, TeamMemberViewSet, InvitationTokenViewSet
from teamapp.views import teamviewset

router = DefaultRouter()
router.register(r'createteams', teamviewset, basename='team')
router.register(r'team-members', TeamMemberViewSet)
router.register(r'invitation-tokens', InvitationTokenViewSet, basename='invitation-token')
urlpatterns = [
    # team and router urls
    path('', include(router.urls)),
]