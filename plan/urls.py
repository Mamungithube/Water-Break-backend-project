from .serializers import DrillSerializer
from rest_framework import routers
from .views import DrillViewSet,BlockViewSet,PlanViewSet
from django.urls import path, include
router = routers.DefaultRouter()
router.register(r'drills', DrillViewSet)
router.register(r'Block', BlockViewSet)
router.register(r'plan', PlanViewSet)
urlpatterns = [
    path('', include(router.urls)),
]
