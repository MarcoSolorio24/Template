from app.config import Base, engine
from app.models.catalogos.cargo import Cargo

def up():
    # Crear la tabla Cargo
    Base.metadata.create_all(bind=engine, tables=[Cargo.__table__])