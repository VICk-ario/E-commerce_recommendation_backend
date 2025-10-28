from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    Recommendation, MLModel, RecommendationConfig, ABTestResult,
    UserRecommendationProfile, TrendingProduct, RecommendationFeedback,
    SimilarProduct
)
from .serializers import (
    RecommendationSerializer, RecommendationCreateSerializer,
    MLModelSerializer, RecommendationConfigSerializer,
    ABTestResultSerializer, UserRecommendationProfileSerializer,
    TrendingProductSerializer, RecommendationFeedbackSerializer,
    SimilarProductSerializer, RecommendationRequestSerializer,
    BatchRecommendationRequestSerializer
)
from .services import RecommendationService
from apps.stores.authentication import StoreAPIKeyAuthentication

class RecommendationViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['algorithm', 'user', 'session_id']
    
    def get_queryset(self):
        store = self.request.auth
        queryset = Recommendation.objects.filter(store=store).select_related(
            'user', 'product', 'store'
        )
        
        # Filter by active recommendations (not expired)
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RecommendationCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate new recommendations for a user/session"""
        serializer = RecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        store = request.auth
        
        # Generate recommendations
        service = RecommendationService(store)
        recommendations = service.get_recommendations(
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            max_results=data.get('max_results', 10),
            context=data.get('context', {}),
            algorithm=data.get('algorithm')
        )
        
        # Serialize results
        result_serializer = RecommendationSerializer(recommendations, many=True)
        
        return Response({
            'count': len(recommendations),
            'user_id': data.get('user_id'),
            'session_id': data.get('session_id'),
            'algorithm': data.get('algorithm', 'hybrid'),
            'recommendations': result_serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def batch_generate(self, request):
        """Generate recommendations for multiple users/sessions"""
        serializer = BatchRecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        store = request.auth
        service = RecommendationService(store)
        results = []
        
        for req_data in serializer.validated_data['requests']:
            recommendations = service.get_recommendations(**req_data)
            result_serializer = RecommendationSerializer(recommendations, many=True)
            
            results.append({
                'user_id': req_data.get('user_id'),
                'session_id': req_data.get('session_id'),
                'algorithm': req_data.get('algorithm', 'hybrid'),
                'recommendations': result_serializer.data
            })
        
        return Response({
            'count': len(results),
            'results': results
        })
    
    @action(detail=True, methods=['post'])
    def record_impression(self, request, pk=None):
        """Record that a recommendation was shown to user"""
        recommendation = self.get_object()
        
        service = RecommendationService(recommendation.store)
        service.record_impression(recommendation.id)
        
        return Response({
            'status': 'success',
            'recommendation_id': recommendation.id,
            'shown_count': recommendation.shown_count
        })
    
    @action(detail=True, methods=['post'])
    def record_click(self, request, pk=None):
        """Record that a recommendation was clicked"""
        recommendation = self.get_object()
        
        service = RecommendationService(recommendation.store)
        service.record_click(recommendation.id)
        
        return Response({
            'status': 'success',
            'recommendation_id': recommendation.id,
            'click_count': recommendation.click_count
        })
    
    @action(detail=False, methods=['get'])
    def similar_products(self, request):
        """Get similar products for a given product"""
        product_id = request.query_params.get('product_id')
        max_results = int(request.query_params.get('max_results', 10))
        
        if not product_id:
            return Response(
                {'error': 'product_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        store = request.auth
        service = RecommendationService(store)
        
        try:
            recommendations = service.get_similar_products(product_id, max_results)
            serializer = RecommendationSerializer([rec['product'] for rec in recommendations], many=True)
            
            return Response({
                'source_product_id': product_id,
                'similar_products': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending products"""
        store = request.auth
        window = request.query_params.get('window', '24h')
        max_results = int(request.query_params.get('max_results', 10))
        
        trending_products = TrendingProduct.objects.filter(
            store=store,
            calculation_window=window
        ).select_related('product').order_by('-score')[:max_results]
        
        serializer = TrendingProductSerializer(trending_products, many=True)
        
        return Response({
            'window': window,
            'trending_products': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def performance(self, request):
        """Get recommendation performance analytics"""
        store = request.auth
        days = int(request.query_params.get('days', 7))
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Overall performance
        performance = Recommendation.objects.filter(
            store=store,
            created_at__gte=start_date
        ).aggregate(
            total_recommendations=Count('id'),
            total_impressions=Sum('shown_count'),
            total_clicks=Sum('click_count'),
            total_purchases=Sum('purchase_count'),
            avg_ctr=Avg('click_count') / Avg('shown_count') * 100,
            avg_conversion_rate=Avg('purchase_count') / Avg('shown_count') * 100
        )
        
        # Performance by algorithm
        algorithm_performance = Recommendation.objects.filter(
            store=store,
            created_at__gte=start_date,
            shown_count__gt=0  # Only consider recommendations that were shown
        ).values('algorithm').annotate(
            total_shown=Sum('shown_count'),
            total_clicks=Sum('click_count'),
            total_purchases=Sum('purchase_count'),
            ctr=Sum('click_count') * 100.0 / Sum('shown_count'),
            conversion_rate=Sum('purchase_count') * 100.0 / Sum('shown_count')
        ).order_by('-ctr')
        
        return Response({
            'store_id': store.id,
            'time_period_days': days,
            'overall_performance': performance,
            'algorithm_performance': list(algorithm_performance)
        })

class MLModelViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = MLModelSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return MLModel.objects.filter(store=store).select_related('store')
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate this ML model"""
        model = self.get_object()
        model.activate()
        
        return Response({
            'status': 'success',
            'model_id': model.id,
            'model_type': model.model_type,
            'version': model.version
        })
    
    @action(detail=False, methods=['post'])
    def train(self, request):
        """Trigger training of a new ML model"""
        from .tasks import train_recommendation_model
        
        store = request.auth
        model_type = request.data.get('model_type', 'hybrid')
        
        # Trigger async training
        task = train_recommendation_model.delay(store.id, model_type)
        
        return Response({
            'status': 'training_started',
            'task_id': task.id,
            'model_type': model_type,
            'store_id': store.id
        })

class RecommendationConfigViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendationConfigSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return RecommendationConfig.objects.filter(store=store).select_related('store')

class UserRecommendationProfileViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserRecommendationProfileSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return UserRecommendationProfile.objects.filter(store=store).select_related('user', 'store')

class RecommendationFeedbackViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendationFeedbackSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return RecommendationFeedback.objects.filter(store=store).select_related('user', 'recommendation')

# Additional view sets for other models...
class TrendingProductViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TrendingProductSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return TrendingProduct.objects.filter(store=store).select_related('product', 'store')

class SimilarProductViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SimilarProductSerializer
    
    def get_queryset(self):
        store = self.request.auth
        return SimilarProduct.objects.filter(store=store).select_related('source_product', 'target_product', 'store')