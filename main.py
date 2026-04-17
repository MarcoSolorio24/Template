from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import get_db, setup_cors
from app.models.catalogos.cargo import Cargo
from app.schemas import CargoBase, CargoResponse

app = FastAPI(title="API de Cargos")

# Configurar CORS
setup_cors(app)

@app.get("/cargos/", response_model=list[CargoResponse])
def listar_cargos(db: Session = Depends(get_db)):
    try:
        cargos = db.query(Cargo).all()
        return cargos
    finally:
        db.close()

@app.post("/cargos/", response_model=CargoResponse)
def crear_cargo(cargo: CargoBase, db: Session = Depends(get_db)):
    try:
        db_cargo = Cargo(**cargo.model_dump())
        db.add(db_cargo)
        db.commit()
        db.refresh(db_cargo)
        return db_cargo
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()