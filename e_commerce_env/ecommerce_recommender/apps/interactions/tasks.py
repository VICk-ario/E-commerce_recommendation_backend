from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Min, Max
from .models import Interaction, UserBehaviorProfile, ProductView

@shared_task
def update_user_behavior_profile(user_id):
    """Update user behavior profile asynchronously"""
    from apps.users.models import User
    from django.db.models import Count, Avg, Sum, F, Window
    from django.db.models.functions import Lag
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get or create behavior profile
        profile, created = UserBehaviorProfile.objects.get_or_create(
            store=user.store,
            user=user
        )
        
        # Calculate interaction frequencies
        interactions = Interaction.objects.filter(user=user)
        profile.total_interactions = interactions.count()
        profile.total_views = interactions.filter(interaction_type='view').count()
        profile.total_purchases = interactions.filter(interaction_type='purchase').count()
        profile.total_cart_adds = interactions.filter(interaction_type='cart_add').count()
        
        # Calculate session metrics
        sessions = user.sessions.all()
        if sessions.exists():
            profile.avg_session_duration = sessions.aggregate(
                avg=Avg('duration_seconds')
            )['avg'] or 0.0
            
            # Calculate time between sessions
            if sessions.count() > 1:
                # This is a simplified calculation
                first_session = sessions.earliest('start_time')
                last_session = sessions.latest('start_time')
                total_days = (last_session.start_time - first_session.start_time).days
                profile.avg_time_between_sessions = total_days / (sessions.count() - 1)
        
        # Update last active date
        last_interaction = interactions.order_by('-created_at').first()
        if last_interaction:
            profile.last_active_date = last_interaction.created_at
        
        # Calculate preferences
        category_interactions = interactions.filter(
            product__isnull=False
        ).values('product__category').annotate(
            count=Count('id'),
            total_weight=Sum('weight')
        ).order_by('-total_weight')
        
        preferred_categories = {}
        for item in category_interactions[:10]:
            preferred_categories[item['product__category']] = float(item['total_weight'])
        
        profile.preferred_categories = preferred_categories
        
        # Calculate price preference
        purchases = interactions.filter(interaction_type='purchase', value__gt=0)
        if purchases.exists():
            price_stats = purchases.aggregate(
                min_price=Min('value'),
                max_price=Max('value'),
                avg_price=Avg('value')
            )
            profile.price_preference = {
                'min': float(price_stats['min_price'] or 0),
                'max': float(price_stats['max_price'] or 0),
                'avg': float(price_stats['avg_price'] or 0)
            }
        
        # Calculate behavioral patterns
        if profile.total_purchases > 10:
            profile.purchase_frequency = 'frequent'
        elif profile.total_purchases > 3:
            profile.purchase_frequency = 'occasional'
        else:
            profile.purchase_frequency = 'rare'
        
        # Calculate browsing pattern
        if profile.total_views > profile.total_interactions * 0.8:
            profile.browsing_pattern = 'explorer'
        elif profile.total_purchases / max(profile.total_views, 1) > 0.1:
            profile.browsing_pattern = 'focused'
        else:
            profile.browsing_pattern = 'browser'
        
        # Calculate average order value
        if profile.total_purchases > 0:
            total_purchase_value = purchases.aggregate(
                total=Sum('value')
            )['total'] or 0
            profile.avg_order_value = total_purchase_value / profile.total_purchases
        
        profile.save()
        
    except User.DoesNotExist:
        pass

@shared_task
def update_daily_product_views(product_id):
    """Update daily product view aggregates"""
    from apps.products.models import Product
    
    try:
        product = Product.objects.get(id=product_id)
        today = timezone.now().date()
        
        # Get or create today's product view record
        product_view, created = ProductView.objects.get_or_create(
            store=product.store,
            product=product,
            date=today
        )
        
        # Update metrics
        today_interactions = Interaction.objects.filter(
            product=product,
            created_at__date=today
        )
        
        product_view.total_views = today_interactions.filter(
            interaction_type='view'
        ).count()
        
        product_view.unique_views = today_interactions.filter(
            interaction_type='view'
        ).values('user').distinct().count()
        
        product_view.detail_views = today_interactions.filter(
            interaction_type='detail_view'
        ).count()
        
        product_view.cart_adds = today_interactions.filter(
            interaction_type='cart_add'
        ).count()
        
        product_view.purchases = today_interactions.filter(
            interaction_type='purchase'
        ).count()
        
        purchase_value = today_interactions.filter(
            interaction_type='purchase'
        ).aggregate(total=Sum('value'))['total'] or 0
        product_view.revenue = purchase_value
        
        # Calculate average time on page
        time_stats = today_interactions.filter(
            time_on_page__gt=0
        ).aggregate(avg_time=Avg('time_on_page'))
        product_view.avg_time_on_page = time_stats['avg_time'] or 0.0
        
        product_view.save()
        
    except Product.DoesNotExist:
        pass

@shared_task
def cleanup_old_interactions():
    """Clean up old interaction data to manage database size"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Delete interactions older than 2 years
    cutoff_date = timezone.now() - timedelta(days=730)
    deleted_count = Interaction.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old interactions"