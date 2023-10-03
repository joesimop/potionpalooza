from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)

    with db.engine.begin() as conn:
         for potion in potions_delivered:

            # If red potion...
            if potion.potion_type == [100, 0, 0, 0]:

                # Update the number of red potions and fluid in inventory
                conn.execute(
                     sqlalchemy.text(
                          f"UPDATE global_inventory SET num_red_potions = num_red_potions + {potion.quantity}, \
                                                        num_red_ml = num_red_ml - {potion.quantity * 100}"
                    )
                )
            

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    with db.engine.begin() as conn:

            # Gets the number of red fluid in inventory
            result = conn.execute(
                 sqlalchemy.text(
                      "SELECT num_red_ml FROM global_inventory"
                )
            )

            # Extract data and setup mixing conversion variables.
            firstRow = result.first()
            inventoryRedFluidAmount = firstRow[0]
            bottledRedPotionCount = 0

            # Bottle all red fluid into red potions by 100ml increments.
            bottledRedPotionCount  = inventoryRedFluidAmount // 100
    
    return [
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": bottledRedPotionCount,
            }
        ]
