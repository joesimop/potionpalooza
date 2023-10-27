import sqlalchemy
from src import database as db

metadata = sqlalchemy.MetaData()
barrel_inventory = sqlalchemy.Table("barrel_inventory", metadata, autoload_with=db.engine)
potion_inventory = sqlalchemy.Table("potion_inventory", metadata, autoload_with=db.engine)
carts = sqlalchemy.Table("carts", metadata, autoload_with=db.engine)
cart_items = sqlalchemy.Table("cart_items", metadata, autoload_with=db.engine)
barrel_fluid_ledger = sqlalchemy.Table("barrel_fluid_ledger", metadata, autoload_with=db.engine)
potion_quantity_ledger = sqlalchemy.Table("potion_quantity_ledger", metadata, autoload_with=db.engine)
gold_ledger = sqlalchemy.Table("gold_ledger", metadata, autoload_with=db.engine)
invoices = sqlalchemy.Table("invoices", metadata, autoload_with=db.engine)