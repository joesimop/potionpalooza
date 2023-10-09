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

        # Get gold
        result = conn.execute(
            sqlalchemy.text(
                "SELECT gold FROM global_inventory"
            )
        )
        gold = result.first()[0]

        # Get number of potions
        result = conn.execute(
            sqlalchemy.text(
                "SELECT count FROM potion_inventory"
            )
        )
        #Sum up all the counts of potions
        potionCount = sum([row[0] for row in result.fetchall()])

        # Get ml of fluid
        result = conn.execute(
            sqlalchemy.text(
                "SELECT ml_amount FROM barrel_inventory"
            )
        )
        #Sum up all the ml of fluid
        fluidAmount = sum([row[0] for row in result.fetchall()])



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
