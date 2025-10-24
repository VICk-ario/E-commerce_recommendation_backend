from django.contrib import admin
from apps.stores.models import Store, StoreAPIKey

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'platform', 'is_active', 'is_verified', 'created_at']
    list_filter = ['platform', 'is_active', 'is_verified', 'created_at']
    search_fields = ['name', 'domain']
    readonly_fields = ['api_key', 'webhook_secret', 'created_at', 'updated_at']
    list_editable = ['is_active', 'is_verified']
    
    fieldsets = (
        ('Store Information', {
            'fields': ('name', 'domain', 'platform')
        }),
        ('API Configuration', {
            'fields': ('api_key', 'webhook_secret', 'config')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'last_sync_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(StoreAPIKey)
class StoreAPIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'is_active', 'created_at', 'last_used']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'store__name', 'key']
    readonly_fields = ['key', 'created_at']
    
    fieldsets = (
        ('API Key Information', {
            'fields': ('store', 'name', 'key', 'is_active')
        }),
        ('Usage', {
            'fields': ('last_used',)
        }),
    )
