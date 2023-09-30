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

    with db.engine.begin() as conn:

        # Gets the number of red potions and gold in inventory
        result = conn.execute(
            sqlalchemy.text(
                "SELECT num_red_potions, gold FROM global_inventory"
            )
        )

        #Extract data from the first row
        firstRow = result.first()
        inventoryRedPotionCount = firstRow[0]
        gold = firstRow[1]

        # Qualifications to buy a barrel:
        sufficientGoldToBuyBarrel = (gold > wholesale_catalog[0].price)
        needMoreRedPotions = (inventoryRedPotionCount < 10)

        if (needMoreRedPotions and sufficientGoldToBuyBarrel):

            #Buy a barrel of red potion
            return [
                        {
                            "sku": "SMALL_RED_BARREL",
                            "quantity": 1,
                        }
                    ]
        else:

            #Don't buy anything
            return [{}]
    
# Passes what was actually delivered based off what I ordered.
# Adds newly gained ml of potion to my inventory.
@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """

    with db.engine.begin() as conn:

        for barrel in barrels_delivered:

            # Gets the amount of red fluid and gold in inventory
            result = conn.execute(
                sqlalchemy.text(
                    "SELECT num_red_ml, gold FROM global_inventory"
                )
            )

            #Extract data from the first row
            firstRow = result.first()
            inventoryRedFluidAmount = firstRow[0]
            inventoryGoldAmount = firstRow[1]

            # Update the global inventory with the new amount of red fluid and gold.
            inventoryRedFluidAmount += barrel.quantity * barrel.ml_per_barrel
            inventoryGoldAmount -= barrel.quantity * barrel.price

            # Push the new inventory amounts to the database
            conn.execute(
                sqlalchemy.text(
                    f"UPDATE global_inventory SET num_red_ml = {inventoryRedFluidAmount}, gold = {inventoryGoldAmount}"
                )
            )


    return "OK\n"
