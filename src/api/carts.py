from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth


import sqlalchemy
from sqlalchemy.sql.expression import case
from src import database as db
from src.schemas import carts, cart_items, gold_ledger, potion_quantity_ledger,potion_inventory


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
            sqlalchemy
            .insert(carts)
            .values(customer=new_cart.customer)
        )

        primaryKey = result.inserted_primary_key[0]

    # Return the cart ID
    return {
            "cart_id": primaryKey,
    }
    

@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    with db.engine.begin() as conn:

        result = conn.execute(
            sqlalchemy
            .select(carts.c.customer)
            .where(carts.c.id == cart_id)
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
        
        #Ensure Cart Exists
        get_cart(cart_id)
       
        # Try to update the quantity of the item in the cart
        result = conn.execute(
            sqlalchemy
            .update(cart_items)
            .where(cart_items.c.cart_id == cart_id,
                   cart_items.c.name == item_sku)
            .values(quantity=cart_item.quantity)
            .returning(cart_items.c.id)
        ) 

        cartItemUpdated = result.first()
        
        #If we didn't update anything, insert a new item into the cart
        if cartItemUpdated is None:

            # result = conn.execute(
            #     sqlalchemy
            #     .insert(cart_items)
            #     .from_select([":cart_id", ":item_sku", ":quantity", "id"], 
            #                   potion_inventory.select().where(potion_inventory.c.sku == item_sku))
            #     .values(cart_id=cart_id, item_sku=item_sku, quantity=cart_item.quantity)
                              
            # )

            # Don't know how to do this with sqlalchemy, so I'm using raw SQL
            result = conn.execute(
                sqlalchemy.text(
                    "INSERT INTO cart_items (cart_id, name, quantity, potion_id) \
                        SELECT :cart_id, :item_sku, :quantity, id \
                        FROM potion_inventory WHERE sku = :item_sku "
                ),
                [{"cart_id": cart_id, "item_sku": item_sku, "quantity": cart_item.quantity}]
            )

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    # Get the cart with the matching ID, error if it doesn't exist
    with db.engine.begin() as conn:

        # Ensure Cart Exists
        get_cart(cart_id)

        # Get the items in the cart, not effecient, but good error handling
        result = conn.execute(
            sqlalchemy
            .select(cart_items.c.name, cart_items.c.quantity, cart_items.c.potion_id)
            .where(cart_items.c.cart_id == cart_id)
        )

        checkoutItems = result.fetchall()

        if checkoutItems is None:
            raise HTTPException(status_code=404, detail="Cart is empty")
    
            
        # Add up gold total
        goldTotal = 0
        for item in checkoutItems:
            quantity = item[1]
            goldTotal += quantity * 50


        # Potion ledger subtraction from cart checkout
        conn.execute(
            sqlalchemy
            .insert(potion_quantity_ledger)
            .values(
                [
                    {
                        "potion_id": item[2],
                        "delta": -item[1]
                    }
                    for item in checkoutItems
                ]
            )
        )

        # Add gold ledger to database
        conn.execute(
            sqlalchemy
            .insert(gold_ledger)
            .values(delta = goldTotal)
        )

        # Cascade deletes cart_items
        conn.execute(
            sqlalchemy
            .delete(carts)
            .where(carts.c.id == cart_id)
        )

        return "OK"
