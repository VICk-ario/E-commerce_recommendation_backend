from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.stores.models import Store, StoreAPIKey
from apps.stores.serializers import (
    StoreSerializer, StoreCreateSerializer, StoreConfigSerializer,
    StoreAPIKeySerializer, StoreAPIKeyCreateSerializer
)
from apps.stores.authentication import StoreAPIKeyAuthentication

class StoreViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['platform', 'is_active', 'is_verified']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StoreCreateSerializer
        return super().get_serializer_class()
    
    def get_queryset(self):
        # Stores can only see themselves
        if hasattr(self.request, 'auth'):
            return Store.objects.filter(id=self.request.auth.id)
        return Store.objects.none()
    
    @action(detail=True, methods=['post'])
    def regenerate_api_key(self, request, pk=None):
        store = self.get_object()
        store.api_key = None  # This will trigger new key generation in save()
        store.save()
        return Response({
            'store_id': store.id,
            'new_api_key': store.api_key
        })
    
    @action(detail=True, methods=['put', 'patch'])
    def update_config(self, request, pk=None):
        store = self.get_object()
        serializer = StoreConfigSerializer(store, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StoreAPIKeyViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = StoreAPIKeySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def get_queryset(self):
        # Stores can only see their own API keys
        if hasattr(self.request, 'auth'):
            return StoreAPIKey.objects.filter(store=self.request.auth)
        return StoreAPIKey.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StoreAPIKeyCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        api_key = self.get_object()
        api_key.key = None  # This will trigger new key generation in save()
        api_key.save()
        return Response({
            'api_key_id': api_key.id,
            'new_key': api_key.key
        })
