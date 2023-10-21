from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db
from sqlalchemy.sql.functions import coalesce
from src.schemas import barrel_fluid_ledger, gold_ledger, barrel_inventory
from src.helpers import GetBarrelType, GetRecipeNameFromIndex
from src.databasesync import barrelInventoryIds

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

    # I'm gonna leave the logic mostly in for loops for the potion types because I don't think we
    # will have that many types, if we end up getting more, we should refactor to more db calls 
    # to limit the amount of looping.
    with db.engine.begin() as conn:

        # Get amount of gold in inventory
        # Note coalesce is used to return 0 if there is no ledgers
        result = conn.execute(
            sqlalchemy
            .select(coalesce(sqlalchemy.func.sum(gold_ledger.c.delta), 0).label("total_gold"))
        )
        totalGold = result.first()[0]


        # Get amount of potions in inventory
        # Relying on the id's being in order of [r, g, b, d]
        result = conn.execute(
            sqlalchemy
            .select(coalesce(sqlalchemy.func.sum(barrel_fluid_ledger.c.delta), 0).label("total_fluid"),
                    barrel_inventory.c.recipe)
            .select_from(barrel_inventory)
            .join(barrel_fluid_ledger, barrel_fluid_ledger.c.barrel_id == barrel_inventory.c.id, 
                  isouter=True) 
            .group_by(barrel_inventory.c.id)
            .order_by(barrel_inventory.c.id)
        )

        potionInventory = result.fetchall()

        return ChooseBarrelPurchases(wholesale_catalog, potionInventory, totalGold)
    
# Passes what was actually delivered based off what I ordered.
# Adds newly gained ml of potion to my inventory.
@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ 
    Note: We will have enough gold to buy all the barrels because we ensured in /plan.
    """

    totalGoldSpent  = 0
    totalFluidsBought = [0,0,0,0]

    with db.engine.begin() as conn:

        # Calculate how much fluid we bought and how much gold we spent
        for barrel in barrels_delivered:

            totalMlBought = barrel.quantity * barrel.ml_per_barrel
            totalGoldSpent += barrel.price * barrel.quantity

            # Calculate how much of each fluid we bought in this barrel
            for i in range(len(barrel.potion_type)):
                totalFluidsBought[i] += barrel.potion_type[i] * totalMlBought
    

        #Build ledger list
        ledgerList = []

        for i, fluidBought in enumerate(totalFluidsBought):
            if fluidBought > 0:
                ledgerList.append( 
                    { 
                      "barrel_id" : barrelInventoryIds[GetRecipeNameFromIndex(i)], 
                      "delta" : fluidBought
                    } 
                )

        # Add barrel ledgers to database
        conn.execute(
            sqlalchemy
            .insert(barrel_fluid_ledger)
            .values(ledgerList)
        )

        # Add gold ledger to database
        conn.execute(
            sqlalchemy
            .insert(gold_ledger)
            .values(delta = -totalGoldSpent)
        )

    return "OK\n"


# - - - - - - - - - - - - - - - - - - 

def ChooseBarrelPurchases(wholesale_catalog, potionInventory, totalGold):

    # Setup variables
    returnList = []
    runningGoldTotal = totalGold
    totalMlInInventory = sum([potion[0] for potion in potionInventory])

    #(Percentage of ml for type of total ml, Recipe)
    if totalMlInInventory > 0:
        percentageMlAmounts = [(potionData[0] / totalMlInInventory, potionData[1]) for potionData in potionInventory]
        percentageMlAmounts.sort(key=lambda x: x[0], reverse=False)
    else:
        percentageMlAmounts = [(0, [1,0,0,0]), (0, [0,1,0,0]), (0, [0,0,1,0]), (0, [0,0,0,1])]

    #Sorted by percentage of ml

    #Sorted by ml per barrel
    wholesale_catalog.sort(key=lambda x: x.ml_per_barrel, reverse=True)

    # Now, we are going to iterate by the lowest percentage first,
    # so we can buy the most of the potion type that we have the least of.
    for potionType in percentageMlAmounts:

        potionRecipe = potionType[1]
        percentageOfMl = potionType[0]

        for catalogOption in wholesale_catalog:

            #If we have enough in inventory to where percentage means something.
            if totalMlInInventory > 500:
                #if we have enough of the potion already and its a large or medium option, skip
                if percentageOfMl >= 0.5 and GetBarrelType(catalogOption.sku) > 1:
                    continue

            # The first catalog option will be the largest, buy that
            # If we less than 500ml total, first come first serve
            if catalogOption.potion_type == potionRecipe:
                if runningGoldTotal >= catalogOption.price:
                    returnList.append(
                        {
                            "sku": catalogOption.sku,
                            "quantity": 1,
                        }
                    )
                    runningGoldTotal -= catalogOption.price
                    break

    return returnList