import sys
import os
from pathlib import Path
from PIL import Image

# Configurar sys.path para reconocer la carpeta app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import SessionLocal
from app.services.aoi_service import save_aoi_image

def validate_image(image_path: str) -> bool:
    """
    Valida que el archivo sea una imagen válida.
    
    Args:
        image_path (str): Ruta de la imagen
        
    Returns:
        bool: True si es una imagen válida, False en caso contrario
    """
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
    
    if not os.path.exists(image_path):
        print(f"❌ Error: El archivo no existe: {image_path}")
        return False
    
    if not image_path.lower().endswith(valid_extensions):
        print(f"❌ Error: El archivo no es una imagen válida. Extensiones permitidas: {valid_extensions}")
        return False
    
    try:
        with Image.open(image_path) as img:
            img.verify()
        print(f"✓ Imagen válida: {image_path}")
        return True
    except Exception as e:
        print(f"❌ Error al validar la imagen: {e}")
        return False

def upload_image_to_db(image_path: str, es_entrenamiento: bool = False) -> bool:
    """
    Sube la información de una imagen a la base de datos.
    
    Args:
        image_path (str): Ruta completa de la imagen
        es_entrenamiento (bool): Si es para entrenamiento o no (default: False)
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    # Validar que la imagen existe y es válida
    if not validate_image(image_path):
        return False
    
    # Obtener el nombre del archivo
    nombre_archivo = os.path.basename(image_path)
    
    # Convertir a ruta relativa respecto a la carpeta del proyecto
    ruta_absoluta = os.path.abspath(image_path)
    proyecto_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        ruta_relativa = os.path.relpath(ruta_absoluta, proyecto_root)
    except ValueError:
        # Si está en otra unidad, usar la ruta absoluta como fallback
        ruta_relativa = ruta_absoluta
    
    # Obtener sesión de la base de datos
    db = SessionLocal()
    
    try:
        # Guardar en la base de datos
        registro = save_aoi_image(db, nombre_archivo, ruta_relativa)
        print(f"✓ Imagen registrada en la BD:")
        print(f"  - ID: {registro.id}")
        print(f"  - Nombre: {registro.nombre_archivo}")
        print(f"  - Ruta (relativa): {registro.ruta_fisica}")
        print(f"  - Fecha de registro: {registro.fecha_registro}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar en la BD: {e}")
        return False
    finally:
        db.close()

def main_interactive():
    """
    Modo interactivo: pide la ruta de una imagen al usuario.
    """
    print("\n" + "="*60)
    print("SUBIDOR DE IMÁGENES A BASE DE DATOS")
    print("="*60)
    
    while True:
        print("\nOpciones:")
        print("1. Subir una imagen")
        print("2. Subir múltiples imágenes desde una carpeta")
        print("3. Salir")
        
        opcion = input("\nSelecciona una opción (1-3): ").strip()
        
        if opcion == "1":
            image_path = input("\nIngresa la ruta completa de la imagen: ").strip()
            es_entrenamiento_input = input("¿Es para entrenamiento? (s/n, default=n): ").strip().lower()
            es_entrenamiento = es_entrenamiento_input == 's'
            
            if upload_image_to_db(image_path, es_entrenamiento):
                print("\n✓ Imagen subida exitosamente\n")
            else:
                print("\n✗ Error al subir la imagen\n")
        
        elif opcion == "2":
            folder_path = input("\nIngresa la ruta de la carpeta: ").strip()
            
            if not os.path.isdir(folder_path):
                print(f"❌ Error: La carpeta no existe: {folder_path}\n")
                continue
            
            es_entrenamiento_input = input("¿Son para entrenamiento? (s/n, default=n): ").strip().lower()
            es_entrenamiento = es_entrenamiento_input == 's'
            
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
            images = [f for f in os.listdir(folder_path) 
                     if f.lower().endswith(image_extensions)]
            
            if not images:
                print(f"❌ No se encontraron imágenes en: {folder_path}\n")
                continue
            
            print(f"\nSe encontraron {len(images)} imágenes. Subiendo...\n")
            
            successful = 0
            failed = 0
            
            for image_name in images:
                image_path = os.path.join(folder_path, image_name)
                if upload_image_to_db(image_path, es_entrenamiento):
                    successful += 1
                else:
                    failed += 1
            
            print(f"\n📊 Resumen:")
            print(f"  - Exitosas: {successful}")
            print(f"  - Fallidas: {failed}\n")
        
        elif opcion == "3":
            print("\n¡Hasta luego!\n")
            break
        else:
            print("\n❌ Opción inválida. Intenta de nuevo.\n")

def main_cli(image_path: str, es_entrenamiento: bool = False):
    """
    Modo CLI: recibe argumentos desde la línea de comandos.
    
    Args:
        image_path (str): Ruta de la imagen
        es_entrenamiento (bool): Si es para entrenamiento
    """
    if upload_image_to_db(image_path, es_entrenamiento):
        print("\n✓ Operación completada exitosamente")
        return 0
    else:
        print("\n✗ Error durante la operación")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Modo CLI
        image_path = sys.argv[1]
        es_entrenamiento = len(sys.argv) > 2 and sys.argv[2].lower() in ['true', '1', 'yes', 's']
        exit_code = main_cli(image_path, es_entrenamiento)
        sys.exit(exit_code)
    else:
        # Modo interactivo
        main_interactive()
