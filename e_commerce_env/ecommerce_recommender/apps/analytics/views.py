from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta

from .models import DailyMetrics, Report
from .serializers import DailyMetricsSerializer, ReportSerializer, AnalyticsQuerySerializer
from apps.stores.authentication import StoreAPIKeyAuthentication

class DailyMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DailyMetricsSerializer

    def get_queryset(self):
        store = self.request.auth
        return DailyMetrics.objects.filter(store=store)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        store = request.auth
        days = int(request.query_params.get('days', 7))
        
        # Get recent metrics
        recent_metrics = self.get_queryset().order_by('-date')[:days]
        serializer = self.get_serializer(recent_metrics, many=True)
        
        # Calculate summary
        summary = self.get_queryset().aggregate(
            total_revenue=Sum('revenue'),
            total_users=Sum('active_users'),
            avg_conversion=Avg('conversion_rate')
        )
        
        return Response({
            'recent_metrics': serializer.data,
            'summary': summary
        })

class ReportViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        store = self.request.auth
        return Report.objects.filter(store=store)

    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        store = request.auth
        report_type = request.data.get('report_type', 'daily')
        
        # Generate report data
        data = self._generate_report_data(store, report_type)
        
        report = Report.objects.create(
            store=store,
            name=f"{report_type.title()} Report - {timezone.now().date()}",
            report_type=report_type,
            data=data
        )
        
        return Response(ReportSerializer(report).data)

    def _generate_report_data(self, store, report_type):
        # Simplified report generation
        days = 7 if report_type == 'weekly' else 30
        
        metrics = DailyMetrics.objects.filter(
            store=store,
            date__gte=timezone.now() - timedelta(days=days)
        ).aggregate(
            total_revenue=Sum('revenue'),
            total_users=Sum('active_users'),
            avg_conversion=Avg('conversion_rate')
        )
        
        return {
            'time_period': f"Last {days} days",
            'metrics': metrics,
            'generated_at': timezone.now().isoformat()
        }