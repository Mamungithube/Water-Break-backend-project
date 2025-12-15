from django.urls import path
from .views import (
    UserAPIView, 

)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    # user list and show
    path('user_all/', UserAPIView.as_view(), name='user-list'), 
    path('user/<int:pk>/', UserAPIView.as_view(), name='user-detail'),
]