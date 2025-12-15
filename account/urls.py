from django.urls import path
from .views import (
    UserAPIView, 
    RegisterApiView,
    GoogleLoginAPIView,
    # ResendOTPApiView,
    VerifyOTPApiView

)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    # user list and show
    path('user_all/', UserAPIView.as_view(), name='user-list'), 
    path('user/<int:pk>/', UserAPIView.as_view(), name='user-detail'),
    path('register/', RegisterApiView.as_view(), name='user-register'),
     path('auth/google/',GoogleLoginAPIView.as_view(), name='google-login'),
    # path('resend_otp/', ResendOTPApiView.as_view(), name='resend-otp'),
    path('verify_otp/', VerifyOTPApiView.as_view(), name='verify-otp'),
    
]