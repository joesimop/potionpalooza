import sqlalchemy
from src import database as db


"""
THIS FILE IS MORE OR LESS DEPRECATED
It would be worth getting the database id and fluid type from barrel_inventory to make sure we are synced


"""

# Get all the potion names
potionNameRecipeAssociations ={}

with db.engine.begin() as conn:

    # Get existing potions we have sold
    result = conn.execute(
        sqlalchemy.text(
            f"SELECT recipe, sku FROM potion_inventory"
        )
    )

    potionRecipes = result.fetchall()

    for potion in potionRecipes:

        recipe = potion[0]
        name = potion[1]

        potionNameRecipeAssociations[name] = recipe
