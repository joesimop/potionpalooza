from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth


import sqlalchemy
from sqlalchemy import insert
from src import database as db

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

class Cart(BaseModel):
    id: int
    customer: str

"""
ENDPOINTS -------------------------------------
"""
@router.post("/")
def create_cart(new_cart: NewCart):
    """Creates a new cart and returns the cart ID."""

    with db.engine.begin() as conn:
        result = conn.execute(
            sqlalchemy.text(
                f"INSERT INTO carts (customer) VALUES ('{new_cart.customer}') RETURNING id"
            )
        )

        primaryKey = result.first()[0]

    # Return the cart ID
    return {
            "cart_id": primaryKey,
    }
    

@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    with db.engine.begin() as conn:
        result = conn.execute(
            sqlalchemy.text(
                f"SELECT customer FROM carts WHERE id = {cart_id}"
            )
        )
        cart = result.first()
    
    # Return nothing if there is no cart with a matching ID
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    return cart


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
     
    # Get the cart with the matching ID, error if it doesn't exist
    with db.engine.begin() as conn:

        # Get the cart with the matching ID
        result = conn.execute(
            sqlalchemy.text(
                f"SELECT * FROM carts WHERE id = {cart_id}"
            )
        )
        cart = result.first()
    
        # If there is no cart with a matching ID
        if cart is None:
            raise HTTPException(status_code=404, detail="Cart not found")
    

        #Get all the items in cart_items with the cart_id
        result = conn.execute(
            sqlalchemy.text(
                f"SELECT id FROM cart_items WHERE cart_id = {cart_id} and name = \'{item_sku}\'"
            )
        )
        cart_item_id = result.first()


        # If the item is already in the cart, update the quantity
        if cart_item_id is not None:
            conn.execute(
                sqlalchemy.text(
                    f"UPDATE cart_items SET quantity = {cart_item.quantity} WHERE id = {cart_item_id[0]}"
                )
            )
        
        # Otherwise, add a new item to the cart
        else:
            conn.execute(
                sqlalchemy.text(
                    f"INSERT INTO cart_items (cart_id, name, quantity) \
                        VALUES ({cart_id}, \'{item_sku}\', {cart_item.quantity})"
                )
            )

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    # Get the cart with the matching ID, error if it doesn't exist
    with db.engine.begin() as conn:

        # Get the cart with the matching ID
        result = conn.execute(
            sqlalchemy.text(
                f"SELECT * FROM carts WHERE id = {cart_id}"
            )
        )
        cart = result.first()
    
        # If there is no cart with a matching ID
        if cart is None:
            raise HTTPException(status_code=404, detail="Cart not found")
        

        # Get the items in the cart
        result = conn.execute(
            sqlalchemy.text(
                f"SELECT name, quantity FROM cart_items WHERE cart_id = {cart_id}"
            )
        )

        checkoutItems = result.fetchall()

        if checkoutItems is None:
            raise HTTPException(status_code=404, detail="Cart is empty")
    
        else:
            
            goldTotal = 0
            for item in checkoutItems:

                #Variables for readability
                name = item[0]
                quantity = item[1]
                goldTotal += quantity * 50

                # Update potion in potion_inventory
                conn.execute(
                    sqlalchemy.text(
                        f"UPDATE potion_inventory SET count = count - {quantity} WHERE name = \'{name}\'"
                    )
                )


            # Update gold in global_inventory
            conn.execute(
                sqlalchemy.text(
                    f"UPDATE global_inventory SET gold = gold + {goldTotal}"
                )
            )

            # Delete the cart and cart items
            conn.execute(
                sqlalchemy.text(
                    f"DELETE FROM cart_items WHERE cart_id = {cart_id}"
                )
            )

            conn.execute(
                sqlalchemy.text(
                    f"DELETE FROM carts WHERE id = {cart_id}"
                )
            )

            return "OK"
