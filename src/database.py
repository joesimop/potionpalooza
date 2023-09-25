import os
import dotenv
from sqlalchemy import create_engine

def database_connection_url():
    dotenv.load_dotenv()

    return os.environ.get("DATABASE_URL")

engine = create_engine(database_connection_url(), pool_pre_ping=True)