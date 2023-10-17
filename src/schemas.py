import sqlalchemy
from src import database as db

metadata = sqlalchemy.MetaData()
barrel_inventory = sqlalchemy.Table("barrel_inventory", metadata, autoload_with=db.engine)
potion_inventory = sqlalchemy.Table("potion_inventory", metadata, autoload_with=db.engine)
carts = sqlalchemy.Table("carts", metadata, autoload_with=db.engine)
cart_items = sqlalchemy.Table("cart_items", metadata, autoload_with=db.engine)
global_inventory = sqlalchemy.Table("global_inventory", metadata, autoload_with=db.engine)