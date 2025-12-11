"""
🌐 URL Configuration for the Ecom project.

This file routes top-level URLs to the application's URL modules.

Key Structure:
- /admin/ → Django admin
- /       → store app (home, products, cart, orders, auth, etc.)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 🛠 Django admin dashboard
    path('admin/', admin.site.urls),

    # 🛒 Main store application routes
    # Includes: home, product list, cart, orders, login, register, etc.
    path('', include('store.urls')),
]

# 📸 Serve media files (product images) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
