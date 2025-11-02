from django.contrib import admin
from .models import DailyMetrics, Report

@admin.register(DailyMetrics)
class DailyMetricsAdmin(admin.ModelAdmin):
    list_display = ['store', 'date', 'active_users', 'revenue', 'conversion_rate']
    list_filter = ['store', 'date']
    readonly_fields = ['conversion_rate', 'click_through_rate']

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'report_type', 'created_at']
    list_filter = ['store', 'report_type']