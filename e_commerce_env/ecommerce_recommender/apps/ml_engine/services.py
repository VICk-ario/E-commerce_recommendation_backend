from celery import shared_task
from django.utils import timezone

class MLService:
    def __init__(self, store):
        self.store = store

    def train_model(self, model_type, parameters):
        return train_ml_model.delay(self.store.id, model_type, parameters)

    def get_predictions(self, user_id, product_id):
        # Simplified prediction logic
        from apps.recommendations.models import Recommendation
        
        if user_id:
            return Recommendation.objects.filter(
                store=self.store, 
                user__user_id=user_id,
                is_active=True
            )[:10]
        
        if product_id:
            from apps.recommendations.models import SimilarProduct
            return SimilarProduct.objects.filter(
                store=self.store,
                source_product__product_id=product_id
            )[:10]
        
        return []

@shared_task
def train_ml_model(store_id, model_type, parameters):
    # Simplified training - in real implementation, integrate with ML libraries
    from apps.stores.models import Store
    from .models import MLModel
    
    store = Store.objects.get(id=store_id)
    version = f"v{timezone.now().strftime('%Y%m%d_%H%M')}"
    
    model = MLModel.objects.create(
        store=store,
        name=f"{model_type}_model",
        model_type=model_type,
        version=version,
        accuracy=0.85,  # Mock accuracy
        is_active=True
    )
    
    model.activate()
    return f"Trained {model_type} model v{version}"