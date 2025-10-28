from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.core.cache import cache

from apps.products.models import Product
from apps.products.serializers import (
    ProductSerializer, ProductCreateSerializer, ProductUpdateSerializer,
    ProductBulkCreateSerializer
)
from apps.stores.authentication import StoreAPIKeyAuthentication

class ProductViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'brand', 'is_active', 'in_stock', 'is_published']
    
    def get_queryset(self):
        store = self.request.auth
        queryset = Product.objects.filter(store=store).select_related('store').prefetch_related('images')
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(category__icontains=search) |
                Q(brand__icontains=search)
            )
        
        # Category filter
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
            
        # Brand filter
        brand = self.request.query_params.get('brand', None)
        if brand:
            queryset = queryset.filter(brand=brand)
            
        # Price range filter
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProductCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProductUpdateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create products"""
        serializer = ProductBulkCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            products = serializer.save()
            return Response({
                'status': 'success',
                'created_count': len(products),
                'products': ProductSerializer(products, many=True).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get unique categories for the store"""
        store = request.auth
        cache_key = f'product_categories:{store.id}'
        categories = cache.get(cache_key)
        
        if not categories:
            categories = Product.objects.filter(
                store=store, 
                is_active=True,
                category__isnull=False
            ).exclude(
                category__exact=''
            ).values_list('category', flat=True).distinct()
            categories = list(categories)
            cache.set(cache_key, categories, 3600)  # Cache for 1 hour
        
        return Response({'categories': categories})
    
    @action(detail=False, methods=['get'])
    def brands(self, request):
        """Get unique brands for the store"""
        store = request.auth
        cache_key = f'product_brands:{store.id}'
        brands = cache.get(cache_key)
        
        if not brands:
            brands = Product.objects.filter(
                store=store, 
                is_active=True,
                brand__isnull=False
            ).exclude(
                brand__exact=''
            ).values_list('brand', flat=True).distinct()
            brands = list(brands)
            cache.set(cache_key, brands, 3600)  # Cache for 1 hour
        
        return Response({'brands': brands})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get product statistics for the store"""
        store = request.auth
        cache_key = f'product_stats:{store.id}'
        stats = cache.get(cache_key)
        
        if not stats:
            stats = Product.objects.filter(store=store).aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(is_active=True)),
                in_stock=Count('id', filter=Q(in_stock=True)),
                published=Count('id', filter=Q(is_published=True)),
                categories=Count('category', distinct=True),
                brands=Count('brand', distinct=True),
                on_sale=Count('id', filter=Q(compare_at_price__gt=0))
            )
            cache.set(cache_key, stats, 300)  # Cache for 5 minutes
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Enhanced search with filters"""
        store = request.auth
        query = request.query_params.get('q', '')
        
        if not query:
            return Response({'products': [], 'count': 0})
        
        products = Product.objects.filter(
            store=store,
            is_active=True,
            is_published=True
        ).filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query) |
            Q(brand__icontains=query) |
            Q(tags__contains=[query])
        )[:50]  # Limit results
        
        serializer = self.get_serializer(products, many=True)
        return Response({
            'products': serializer.data,
            'count': products.count(),
            'query': query
        })
