from django.contrib import admin
from .models import MLModel

@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'model_type', 'version', 'accuracy', 'is_active']
    list_filter = ['store', 'model_type', 'is_active']
    actions = ['activate_models']

    def activate_models(self, request, queryset):
        for model in queryset:
            model.activate()
    activate_models.short_description = "Activate selected models"