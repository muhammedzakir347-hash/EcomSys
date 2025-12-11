    # store/views.py

from cProfile import Profile
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse  # (optional: currently not used)
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
import csv, zipfile, os
from django.core.files.base import ContentFile
from .forms import ProductForm, ProfileForm, RegistrationForm
from .models import Product, Cart, CartItem, Order,Profile,Brand,Category


# 🏠 HOME & PRODUCT / ORDER LIST VIEWS
# -----------------------------------

def home(request):
    # main product list for the horizontal row
    products = Product.objects.all()

    # 🔹 Get recently viewed IDs from session
    rv_ids = request.session.get('recently_viewed', [])

    # Fetch those products from DB
    recently_viewed_qs = Product.objects.filter(id__in=rv_ids)

    # Preserve the order of ids from the session (most recent first)
    id_order = {pid: index for index, pid in enumerate(rv_ids)}
    recently_viewed = sorted(
        recently_viewed_qs,
        key=lambda p: id_order.get(p.id, 999)
    )

    # 🔹 FEATURED BRANDS (pick first few brands that actually exist)
    brand_sections = []
    for brand in Brand.objects.all()[3:6]:   # change 3 to however many sections you want
        brand_products = Product.objects.filter(brand=brand)[:15]
        if brand_products:
            brand_sections.append({
                "brand": brand,
                "products": brand_products,
            })

    # 🔹 FEATURED CATEGORIES (same idea)
    category_sections = []
    for category in Category.objects.all()[2:6]:
        category_products = Product.objects.filter(category=category)[:15]
        if category_products:
            category_sections.append({
                "category": category,
                "products": category_products,
            })

    context = {
        'products': products,
        'recently_viewed': recently_viewed,
        'brand_sections': brand_sections,
        'category_sections': category_sections,
    }
    return render(request, 'store/home.html', context)





def product_list(request):
    """
    🛒 Product list page: grid of all products with brand & category filters.
    Filters are linked: each list only shows options that have products.
    """
    products = Product.objects.all()

    brand_slug = request.GET.get("brand")
    category_slug = request.GET.get("category")

    # Apply filters to products first
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)

    if category_slug:
        products = products.filter(category__slug=category_slug)

    # 🔗 Now derive brands & categories FROM the filtered products
    brands = Brand.objects.filter(
        id__in=products.values("brand_id").distinct()
    )

    categories = Category.objects.filter(
        id__in=products.values("category_id").distinct()
    )

    return render(request, "store/product_list.html", {
        "products": products,
        "brands": brands,
        "categories": categories,
        "current_brand_slug": brand_slug,
        "current_category_slug": category_slug,
    })



def order_list(request):
    """
    📦 Admin-style order list: shows all orders with items (for assignment demo).
    """
    orders = Order.objects.all().prefetch_related('items__product')
    return render(request, 'store/order_list.html', {'orders': orders})


def order_detail(request, order_id):
    """
    📄 Order detail page: shows one order and its items.
    """
    order = get_object_or_404(Order, id=order_id)
    items = order.items.select_related('product')
    return render(request, 'store/order_detail.html', {
        'order': order,
        'items': items,
    })


# 👤 AUTHENTICATION VIEWS
# ----------------------

def register_view(request):
    """
    📝 User registration view:
    - Shows a registration form
    - Creates a new user if the form is valid
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. You can now log in.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'store/register.html', {'form': form})


def login_view(request):
    """
    🔐 Login view:
    - Authenticates user
    - Redirects to dashboard or 'next' URL if provided
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "You are now logged in.")

            # If user was redirected from a protected page, go back there
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'store/login.html')


@login_required
def logout_view(request):
    """
    🚪 Logout view:
    - Logs the user out and redirects to login page.
    """
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')


# 📊 DASHBOARD & USER ORDERS
# --------------------------

