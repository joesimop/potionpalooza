from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db
from src.databasesync import potionNameRecipeAssociations
from src.schemas import barrel_inventory, potion_inventory
from src.helpers import GetPotionRecipeFromName

from sys import maxsize as MAX_INT
from random import choice

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

niceValues = [0,1,5,10,12,13,25, 50, 100]

# Gets called 4 times a day
# This might be the most horrendous piece of code I have ever written
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
                 sqlalchemy
                 .select(barrel_inventory.c.fluid_type, barrel_inventory.c.ml_amount)
                 .order_by(barrel_inventory.c.recipe.desc())
            )

            # Extract data and setup mixing conversion variables.
            # All lists are ordered as [r,g,b,d]
            potionFluids = result.fetchall()
            potionFluidsTotal = [potionFluid[1] for potionFluid in potionFluids]
            returnList = []

            runningSum = sum(potionFluidsTotal)

            # So we don't choose 0 as the least amount of fluid.
            potionFluidsTotal = [MAX_INT if fluid == 0 else fluid for fluid in potionFluidsTotal]

            # While we can make at least one more potion.
            while(runningSum > 100):

                potionCreated = [0,0,0,0]
                potionLeft = 100
                UsingLimitedFluid = False

                # Get the limiting fluid amount
                # Okay if there are duplicates, we just want the least.
                limitingFluidAmount = min(potionFluidsTotal)
                limitingFluidIndex = potionFluidsTotal.index(limitingFluidAmount)

                # If less than 100, use all of the limiting potion.
                if limitingFluidAmount < 100:
                    potionCreated[limitingFluidIndex] = limitingFluidAmount
                    potionFluidsTotal[limitingFluidIndex] = MAX_INT                 #Set to max so we don't use it again
                    potionLeft -= limitingFluidAmount
                    UsingLimitedFluid = True

                #Random indexing to even out potion creation
                indexes = [0,1,2,3]
                while (len(indexes) != 1):
                    i = choice(indexes)
                    indexes.remove(i)

                    if (i == limitingFluidIndex and UsingLimitedFluid) or potionFluidsTotal[i] == MAX_INT:
                        continue

                    possibleValues = list(filter(lambda x: x <= potionLeft and x <= potionFluidsTotal[i], niceValues))
                    fluidAmount = choice(possibleValues)
                    
                    potionCreated[i] = fluidAmount
                    potionFluidsTotal[i] -= fluidAmount
                    potionLeft -= fluidAmount
                

                #At this point we have a distributed potion, now just fill in the gaps
                for i in range(4):
                    index = (indexes[0] + i) % 4

                    #If we have any fluid remaining, 
                    if potionFluidsTotal[index] != MAX_INT:

                        #If we have enough to fill it, use it
                        if potionFluidsTotal[index] > potionLeft:
                            potionCreated[index] += potionLeft
                            potionFluidsTotal[index] -= potionLeft
                            potionLeft = 0
                            break

                        #Otherwise use remaining and get more from fluids in order
                        else:
                            potionCreated[index] = potionFluidsTotal[index]
                            potionLeft -= potionFluidsTotal[index]
                            potionFluidsTotal[index] = MAX_INT


                # If we have a potion of this type already, add to it
                for potion in returnList:
                    if potion["potion_type"] == potionCreated:
                        potion["quantity"] = potion["quantity"] + 1
                        break

                #Otherwise, add a new potion
                else:
                    returnList.append(
                        {
                            "potion_type": potionCreated,
                            "quantity": 1,
                        }
                    )

                runningSum -= 100

    zredTotal = sum([potion["potion_type"][0] * potion["quantity"] for potion in returnList])
    zgreenTotal = sum([potion["potion_type"][1] * potion["quantity"] for potion in returnList])
    zblueTotal = sum([potion["potion_type"][2] * potion["quantity"] for potion in returnList])
    zdarkTotal = sum([potion["potion_type"][3] * potion["quantity"] for potion in returnList])
    return returnList

def CreatePotionName(recipe):
    return "BOTTLE_OF_" + "_".join([str(x) for x in recipe])

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)

    with db.engine.begin() as conn:
         
        totalFluidUsed = [0,0,0,0]
         
        # For each potion, calculate how much fluid we bottles,
        # add a case statement to the update query.
        for potion in potions_delivered:
            
            
            potionRecipe = potion.potion_type

            # Want to use a name, but would need to use list as a key,
            # find better way later
            # potionName = potionNameRecipeAssociations.get(potionRecipe, None)

            #If this is a new potion, insert it into the table with a new name!
            if potionRecipe not in potionNameRecipeAssociations.values():
                potionSku = CreatePotionName(potionRecipe)

                conn.execute(
                    sqlalchemy
                    .insert(potion_inventory)
                    .values(sku=potionSku, recipe=potionRecipe, count=0)
                )

                potionNameRecipeAssociations[potionSku] = potionRecipe

            #Collect fluid used
            for i in range(len(potionRecipe)):
                totalFluidUsed[i] += potionRecipe[i] * potion.quantity
                

        #Update the potion inventory
        conn.execute(
            sqlalchemy
            .update(potion_inventory)
            .values(count = potion_inventory.c.count +
                    sqlalchemy.case(
                        *((potion_inventory.c.recipe == potion.potion_type, potion.quantity) 
                          for potion in potions_delivered),
                        else_ = 0
                    )
            )
        )

        #Update the barrel inventory
        conn.execute(
            sqlalchemy
            .update(barrel_inventory)
            .values(ml_amount = barrel_inventory.c.ml_amount -
                    sqlalchemy.case(
                        (barrel_inventory.c.fluid_type == "red", totalFluidUsed[0]),
                        (barrel_inventory.c.fluid_type == "green", totalFluidUsed[1]),
                        (barrel_inventory.c.fluid_type == "blue", totalFluidUsed[2]),
                        (barrel_inventory.c.fluid_type == "dark", totalFluidUsed[3]),
                    )
            )
        )

    return "OK"