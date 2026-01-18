from .views import PrivacyPolicyViewSet, TermsAndConditionsViewSet, AboutUsViewSet
from rest_framework.routers import DefaultRouter
from django.urls import path, include   

router = DefaultRouter()    
router.register(r'privacy-policy', PrivacyPolicyViewSet, basename='privacy-policy')
router.register(r'terms-and-conditions', TermsAndConditionsViewSet, basename='terms-and-conditions')
router.register(r'about-us', AboutUsViewSet, basename='about-us')
urlpatterns = [
    path('', include(router.urls)), 
]