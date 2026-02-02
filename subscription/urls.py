from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import SubscriptionViewSet, SubscriptionPlanViewSet

router = DefaultRouter()
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')

urlpatterns = [
    path('', include(router.urls)),
]