@login_required
def dashboard_view(request):
    """
    📊 Simple dashboard:
    - Shows how many orders the current user has
    - Lists the 5 most recent orders
    """
    user_orders = Order.objects.filter(user=request.user)
    context = {
        'order_count': user_orders.count(),
        'recent_orders': user_orders.order_by('-order_date')[:15],
    }
    return render(request, 'store/dashboard.html', context)


@login_required
def my_orders(request):
    """
    🧾 Protected order history:
    - Only shows orders that belong to the logged-in user.
    """
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items__product')
    )
    return render(request, 'store/my_orders.html', {'orders': orders})


# 🛒 CART HELPERS & VIEWS (DB-BACKED CART)
# ----------------------------------------

def _get_user_cart(user):
    """
    🧰 Internal helper:
    Get or create the Cart object for a given user.
    Ensures each user has at most one cart.
    """
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def add_to_cart(request, product_id):
    """
    ➕ Add to Cart (Function-Based View):
    - Adds a product to the user's cart, or increases quantity if it exists.
    - Only accepts POST requests.
    - Only accessible by authenticated users.
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        qty_str = request.POST.get('quantity', '1')

        # ✅ Validate quantity input
        try:
            quantity = int(qty_str)
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect('product_list')

        if quantity <= 0:
            messages.error(request, "Quantity must be at least 1.")
            return redirect('product_list')

        # Get or create the user's active cart
        cart = _get_user_cart(request.user)

        # If item already exists, increase quantity; else create new CartItem
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f"Added {quantity} × {product.name} to your cart.")
        return redirect('cart_detail')

    # If someone hits this view with GET, just send them back.
    return redirect('product_list')


@login_required
def cart_detail(request):
    """
    🧺 Cart detail page:
    - Shows all items in the current user's cart
    - Displays the total cart amount
    """
    # Try to get the cart via the reverse one-to-one relation
    cart = getattr(request.user, 'cart', None)

    if not cart:
        # No cart yet → show empty cart
        return render(request, 'store/cart_detail.html', {
            'cart': None,
            'items': [],
            'total_amount': 0,
        })

    items = cart.items.select_related('product')
    total = cart.total_amount

    return render(request, 'store/cart_detail.html', {
        'cart': cart,
        'items': items,
        'total_amount': total,
    })


@login_required
def update_cart_item(request, item_id):
    """
    ✏️ Update cart item quantity:
    - If new quantity <= 0 → removes the item.
    - Only allows changes on the logged-in user's own cart.
    """
    cart = _get_user_cart(request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if request.method == 'POST':
        qty_str = request.POST.get('quantity', '')

        # ✅ Validate quantity input
        try:
            quantity = int(qty_str)
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect('cart_detail')

        if quantity <= 0:
            # Quantity 0 or negative → delete the item
            cart_item.delete()
            messages.info(request, "Item removed from cart.")
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated.")

    return redirect('cart_detail')


@login_required
def remove_cart_item(request, item_id):
    """
    🗑 Remove a single item from the cart.
    - Ensures the item belongs to the current user's cart.
    """
    cart = _get_user_cart(request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    messages.info(request, "Item removed from cart.")
    return redirect('cart_detail')

# ============================================
# 🧺 SESSION-BASED CART 
# ============================================

def _get_session_cart(request):
    """
    🧺 Helper to safely get the cart from the session.
    Stored as: { "product_id": quantity, ... }
    """
    cart = request.session.get('session_cart', {})
    return cart


def _save_session_cart(request, cart):
    """
    💾 Helper to save cart back into session.
    Mark session as modified so Django persists it.
    """
    request.session['session_cart'] = cart
    request.session.modified = True


@login_required
def session_add_to_cart(request, product_id):
    """
    ➕ Add product to SESSION cart (Assignment 12 version).
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        qty_str = request.POST.get('quantity', '1')
        try:
            quantity = int(qty_str)
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect('product_list')

        if quantity <= 0:
            messages.error(request, "Quantity must be at least 1.")
            return redirect('product_list')

        cart = _get_session_cart(request)
        pid = str(product.id)

        # If exists, increase; else set
        if pid in cart:
            cart[pid] += quantity
        else:
            cart[pid] = quantity

        _save_session_cart(request, cart)
        messages.success(request, f"Added {quantity} × {product.name} to your session cart 🧺")
        return redirect('session_cart_detail')

    return redirect('product_list')


