import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Esto asegura que busque el archivo .env en la carpeta actual
load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url is None:
    raise ValueError("Error: No se encontró DATABASE_URL en el archivo .env")

engine = create_engine(db_url)
# ... el resto del código sigue igual ...

engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependencia para obtener la DB en cada ruta
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



        # user norie001
        # psw database_manager
        # ip 10.113.2.242
        # port 5432
        # postgres 