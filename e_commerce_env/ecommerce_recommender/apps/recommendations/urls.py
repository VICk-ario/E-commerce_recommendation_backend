from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RecommendationViewSet, MLModelViewSet, RecommendationConfigViewSet,
    UserRecommendationProfileViewSet, RecommendationFeedbackViewSet,
    TrendingProductViewSet, SimilarProductViewSet
)

router = DefaultRouter()
router.register(r'recommendations', RecommendationViewSet, basename='recommendation')
router.register(r'ml-models', MLModelViewSet, basename='ml-model')
router.register(r'configs', RecommendationConfigViewSet, basename='config')
router.register(r'user-profiles', UserRecommendationProfileViewSet, basename='user-profile')
router.register(r'feedback', RecommendationFeedbackViewSet, basename='feedback')
router.register(r'trending', TrendingProductViewSet, basename='trending')
router.register(r'similar-products', SimilarProductViewSet, basename='similar-product')

urlpatterns = [
    path('api/', include(router.urls)),
]