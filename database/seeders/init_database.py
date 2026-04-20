import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
from app.config import Base, engine
from database.migrations.aoi.migration_aoi_ncs_images import up as migrate_aoi_ncs_images


def main():
    Base.metadata.drop_all(bind=engine)
    print("Todas las tablas fueron eliminadas")
    migrate_aoi_ncs_images()
    print("Migración de cargos completada")


if __name__ == "__main__":
    main()