from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth


import sqlalchemy
from src import database as db

customerCarts = {}
cartCounter = 0

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


"""
SCHEMAS -------------------------------------
"""
class NewCart(BaseModel):
    customer: str

class PotionSale(BaseModel):
    sku: str
    quantity: int
    price_per: int
    price_total: int

class Cart(BaseModel):
    cart_id: int
    customer: str
    items: list[PotionSale]

"""
ENDPOINTS -------------------------------------
"""
@router.post("/")
def create_cart(new_cart: NewCart):
    """ """

    # Update globals to keep track of carts
    global cartCounter, customerCarts
    cartId = cartCounter
    cartCounter += 1

    # Create a new cart and add to dictionary
    customerCarts[cartId] = Cart(
            cart_id = cartId,
            customer = new_cart.customer,
            items = [],
    )

    # Return the cart ID
    return {
            "cart_id": cartId,
    }
    

@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    # Get the cart with the matching ID
    global customerCarts
    cart = customerCarts.get(cart_id)
    
    # Return nothing if there is no cart with a matching ID
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    return cart


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
     # Get the cart with the matching ID
    global customerCarts
    cart = customerCarts.get(cart_id)
    
    # If there is no cart with a matching ID
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # If the sku already exists in the cart, update the quantity
    for item in cart.items:
        if item.sku == item_sku:
            item.quantity = cart_item.quantity
            item.price_total = item.price_per * cart_item.quantity
            return "200 OK"

    # Otherwise, add a new sale to the items list
    else:
        cart.items.append(
                PotionSale(
                    sku = item_sku,
                    quantity = cart_item.quantity,
                    price_per = 50,
                    price_total = 50 * cart_item.quantity
                )
        )

        return "200 OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    # Get the cart with the matching ID
    global customerCarts
    cart = customerCarts.get(cart_id)

    # If there is no cart with a matching ID
    if cart is None:
        return "404 Cart not found"

    # Setup loop total variables
    cartTotal = 0
    potionQuantityTotal = 0

    # Collect all sales inside the cart
    for item in cart.items:
        cartTotal += item.price_total
        potionQuantityTotal += item.quantity

    # If the cart is empty, send bad request
    if potionQuantityTotal == 0:
        return "400 Cart is empty"
    
    # Return total sales
    return {"total_potions_bought": potionQuantityTotal, 
            "total_gold_paid": cartTotal,}

    """
    Loop might look something like this, if we don't include so much data in PotionSale: 

    cartTotal = 0
    with db.engine.begin() as conn:
    
        # Get the price of the item from the catalog
            result = conn.execute(
                sqlalchemy.text(
                    f"SELECT quantity, price FROM catalog WHERE sku = {**SOME LIST COMPREHENSION??**}"
                )
            )

        for row in result:      <----Don't know if this is feasivble
        
            quantity = row[0]
            price_per = row[1]

            # Add the price of the item to the cart total
            cartTotal += quantity * price_per
    """
