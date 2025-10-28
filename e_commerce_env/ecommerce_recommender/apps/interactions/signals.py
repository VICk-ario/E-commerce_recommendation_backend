from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Interaction, UserBehaviorProfile
from .tasks import update_user_behavior_profile, update_daily_product_views 

@receiver(post_save, sender=Interaction)
def update_behavior_profile(sender, instance, created, **kwargs):
    """Update user behavior profile when new interaction is created"""
    if created and instance.user:
        transaction.on_commit(
            lambda: update_user_behavior_profile.delay(instance.user.id)
        )

@receiver(post_save, sender=Interaction)
def update_product_views(sender, instance, created, **kwargs):
    """Update product view aggregates"""
    if created and instance.product and instance.interaction_type == 'view':
        transaction.on_commit(
            lambda: update_daily_product_views.delay(instance.product.id)
        )