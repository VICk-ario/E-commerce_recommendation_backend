from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Count, Avg, Q
from apps.users.models import User, UserSession, UserPreference

class UserSessionInline(admin.TabularInline):
    model = UserSession
    extra = 0
    max_num = 5
    readonly_fields = ['session_id', 'start_time', 'end_time', 'page_views', 'duration_seconds']
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False

class UserPreferenceInline(admin.TabularInline):
    model = UserPreference
    extra = 1
    fields = ['preference_type', 'preference_value', 'confidence', 'source']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'user_id', 'store', 'email', 'engagement_score_display', 
        'customer_segment', 'total_purchases', 'last_seen', 'is_active'
    ]
    list_filter = [
        'store', 'is_active', 'first_seen', 'last_seen', 'last_purchase'
    ]
    search_fields = ['user_id', 'email', 'first_name', 'last_name']
    readonly_fields = [
        'first_seen', 'last_seen', 'last_purchase', 'engagement_metrics',
        'full_name_display', 'engagement_score_display'
    ]
    list_select_related = ['store']
    inlines = [UserSessionInline, UserPreferenceInline]
    
    fieldsets = (
        ('Store Information', {
            'fields': ('store', 'user_id', 'session_id')
        }),
        ('User Profile', {
            'fields': ('email', 'first_name', 'last_name', 'full_name_display', 'user_profile')
        }),
        ('Engagement Metrics', {
            'fields': (
                'engagement_metrics', 'engagement_score_display', 'customer_segment',
                'total_interactions', 'total_purchases', 'total_value', 'avg_order_value'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('first_seen', 'last_seen', 'last_purchase'),
            'classes': ('collapse',)
        }),
    )
    
    def engagement_metrics(self, obj):
        """Display engagement metrics in admin"""
        if obj.total_interactions == 0:
            return "No interactions yet"
        
        purchase_rate = (obj.total_purchases / obj.total_interactions) * 100
        days_since_seen = (timezone.now() - obj.last_seen).days if obj.last_seen else "N/A"
        
        metrics = [
            f"Purchase Rate: {purchase_rate:.1f}%",
            f"Last Seen: {days_since_seen} days ago",
            f"Total Value: ${obj.total_value:.2f}",
            f"AOV: ${obj.avg_order_value:.2f}"
        ]
        return " | ".join(metrics)
    engagement_metrics.short_description = 'Engagement Analytics'
    
    def engagement_score_display(self, obj):
        """Display engagement score with color coding"""
        score = obj.engagement_score
        if score >= 70:
            color = 'green'
        elif score >= 40:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, f"{score}/100"
        )
    engagement_score_display.short_description = 'Engagement Score'
    
    def full_name_display(self, obj):
        return obj.full_name
    full_name_display.short_description = 'Full Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('store')

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'store', 'start_time', 'end_time', 'page_views', 'duration_display']
    list_filter = ['store', 'start_time']
    search_fields = ['session_id', 'user__user_id', 'user__email']
    readonly_fields = ['start_time', 'end_time', 'duration_display']
    list_select_related = ['user', 'store']
    
    def duration_display(self, obj):
        if obj.duration_seconds:
            minutes = obj.duration_seconds // 60
            seconds = obj.duration_seconds % 60
            return f"{minutes}m {seconds}s"
        return "Active" if obj.is_active else "N/A"
    duration_display.short_description = 'Duration'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user__store', 'store')

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'preference_type', 'preference_value', 'confidence', 'source']
    list_filter = ['preference_type', 'source', 'confidence']
    search_fields = ['user__user_id', 'preference_value']
    list_select_related = ['user']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user__store')