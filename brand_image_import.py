import os
from django.conf import settings
from store.models import Product

# 👉 If your folder is actually named "produts" (typo), change this to "produts"
IMAGES_SUBFOLDER = "products"

folder = os.path.join(settings.MEDIA_ROOT, IMAGES_SUBFOLDER)
print("Looking for images in:", folder)

extensions = [".png", ".jpg", ".jpeg", ".webp"]

linked = 0
missing = 0

for product in Product.objects.all():
    found = False

    for ext in extensions:
        filename = f"{product.sku}{ext}"  # e.g. KW083402.png
        full_path = os.path.join(folder, filename)

        if os.path.exists(full_path):
            # This is what gets stored in the DB relative to MEDIA_ROOT
            product.image.name = f"{IMAGES_SUBFOLDER}/{filename}"
            product.save()
            print(f"✔ Linked {filename} → {product.sku}")
            linked += 1
            found = True
            break

    if not found:
        print(f"✘ No image found for SKU {product.sku}")
        missing += 1

print(f"\nDone. Linked: {linked}, Missing: {missing}")
