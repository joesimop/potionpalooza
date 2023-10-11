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

def GetNameFromRecipe(recipe):
    """Returns the name of the potion from the recipe."""
    if recipe == [1, 0 , 0, 0]:
        return "red"
    elif recipe == [0, 1, 0, 0]:
        return "green"
    elif recipe == [0, 0 , 1, 0]:
        return "blue"
    elif recipe == [0, 0, 0, 1]:
        return "dark"
    return None
    

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

        # Gets all the potion stock from barrel_inventory
        result = conn.execute(
            sqlalchemy.text(
                "SELECT fluid_type, ml_amount FROM barrel_inventory"
            )
        )

        potionInventory = result.fetchall()
        potionTypes = [row[0] for row in potionInventory]
        

        for barrel in wholesale_catalog:

            # Setup poiton specific properties
            inventoryPotionMlAmount = 0

            """Was here in case we encountered potions we hadn't seen before, keep just in case."""
            # # If we do not have the barrel in our inventory, add it.
            # # TODO: This is not the most efficient way to do this, look for more unique specifiers later.
            # if barrel.potion_type not in potionTypes:
                    
            #         # Insert the barrel into our inventory
            #         conn.execute(
            #             sqlalchemy.text(
            #                 f"INSERT INTO barrel_inventory (recipe, ml_amount) VALUES \
            #                 (ARRAY{barrel.potion_type}, 0)"
            #             )
            #         )

            #         # Incase we buy barrels of two different sizes of a potion type
            #         # we haven't seen before
            #         potionRecipies.append(barrel.potion_type)

            # Otherwise, get details from inventory
            #else:
            for row in potionInventory:
                potionName = row[0]
                barrelPotionName = GetNameFromRecipe(barrel.potion_type)
                if potionName == barrelPotionName:
                    inventoryPotionMlAmount = row[1]
                    break
            """
            At this point, the potion specific properties should be set up, new or old,
            and we can start the logic for the purchase plan.
            """

            associatePotionRecipe = [ x * 100 for x in barrel.potion_type ]

            result = conn.execute(
                sqlalchemy.text(
                    f"SELECT count FROM potion_inventory WHERE recipe = ARRAY{associatePotionRecipe}::smallint[]"
                )
            )

            potionCount = result.first()[0]

            # We will buy at least one of each barrel if possible.
            # Right now buying the barrels if we don't have any potions of that type.
            # Otherwise we want to save money to buy other barrels.
            if runningGoldTotal >= barrel.price and potionCount == 0:
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
    totalFluidsBought = [0,0,0,0]

    with db.engine.begin() as conn:

        # Calculate how much fluid we bought and how much gold we spent
        for barrel in barrels_delivered:

            totalMlBought = barrel.quantity * barrel.ml_per_barrel
            totalGoldSpent += barrel.price * barrel.quantity

            # Calculate how much of each fluid we bought in this barrel
            for i in range(len(barrel.potion_type)):
                totalFluidsBought[i] += barrel.potion_type[i] * totalMlBought
            

        # Setup case statements for the update query
        caseStatements += f"when fluid_type = \'red\' then {totalFluidsBought[0]} "
        caseStatements += f"when fluid_type = \'green\' then {totalFluidsBought[1]} "
        caseStatements += f"when fluid_type = \'blue\' then {totalFluidsBought[2]} "
        caseStatements += f"when fluid_type = \'dark\' then {totalFluidsBought[3]} "
        

        # Push the new inventory amounts to the database
        # Note: We are iterating through the whole table in the query
        # Also, don't love the case statements, if time, look into another way
        conn.execute(
            sqlalchemy.text(
                f"UPDATE barrel_inventory SET ml_amount = ml_amount + (case {caseStatements} ELSE 0 end) \
                    WHERE fluid_type IN (SELECT fluid_type FROM barrel_inventory)"
            )
        )

        # Update gold amount
        result = conn.execute(
            sqlalchemy.text(
                f"UPDATE global_inventory SET gold = gold - {totalGoldSpent}"
            )
        )


    return "OK\n"
