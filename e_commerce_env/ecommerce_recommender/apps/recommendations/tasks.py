from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import pandas as pd
from django.db.models import Count, Avg, Sum, Q

from .models import MLModel, TrendingProduct, SimilarProduct, Recommendation
from apps.interactions.models import Interaction
from apps.products.models import Product

@shared_task
def train_recommendation_model(store_id, model_type):
    """Train a recommendation model asynchronously"""
    from apps.stores.models import Store
    
    try:
        store = Store.objects.get(id=store_id)
        
        # Create model record
        version = f"v{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        model = MLModel.objects.create(
            store=store,
            model_type=model_type,
            version=version,
            status='training',
            description=f"Auto-trained {model_type} model"
        )
        
        # Simulate training process (replace with actual ML training)
        # This is where you'd integrate with scikit-learn, TensorFlow, etc.
        
        # For now, we'll just calculate some basic metrics
        interactions_count = Interaction.objects.filter(store=store).count()
        
        model.training_data_size = interactions_count
        model.features_used = ['user_id', 'product_id', 'interaction_type', 'timestamp']
        
        # Simulate training completion
        model.accuracy = 0.85
        model.precision = 0.82
        model.recall = 0.79
        model.f1_score = 0.80
        model.training_loss = 0.15
        model.training_duration = 120.5  # seconds
        model.status = 'active'
        
        model.save()
        
        # Activate the model
        model.activate()
        
        return f"Model training completed: {model.model_type} v{model.version}"
    
    except Store.DoesNotExist:
        return f"Store {store_id} not found"

@shared_task
def calculate_trending_products(store_id):
    """Calculate trending products based on recent interactions"""
    from apps.stores.models import Store
    
    try:
        store = Store.objects.get(id=store_id)
        
        # Define time windows
        windows = [
            ('1h', timedelta(hours=1)),
            ('6h', timedelta(hours=6)),
            ('24h', timedelta(hours=24)),
            ('7d', timedelta(days=7)),
        ]
        
        for window_name, time_delta in windows:
            since_date = timezone.now() - time_delta
            
            # Get interaction counts for the time window
            trending_data = Interaction.objects.filter(
                store=store,
                created_at__gte=since_date,
                product__isnull=False
            ).values('product').annotate(
                interaction_count=Count('id'),
                purchase_count=Count('id', filter=Q(interaction_type='purchase')),
                velocity=Count('id', filter=Q(created_at__gte=timezone.now() - time_delta / 2))  # Recent half for velocity
            ).order_by('-interaction_count')[:50]
            
            # Calculate trending scores
            for idx, item in enumerate(trending_data):
                try:
                    product = Product.objects.get(id=item['product'])
                    
                    # Calculate trending score
                    base_score = item['interaction_count']
                    purchase_boost = item['purchase_count'] * 5
                    velocity_boost = item['velocity'] * 2
                    
                    trending_score = base_score + purchase_boost + velocity_boost
                    velocity = item['velocity'] / max(item['interaction_count'], 1)
                    
                    # Create or update trending entry
                    TrendingProduct.objects.update_or_create(
                        store=store,
                        product=product,
                        calculation_window=window_name,
                        defaults={
                            'score': trending_score,
                            'velocity': velocity,
                            'rank': idx + 1
                        }
                    )
                    
                except Product.DoesNotExist:
                    continue
        
        return f"Trending products calculated for store {store_id}"
    
    except Store.DoesNotExist:
        return f"Store {store_id} not found"

@shared_task  
def precompute_similar_products(store_id):
    """Precompute similar products for all products"""
    from apps.stores.models import Store
    
    try:
        store = Store.objects.get(id=store_id)
        
        # Get all products
        products = Product.objects.filter(store=store)
        
        # Simple content-based similarity (in real implementation, use more sophisticated approach)
        for source_product in products:
            # Find similar products by category and price
            similar_products = Product.objects.filter(
                store=store,
                category=source_product.category
            ).exclude(id=source_product.id)[:20]
            
            for target_product in similar_products:
                # Calculate similarity score
                similarity_score = 0.7  # Base for same category
                
                # Price similarity
                if source_product.price and target_product.price:
                    price_diff = abs(source_product.price - target_product.price)
                    max_price = max(source_product.price, target_product.price)
                    if max_price > 0:
                        price_similarity = 1 - (price_diff / max_price)
                        similarity_score += price_similarity * 0.3
                
                # Create similar product entry
                SimilarProduct.objects.update_or_create(
                    store=store,
                    source_product=source_product,
                    target_product=target_product,
                    defaults={
                        'similarity_score': similarity_score,
                        'similarity_type': 'content_based',
                        'features_used': ['category', 'price']
                    }
                )
        
        return f"Similar products precomputed for store {store_id}"
    
    except Store.DoesNotExist:
        return f"Store {store_id} not found"

@shared_task
def cleanup_old_recommendations():
    """Clean up expired recommendations"""
    cutoff_date = timezone.now() - timedelta(days=30)
    
    # Delete recommendations older than 30 days or expired
    deleted_count = Recommendation.objects.filter(
        Q(created_at__lt=cutoff_date) | 
        Q(expires_at__lt=timezone.now())
    ).delete()[0]
    
    return f"Cleaned up {deleted_count} old recommendations"