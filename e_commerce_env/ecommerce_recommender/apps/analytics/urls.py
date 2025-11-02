from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DailyMetricsViewSet, ReportViewSet

router = DefaultRouter()
router.register(r'metrics', DailyMetricsViewSet, basename='metrics')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('api/', include(router.urls)),
]