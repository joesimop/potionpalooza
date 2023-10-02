from fastapi import APIRouter

import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    # Can return a max of 20 items.
    with db.engine.begin() as conn:

        # Get the number of possible red potions we can sell from inventory
        result = conn.execute(
            sqlalchemy.text(
                "SELECT num_red_potions FROM global_inventory"
            )
        )

        # Get number of red potions
        firstRow = result.first()
        inventoryRedPotionCount = firstRow[0]

    return [
            {
                "sku": "RED_POTION_0",
                "name": "Royal Red Potion",
                "quantity": inventoryRedPotionCount,
                "price": 150,
                "potion_type": [100, 0, 0, 0],
            }
        ]
