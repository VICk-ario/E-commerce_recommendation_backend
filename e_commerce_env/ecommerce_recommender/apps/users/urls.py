from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import UserViewSet, UserSessionViewSet, UserPreferenceViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'sessions', UserSessionViewSet, basename='session')
router.register(r'preferences', UserPreferenceViewSet, basename='preference')

urlpatterns = [
    path('api/', include(router.urls)),
]