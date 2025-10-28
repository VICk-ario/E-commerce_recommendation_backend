from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from apps.stores.models import Store
from apps.users.models import User
from apps.products.models import Product

class UserInteractionSession(models.Model):
    """Enhanced session tracking for user behavior analysis"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='interaction_sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions_sessions', null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True)
    
    # Session metadata
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    # Session analytics
    page_views = models.IntegerField(default=0)
    products_viewed = models.IntegerField(default=0)
    unique_products_viewed = models.IntegerField(default=0)
    total_interactions = models.IntegerField(default=0)
    
    # Technical data
    landing_page = models.URLField(max_length=1000, blank=True)
    exit_page = models.URLField(max_length=1000, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referrer = models.URLField(max_length=1000, blank=True)
    device_type = models.CharField(max_length=50, blank=True)  # mobile, desktop, tablet
    browser = models.CharField(max_length=100, blank=True)
    operating_system = models.CharField(max_length=100, blank=True)
    
    # Geographic data
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # E-commerce metrics
    added_to_cart = models.BooleanField(default=False)
    purchased = models.BooleanField(default=False)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    
    class Meta:
        db_table = 'user_interaction_sessions'
        indexes = [
            models.Index(fields=['store', 'session_id']),
            models.Index(fields=['store', 'start_time']),
            models.Index(fields=['session_id']),
            models.Index(fields=['start_time']),
            models.Index(fields=['user', 'start_time']),
        ]
        ordering = ['-start_time']
    
    def __str__(self):
        user_id = self.user.user_id if self.user else "Anonymous"
        return f"Session {self.session_id} - {user_id}"
    
    @property
    def is_active(self):
        """Check if session is still active"""
        return self.end_time is None
    
    @property
    def conversion_rate(self):
        """Calculate session conversion rate"""
        if self.page_views == 0:
            return 0.0
        return (self.products_viewed / self.page_views) * 100
    
    def end_session(self):
        """End the session and calculate duration"""
        if self.is_active:
            self.end_time = timezone.now()
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
            self.save()
    
    def update_session_metrics(self):
        """Update session metrics from interactions"""
        from .models import Interaction
        
        interactions = self.interactions.all()
        self.total_interactions = interactions.count()
        
        # Update product views
        product_views = interactions.filter(interaction_type='view').values('product').distinct()
        self.unique_products_viewed = product_views.count()
        self.products_viewed = interactions.filter(interaction_type='view').count()
        
        # Update e-commerce metrics
        self.added_to_cart = interactions.filter(interaction_type='cart').exists()
        self.purchased = interactions.filter(interaction_type='purchase').exists()
        
        # Calculate total value from purchases
        purchase_value = interactions.filter(
            interaction_type='purchase'
        ).aggregate(total=models.Sum('value'))['total'] or 0.0
        self.total_value = purchase_value
        
        self.save()

class Interaction(models.Model):
    """Track all user-product interactions"""
    INTERACTION_TYPES = [
        ('view', 'View'),
        ('click', 'Click'),
        ('detail_view', 'Detail View'),
        ('cart_add', 'Add to Cart'),
        ('cart_remove', 'Remove from Cart'),
        ('wishlist_add', 'Add to Wishlist'),
        ('wishlist_remove', 'Remove from Wishlist'),
        ('purchase', 'Purchase'),
        ('review', 'Review'),
        ('share', 'Share'),
        ('like', 'Like'),
        ('dislike', 'Dislike'),
        ('search', 'Search'),
        ('filter', 'Filter'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='interactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    session = models.ForeignKey(UserInteractionSession, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    
    # Core interaction data
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)  # Purchase value, etc.
    weight = models.FloatField(default=1.0)  # Importance weight for ML
    
    # Context data
    page_url = models.URLField(max_length=1000, blank=True)
    page_title = models.CharField(max_length=255, blank=True)
    referrer_url = models.URLField(max_length=1000, blank=True)
    
    # User context
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    screen_resolution = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=10, blank=True)
    
    # Product context
    product_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_category = models.CharField(max_length=255, blank=True)
    
    # Search context
    search_query = models.CharField(max_length=255, blank=True)
    search_results_count = models.IntegerField(null=True, blank=True)
    search_position = models.IntegerField(null=True, blank=True)
    
    # Additional metadata
    time_on_page = models.IntegerField(default=0)  # Seconds
    scroll_depth = models.FloatField(default=0.0)  # 0-1 percentage
    metadata = models.JSONField(default=dict, blank=True)  # Flexible additional data
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'interactions'
        indexes = [
            models.Index(fields=['store', 'user', 'interaction_type']),
            models.Index(fields=['store', 'product', 'interaction_type']),
            models.Index(fields=['store', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['interaction_type', 'created_at']),
            models.Index(fields=['session', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        user_id = self.user.user_id if self.user else "Anonymous"
        product_title = self.product.title if self.product else "No Product"
        return f"{user_id} - {self.interaction_type} - {product_title}"
    
    def save(self, *args, **kwargs):
        """Override save to update related models"""
        # Set product context if product exists
        if self.product and not self.product_category:
            self.product_category = self.product.category
            self.product_price = self.product.price
        
        # Update weight based on interaction type
        weight_map = {
            'view': 0.1,
            'click': 0.3,
            'detail_view': 0.5,
            'cart_add': 2.0,
            'wishlist_add': 1.5,
            'purchase': 5.0,
            'review': 3.0,
            'like': 1.0,
            'dislike': 0.5,
        }
        self.weight = weight_map.get(self.interaction_type, 1.0)
        
        super().save(*args, **kwargs)
        
        # Update session metrics
        if self.session:
            self.session.update_session_metrics()
        
        # Update user engagement metrics
        if self.user:
            self.user.update_engagement_metrics()

class ProductView(models.Model):
    """Aggregated product view data for performance"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='product_views')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='view_analytics')
    date = models.DateField()
    
    # View metrics
    total_views = models.IntegerField(default=0)
    unique_views = models.IntegerField(default=0)
    detail_views = models.IntegerField(default=0)
    avg_time_on_page = models.FloatField(default=0.0)
    
    # Conversion metrics
    cart_adds = models.IntegerField(default=0)
    purchases = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    
    class Meta:
        db_table = 'product_views'
        unique_together = ['store', 'product', 'date']
        indexes = [
            models.Index(fields=['store', 'date']),
            models.Index(fields=['product', 'date']),
        ]
    
    def __str__(self):
        return f"{self.product.title} - {self.date}"

