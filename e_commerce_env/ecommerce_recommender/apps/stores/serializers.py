from rest_framework import serializers
from apps.stores.models import Store, StoreAPIKey

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'domain', 'platform', 'is_active', 
            'is_verified', 'created_at', 'updated_at', 'last_sync_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync_at']

class StoreCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['name', 'domain', 'platform']
    
    def create(self, validated_data):
        store = Store.objects.create(**validated_data)
        return store

class StoreConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['config']

class StoreAPIKeySerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = StoreAPIKey
        fields = ['id', 'name', 'key', 'store', 'store_name', 'is_active', 'created_at', 'last_used']
        read_only_fields = ['id', 'key', 'created_at', 'last_used']

class StoreAPIKeyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreAPIKey
        fields = ['name', 'store']