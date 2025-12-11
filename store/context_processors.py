# store/context_processors.py
from .models import Brand,Category
def cart_item_count(request):
    """
    Returns total cart item count to be used in base.html header.
    Adjust logic based on how you store the cart.
    """
    count = 0

    # Example 1: cart stored in session as dict of {product_id: quantity}
    cart = request.session.get('cart', {})
    if isinstance(cart, dict):
        count = sum(cart.values())

    # Example 2 (if you have a Cart model):
    # from .models import CartItem
    # if request.user.is_authenticated:
    #     count = CartItem.objects.filter(user=request.user).count()

    return {'cart_item_count': count}


def brand_list(request):
    return {
        'all_brands': Brand.objects.all()
    }




def category_list(request):
    return {
        "all_categories": Category.objects.all()
    }
