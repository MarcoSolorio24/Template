from pydantic import BaseModel

class CargoBase(BaseModel):
    nombre_cargo: str

class CargoResponse(CargoBase):
    cargo_id: int

    class Config:
        from_attributes = True