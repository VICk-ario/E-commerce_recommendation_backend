from django.db import models
import secrets
from django.utils import timezone

class Store(models.Model):
    PLATFORM_CHOICES = [
        ('shopify', 'Shopify'),
        ('woocommerce', 'WooCommerce'),
        ('bigcommerce', 'BigCommerce'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    webhook_secret = models.CharField(max_length=32, blank=True)
    
    # Configuration
    config = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'stores'
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['api_key']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.domain})"
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = f"sk_{secrets.token_urlsafe(32)}"
        if not self.webhook_secret:
            self.webhook_secret = f"wh_{secrets.token_urlsafe(16)}"
        super().save(*args, **kwargs)

class StoreAPIKey(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'store_api_keys'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.store.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = f"sk_{secrets.token_urlsafe(32)}"
        super().save(*args, **kwargs)
    
    def update_last_used(self):
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])

