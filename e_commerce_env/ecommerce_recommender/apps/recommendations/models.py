from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from apps.stores.models import Store
from apps.users.models import User
from apps.products.models import Product

class Recommendation(models.Model):
    """Store generated recommendations for users"""
    ALGORITHM_CHOICES = [
        ('collaborative_filtering', 'Collaborative Filtering'),
        ('content_based', 'Content-Based'),
        ('hybrid', 'Hybrid'),
        ('popularity', 'Popularity-Based'),
        ('session_based', 'Session-Based'),
        ('trending', 'Trending'),
        ('frequently_bought_together', 'Frequently Bought Together'),
        ('similar_users', 'Similar Users'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='recommendations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations', null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True)  # For session-based recommendations
    
    # Recommendation target
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recommended_in')
    
    # Algorithm and scoring
    algorithm = models.CharField(max_length=50, choices=ALGORITHM_CHOICES)
    score = models.FloatField()  # Confidence score 0-1
    rank = models.IntegerField()  # Position in recommendation list (1-20)
    
    # Context and metadata
    context = models.JSONField(default=dict)  # Page, time, user segment, etc.
    explanation = models.TextField(blank=True)  # Human-readable explanation
    
    # Performance tracking
    shown_count = models.IntegerField(default=0)  # How many times shown to user
    click_count = models.IntegerField(default=0)  # How many times clicked
    purchase_count = models.IntegerField(default=0)  # How many times led to purchase
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # When recommendation becomes stale
    
    class Meta:
        db_table = 'recommendations'
        indexes = [
            models.Index(fields=['store', 'user', 'algorithm']),
            models.Index(fields=['store', 'session_id']),
            models.Index(fields=['store', 'product']),
            models.Index(fields=['algorithm', 'score']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = ['store', 'user', 'session_id', 'product', 'algorithm']
        ordering = ['-score', 'rank']
    
    def __str__(self):
        user_id = self.user.user_id if self.user else self.session_id
        return f"{self.algorithm}: {user_id} → {self.product.title} ({self.score:.2f})"
    
    @property
    def click_through_rate(self):
        """Calculate CTR for this recommendation"""
        if self.shown_count == 0:
            return 0.0
        return (self.click_count / self.shown_count) * 100
    
    @property
    def conversion_rate(self):
        """Calculate conversion rate"""
        if self.shown_count == 0:
            return 0.0
        return (self.purchase_count / self.shown_count) * 100
    
    def increment_shown(self):
        """Increment shown count"""
        self.shown_count += 1
        self.save(update_fields=['shown_count'])
    
    def increment_click(self):
        """Increment click count"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    def increment_purchase(self):
        """Increment purchase count"""
        self.purchase_count += 1
        self.save(update_fields=['purchase_count'])

class MLModel(models.Model):
    """Store trained ML model metadata and performance"""
    MODEL_TYPES = [
        ('collaborative_filtering', 'Collaborative Filtering'),
        ('content_based', 'Content-Based'),
        ('hybrid', 'Hybrid'),
        ('session_based', 'Session-Based'),
    ]
    
    STATUS_CHOICES = [
        ('training', 'Training'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('failed', 'Failed'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='ml_models')
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    version = models.CharField(max_length=50)
    
    # Model storage
    model_file = models.FileField(upload_to='ml_models/', null=True, blank=True)
    model_config = models.JSONField(default=dict)  # Hyperparameters, feature config
    
    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    training_loss = models.FloatField(null=True, blank=True)
    
    # Training data
    training_data_size = models.IntegerField(default=0)
    features_used = models.JSONField(default=list)  # List of features used
    feature_importance = models.JSONField(default=dict)  # Feature importance scores
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='training')
    is_active = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    # Training info
    trained_at = models.DateTimeField(auto_now=True)
    training_duration = models.FloatField(null=True, blank=True)  # in seconds
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ml_models'
        indexes = [
            models.Index(fields=['store', 'model_type']),
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['store', 'status']),
        ]
        unique_together = ['store', 'model_type', 'version']
        ordering = ['-trained_at']
    
    def __str__(self):
        return f"{self.model_type} v{self.version} - {self.store.name}"
    
    def activate(self):
        """Activate this model and deactivate others of same type"""
        # Deactivate other models of same type
        MLModel.objects.filter(
            store=self.store,
            model_type=self.model_type,
            is_active=True
        ).update(is_active=False)
        
        # Activate this model
        self.is_active = True
        self.status = 'active'
        self.save()
    
    def update_performance(self, metrics):
        """Update model performance metrics"""
        self.accuracy = metrics.get('accuracy')
        self.precision = metrics.get('precision')
        self.recall = metrics.get('recall')
        self.f1_score = metrics.get('f1_score')
        self.training_loss = metrics.get('training_loss')
        self.save()

class RecommendationConfig(models.Model):
    """Configuration for recommendation algorithms"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='recommendation_configs')
    name = models.CharField(max_length=100)
    algorithm = models.CharField(max_length=50, choices=Recommendation.ALGORITHM_CHOICES)
    
    # Algorithm configuration
    config = models.JSONField(default=dict)  # Algorithm-specific parameters
    is_active = models.BooleanField(default=True)
    
    # Weight in hybrid recommendations
    weight = models.FloatField(default=1.0)
    
    # Filters and constraints
    filters = models.JSONField(default=dict)  # Category, price range, etc.
    max_recommendations = models.IntegerField(default=10)
    
    class Meta:
        db_table = 'recommendation_configs'
        unique_together = ['store', 'algorithm']
    
    def __str__(self):
        return f"{self.algorithm} - {self.store.name}"

class ABTestResult(models.Model):
    """A/B test results for recommendation algorithms"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='ab_test_results')
    test_name = models.CharField(max_length=255)
    
    # Test configuration
    variants = models.JSONField(default=dict)  # {variant_name: config}
    traffic_allocation = models.JSONField(default=dict)  # {variant_name: percentage}
    
    # Results
    primary_metric = models.CharField(max_length=100, default='click_through_rate')
    results = models.JSONField(default=dict)
    winning_variant = models.CharField(max_length=100, blank=True)
    confidence_level = models.FloatField(null=True, blank=True)  # Statistical significance
    
    # Test duration
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    total_participants = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ab_test_results'
        indexes = [
            models.Index(fields=['store', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.test_name} - {self.store.name}"

class UserRecommendationProfile(models.Model):
    """User-specific recommendation preferences and history"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='user_recommendation_profiles')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendation_profile')
    
    # Algorithm preferences (which algorithms work best for this user)
    algorithm_weights = models.JSONField(default=dict)  # {algorithm: weight}
    
    # Recommendation history
    total_recommendations_shown = models.IntegerField(default=0)
    total_recommendations_clicked = models.IntegerField(default=0)
    total_recommendations_purchased = models.IntegerField(default=0)
    
    # Performance metrics
    overall_ctr = models.FloatField(default=0.0)
    overall_conversion_rate = models.FloatField(default=0.0)
    
    # User preferences (explicit and inferred)
    preferred_categories = models.JSONField(default=dict)
    preferred_brands = models.JSONField(default=dict)
    price_sensitivity = models.FloatField(null=True, blank=True)  # 0-1 scale
    novelty_seeking = models.FloatField(default=0.5)  # 0-1 scale
    
    # Timestamps
    last_recommendation_at = models.DateTimeField(null=True, blank=True)
    profile_updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_recommendation_profiles'
        unique_together = ['store', 'user']
    
    def __str__(self):
        return f"Recommendation Profile - {self.user.user_id}"
    
    def update_performance_metrics(self):
        """Update performance metrics"""
        if self.total_recommendations_shown > 0:
            self.overall_ctr = (self.total_recommendations_clicked / self.total_recommendations_shown) * 100
            self.overall_conversion_rate = (self.total_recommendations_purchased / self.total_recommendations_shown) * 100
            self.save()

class TrendingProduct(models.Model):
    """Trending products calculated in real-time"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='trending_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='trending_entries')
    
    # Trending metrics
    score = models.FloatField()  # Trending score 0-100
    velocity = models.FloatField()  # Rate of increase in popularity
    rank = models.IntegerField()  # Current ranking
    
    # Time window
    calculation_window = models.CharField(max_length=20, default='24h')  # 1h, 6h, 24h, 7d
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'trending_products'
        unique_together = ['store', 'product', 'calculation_window']
        indexes = [
            models.Index(fields=['store', 'calculation_window', 'score']),
        ]
        ordering = ['-score']
    
    def __str__(self):
        return f"Trending: {self.product.title} ({self.score:.1f})"

class RecommendationFeedback(models.Model):
    """User feedback on recommendations"""
    FEEDBACK_TYPES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='recommendation_feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendation_feedback')
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='feedback')
    
    feedback_type = models.CharField(max_length=10, choices=FEEDBACK_TYPES)
    rating = models.IntegerField(null=True, blank=True)  # 1-5 scale
    comment = models.TextField(blank=True)
    
    # Context
    context = models.JSONField(default=dict)  # Page, position, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'recommendation_feedback'
        indexes = [
            models.Index(fields=['store', 'user', 'feedback_type']),
            models.Index(fields=['recommendation', 'feedback_type']),
        ]
    
    def __str__(self):
        return f"{self.feedback_type} - {self.user.user_id}"

class SimilarProduct(models.Model):
    """Pre-computed similar products"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='similar_products')
    source_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='similar_to')
    target_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='similar_from')
    
    # Similarity metrics
    similarity_score = models.FloatField()  # 0-1 similarity
    similarity_type = models.CharField(max_length=50)  # content, collaborative, visual
    features_used = models.JSONField(default=list)
    
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'similar_products'
        unique_together = ['store', 'source_product', 'target_product']
        indexes = [
            models.Index(fields=['store', 'source_product', 'similarity_score']),
        ]
        ordering = ['-similarity_score']
    
    def __str__(self):
        return f"{self.source_product.title} ≈ {self.target_product.title} ({self.similarity_score:.2f})"