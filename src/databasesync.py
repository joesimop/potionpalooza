import sqlalchemy
from src import database as db


"""
THIS FILE IS MORE OR LESS DEPRECATED
It would be worth getting the database id and fluid type from barrel_inventory to make sure we are synced


"""


# We need to generate the enums from the already existing database so we are synced
potionNameList = ["Elixir of Healing", "Dragon's Breath Tonic", "Witch's Brew", "Basilisk Bane Elixir", "Love Potion No. 9", "Potion of Invisibility", "Phoenix Feather Elixir", "Trollbane Tincture", "Potion of Eternal Youth", "Gorgon Gaze Antidote", "Moonlit Serenade Elixir", "Manticore Venom Remedy", "Potion of Strength", "Feywild Essence Elixir", "Potion of Clairvoyance", "Nightshade Elixir", "Chimera's Courage Brew", "Druid's Dream Potion", "Spectral Sight Serum", "Potion of Luck"]
usableNameList = potionNameList.copy()
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

        # Keep track of all names and all usable names
        if name not in potionNameList:
            potionNameList.append(name)

        else:
            usableNameList.remove(name)
