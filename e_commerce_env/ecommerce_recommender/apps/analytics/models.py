from django.db import models
from apps.stores.models import Store
from apps.users.models import User
from apps.products.models import Product

class DailyMetrics(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    date = models.DateField()
    
    # User metrics
    total_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    
    # Interaction metrics
    total_interactions = models.IntegerField(default=0)
    purchases = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    
    # Recommendation performance
    recs_shown = models.IntegerField(default=0)
    recs_clicked = models.IntegerField(default=0)
    rec_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ['store', 'date']
        indexes = [models.Index(fields=['store', 'date'])]

    def __str__(self):
        return f"{self.store.name} - {self.date}"

    @property
    def conversion_rate(self):
        return (self.recs_clicked / self.recs_shown * 100) if self.recs_shown else 0

    @property
    def click_through_rate(self):
        return (self.recs_clicked / self.recs_shown * 100) if self.recs_shown else 0

class Report(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=50, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'), 
        ('monthly', 'Monthly')
    ])
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.store.name}"