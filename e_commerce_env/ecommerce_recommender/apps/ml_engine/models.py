from django.db import models
from apps.stores.models import Store

class MLModel(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50, choices=[
        ('collaborative', 'Collaborative Filtering'),
        ('content', 'Content-Based'),
        ('hybrid', 'Hybrid')
    ])
    version = models.CharField(max_length=50)
    model_file = models.FileField(upload_to='ml_models/')
    accuracy = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['store', 'name', 'version']

    def __str__(self):
        return f"{self.name} v{self.version}"

    def activate(self):
        MLModel.objects.filter(store=self.store, model_type=self.model_type).update(is_active=False)
        self.is_active = True
        self.save()