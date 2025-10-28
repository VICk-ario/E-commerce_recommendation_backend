from rest_framework import serializers
from apps.products.models import Product, ProductImage

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'url', 'alt_text', 'position']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'store', 'store_name', 'store_product_id', 'variant_id',
            'title', 'description', 'handle', 'category', 'brand',
            'price', 'compare_at_price', 'is_on_sale', 'discount_percentage',
            'image_url', 'product_url', 'tags', 'options', 'metadata',
            'is_active', 'in_stock', 'is_published',
            'created_at', 'updated_at', 'last_seen_at', 'images'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_seen_at', 
            'is_on_sale', 'discount_percentage', 'store_name'
        ]

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'store_product_id', 'variant_id', 'title', 'description',
            'handle', 'category', 'brand', 'price', 'compare_at_price',
            'image_url', 'product_url', 'tags', 'options', 'metadata',
            'is_active', 'in_stock', 'is_published'
        ]
    
    def create(self, validated_data):
        store = self.context['request'].auth
        validated_data['store'] = store
        return super().create(validated_data)

class ProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'title', 'description', 'category', 'brand', 'price',
            'compare_at_price', 'image_url', 'tags', 'options', 'metadata',
            'is_active', 'in_stock', 'is_published'
        ]

class ProductBulkCreateSerializer(serializers.Serializer):
    products = ProductCreateSerializer(many=True)
    
    def create(self, validated_data):
        store = self.context['request'].auth
        products_data = validated_data['products']
        
        products = []
        for product_data in products_data:
            product_data['store'] = store
            products.append(Product(**product_data))
        
        return Product.objects.bulk_create(products)