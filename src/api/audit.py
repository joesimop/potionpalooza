from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as conn:
        result = conn.execute(
            sqlalchemy.text(
                "SELECT num_red_potions, num_red_ml, gold FROM global_inventory"
            )
        )

        firstRow = result.first()
        inventoryRedPotionCount = firstRow[0]
        inventoryRedFluidCount = firstRow[1]
        gold = firstRow[2]

    return {"number_of_potions": inventoryRedPotionCount, 
            "ml_in_barrels": inventoryRedFluidCount, 
            "gold": gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"
