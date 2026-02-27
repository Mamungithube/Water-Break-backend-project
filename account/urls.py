from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    UserAPIView, 
    RegisterApiView,
    GoogleLoginInitView,
    GoogleCallbackView,
    ResendOTPApiView,
    VerifyOTPApiView,
    ForgotPasswordAPIView,
    ChangePasswordViewSet,
    LoginAPIView,
    DeleteAccountView,
    ProfileDetailsView,
    ProfileUpdateView,
    NotificationViewSet,
    DeviceTokenViewSet,
)

router = DefaultRouter()
router.register(r'device-tokens', DeviceTokenViewSet, basename='device-token')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # user list 
    path('user_all/', UserAPIView.as_view(), name='user-list'), 
    path('user/<int:pk>/', UserAPIView.as_view(), name='user-detail'),

    # authentication part urls
    path('register/', RegisterApiView.as_view(), name='user-register'),
    path('auth/google/login/', GoogleLoginInitView.as_view(), name='google-login'),
    path('auth/google/callback/', GoogleCallbackView.as_view(), name='google-callback'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('resend_otp/', ResendOTPApiView.as_view(), name='resend-otp'),
    path('verify_otp/', VerifyOTPApiView.as_view(), name='verify-otp'),
    path('forget-pass/', ForgotPasswordAPIView.as_view(), name='forget-password'),
    path('change-pass/', ChangePasswordViewSet.as_view({'post': 'create'}), name='password-change'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),

    # profile urls
    path('profile-data/', ProfileDetailsView.as_view(), name='Profile-Details'),
    path('profile-update/', ProfileUpdateView.as_view(), name='Profile-Update'),

    # team and router urls
    path('', include(router.urls)),
]