from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
"""
🧾 E-commerce Models

This file defines the main data structures for the e-commerce application:
- Product  ➝ Store items (SKU, UPC, price, stock, image)
- Order    ➝ A purchase made by a user
- OrderItem ➝ A single product inside an order
- Cart     ➝ A shopping cart belonging to a user
- CartItem ➝ A single product inside a cart
"""


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ⭐ Brand
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    image = models.ImageField(upload_to='brands/', blank=True, null=True)  # new field

    def __str__(self):
        return self.name



# 🛍️ Product Model
class Product(models.Model):
    """
    Represents a product available in the store.
    Includes SKU, UPC, name, description, price, stock, and optional image.
    """
    sku = models.CharField(max_length=20, unique=True)   # Stock Keeping Unit
    upc = models.CharField(max_length=20, unique=True)   # Universal Product Code / barcode
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=3)  # e.g. 1.250 KD
    stock = models.IntegerField()
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')
    brand = models.ForeignKey(Brand,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')

    def __str__(self):
        # Example: "SKU123: Bottle Water 1.5L"
        return f"{self.sku}: {self.name}"


# 📦 Order Model
class Order(models.Model):

    # 🔹 Possible status values for an order
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    # 🔹 Status field using the choices above
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )

    # 🔹 Each order belongs to one user (a user can have many orders)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    # 🔹 Date/time when the order was created
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Example: "Order#5 by nashi"
        return f"Order#{self.id} by {self.user.username}"

    @property
    def total_items(self) -> int:
        """
        🔢 Returns the total quantity of items in this order.
        Example: 3x A + 2x B ➝ total_items = 5
        """
        return sum(item.quantity for item in self.items.all())

    @property
    def total_amount(self):
        """
        💰 Returns the total price for this order.
        Sum of all line totals of the order items.
        """
        return sum(item.quantity * item.product.price for item in self.items.all())



# 🧾 OrderItem Model
class OrderItem(models.Model):
    """
    A single product line inside an Order.
    Connects an Order with a Product and stores the quantity.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    quantity = models.IntegerField()

    @property
    def line_total(self):
        """
        Returns the total price for this line:
        product price × quantity.
        """
        return self.quantity * self.product.price

    def __str__(self):
        # Example: "2 x Bottle Water 1.5L (Order #5)"
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"


# 🛒 Cart Model
class Cart(models.Model):
    """
    Represents a shopping cart belonging to a single user.

    🧠 Design choice:
    - One-to-one relation: each user has at most one active cart.
    - Items are stored in the related CartItem model.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_items(self) -> int:
        """
        Returns total quantity of items in the cart.
        Example: 1x A + 3x B ➝ total_items = 4
        """
        return sum(item.quantity for item in self.items.all())

    @property
    def total_amount(self):
        """
        Returns the total price of all items in the cart.
        """
        return sum(item.quantity * item.product.price for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user.username}"


# 🧺 CartItem Model
class CartItem(models.Model):
    """
    A single product line inside a Cart.
    Connects a Cart with a Product and stores the quantity.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        # ✅ Ensures one row per (cart, product) combination
        #    If user adds the same product again, we update quantity instead.
        unique_together = ('cart', 'product')

    @property
    def line_total(self):
        """
        Returns the total price for this cart line:
        product price × quantity.
        """
        return self.quantity * self.product.price

    def __str__(self):
        # Example: "3 x Bottle Water 1.5L in Cart for zakir"
        return f"{self.quantity} x {self.product.name} in {self.cart}"

class Profile(models.Model):
    """
    👤 Extended user profile for storing additional information.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    # Optional future enhancement:
    # avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

