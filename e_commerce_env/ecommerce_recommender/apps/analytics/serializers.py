from rest_framework import serializers
from .models import DailyMetrics, Report

class DailyMetricsSerializer(serializers.ModelSerializer):
    conversion_rate = serializers.FloatField(read_only=True)
    click_through_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = DailyMetrics
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

class AnalyticsQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    metrics = serializers.ListField(child=serializers.CharField(), required=False)