class UserBehaviorProfile(models.Model):
    """Aggregated user behavior data for ML features"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='user_profiles')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='behavior_profile')
    
    # Interaction frequencies
    total_interactions = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    total_purchases = models.IntegerField(default=0)
    total_cart_adds = models.IntegerField(default=0)
    
    # Time-based metrics
    avg_session_duration = models.FloatField(default=0.0)
    avg_time_between_sessions = models.FloatField(default=0.0)
    last_active_date = models.DateTimeField(null=True, blank=True)
    
    # Product preferences
    preferred_categories = models.JSONField(default=dict, blank=True)  # {category: weight}
    preferred_brands = models.JSONField(default=dict, blank=True)     # {brand: weight}
    price_preference = models.JSONField(default=dict, blank=True)     # {min, max, avg}
    
    # Behavioral patterns
    browsing_pattern = models.CharField(max_length=50, blank=True)  # 'explorer', 'focused', 'bargain_hunter'
    purchase_frequency = models.CharField(max_length=50, blank=True)  # 'frequent', 'occasional', 'rare'
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    # ML features
    feature_vector = models.JSONField(default=dict, blank=True)  # Precomputed feature vector
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_behavior_profiles'
        unique_together = ['store', 'user']
        indexes = [
            models.Index(fields=['store', 'user']),
        ]
    
    def __str__(self):
        return f"Behavior Profile - {self.user.user_id}"

class ABTest(models.Model):
    """A/B testing framework for recommendations"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='ab_tests')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Test configuration
    test_type = models.CharField(max_length=50, choices=[
        ('recommendation_algorithm', 'Recommendation Algorithm'),
        ('ui_placement', 'UI Placement'),
        ('personalization', 'Personalization Level'),
    ])
    variants = models.JSONField(default=dict)  # {variant_name: config}
    
    # Traffic allocation
    traffic_percentage = models.FloatField(default=100.0)  # Percentage of users to include
    variant_weights = models.JSONField(default=dict)  # {variant_name: weight}
    
    # Test status
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ], default='draft')
    
    # Results
    primary_metric = models.CharField(max_length=100, default='conversion_rate')
    results = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ab_tests'
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['store', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.store.name}"

class InteractionEvent(models.Model):
    """Raw interaction events for real-time processing"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='interaction_events')
    event_type = models.CharField(max_length=100)
    event_data = models.JSONField(default=dict)
    user_id = models.CharField(max_length=255, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    product_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'interaction_events'
        indexes = [
            models.Index(fields=['store', 'created_at']),
            models.Index(fields=['store', 'processed']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.session_id}"