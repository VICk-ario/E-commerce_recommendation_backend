from django.contrib import admin
from django.utils.html import format_html
from apps.products.models import Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" height="50" />', obj.url)
        return "-"
    image_preview.short_description = 'Preview'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'store', 'price', 'category', 'is_active', 'created_at', 'in_stock']
    list_filter = ['store', 'category', 'brand', 'is_active', 'in_stock', 'is_published', 'created_at']
    search_fields = ['title', 'store_product_id', 'description', 'category', 'brand']
    readonly_fields = ['created_at', 'updated_at', 'last_seen_at', 'discount_display']
    list_editable = ['is_active', 'in_stock']
    list_select_related = ['store']
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Store Information', {
            'fields': ('store', 'store_product_id', 'variant_id')
        }),
        ('Product Details', {
            'fields': ('title', 'description', 'handle', 'category', 'brand')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price', 'discount_display')
        }),
        ('Media & Links', {
            'fields': ('image_url', 'product_url'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('tags', 'options', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'in_stock', 'is_published')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_seen_at'),
            'classes': ('collapse',)
        }),
    )
    
    def discount_display(self, obj):
        if obj.is_on_sale:
            return f"{obj.discount_percentage}% off"
        return "No discount"
    discount_display.short_description = 'Discount'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('store')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'position', 'image_preview']
    list_filter = ['product__store']
    search_fields = ['product__title', 'alt_text']
    list_editable = ['position']
    
    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" height="50" />', obj.url)
        return "-"
    image_preview.short_description = 'Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product__store')