@login_required
def session_cart_detail(request):
    """
    🧺 Show the session-based cart contents.
    We resolve product IDs and compute totals here.
    """
    cart = _get_session_cart(request)

    # Build a list of item objects for template
    items = []
    total_amount = 0

    for pid, quantity in cart.items():
        product = get_object_or_404(Product, id=int(pid))
        line_total = product.price * quantity
        total_amount += line_total
        items.append({
            'product': product,
            'quantity': quantity,
            'line_total': line_total,
        })

    context = {
        'items': items,
        'total_amount': total_amount,
    }
    return render(request, 'store/session_cart_detail.html', context)


@login_required
def session_update_cart(request, product_id):
    """
    ✏️ Update quantity for a given product in the SESSION cart.
    If quantity <= 0, remove it.
    """
    cart = _get_session_cart(request)
    pid = str(product_id)

    if request.method == 'POST':
        qty_str = request.POST.get('quantity', '')
        try:
            quantity = int(qty_str)
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect('session_cart_detail')

        if quantity <= 0:
            cart.pop(pid, None)
            messages.info(request, "Item removed from session cart.")
        else:
            if pid in cart:
                cart[pid] = quantity
                messages.success(request, "Session cart updated.")
            else:
                messages.error(request, "Item not found in session cart.")

        _save_session_cart(request, cart)

    return redirect('session_cart_detail')


@login_required
def session_remove_from_cart(request, product_id):
    """
    🗑 Remove product from the SESSION cart.
    """
    cart = _get_session_cart(request)
    pid = str(product_id)

    if pid in cart:
        cart.pop(pid, None)
        _save_session_cart(request, cart)
        messages.info(request, "Item removed from session cart.")

    return redirect('session_cart_detail')




def product_detail(request, product_id):
    # Current product
    product = get_object_or_404(Product, id=product_id)

    # -----------------------------
    # Recently Viewed Logic
    # -----------------------------
    rv_ids = request.session.get("recently_viewed", [])

    # Remove if already exists
    if product.id in rv_ids:
        rv_ids.remove(product.id)

    # Add current product at the front
    rv_ids.insert(0, product.id)

    # Limit to 5 items
    rv_ids = rv_ids[:15]
    request.session["recently_viewed"] = rv_ids

    # Fetch products except current one
    qs = Product.objects.filter(id__in=rv_ids).exclude(id=product.id)

    # Maintain original order
    id_order = {pid: idx for idx, pid in enumerate(rv_ids)}
    recently_viewed = sorted(qs, key=lambda p: id_order.get(p.id, 999))

    return render(request, "store/product_detail.html", {
        "product": product,
        "recently_viewed": recently_viewed,
    })




def staff_required(user):
    return user.is_staff

@user_passes_test(staff_required)
def product_create(request):
    """
    ➕ Create a new product (staff only).
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product created successfully.")
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'store/product_form.html', {'form': form, 'mode': 'create'})


@user_passes_test(staff_required)
def product_update(request, product_id):
    """
    ✏️ Edit an existing product (staff only).
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'store/product_form.html', {'form': form, 'mode': 'update'})


