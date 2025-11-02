from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Q

from .models import DailyMetrics
from apps.interactions.models import Interaction
from apps.users.models import User
from apps.recommendations.models import Recommendation

@shared_task
def calculate_daily_metrics():
    """Calculate daily metrics for all stores"""
    from apps.stores.models import Store
    
    yesterday = timezone.now() - timedelta(days=1)
    date = yesterday.date()
    
    for store in Store.objects.all():
        # User metrics
        user_metrics = User.objects.filter(store=store).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(last_seen__date=date)),
            new=Count('id', filter=Q(first_seen__date=date))
        )
        
        # Interaction metrics
        interaction_metrics = Interaction.objects.filter(
            store=store,
            created_at__date=date
        ).aggregate(
            total=Count('id'),
            purchases=Count('id', filter=Q(interaction_type='purchase')),
            revenue=Sum('value', filter=Q(interaction_type='purchase'))
        )
        
        # Recommendation metrics
        rec_metrics = Recommendation.objects.filter(
            store=store,
            created_at__date=date
        ).aggregate(
            shown=Sum('shown_count'),
            clicked=Sum('click_count'),
            revenue=Sum('purchase_count')  # Simplified
        )
        
        # Create or update daily metrics
        DailyMetrics.objects.update_or_create(
            store=store,
            date=date,
            defaults={
                'total_users': user_metrics['total'],
                'active_users': user_metrics['active'],
                'new_users': user_metrics['new'],
                'total_interactions': interaction_metrics['total'],
                'purchases': interaction_metrics['purchases'],
                'revenue': interaction_metrics['revenue'] or 0,
                'recs_shown': rec_metrics['shown'] or 0,
                'recs_clicked': rec_metrics['clicked'] or 0,
                'rec_revenue': rec_metrics['revenue'] or 0
            }
        )
    
    return "Daily metrics calculated"