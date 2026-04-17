import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
from app.config import Base, engine
from database.migrations.catalogos.migration_cargo import up as migrate_cargo


def main():
    Base.metadata.drop_all(bind=engine)
    print("Todas las tablas fueron eliminadas")
    migrate_cargo()
    print("Migración de cargos completada")


if __name__ == "__main__":
    main()