@user_passes_test(staff_required)
def product_delete(request, product_id):
    """
    🗑 Delete a product (staff only).
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted.")
        return redirect('product_list')

    return render(request, 'store/product_confirm_delete.html', {'product': product})

@user_passes_test(staff_required)
def order_update_status(request, order_id):
    """
    ✏️ Staff-only: update order status.
    """
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, "Order status updated.")
        else:
            messages.error(request, "Invalid status.")
        return redirect('order_detail', order_id=order.id)

    return render(request, 'store/order_status_form.html', {'order': order})
    

@user_passes_test(staff_required)
def order_delete(request, order_id):
    """
    🗑 Staff-only: delete an order.
    """
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        order.delete()
        messages.success(request, "Order deleted.")
        return redirect('order_list')

    return render(request, 'store/order_confirm_delete.html', {'order': order})

@login_required
def profile_view(request):
    """
    👀 View current user's profile.
    """
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'store/profile.html', {'profile': profile})


@login_required
def profile_edit(request):
    """
    ✏️ Update current user's profile (phone, address).
    """
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'store/profile_edit.html', {'form': form})


@staff_member_required
def product_delete_list(request):
    products = Product.objects.all()
    return render(request, "store/product_delete_list.html", {"products": products})

@staff_member_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect('product_delete_list')

@staff_member_required
def product_edit(request, pk):
    """
    Edit an existing product (staff only).
    """
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'store/product_edit.html', {'form': form, 'product': product})

def brand_products(request, slug):
    """
    🏷 Display all products for a specific brand.
    """
    # Get the brand or return 404 if it doesn't exist
    brand = get_object_or_404(Brand, slug=slug)

    # Get all products for this brand
    products = Product.objects.filter(brand=brand)

    return render(request, 'store/brand_products.html', {
        'brand': brand,
        'products': products,
    })

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category)

    context = {
        "category": category,
        "products": products,
    }
    return render(request, "store/category_products.html", context)

@staff_member_required
def bulk_upload(request):
    if request.method == "POST":
        upload_type = request.POST.get("upload_type")
        csv_file = request.FILES.get("csv_file")
        zip_file = request.FILES.get("zip_file")

        if not csv_file:
            messages.error(request, "CSV file is required.")
            return redirect("bulk_upload")

        # Read CSV
        try:
            csv_data = csv_file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(csv_data)
        except Exception as e:
            messages.error(request, f"CSV Error: {e}")
            return redirect("bulk_upload")

        # Read ZIP if available
        images = {}
        if zip_file:
            try:
                with zipfile.ZipFile(zip_file) as z:
                    for filename in z.namelist():
                        images[filename] = z.read(filename)
            except Exception as e:
                messages.error(request, f"ZIP Error: {e}")
                return redirect("bulk_upload")

        # ============================
        # BRAND CREATE
        # ============================
        if upload_type == "brand_create":
            for row in reader:
                Brand.objects.get_or_create(
                    name=row["name"],
                    slug=row["slug"]
                )
            messages.success(request, "Brands uploaded successfully!")
            return redirect("bulk_upload")

        # ============================
        # CATEGORY CREATE
        # ============================
        if upload_type == "category_create":
            for row in reader:
                Category.objects.get_or_create(
                    name=row["name"],
                    slug=row["slug"]
                )
            messages.success(request, "Categories uploaded successfully!")
            return redirect("bulk_upload")

        # ============================
        # PRODUCT CREATE
        # ============================
        if upload_type == "product_create":
            for row in reader:
                product = Product(
                    sku=row["sku"],
                    upc=row["upc"],
                    name=row["name"],
                    description=row["description"],
                    price=row["price"],
                    stock=row["stock"],
                    brand_id=row.get("brand_id"),
                    category_id=row.get("category_id"),
                )
                product.save()

                img_name = row.get("image")
                if img_name and img_name in images:
                    product.image.save(img_name, ContentFile(images[img_name]), save=True)

            messages.success(request, "Products + images uploaded successfully!")
            return redirect("bulk_upload")

        # ============================
        # PRODUCT UPDATE
        # ============================
        if upload_type == "product_update":
            for row in reader:
                try:
                    product = Product.objects.get(sku=row["sku"])

                    if "price" in row and row["price"]:
                        product.price = row["price"]

                    if "stock" in row and row["stock"]:
                        product.stock = row["stock"]

                    product.save()

                except Product.DoesNotExist:
                    continue

            messages.success(request, "Products updated successfully!")
            return redirect("bulk_upload")

    return render(request, "store/bulk_upload.html")




