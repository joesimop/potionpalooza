from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db
from src.databasesync import potionNameRecipeAssociations, usableNameList

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int


# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    Right now, we are just bottling the barrels as we receive them.
    Might want to look into mixing if we can, not sure if that is an option however.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: just bottles of red green and blue as we can.
    # We can add more logic later to mix potions if we want to.
    with db.engine.begin() as conn:
            

            # Get the amount of recipes from the inventory.
            result = conn.execute(
                 sqlalchemy.text(
                      "SELECT recipe, ml_amount FROM barrel_inventory"
                )
            )

            # Extract data and setup mixing conversion variables.
            potionRecipes = result.fetchall()
            returnList = []

            # For each potion recipe, determine how many potions we can make.
            # If we can add at least one, add it to the return list.
            for potion in potionRecipes:

                potionRecipe = potion[0]
                fluidAmount = potion[1]

                # Get the number of potions we can make from the fluid amount.
                numberOfPotions = fluidAmount // 100
                
                if numberOfPotions > 0:
                    returnList.append(
                        {
                            "potion_type": [x * 100 for x in potionRecipe],
                            "quantity": numberOfPotions,
                        }
                    )
    
    return returnList

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)

    with db.engine.begin() as conn:
         
        potionCaseStatements = ""
        barrelCaseStatements = ""
         
        # For each potion, calculate how much fluid we bottles,
        # add a case statement to the update query.
        for potion in potions_delivered:
            
            
            potionRecipe = potion.potion_type

            # Want to use a name, but would need to use list as a key,
            # find better way later
            # potionName = potionNameRecipeAssociations.get(potionRecipe, None)

            #If this is a new potion, insert it into the table with a new name!
            if potionRecipe not in potionNameRecipeAssociations.values():
                potionName = usableNameList.pop()
                conn.execute(
                    sqlalchemy.text(
                        f"INSERT INTO potion_inventory (name, recipe, price_per_potion, count) VALUES \
                        (\'{potionName}\', ARRAY{potionRecipe}, 300, 0)"
                    )
                )
                potionNameRecipeAssociations[potionName] = potionRecipe
                 

            # This logic is hard-coded. How we will implement this generally will depend on 
            # how we mix potions and how we track what fluid we take from which barrels
            # HARDCODED LOGIC IN THIS BLOCK
            bottledFluid = potion.quantity * 100
            if potionRecipe == [100,0,0,0]:
                 sourceBarrel = [1,0,0,0]
            elif potionRecipe == [0,100,0,0]:
                 sourceBarrel = [0,1,0,0]
            elif potionRecipe == [0,0,100,0]:
                 sourceBarrel = [0,0,1,0]

            potionCaseStatements += f"when recipe = ARRAY{potionRecipe} then {potion.quantity} "
            barrelCaseStatements += f"when recipe = ARRAY{sourceBarrel} then {bottledFluid} "


        # Push the new potion amounts to the database
        conn.execute(
            sqlalchemy.text(
                f"UPDATE potion_inventory SET count = count + (case {potionCaseStatements} ELSE 0 end) \
                    WHERE recipe IN (SELECT recipe FROM potion_inventory)"
            )
        )

        # Push the new barrel amounts to the database
        conn.execute(
            sqlalchemy.text(
                f"UPDATE barrel_inventory SET ml_amount = ml_amount - (case {barrelCaseStatements} ELSE 0 end) \
                    WHERE recipe IN (SELECT recipe FROM barrel_inventory)"
            )
        )

    return "OK"