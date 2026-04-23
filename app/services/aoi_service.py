from sqlalchemy.orm import Session
from app.models.aoi.aoi_ncs_images import aoi_ncs_images
from datetime import date

def save_aoi_image(
    db: Session, 
    nombre_archivo: str, 
    ruta_fisica: str,
    fecha_captura: date = None,
    modelo_material: str = None,
    pallet: str = None,
    nombre_falla: str = None,
    es_entrenamiento: bool = False
) -> aoi_ncs_images:
    """
    Guarda un nuevo registro de imagen AOI en la base de datos.

    Args:
        db (Session): Sesión de SQLAlchemy.
        nombre_archivo (str): Nombre del archivo de la imagen.
        ruta_fisica (str): Ruta física donde se almacena la imagen.
        fecha_captura (date, optional): Fecha de captura (YYYY-MM-DD).
        modelo_material (str, optional): Modelo/Material de la PCB.
        pallet (str, optional): Identificador del pallet.
        nombre_falla (str, optional): Nombre de la falla detectada.
        es_entrenamiento (bool, optional): Si es para entrenamiento.

    Returns:
        aoi_ncs_images: La instancia creada del registro.
    """
    try:
        new_image = aoi_ncs_images(
            nombre_archivo=nombre_archivo,
            ruta_fisica=ruta_fisica,
            fecha_captura=fecha_captura,
            modelo_material=modelo_material,
            pallet=pallet,
            nombre_falla=nombre_falla,
            es_entrenamiento=es_entrenamiento
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        return new_image
    except Exception as e:
        db.rollback()
        raise e
