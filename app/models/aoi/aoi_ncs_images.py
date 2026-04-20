from sqlalchemy import String, Integer, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.config import Base
from datetime import datetime

class aoi_ncs_images(Base):
    __tablename__ = "aoi_ncs_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_fisica: Mapped[str] = mapped_column(Text, nullable=False)
    panel_id: Mapped[str] = mapped_column(String(100), nullable=True) # ID de la placa/panel
    componente: Mapped[str] = mapped_column(String(100), nullable=True) # R1, C5, U10...
    etiqueta_real: Mapped[str] = mapped_column(String(50), default="Pendiente") # OK, NG, Basura
    es_entrenamiento: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())