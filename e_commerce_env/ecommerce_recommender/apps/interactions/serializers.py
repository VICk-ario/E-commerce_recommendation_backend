from rest_framework import serializers
from apps.interactions.models import Interaction, UserInteractionSession, ProductView, UserBehaviorProfile, ABTest, InteractionEvent
from django.utils import timezone

class InteractionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionEvent
        fields = [
            'event_type', 'event_data', 'user_id', 'session_id', 
            'product_id', 'created_at'
        ]
        read_only_fields = ['created_at']

class InteractionSerializer(serializers.ModelSerializer):
    user_id_display = serializers.CharField(source='user.user_id', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    session_id_display = serializers.CharField(source='session.session_id', read_only=True)
    
    class Meta:
        model = Interaction
        fields = [
            'id', 'store', 'store_name', 'user', 'user_id_display', 
            'product', 'product_title', 'session', 'session_id_display',
            'interaction_type', 'value', 'weight',
            'page_url', 'page_title', 'referrer_url',
            'user_agent', 'ip_address', 'screen_resolution', 'language',
            'product_price', 'product_category',
            'search_query', 'search_results_count', 'search_position',
            'time_on_page', 'scroll_depth', 'metadata',
            'created_at'
        ]
        read_only_fields = [
            'id', 'store_name', 'user_id_display', 'product_title', 
            'session_id_display', 'created_at', 'weight'
        ]

class InteractionCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(write_only=True, required=False)
    session_id = serializers.CharField(write_only=True, required=False)
    product_id = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Interaction
        fields = [
            'user_id', 'session_id', 'product_id', 'interaction_type',
            'value', 'page_url', 'page_title', 'referrer_url',
            'user_agent', 'ip_address', 'screen_resolution', 'language',
            'search_query', 'search_results_count', 'search_position',
            'time_on_page', 'scroll_depth', 'metadata'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        store = request.auth
        
        # Extract foreign key IDs
        user_id = validated_data.pop('user_id', None)
        session_id = validated_data.pop('session_id', None)
        product_id = validated_data.pop('product_id', None)
        
        # Get or create user
        user = None
        if user_id:
            from apps.users.models import User
            user, created = User.objects.get_or_create(
                store=store,
                user_id=user_id,
                defaults={'last_seen': serializers.DateTimeField().to_representation(serializers.DateTimeField().to_representation(serializers.DateTimeField()))}
            )
            if not created:
                user.update_last_seen()
        
        # Get or create session
        session = None
        if session_id:
            session, created = UserInteractionSession.objects.get_or_create(
                store=store,
                session_id=session_id,
                defaults={
                    'user': user,
                    'landing_page': validated_data.get('page_url', ''),
                    'user_agent': validated_data.get('user_agent', ''),
                    'ip_address': validated_data.get('ip_address'),
                }
            )
            if not created and user and not session.user:
                session.user = user
                session.save()
        
        # Get product
        product = None
        if product_id:
            from apps.products.models import Product
            try:
                product = Product.objects.get(store=store, product_id=product_id)
            except Product.DoesNotExist:
                # Product might not be synced yet, that's okay
                pass
        
        # Create interaction
        interaction = Interaction.objects.create(
            store=store,
            user=user,
            product=product,
            session=session,
            **validated_data
        )
        
        return interaction

class UserSessionSerializer(serializers.ModelSerializer):
    user_id_display = serializers.CharField(source='user.user_id', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    duration_display = serializers.CharField(read_only=True)
    conversion_rate = serializers.FloatField(read_only=True)
    interactions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UserInteractionSession
        fields = [
            'id', 'store', 'store_name', 'user', 'user_id_display', 'session_id',
            'start_time', 'end_time', 'is_active', 'duration_seconds', 'duration_display',
            'page_views', 'products_viewed', 'unique_products_viewed', 'total_interactions',
            'interactions_count', 'conversion_rate',
            'landing_page', 'exit_page', 'user_agent', 'ip_address', 'referrer',
            'device_type', 'browser', 'operating_system',
            'country', 'region', 'city',
            'added_to_cart', 'purchased', 'total_value',
        ]
        read_only_fields = [
            'id', 'store_name', 'user_id_display', 'is_active', 'duration_display',
            'conversion_rate', 'start_time', 'end_time'
        ]
    
    def get_interactions_count(self, obj):
        return obj.interactions.count()

class UserSessionCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(required=False)
    
    class Meta:
        model = UserInteractionSession
        fields = [
            'session_id', 'user_id', 'landing_page', 'user_agent', 
            'ip_address', 'referrer', 'device_type', 'browser', 
            'operating_system', 'country', 'region', 'city'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        store = request.auth
        
        user_id = validated_data.pop('user_id', None)
        user = None
        
        if user_id:
            from apps.users.models import User
            user, created = User.objects.get_or_create(
                store=store,
                user_id=user_id,
                defaults={'last_seen': serializers.DateTimeField().to_representation(serializers.DateTimeField().to_representation(serializers.DateTimeField()))}
            )
            if not created:
                user.update_last_seen()
        
        session = UserInteractionSession.objects.create(
            store=store,
            user=user,
            **validated_data
        )
        
        return session

class ProductViewSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_category = serializers.CharField(source='product.category', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = ProductView
        fields = [
            'id', 'store', 'store_name', 'product', 'product_title', 
            'product_category', 'date', 'total_views', 'unique_views',
            'detail_views', 'avg_time_on_page', 'cart_adds', 'purchases', 'revenue'
        ]
        read_only_fields = ['id', 'store_name', 'product_title', 'product_category']

class UserBehaviorProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.user_id', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = UserBehaviorProfile
        fields = [
            'id', 'store', 'store_name', 'user', 'user_id', 'user_email',
            'total_interactions', 'total_views', 'total_purchases', 'total_cart_adds',
            'avg_session_duration', 'avg_time_between_sessions', 'last_active_date',
            'preferred_categories', 'preferred_brands', 'price_preference',
            'browsing_pattern', 'purchase_frequency', 'avg_order_value',
            'feature_vector', 'updated_at'
        ]
        read_only_fields = [
            'id', 'store_name', 'user_id', 'user_email', 'updated_at'
        ]

class ABTestSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    is_active = serializers.SerializerMethodField()
    days_running = serializers.SerializerMethodField()
    
    class Meta:
        model = ABTest
        fields = [
            'id', 'store', 'store_name', 'name', 'description',
            'test_type', 'variants', 'traffic_percentage', 'variant_weights',
            'status', 'primary_metric', 'results',
            'start_date', 'end_date', 'is_active', 'days_running',
            'created_at'
        ]
        read_only_fields = ['id', 'store_name', 'is_active', 'days_running', 'created_at']
    
    def get_is_active(self, obj):
        return obj.status == 'running'
    
    def get_days_running(self, obj):
        if obj.start_date and obj.status == 'running':
            return (timezone.now() - obj.start_date).days
        return 0

class BulkInteractionSerializer(serializers.Serializer):
    interactions = InteractionCreateSerializer(many=True)
    
    def create(self, validated_data):
        interactions_data = validated_data['interactions']
        interactions = []
        
        for interaction_data in interactions_data:
            serializer = InteractionCreateSerializer(
                data=interaction_data,
                context=self.context
            )
            if serializer.is_valid():
                interaction = serializer.save()
                interactions.append(interaction)
        
        return {'interactions_created': len(interactions)}

class InteractionAnalyticsSerializer(serializers.Serializer):
    date_range = serializers.CharField(required=False, default='7d')
    interaction_type = serializers.CharField(required=False)
    group_by = serializers.CharField(required=False, default='day')
    
    class Meta:
        fields = ['date_range', 'interaction_type', 'group_by']