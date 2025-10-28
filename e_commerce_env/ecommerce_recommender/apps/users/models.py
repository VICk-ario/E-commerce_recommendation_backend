from django.db import models
from django.utils import timezone
from apps.stores.models import Store

class User(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='users')
    
    # User identification
    user_id = models.CharField(max_length=255)  # Store's user ID
    email = models.EmailField(blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    
    # User profile
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    user_profile = models.JSONField(default=dict, blank=True)  # Preferences, demographics
    
    # Engagement metrics
    total_interactions = models.IntegerField(default=0)
    total_purchases = models.IntegerField(default=0)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    last_purchase = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['store', 'user_id']),
            models.Index(fields=['store', 'email']),
            models.Index(fields=['store', 'session_id']),
            models.Index(fields=['first_seen']),
            models.Index(fields=['last_seen']),
            models.Index(fields=['total_interactions']),
        ]
        unique_together = ['store', 'user_id']
        ordering = ['-last_seen']
    
    def __str__(self):
        return f"{self.user_id} ({self.store.name})"
    
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.user_id
    
    @property
    def engagement_score(self):
        """Calculate user engagement score (0-100)"""
        if self.total_interactions == 0:
            return 0
        
        # Simple engagement formula (customize as needed)
        purchase_score = min(self.total_purchases * 20, 40)  # Max 40 points for purchases
        interaction_score = min(self.total_interactions * 0.5, 30)  # Max 30 points for interactions
        recency_score = 30  # Base recency score
        
        # Adjust recency based on last activity
        if self.last_seen:
            days_since_seen = (timezone.now() - self.last_seen).days
            if days_since_seen > 30:
                recency_score = 10
            elif days_since_seen > 7:
                recency_score = 20
        
        return min(purchase_score + interaction_score + recency_score, 100)
    
    @property
    def customer_segment(self):
        """Segment users based on behavior"""
        if self.total_purchases == 0:
            return "browser"
        elif self.total_purchases == 1:
            return "first_time"
        elif self.total_purchases <= 5:
            return "regular"
        else:
            return "vip"
    
    def update_engagement_metrics(self):
        """Update engagement metrics from interactions"""
        from apps.interactions.models import Interaction
        from django.db.models import Sum, Count
        
        # Update interaction count
        self.total_interactions = self.interactions.count()
        
        # Update purchase metrics
        purchases = self.interactions.filter(interaction_type='purchase')
        self.total_purchases = purchases.count()
        
        if self.total_purchases > 0:
            purchase_data = purchases.aggregate(
                total_value=Sum('value'),
                avg_value=Sum('value') / Count('id')
            )
            self.total_value = purchase_data['total_value'] or 0
            self.avg_order_value = purchase_data['avg_value'] or 0
        
        self.save()
    
    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])

class UserSession(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_sessions')
    session_id = models.CharField(max_length=255)
    
    # Session metrics
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    page_views = models.IntegerField(default=0)
    products_viewed = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(default=0)
    
    # Session data
    landing_page = models.URLField(max_length=1000, blank=True)
    exit_page = models.URLField(max_length=1000, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referrer = models.URLField(max_length=1000, blank=True)
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['store', 'user', 'start_time']),
            models.Index(fields=['session_id']),
            models.Index(fields=['start_time']),
        ]
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user.user_id}"
    
    @property
    def is_active(self):
        """Check if session is still active"""
        return self.end_time is None
    
    def end_session(self):
        """End the session and calculate duration"""
        if self.is_active:
            self.end_time = timezone.now()
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
            self.save()
    
    def increment_page_views(self):
        """Increment page view count"""
        self.page_views += 1
        self.save(update_fields=['page_views'])
    
    def increment_products_viewed(self):
        """Increment products viewed count"""
        self.products_viewed += 1
        self.save(update_fields=['products_viewed'])

class UserPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferences')
    preference_type = models.CharField(max_length=100)  # 'category', 'brand', 'price_range'
    preference_value = models.CharField(max_length=255)
    confidence = models.FloatField(default=1.0)  # 0-1 confidence score
    source = models.CharField(max_length=50, default='inferred')  # 'explicit', 'inferred'
    
    class Meta:
        db_table = 'user_preferences'
        unique_together = ['user', 'preference_type', 'preference_value']
        indexes = [
            models.Index(fields=['user', 'preference_type']),
        ]
    
    def __str__(self):
        return f"{self.user.user_id} - {self.preference_type}: {self.preference_value}"