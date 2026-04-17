from sqlalchemy import Column, Integer, String, Boolean, DateTime, SmallInteger, Text
from database import Base
import datetime

class AOIImage(Base):
    __tablename__ = "aoi_ncs_images"

    id = Column(Integer, primary_key=True, index=True)
    maquina_id = Column(SmallInteger, nullable=False)
    pcb_serial = Column(String(100), nullable=False)
    panel_num = Column(SmallInteger)
    ref_desig = Column(String(20))
    pin_num = Column(String(10))
    part_number = Column(String(50))
    falla_codigo = Column(String(50), nullable=False)
    modo_captura = Column(String(50))
    path_imagen = Column(Text, unique=True, nullable=False)
    fecha_inspeccion = Column(DateTime, nullable=False)
    procesado_ml = Column(Boolean, default=False)