from sqlalchemy import String, Integer, DateTime, Text, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.config import Base
from datetime import datetime, date

class aoi_ncs_images(Base):
    __tablename__ = "aoi_ncs_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_fisica: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_captura: Mapped[date] = mapped_column(Date, nullable=True)  # YYYY/MM/DD
    modelo_material: Mapped[str] = mapped_column(String(255), nullable=True)  # Ej: 12165129_C0147082_POWER_NAR_MACH_E
    pallet: Mapped[str] = mapped_column(String(50), nullable=True)  # Ej: MKEMM_0535
    nombre_falla: Mapped[str] = mapped_column(String(255), nullable=True)  # Nombre sin extensión
    es_entrenamiento: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), nullable=True)  # Ej: 'pendiente', 'procesada', 'error'