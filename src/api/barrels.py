from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

# Provides a list of barrels to purchase, and I return what I want to buy.
# The /deliver endpoint is called after I return my purchase plan.
# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    returnList = []

    # I'm gonna leave the logic mostly in for loops for the potion types because I don't think we
    # will have that many types, if we end up getting more, we should refactor to more db calls 
    # to limit the amount of looping.
    with db.engine.begin() as conn:

        # Gets gold in inventory
        result = conn.execute(
            sqlalchemy.text(
                "SELECT gold FROM global_inventory"
            )
        )

        runningGoldTotal = result.first()[0] 

        # Gets all the potion stock from potion_inventory
        result = conn.execute(
            sqlalchemy.text(
                "SELECT recipe, potion_count, ml_amount FROM potion_inventory"
            )
        )

        potionInventory = result.fetchall()
        potionRecipies = [row[0] for row in potionInventory]
        

        for barrel in wholesale_catalog:

            # Setup poiton specific properties
            inventoryPotionQuantity = 0
            inventoryPotionMlAmount = 0

            # If we do not have the barrel in our inventory, add it.
            # TODO: This is not the most efficient way to do this, look for more unique specifiers later.
            if barrel.potion_type not in potionRecipies:
                    
                    # Insert the barrel into our inventory
                    conn.execute(
                        sqlalchemy.text(
                            f"INSERT INTO potion_inventory (sku, recipe, potion_count, ml_amount, price_per_potion, product_name) VALUES \
                            (\'{barrel.sku}\', ARRAY{barrel.potion_type}, 0, 0, 0, \'CREATE_PRODUCT_NAME\')"
                        )
                    )

            # Otherwise, get details from inventory
            else:
                for row in potionInventory:
                    if row[0] == barrel.potion_type:
                        inventoryPotionQuantity = row[1]
                        inventoryPotionMlAmount = row[2]
                        break
            """
            At this point, the potion specific properties should be set up, new or old,
            and we can start the logic for the purchase plan.
            """

            # We will buy at least one of each barrel if possible.
            if runningGoldTotal >= barrel.price:
                returnList.append(
                    {
                        "sku": barrel.sku,
                        "quantity": 1,
                    }
                )
                runningGoldTotal -= barrel.price
                continue


        """
        We have now bought as much of at least one of each barrel as we can.
        We can now buy more of the barrels we want most, which, right now, is just blue cause its my favorite color.
        """


        return returnList
    
# Passes what was actually delivered based off what I ordered.
# Adds newly gained ml of potion to my inventory.
@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ 
    Note: We will have enough gold to buy all the barrels because we ensured in /plan.
    """

    totalGoldSpent = 0
    caseStatements = ""
    potionTypeList = ""

    with db.engine.begin() as conn:

        for barrel in barrels_delivered:

            totalMlBought = barrel.quantity * barrel.ml_per_barrel
            totalGoldSpent += barrel.price * barrel.quantity
            caseStatements += f"when recipe = ARRAY{barrel.potion_type} then {totalMlBought}"
        

        # Push the new inventory amounts to the database
        # Note: We are iterating through the whole table in the query
        # Also, don't love the case statements, if time, look into another way
        conn.execute(
            sqlalchemy.text(
                f"UPDATE potion_inventory SET ml_amount = ml_amount + (case {caseStatements} ELSE 0 end) \
                    WHERE recipe IN (SELECT recipe FROM potion_inventory)"
            )
        )

        # Update gold amount
        result = conn.execute(
            sqlalchemy.text(
                f"UPDATE global_inventory SET gold = gold - {totalGoldSpent}"
            )
        )


    return "OK\n"
