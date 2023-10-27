from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth
from enum import Enum


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


class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

"""
ENDPOINTS -------------------------------------
"""


@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }



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
