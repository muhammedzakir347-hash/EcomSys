from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Product,
    Order,
    OrderItem,
    Cart,
    CartItem,
    Category,
    Brand,
    Profile,
)

# 🏷️ Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')


# ⭐ Brand Admin
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')


# 🧾 Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'sku', 'price', 'stock', 'category', 'brand')
    search_fields = ('name', 'sku', 'upc')
    list_filter = ('category', 'brand')


# 🔗 OrderItem inline inside Order
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


# 📦 Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order_date', 'get_total_items', 'get_total_amount')
    list_filter = ('order_date', 'user')
    search_fields = ('user__username',)
    inlines = [OrderItemInline]

    def get_total_items(self, obj):
        return obj.total_items
    get_total_items.short_description = 'Total Items'

    def get_total_amount(self, obj):
        return obj.total_amount
    get_total_amount.short_description = 'Total Amount'


# 🧾 OrderItem Admin
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity')
    list_filter = ('order', 'product')


# 🛒 Cart Admin
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at')


# 🛒 CartItem Admin
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity')
    list_filter = ('cart', 'product')


# 👤 Profile Admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone')
    search_fields = ('user__username', 'phone')
