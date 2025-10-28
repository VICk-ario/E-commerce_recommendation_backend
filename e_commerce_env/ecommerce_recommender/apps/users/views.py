from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User, UserSession, UserPreference
from apps.users.serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserSessionSerializer, UserSessionCreateSerializer,
    UserPreferenceSerializer, UserPreferenceCreateSerializer
)
from apps.stores.authentication import StoreAPIKeyAuthentication

class UserViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'customer_segment']
    
    def get_queryset(self):
        store = self.request.auth
        queryset = User.objects.filter(store=store).select_related('store').prefetch_related('sessions', 'preferences')
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(user_id__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Filter by engagement level
        engagement = self.request.query_params.get('engagement', None)
        if engagement:
            if engagement == 'high':
                queryset = queryset.filter(total_interactions__gte=10, total_purchases__gte=3)
            elif engagement == 'medium':
                queryset = queryset.filter(total_interactions__gte=5, total_purchases__gte=1)
            elif engagement == 'low':
                queryset = queryset.filter(total_interactions__lt=5)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)
    
    @action(detail=True, methods=['get'])
    def interactions(self, request, pk=None):
        """Get user's interaction history"""
        user = self.get_object()
        
        # This will be enhanced when we build the Interactions app
        from apps.interactions.models import Interaction
        interactions = Interaction.objects.filter(user=user).select_related('product')[:50]
        
        # Simplified response for now
        interaction_data = [
            {
                'id': interaction.id,
                'product_id': interaction.product.id,
                'product_title': interaction.product.title,
                'interaction_type': interaction.interaction_type,
                'created_at': interaction.created_at.isoformat()
            }
            for interaction in interactions
        ]
        
        return Response({
            'user_id': user.user_id,
            'total_interactions': interactions.count(),
            'interactions': interaction_data
        })
    
    @action(detail=True, methods=['post'])
    def update_last_seen(self, request, pk=None):
        """Update user's last seen timestamp"""
        user = self.get_object()
        user.update_last_seen()
        
        return Response({
            'status': 'success',
            'user_id': user.user_id,
            'last_seen': user.last_seen.isoformat()
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics for the store"""
        store = request.auth
        
        # Basic user stats
        stats = User.objects.filter(store=store).aggregate(
            total_users=Count('id'),
            active_users=Count('id', filter=Q(is_active=True)),
            new_today=Count('id', filter=Q(first_seen__date=timezone.now().date())),
            avg_engagement=Avg('total_interactions'),
            total_value=Sum('total_value')
        )
        
        # Customer segmentation
        segments = User.objects.filter(store=store).values('customer_segment').annotate(
            count=Count('id'),
            avg_value=Avg('total_value')
        )
        
        # Recent activity
        recent_users = User.objects.filter(
            store=store,
            last_seen__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        return Response({
            'store_id': store.id,
            'user_statistics': stats,
            'segmentation': list(segments),
            'recent_activity': {
                'active_last_7_days': recent_users,
                'active_last_30_days': User.objects.filter(
                    store=store,
                    last_seen__gte=timezone.now() - timedelta(days=30)
                ).count()
            }
        })
    
    @action(detail=False, methods=['get'])
    def segments(self, request):
        """Get detailed customer segmentation"""
        store = request.auth
        
        segments = {
            'browser': User.objects.filter(store=store, total_purchases=0),
            'first_time': User.objects.filter(store=store, total_purchases=1),
            'regular': User.objects.filter(store=store, total_purchases__range=(2, 5)),
            'vip': User.objects.filter(store=store, total_purchases__gt=5),
        }
        
        segment_data = {}
        for segment_name, queryset in segments.items():
            segment_data[segment_name] = {
                'count': queryset.count(),
                'avg_interactions': queryset.aggregate(avg=Avg('total_interactions'))['avg'] or 0,
                'total_value': queryset.aggregate(total=Sum('total_value'))['total'] or 0,
                'avg_order_value': queryset.aggregate(avg=Avg('avg_order_value'))['avg'] or 0,
            }
        
        return Response(segment_data)

class UserSessionViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserSessionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def get_queryset(self):
        store = self.request.auth
        return UserSession.objects.filter(store=store).select_related('user')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserSessionCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        # Get user from query params or create new user
        user_id = self.request.data.get('user_id')
        session_id = self.request.data.get('session_id')
        
        user, created = User.objects.get_or_create(
            store=self.request.auth,
            user_id=user_id,
            defaults={
                'session_id': session_id,
                'first_seen': timezone.now(),
                'last_seen': timezone.now()
            }
        )
        
        if not created:
            user.session_id = session_id
            user.update_last_seen()
            user.save(update_fields=['session_id', 'last_seen'])
        
        serializer.save(user=user, store=self.request.auth)
    
    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End a user session"""
        session = self.get_object()
        session.end_session()
        
        return Response({
            'status': 'success',
            'session_id': session.session_id,
            'ended_at': session.end_time.isoformat(),
            'duration_seconds': session.duration_seconds
        })
    
    @action(detail=True, methods=['post'])
    def increment_page_views(self, request, pk=None):
        """Increment page views for a session"""
        session = self.get_object()
        session.increment_page_views()
        
        return Response({
            'status': 'success',
            'session_id': session.session_id,
            'page_views': session.page_views
        })

class UserPreferenceViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserPreferenceSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return UserPreference.objects.filter(user__store=store).select_related('user')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserPreferenceCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        user_id = self.request.data.get('user_id')
        
        try:
            user = User.objects.get(store=self.request.auth, user_id=user_id)
            serializer.save(user=user)
        except User.DoesNotExist:
            raise serializer.ValidationError({"user_id": "User not found"})
    
    @action(detail=False, methods=['get'])
    def popular_categories(self, request):
        """Get popular categories across all users"""
        store = request.auth
        
        popular_categories = UserPreference.objects.filter(
            user__store=store,
            preference_type='category',
            confidence__gte=0.7
        ).values('preference_value').annotate(
            user_count=Count('user', distinct=True),
            avg_confidence=Avg('confidence')
        ).order_by('-user_count')[:10]
        
        return Response({
            'store_id': store.id,
            'popular_categories': list(popular_categories)
        })
