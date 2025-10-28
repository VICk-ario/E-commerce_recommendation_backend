from django.db import models
from apps.stores.models import Store

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    
    # Store's product identifier
    store_product_id = models.CharField(max_length=255)
    variant_id = models.CharField(max_length=255, blank=True)
    
    # Product details
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    handle = models.CharField(max_length=500, blank=True)  # URL slug
    category = models.CharField(max_length=255, blank=True)
    brand = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    product_url = models.URLField(max_length=1000, blank=True)
    
    # Additional attributes
    tags = models.JSONField(default=list, blank=True)
    options = models.JSONField(default=dict, blank=True)  # Size, color, etc.
    metadata = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    in_stock = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['store', 'store_product_id']),
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['brand']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
        ]
        unique_together = ['store', 'store_product_id']
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_on_sale(self):
        """Check if product is on sale"""
        return self.compare_at_price and self.price and self.price < self.compare_at_price
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.is_on_sale:
            return int(((self.compare_at_price - self.price) / self.compare_at_price) * 100)
        return 0

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    url = models.URLField(max_length=1000)
    alt_text = models.CharField(max_length=500, blank=True)
    position = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['position', 'id']
    
    def __str__(self):
        return f"Image for {self.product.title}"