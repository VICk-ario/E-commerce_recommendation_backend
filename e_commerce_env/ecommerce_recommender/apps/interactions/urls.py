from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InteractionViewSet, UserSessionViewSet, ProductViewViewSet,
    UserBehaviorProfileViewSet, ABTestViewSet, InteractionEventViewSet
)

router = DefaultRouter()
router.register(r'interactions', InteractionViewSet, basename='interaction')
router.register(r'sessions', UserSessionViewSet, basename='session')
router.register(r'product-views', ProductViewViewSet, basename='product-view')
router.register(r'behavior-profiles', UserBehaviorProfileViewSet, basename='behavior-profile')
router.register(r'ab-tests', ABTestViewSet, basename='ab-test')
router.register(r'events', InteractionEventViewSet, basename='event')

urlpatterns = [
    path('api/', include(router.urls)),
]