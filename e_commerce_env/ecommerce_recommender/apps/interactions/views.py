from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg, Sum, Q, F, Window, Min, Max
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta, datetime
import json

from apps.interactions.models import Interaction, UserInteractionSession, ProductView, UserBehaviorProfile, ABTest, InteractionEvent
from .serializers import (
    InteractionSerializer, InteractionCreateSerializer, BulkInteractionSerializer,
    UserSessionSerializer, UserSessionCreateSerializer,
    ProductViewSerializer, UserBehaviorProfileSerializer,
    ABTestSerializer, InteractionEventSerializer,
    InteractionAnalyticsSerializer
)
from apps.stores.authentication import StoreAPIKeyAuthentication

class InteractionViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = InteractionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['interaction_type', 'product', 'user', 'session']
    
    def get_queryset(self):
        store = self.request.auth
        queryset = Interaction.objects.filter(store=store).select_related(
            'user', 'product', 'session', 'store'
        )
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Filter by interaction type
        interaction_type = self.request.query_params.get('interaction_type')
        if interaction_type:
            queryset = queryset.filter(interaction_type=interaction_type)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InteractionCreateSerializer
        elif self.action == 'bulk_create':
            return BulkInteractionSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple interactions in one request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = serializer.save()
        return Response({
            'status': 'success',
            'interactions_created': result['interactions_created']
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get interaction analytics"""
        store = request.auth
        serializer = InteractionAnalyticsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        date_range = data.get('date_range', '7d')
        interaction_type = data.get('interaction_type')
        group_by = data.get('group_by', 'day')
        
        # Calculate date range
        end_date = timezone.now()
        if date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)
        
        # Base queryset
        queryset = Interaction.objects.filter(
            store=store,
            created_at__range=[start_date, end_date]
        )
        
        if interaction_type:
            queryset = queryset.filter(interaction_type=interaction_type)
        
        # Group by time period
        if group_by == 'hour':
            trunc_func = TruncHour('created_at')
        else:  # day
            trunc_func = TruncDate('created_at')
        
        analytics_data = queryset.annotate(
            period=trunc_func
        ).values('period').annotate(
            count=Count('id'),
            unique_users=Count('user', distinct=True),
            total_value=Sum('value'),
            avg_weight=Avg('weight')
        ).order_by('period')
        
        # Overall statistics
        overall_stats = queryset.aggregate(
            total_interactions=Count('id'),
            total_users=Count('user', distinct=True),
            total_value=Sum('value'),
            avg_interactions_per_user=Count('id') / Count('user', distinct=True)
        )
        
        # Interaction type distribution
        type_distribution = queryset.values('interaction_type').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / Count('id', filter=Q(store=store))
        ).order_by('-count')
        
        return Response({
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'analytics': list(analytics_data),
            'overall_stats': overall_stats,
            'type_distribution': list(type_distribution),
            'store_id': store.id
        })
    
    @action(detail=False, methods=['get'])
    def popular_products(self, request):
        """Get most popular products based on interactions"""
        store = request.auth
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now() - timedelta(days=days)
        
        popular_products = Interaction.objects.filter(
            store=store,
            created_at__gte=start_date,
            product__isnull=False
        ).values(
            'product_id', 'product__title', 'product__category'
        ).annotate(
            total_views=Count('id', filter=Q(interaction_type='view')),
            total_clicks=Count('id', filter=Q(interaction_type='click')),
            total_purchases=Count('id', filter=Q(interaction_type='purchase')),
            total_interactions=Count('id'),
            purchase_value=Sum('value', filter=Q(interaction_type='purchase')),
            engagement_score=Sum('weight')
        ).order_by('-engagement_score')[:20]
        
        return Response({
            'store_id': store.id,
            'time_period_days': days,
            'popular_products': list(popular_products)
        })
    
    @action(detail=False, methods=['get'])
    def user_activity(self, request):
        """Get user activity timeline"""
        store = request.auth
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.users.models import User
            user = User.objects.get(store=store, user_id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        interactions = Interaction.objects.filter(
            store=store,
            user=user
        ).select_related('product').order_by('-created_at')[:100]
        
        serializer = InteractionSerializer(interactions, many=True)
        
        # User summary
        user_summary = Interaction.objects.filter(
            store=store,
            user=user
        ).aggregate(
            total_interactions=Count('id'),
            first_interaction=Min('created_at'),
            last_interaction=Max('created_at'),
            total_purchase_value=Sum('value', filter=Q(interaction_type='purchase')),
            favorite_category=Count('product__category')
        )
        
        return Response({
            'user_id': user_id,
            'user_summary': user_summary,
            'recent_activity': serializer.data
        })

class UserSessionViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserSessionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'purchased', 'added_to_cart']
    
    def get_queryset(self):
        store = self.request.auth
        return UserInteractionSession.objects.filter(store=store).select_related('user', 'store')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserSessionCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)
    
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
    
    @action(detail=False, methods=['get'])
    def session_analytics(self, request):
        """Get session analytics"""
        store = request.auth
        days = int(request.query_params.get('days', 7))
        
        start_date = timezone.now() - timedelta(days=days)
        
        sessions = UserInteractionSession.objects.filter(
            store=store,
            start_time__gte=start_date
        )
        
        analytics = sessions.aggregate(
            total_sessions=Count('id'),
            active_sessions=Count('id', filter=Q(end_time__isnull=True)),
            avg_session_duration=Avg('duration_seconds'),
            avg_page_views=Avg('page_views'),
            conversion_rate=Count('id', filter=Q(purchased=True)) * 100.0 / Count('id')
        )
        
        # Sessions over time
        sessions_over_time = sessions.annotate(
            date=TruncDate('start_time')
        ).values('date').annotate(
            count=Count('id'),
            avg_duration=Avg('duration_seconds')
        ).order_by('date')
        
        return Response({
            'store_id': store.id,
            'time_period_days': days,
            'analytics': analytics,
            'sessions_over_time': list(sessions_over_time)
        })

class ProductViewViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProductViewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'date']
    
    def get_queryset(self):
        store = self.request.auth
        return ProductView.objects.filter(store=store).select_related('product', 'store')

class UserBehaviorProfileViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserBehaviorProfileSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return UserBehaviorProfile.objects.filter(store=store).select_related('user', 'store')
    
    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """Get behavioral recommendations for a user"""
        profile = self.get_object()
        
        # This will be implemented in the Recommendations app
        # For now, return basic recommendations based on preferences
        
        preferred_categories = list(profile.preferred_categories.keys())[:3]
        
        from apps.products.models import Product
        recommended_products = Product.objects.filter(
            store=profile.store,
            category__in=preferred_categories
        )[:10]
        
        recommendations = [
            {
                'product_id': product.id,
                'title': product.title,
                'category': product.category,
                'price': float(product.price) if product.price else 0.0,
                'reason': f"Matches your interest in {product.category}"
            }
            for product in recommended_products
        ]
        
        return Response({
            'user_id': profile.user.user_id,
            'preferred_categories': preferred_categories,
            'recommendations': recommendations
        })

class ABTestViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ABTestSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return ABTest.objects.filter(store=store).select_related('store')
    
    @action(detail=True, methods=['post'])
    def start_test(self, request, pk=None):
        """Start an A/B test"""
        test = self.get_object()
        
        if test.status != 'draft':
            return Response(
                {'error': 'Test can only be started from draft status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        test.status = 'running'
        test.start_date = timezone.now()
        test.save()
        
        return Response({
            'status': 'success',
            'test_id': test.id,
            'started_at': test.start_date.isoformat()
        })
    
    @action(detail=True, methods=['post'])
    def end_test(self, request, pk=None):
        """End an A/B test and calculate results"""
        test = self.get_object()
        
        if test.status != 'running':
            return Response(
                {'error': 'Test is not running'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        test.status = 'completed'
        test.end_date = timezone.now()
        
        # Calculate results (simplified)
        # In a real implementation, this would analyze interaction data
        test.results = {
            'winner': 'variant_a',
            'confidence': 0.95,
            'variants': {
                'variant_a': {'conversion_rate': 0.15},
                'variant_b': {'conversion_rate': 0.12}
            }
        }
        
        test.save()
        
        return Response({
            'status': 'success',
            'test_id': test.id,
            'ended_at': test.end_date.isoformat(),
            'results': test.results
        })

class InteractionEventViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = InteractionEventSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return InteractionEvent.objects.filter(store=store)
    
    @action(detail=False, methods=['post'])
    def batch_events(self, request):
        """Process multiple events in batch"""
        events_data = request.data.get('events', [])
        
        events = []
        for event_data in events_data:
            event = InteractionEvent.objects.create(
                store=request.auth,
                **event_data
            )
            events.append(event)
        
        return Response({
            'status': 'success',
            'events_processed': len(events)
        })