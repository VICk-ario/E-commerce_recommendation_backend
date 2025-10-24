from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.stores.views import StoreViewSet, StoreAPIKeyViewSet

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'api-keys', StoreAPIKeyViewSet, basename='api-key')

urlpatterns = [
    path('api/', include(router.urls)),
]