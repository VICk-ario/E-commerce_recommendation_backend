from rest_framework import serializers
from .models import (
    Recommendation, MLModel, RecommendationConfig, ABTestResult,
    UserRecommendationProfile, TrendingProduct, RecommendationFeedback,
    SimilarProduct
)
from django.utils import timezone

class RecommendationSerializer(serializers.ModelSerializer):
    user_id_display = serializers.CharField(source='user.user_id', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.DecimalField(source='product.price', read_only=True, max_digits=10, decimal_places=2)
    product_image = serializers.CharField(source='product.image_url', read_only=True)
    product_category = serializers.CharField(source='product.category', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    click_through_rate = serializers.FloatField(read_only=True)
    conversion_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Recommendation
        fields = [
            'id', 'store', 'store_name', 'user', 'user_id_display', 
            'session_id', 'product', 'product_title', 'product_price',
            'product_image', 'product_category', 'algorithm', 'score',
            'rank', 'explanation', 'context', 'click_through_rate',
            'conversion_rate', 'shown_count', 'click_count', 'purchase_count',
            'created_at', 'expires_at'
        ]
        read_only_fields = [
            'id', 'store_name', 'user_id_display', 'product_title',
            'product_price', 'product_image', 'product_category',
            'click_through_rate', 'conversion_rate', 'created_at'
        ]

class RecommendationCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Recommendation
        fields = [
            'user_id', 'session_id', 'product', 'algorithm', 'score',
            'rank', 'explanation', 'context', 'expires_at'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        store = request.auth
        
        user_id = validated_data.pop('user_id', None)
        user = None
        
        if user_id:
            from apps.users.models import User
            try:
                user = User.objects.get(store=store, user_id=user_id)
            except User.DoesNotExist:
                # Create user if doesn't exist
                user = User.objects.create(
                    store=store,
                    user_id=user_id,
                    last_seen=serializers.DateTimeField().to_representation(serializers.DateTimeField().to_representation(serializers.DateTimeField()))
                )
        
        recommendation = Recommendation.objects.create(
            store=store,
            user=user,
            **validated_data
        )
        
        return recommendation

class MLModelSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    is_training = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = MLModel
        fields = [
            'id', 'store', 'store_name', 'model_type', 'version',
            'model_file', 'model_config', 'accuracy', 'precision',
            'recall', 'f1_score', 'training_loss', 'training_data_size',
            'features_used', 'feature_importance', 'status', 'is_active',
            'is_training', 'description', 'trained_at', 'training_duration',
            'last_used'
        ]
        read_only_fields = [
            'id', 'store_name', 'is_training', 'trained_at', 'last_used'
        ]

class RecommendationConfigSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = RecommendationConfig
        fields = [
            'id', 'store', 'store_name', 'name', 'algorithm', 'config',
            'is_active', 'weight', 'filters', 'max_recommendations'
        ]
        read_only_fields = ['id', 'store_name']

class ABTestResultSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    is_active = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    
    class Meta:
        model = ABTestResult
        fields = [
            'id', 'store', 'store_name', 'test_name', 'variants',
            'traffic_allocation', 'primary_metric', 'results',
            'winning_variant', 'confidence_level', 'start_date',
            'end_date', 'total_participants', 'is_active', 'duration_days',
            'created_at'
        ]
        read_only_fields = ['id', 'store_name', 'is_active', 'duration_days', 'created_at']
    
    def get_is_active(self, obj):
        now = timezone.now()
        return obj.start_date <= now <= obj.end_date
    
    def get_duration_days(self, obj):
        return (obj.end_date - obj.start_date).days

class UserRecommendationProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.user_id', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = UserRecommendationProfile
        fields = [
            'id', 'store', 'store_name', 'user', 'user_id', 'user_email',
            'algorithm_weights', 'total_recommendations_shown',
            'total_recommendations_clicked', 'total_recommendations_purchased',
            'overall_ctr', 'overall_conversion_rate', 'preferred_categories',
            'preferred_brands', 'price_sensitivity', 'novelty_seeking',
            'last_recommendation_at', 'profile_updated_at'
        ]
        read_only_fields = [
            'id', 'store_name', 'user_id', 'user_email', 'profile_updated_at'
        ]

class TrendingProductSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.DecimalField(source='product.price', read_only=True, max_digits=10, decimal_places=2)
    product_image = serializers.CharField(source='product.image_url', read_only=True)
    product_category = serializers.CharField(source='product.category', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = TrendingProduct
        fields = [
            'id', 'store', 'store_name', 'product', 'product_title',
            'product_price', 'product_image', 'product_category', 'score',
            'velocity', 'rank', 'calculation_window', 'calculated_at'
        ]
        read_only_fields = [
            'id', 'store_name', 'product_title', 'product_price',
            'product_image', 'product_category', 'calculated_at'
        ]

class RecommendationFeedbackSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.user_id', read_only=True)
    product_title = serializers.CharField(source='recommendation.product.title', read_only=True)
    algorithm = serializers.CharField(source='recommendation.algorithm', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = RecommendationFeedback
        fields = [
            'id', 'store', 'store_name', 'user', 'user_id', 'recommendation',
            'product_title', 'algorithm', 'feedback_type', 'rating', 'comment',
            'context', 'created_at'
        ]
        read_only_fields = [
            'id', 'store_name', 'user_id', 'product_title', 'algorithm', 'created_at'
        ]

class SimilarProductSerializer(serializers.ModelSerializer):
    source_product_title = serializers.CharField(source='source_product.title', read_only=True)
    target_product_title = serializers.CharField(source='target_product.title', read_only=True)
    target_product_price = serializers.DecimalField(source='target_product.price', read_only=True, max_digits=10, decimal_places=2)
    target_product_image = serializers.CharField(source='target_product.image_url', read_only=True)
    target_product_category = serializers.CharField(source='target_product.category', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = SimilarProduct
        fields = [
            'id', 'store', 'store_name', 'source_product', 'source_product_title',
            'target_product', 'target_product_title', 'target_product_price',
            'target_product_image', 'target_product_category', 'similarity_score',
            'similarity_type', 'features_used', 'calculated_at'
        ]
        read_only_fields = [
            'id', 'store_name', 'source_product_title', 'target_product_title',
            'target_product_price', 'target_product_image', 'target_product_category',
            'calculated_at'
        ]

class RecommendationRequestSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False)
    session_id = serializers.CharField(required=False)
    product_id = serializers.CharField(required=False)  # For similar products
    algorithm = serializers.CharField(required=False)  # Specific algorithm to use
    max_results = serializers.IntegerField(default=10, min_value=1, max_value=50)
    context = serializers.JSONField(default=dict)  # Page, time, etc.
    
    def validate(self, data):
        if not data.get('user_id') and not data.get('session_id'):
            raise serializers.ValidationError("Either user_id or session_id is required")
        return data

class BatchRecommendationRequestSerializer(serializers.Serializer):
    requests = RecommendationRequestSerializer(many=True)
    
    class Meta:
        fields = ['requests']