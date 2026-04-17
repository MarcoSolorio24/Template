from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.config import Base

class Cargo(Base):
    __tablename__ = "cargos"

    cargo_id: Mapped[int] = mapped_column(primary_key=True)
    nombre_cargo: Mapped[str] = mapped_column(String(100), nullable=False)