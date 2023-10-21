from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

import sqlalchemy
from src import database as db
from sqlalchemy.sql.functions import coalesce
from src.schemas import barrel_fluid_ledger, potion_quantity_ledger, gold_ledger

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as conn:

        # Get amount of gold in inventory
        result = conn.execute(
            sqlalchemy
            .select(coalesce(sqlalchemy.func.sum(gold_ledger.c.delta).label("total_gold"), 0))
        )
        gold = result.first()[0]

        # Get amount of potions in inventory
        result = conn.execute(
            sqlalchemy
            .select(coalesce(sqlalchemy.func.sum(potion_quantity_ledger.c.delta).label("total_quantity"), 0))
        )
        potionCount = result.first()[0]

        # Get amount of fluid in barrels
        result = conn.execute(
            sqlalchemy
            .select(coalesce(sqlalchemy.func.sum(barrel_fluid_ledger.c.delta).label("total_fluid"), 0))
        )
        fluidAmount = result.first()[0]

    return {"number_of_potions": potionCount, 
            "ml_in_barrels": fluidAmount, 
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
