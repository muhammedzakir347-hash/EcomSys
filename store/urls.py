# store/urls.py

from django.contrib import admin
from django.urls import path
from . import views  # 👀 import views from the same app


urlpatterns = [
    # 🛠 Django Admin
    path('admin/', admin.site.urls),

    # 🌍 Public pages
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),



    # 📦 Orders (assignment / demo style)
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/status/', views.order_update_status, name='order_update_status'),
    path('orders/<int:order_id>/delete/', views.order_delete, name='order_delete'),


    # 👤 Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 🔐 Protected user pages
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('my-orders/', views.my_orders, name='my_orders'),

    # 🛒 Cart URLs (DB-backed cart with FBVs)
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),

        # 🧺 Session-based cart
    path('session-cart/', views.session_cart_detail, name='session_cart_detail'),
    path('session-cart/add/<int:product_id>/', views.session_add_to_cart, name='session_add_to_cart'),
    path('session-cart/update/<int:product_id>/', views.session_update_cart, name='session_update_cart'),
    path('session-cart/remove/<int:product_id>/', views.session_remove_from_cart, name='session_remove_from_cart'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

        # 🧱 Product CRUD (staff)
    path('products/create/', views.product_create, name='product_create'),
    path("products/delete/", views.product_delete_list, name="product_delete_list"),
    path("products/delete/<int:product_id>/",views.delete_product, name="delete_product"),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),

     path('brand/<slug:slug>/', views.brand_products, name='brand_products'),
     path("category/<slug:slug>/", views.category_products, name="category_products"),
     path("products/bulk-upload/", views.bulk_upload, name="bulk_upload"),
     



]
