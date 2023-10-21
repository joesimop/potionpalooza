import sqlalchemy
from src import database as db

from src.schemas import barrel_inventory, potion_inventory
"""
THIS FILE IS MORE OR LESS DEPRECATED
It would be worth getting the database id and fluid type from barrel_inventory to make sure we are synced


"""

# Get all the potion names
recipePkAssociations = {}
barrelInventoryIds = {}

with db.engine.begin() as conn:

    # Get existing potions we have sold
    result = conn.execute(
        sqlalchemy
        .select(potion_inventory.c.id, potion_inventory.c.recipe)
    )

    potionRecipes = result.fetchall()

    for potion in potionRecipes:

        primaryKey = potion[0]
        recipe = potion[1]

        recipePkAssociations[str(recipe)] = primaryKey 

    
    result = conn.execute(
                sqlalchemy.select(barrel_inventory.c.fluid_type, barrel_inventory.c.id)
            )

    for item in result:
        barrelInventoryIds[item[0]] = item[1]
