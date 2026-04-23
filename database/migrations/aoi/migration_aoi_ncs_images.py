from app.config import Base, engine
from app.models.aoi.aoi_ncs_images import aoi_ncs_images

def up():
    Base.metadata.create_all(bind=engine, tables=[aoi_ncs_images.__table__])