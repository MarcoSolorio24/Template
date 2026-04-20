from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.config import Base

class aoi_ncs_images(Base):
    __tablename__ = "aoi_ncs_images"

    cargo_id: Mapped[int] = mapped_column(primary_key=True)
    imagen: Mapped[str] = mapped_column(String(255), nullable=False)