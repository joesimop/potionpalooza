from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth
from enum import Enum


import sqlalchemy
from sqlalchemy.sql.expression import case
from src import database as db
from src.schemas import carts, cart_items, gold_ledger, potion_inventory, potion_quantity_ledger, invoices


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


sortDict = {
    search_sort_options.customer_name: invoices.c.customer,
    search_sort_options.item_sku: invoices.c.item_sku,
    search_sort_options.line_item_total: invoices.c.line_item_total,
    search_sort_options.timestamp: invoices.c.timestamp
}

"""
ENDPOINTS -------------------------------------
"""

lastPage = 0

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
    
    itemsPerPage = 5
    

    with db.engine.begin() as conn:
        
        result = conn.execute(
            sqlalchemy
            .select(invoices.c.line_item_id,
                    invoices.c.customer, 
                    invoices.c.item_sku, 
                    invoices.c.line_item_total, 
                    invoices.c.timestamp)
            .filter(invoices.c.customer.ilike(f"%{customer_name}%"),
                    invoices.c.item_sku.ilike(f"%{potion_sku}%"),
                    invoices.c.line_item_id > search_page)
            .offset(search_page * itemsPerPage)
            .order_by(sortDict[sort_col].asc() if sort_order == search_sort_order.asc 
                      else sortDict[sort_col].desc())
            .limit(itemsPerPage)
        )

        # Get all results
        searchResults = result.fetchall()

    return {
        "previous": "" if search_page == 0 else search_page - 1,
        "next": search_page if len(searchResults) < itemsPerPage else search_page + 1,
        "results": [
            {
                "line_item_id": line_item[0],
                "customer_name": line_item[1],
                "item_sku": line_item[2],
                "line_item_total": line_item[3],
                "timestamp": line_item[4]
            }
            for line_item in searchResults
        ]
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

        # Get the customer name, items, and price of items in the cart
        result = conn.execute(
            sqlalchemy
            .select(
                carts.c.customer, 
                cart_items.c.name, 
                cart_items.c.quantity, 
                cart_items.c.potion_id, 
                potion_inventory.c.price_per,
                cart_items.c.id
            )
            .select_from(carts)
            .join(cart_items, cart_items.c.cart_id == carts.c.id)
            .select_from(cart_items)
            .join(potion_inventory, cart_items.c.potion_id == potion_inventory.c.id)
            .where(carts.c.id == cart_id)
        )

        checkoutInfo = result.fetchall()

        if checkoutInfo is None:
            raise HTTPException(status_code=404, detail="Cart is empty")


        # Add up gold total
        goldTotal = 0
        for item in checkoutInfo:
            quantity = item[2]
            goldTotal += quantity * item[4]


        # Potion ledger subtraction from cart checkout
        conn.execute(
            sqlalchemy
            .insert(potion_quantity_ledger)
            .values(
                [
                    {
                        "potion_id": item[3],
                        "delta": -item[2]
                    }
                    for item in checkoutInfo
                ]
            )
        )

        # Add invoice for each item to database
        # Not really how invoices work, but okkaaayyy
        conn.execute(
            sqlalchemy
            .insert(invoices)
            .values(
                [
                    {
                        "line_item_id": item[5],
                        "customer": item[0],
                        "item_sku": item[1],
                        "line_item_total": item[2] * item[4]

                    }
                    for item in checkoutInfo
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
