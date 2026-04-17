from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ImageBase(BaseModel):
    maquina_id: int
    pcb_serial: str
    panel_num: int
    ref_desig: str
    falla_codigo: str
    path_imagen: str
    fecha_inspeccion: datetime
    pin_num: Optional[str] = None
    part_number: Optional[str] = None
    modo_captura: Optional[str] = None

class ImageResponse(ImageBase):
    id: int
    procesado_ml: bool

    class Config:
        from_attributes = True