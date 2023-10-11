from fastapi import APIRouter

import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    catalog = []

    # Can return a max of 20 items.
    with db.engine.begin() as conn:

        # Get the number of possible red potions we can sell from inventory
        result = conn.execute(
            sqlalchemy.text(
                "SELECT name, count, recipe FROM potion_inventory"
            )
        )

        potionInventory = result.fetchall()
        
        for potion in potionInventory:

            sku = potion[0]
            name = potion[0].replace("_", " ").lower()
            quantity = potion[1]
            recipe = potion[2]

            if quantity > 0:
                catalog.append(
                    {
                        "sku": sku,
                        "name": name,
                        "quantity": quantity,
                        "price": 50,
                        "potion_type": recipe,
                    }
                )

    return catalog
