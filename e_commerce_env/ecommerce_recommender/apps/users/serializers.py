from rest_framework import serializers
from apps.users.models import User, UserSession, UserPreference

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['preference_type', 'preference_value', 'confidence', 'source']

class UserSessionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    duration_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'session_id', 'start_time', 'end_time', 'is_active',
            'page_views', 'products_viewed', 'duration_seconds', 'duration_display',
            'landing_page', 'exit_page', 'user_agent', 'ip_address', 'referrer'
        ]
        read_only_fields = ['id', 'start_time', 'end_time', 'duration_seconds']

class UserSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    full_name = serializers.CharField(read_only=True)
    engagement_score = serializers.IntegerField(read_only=True)
    customer_segment = serializers.CharField(read_only=True)
    sessions = UserSessionSerializer(many=True, read_only=True)
    preferences = UserPreferenceSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'store', 'store_name', 'user_id', 'email', 'session_id',
            'first_name', 'last_name', 'full_name', 'user_profile',
            'total_interactions', 'total_purchases', 'total_value', 'avg_order_value',
            'engagement_score', 'customer_segment',
            'is_active', 'first_seen', 'last_seen', 'last_purchase',
            'sessions', 'preferences'
        ]
        read_only_fields = [
            'id', 'store_name', 'full_name', 'engagement_score', 'customer_segment',
            'total_interactions', 'total_purchases', 'total_value', 'avg_order_value',
            'first_seen', 'last_seen', 'last_purchase'
        ]

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'email', 'session_id', 'first_name', 'last_name', 'user_profile']
    
    def create(self, validated_data):
        store = self.context['request'].auth
        validated_data['store'] = store
        return super().create(validated_data)

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'user_profile', 'is_active']

class UserSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ['session_id', 'landing_page', 'user_agent', 'ip_address', 'referrer']
    
    def create(self, validated_data):
        # Get user from context (will be set in view)
        user = self.context['user']
        validated_data['user'] = user
        validated_data['store'] = user.store
        return super().create(validated_data)

class UserPreferenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['preference_type', 'preference_value', 'confidence', 'source']
    
    def create(self, validated_data):
        user = self.context['user']
        validated_data['user'] = user
        return super().create(validated_data)