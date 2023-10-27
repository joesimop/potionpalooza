from fastapi import APIRouter

import sqlalchemy
from src import database as db

from src.schemas import potion_quantity_ledger, potion_inventory
from sqlalchemy.sql.functions import coalesce, sum

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    catalog = []

    # Can return a max of 20 items.
    with db.engine.begin() as conn:

        # Subquery that requires alias to be defined before hand
        # due to not being able to order by aggregate values
        quantities = sqlalchemy \
                .select(potion_quantity_ledger.c.potion_id, 
                        sum(potion_quantity_ledger.c.delta).label("quantity")) \
                .group_by(potion_quantity_ledger.c.potion_id) \
                .alias("quantities")
    
        # Gets list of potions in inventory, ordered by quantity
        result = conn.execute(
            sqlalchemy
            .select(potion_inventory.c.sku, 
                    potion_inventory.c.recipe, 
                    quantities.c.quantity, 
                    potion_inventory.c.price_per)
            .select_from(quantities)
            .join(potion_inventory, potion_inventory.c.id == quantities.c.potion_id)
            .order_by(quantities.c.quantity.desc())
        )

        potionCatalog = result.fetchall()

        # Limits catalog to 6 items
        catalogLength = 6 if len(potionCatalog) >= 6 else len(potionCatalog)

        # Go through items and add them to catalog
        # Already ordered by the most potions we have.
        for i in range(catalogLength):
            potion = potionCatalog[i]

            # Note: Name is literally not used for anything
            sku = potion[0]
            name = potion[0].replace("_", " ").lower()
            quantity = potion[2]
            recipe = potion[1]
            price = potion[3]

            if quantity > 0:
                catalog.append(
                    {
                        "sku": sku,
                        "name": name,
                        "quantity": quantity,
                        "price": price,
                        "potion_type": recipe,
                    }
                )

    return catalog
