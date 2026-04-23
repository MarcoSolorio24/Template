import sys
import os
import time
import cv2
import shutil
import numpy as np
import threading
import queue
from pathlib import Path
from datetime import datetime, date
from tkinter import Tk
from tkinter.filedialog import askdirectory
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configurar sys.path para reconocer la carpeta app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import SessionLocal
from app.services.aoi_service import save_aoi_image
from PIL import Image

# --- CONFIGURACIÓN ---
RUTA_DESTINO_BASE = r"C:\Digitalizacion\Python\DB_ConnecrionTest\data\traning_images"
TIEMPO_EXPOSICION_PANEL_MS = 5000
COLUMNAS_PANEL = 4

# Cola para enviar datos del hilo de procesamiento al hilo de la interfaz
cola_visualizacion = queue.Queue()


# --- FUNCIONES DE VALIDACIÓN ---

def es_imagen_valida(ruta_img: str) -> bool:
    """
    Valida que la imagen sea útil (no blanca/ruido).
    
    Args:
        ruta_img (str): Ruta de la imagen
        
    Returns:
        bool: True si es válida, False si es ruido/blanca
    """
    try:
        img_gris = cv2.imread(ruta_img, cv2.IMREAD_GRAYSCALE)
        if img_gris is None:
            return False
        
        promedio, desviacion = cv2.meanStdDev(img_gris)
        # Extraer los valores escalares del array numpy
        promedio = float(promedio[0][0])
        desviacion = float(desviacion[0][0])
        
        # Si promedio > 220 y desviación < 12, es imagen blanca/ruido
        es_ruido = promedio > 235 and desviacion < 35
        return not es_ruido
    except Exception as e:
        print(f"❌ Error al analizar {ruta_img}: {e}")
        return False


# --- FUNCIONES DE EXTRACCIÓN DE DATOS ---

def extraer_informacion_de_ruta(ruta_completa: str) -> dict:
    """
    Extrae información valiosa de la ruta de la imagen.
    
    Estructura esperada:
    YYYY/MM/DD/LOTE/MODELO_MATERIAL/PALLET/nombre_imagen.jpg
    Ejemplo:
    2026/04/23/085742/12165129_C0147082_POWER_NAR_MACH_E/MKEMM_0535/1.R2200.Pin1_Comp.jpg
    
    Args:
        ruta_completa (str): Ruta completa del archivo
        
    Returns:
        dict: Diccionario con información extraída
    """
    info = {
        'fecha_captura': None,
        'modelo_material': None,
        'pallet': None,
        'nombre_falla': None
    }
    
    try:
        # Normalizar la ruta (convertir backslashes a forward slashes)
        ruta_normalizada = ruta_completa.replace('\\', '/')
        partes_ruta = ruta_normalizada.split('/')
        
        # Buscar la fecha (formato YYYY/MM/DD)
        for i, parte in enumerate(partes_ruta):
            # Buscar patrón de año (4 dígitos que empiezan con 2, 1 o 3)
            if len(parte) == 4 and parte[0] in ['1', '2', '3']:
                try:
                    año = int(parte)
                    if i + 2 < len(partes_ruta):
                        mes = int(partes_ruta[i + 1])
                        dia = int(partes_ruta[i + 2])
                        if 1 <= mes <= 12 and 1 <= dia <= 31:
                            info['fecha_captura'] = date(año, mes, dia)
                            
                            # Modelo/Material está típicamente 2 posiciones después del día
                            if i + 4 < len(partes_ruta):
                                info['modelo_material'] = partes_ruta[i + 4]
                            
                            # Pallet está típicamente 1 posición después del modelo
                            if i + 5 < len(partes_ruta):
                                info['pallet'] = partes_ruta[i + 5]
                            
                            break
                except (ValueError, IndexError):
                    continue
        
        # Nombre de falla = nombre del archivo sin extensión
        nombre_archivo = os.path.basename(ruta_completa)
        nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
        info['nombre_falla'] = nombre_sin_ext
        
    except Exception as e:
        print(f"   ⚠️ Error extrayendo información de ruta: {e}")
    
    return info


# --- FUNCIONES DE BASE DE DATOS ---

def guardar_imagen_en_bd(
    ruta_relativa: str, 
    nombre_archivo: str,
    fecha_captura: date = None,
    modelo_material: str = None,
    pallet: str = None,
    nombre_falla: str = None
) -> bool:
    """
    Guarda la información de una imagen en la base de datos automáticamente.
    
    Args:
        ruta_relativa (str): Ruta relativa de la imagen
        nombre_archivo (str): Nombre del archivo
        fecha_captura (date): Fecha de captura
        modelo_material (str): Modelo/Material
        pallet (str): Identificador del pallet
        nombre_falla (str): Nombre de la falla
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    db = SessionLocal()
    try:
        registro = save_aoi_image(
            db, 
            nombre_archivo, 
            ruta_relativa,
            fecha_captura=fecha_captura,
            modelo_material=modelo_material,
            pallet=pallet,
            nombre_falla=nombre_falla,
            es_entrenamiento=True  # Todo se marca como entrenamiento
        )
        print(f"   ✅ BD registrada - ID: {registro.id} | Fecha: {registro.fecha_captura} | Material: {registro.modelo_material} | Pallet: {registro.pallet}")
        return True
    except Exception as e:
        print(f"   ❌ Error al guardar en BD: {e}")
        return False
    finally:
        db.close()


# --- HILO DE VISUALIZACIÓN ---

def hilo_visualizacion():
    """
    Hilo dedicado exclusivamente a gestionar la ventana de OpenCV.
    """
    nombre_ventana = "Visor AOI - Vigilante"
    cv2.namedWindow(nombre_ventana, cv2.WINDOW_AUTOSIZE)
    
    ultima_actualizacion = 0
    mostrando_panel = False

    while True:
        try:
            try:
                panel_final = cola_visualizacion.get_nowait()
                cv2.imshow(nombre_ventana, panel_final)
                ultima_actualizacion = time.time()
                mostrando_panel = True
            except queue.Empty:
                pass

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            if cv2.getWindowProperty(nombre_ventana, cv2.WND_PROP_VISIBLE) < 1 and mostrando_panel:
                cv2.namedWindow(nombre_ventana, cv2.WINDOW_AUTOSIZE)
                mostrando_panel = False

        except Exception as e:
            pass
        
        time.sleep(0.01)

    cv2.destroyAllWindows()


def generar_grid_panel(lista_rutas):
    """
    Construye la imagen del panel para ser enviada al hilo de visor.
    
    Args:
        lista_rutas (list): Lista de rutas de imágenes
        
    Returns:
        numpy.ndarray: Panel con grid de imágenes
    """
    if not lista_rutas:
        return None
    
    imagenes_panel = []
    TW, TH = 250, 200

    for ruta in lista_rutas:
        img = cv2.imread(ruta)
        if img is not None:
            img_res = cv2.resize(img, (TW, TH))
            nombre = os.path.basename(ruta)[:15]
            cv2.putText(img_res, nombre, (5, TH - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            imagenes_panel.append(img_res)

    if not imagenes_panel:
        return None

    num_imgs = len(imagenes_panel)
    filas = (num_imgs + COLUMNAS_PANEL - 1) // COLUMNAS_PANEL
    while len(imagenes_panel) < filas * COLUMNAS_PANEL:
        imagenes_panel.append(np.zeros((TH, TW, 3), dtype=np.uint8))

    filas_imgs = []
    for i in range(filas):
        fila = np.hstack(imagenes_panel[i*COLUMNAS_PANEL : (i+1)*COLUMNAS_PANEL])
        filas_imgs.append(fila)
    
    return np.vstack(filas_imgs)


# --- HANDLER DE EVENTOS DEL OBSERVER ---

class ManejadorAOI(FileSystemEventHandler):
    """
    Maneja eventos del sistema de archivos (creación de carpetas/archivos).
    """
    
    def __init__(self, ruta_origen: str):
        """
        Inicializa el manejador.
        
        Args:
            ruta_origen (str): Ruta origen que se está monitoreando
        """
        self.ruta_origen = ruta_origen
        super().__init__()

    def on_created(self, event):
        """
        Evento disparado cuando se detecta una nueva carpeta o archivo.
        """
        if event.is_directory:
            ruta_carpeta = event.src_path
            nombre_lote = os.path.basename(ruta_carpeta)
            print(f"\n📂 Lote detectado: {nombre_lote}")
            time.sleep(3.0)  # Esperar a que se creen los archivos
            self.procesar_y_almacenar_lote(ruta_carpeta, nombre_lote)

    def procesar_y_almacenar_lote(self, directorio: str, nombre_lote: str):
        """
        Procesa un lote: encuentra imágenes válidas, las copia y las sube a BD.
        
        Args:
            directorio (str): Directorio del lote
            nombre_lote (str): Nombre del lote
        """
        print(f"   🔍 Buscando imágenes...")
        imagenes_encontradas = []
        
        # Buscar todas las imágenes en el directorio
        for root, _, files in os.walk(directorio):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                    imagenes_encontradas.append(os.path.join(root, file))

        if not imagenes_encontradas:
            print(f"   ⚠️ No se encontraron imágenes en {nombre_lote}")
            return

        print(f"   📸 Encontradas {len(imagenes_encontradas)} imágenes. Validando...")

        rutas_guardadas = []
        exitosas = 0
        fallidas = 0

        for ruta_origen_img in imagenes_encontradas:
            # Validar que sea una imagen útil
            if not es_imagen_valida(ruta_origen_img):
                print(f"   ⏭️  Saltada (ruido/blanca): {os.path.basename(ruta_origen_img)}")
                fallidas += 1
                continue

            nombre_archivo = os.path.basename(ruta_origen_img)
            
            # Crear ruta destino
            ruta_final_destino = os.path.join(RUTA_DESTINO_BASE, nombre_archivo)
            
            # Manejo de duplicados (agregar timestamp)
            if os.path.exists(ruta_final_destino):
                ts = int(time.time())
                nombre_sin_ext, ext = os.path.splitext(nombre_archivo)
                ruta_final_destino = os.path.join(RUTA_DESTINO_BASE, f"{nombre_sin_ext}_{ts}{ext}")
                nombre_archivo = os.path.basename(ruta_final_destino)

            try:
                # Copiar archivo
                shutil.copy2(ruta_origen_img, ruta_final_destino)
                print(f"   ✓ Copiada: {nombre_archivo}")
                
                # Calcular ruta relativa
                proyecto_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                try:
                    ruta_relativa = os.path.relpath(ruta_final_destino, proyecto_root)
                except ValueError:
                    ruta_relativa = ruta_final_destino
                
                # Extraer información de la ruta origen
                info_ruta = extraer_informacion_de_ruta(ruta_origen_img)
                
                # Guardar en BD automáticamente con la información extraída
                if guardar_imagen_en_bd(
                    ruta_relativa, 
                    nombre_archivo,
                    fecha_captura=info_ruta['fecha_captura'],
                    modelo_material=info_ruta['modelo_material'],
                    pallet=info_ruta['pallet'],
                    nombre_falla=info_ruta['nombre_falla']
                ):
                    rutas_guardadas.append(ruta_final_destino)
                    exitosas += 1
                else:
                    fallidas += 1
                    
            except Exception as e:
                print(f"   ❌ Error al procesar {nombre_archivo}: {e}")
                fallidas += 1

        # Mostrar resumen
        print(f"\n   📊 Lote {nombre_lote} procesado:")
        print(f"      - Exitosas: {exitosas}")
        print(f"      - Fallidas: {fallidas}")

        # Generar panel visual
        if rutas_guardadas:
            print(f"   📺 Generando panel visual...")
            panel = generar_grid_panel(rutas_guardadas)
            if panel is not None:
                cola_visualizacion.put(panel)


# --- SELECCIÓN DE DIRECTORIO ---

def seleccionar_directorio_origen() -> str:
    """
    Abre un diálogo gráfico para seleccionar la carpeta de origen.
    
    Returns:
        str: Ruta del directorio seleccionado, o None si se cancela
    """
    print("\n" + "="*70)
    print("VIGILANTE AOI CON SUBIDA AUTOMÁTICA A BASE DE DATOS")
    print("="*70)
    print("\n📂 Se abrirá un explorador de archivos...")
    print("   Selecciona la carpeta de ORIGEN (red o local) donde están las imágenes\n")
    
    root = Tk()
    root.withdraw()  # Ocultar ventana principal
    root.attributes('-topmost', True)  # Poner diálogo al frente
    
    directorio = askdirectory(
        title="Selecciona carpeta de ORIGEN para monitorear",
        mustexist=True
    )
    
    root.destroy()
    
    return directorio


# --- MAIN ---

def main():
    """
    Función principal que inicia el vigilante.
    """
    # Paso 1: Seleccionar directorio
    ruta_origen = seleccionar_directorio_origen()
    
    if not ruta_origen:
        print("\n❌ No se seleccionó directorio. Saliendo...")
        return

    print(f"\n✅ Directorio seleccionado: {ruta_origen}")

    # Crear directorio destino si no existe
    os.makedirs(RUTA_DESTINO_BASE, exist_ok=True)
    print(f"💾 Destino configurado: {RUTA_DESTINO_BASE}")

    # Verificar conexión a BD
    try:
        db = SessionLocal()
        db.close()
        print("✅ Conexión a BD verificada")
    except Exception as e:
        print(f"❌ Error de conexión a BD: {e}")
        print("   Asegúrate de que PostgreSQL está corriendo y el .env está configurado")
        return

    print("\n" + "="*70)
    print("🚀 INICIANDO VIGILANCIA AUTOMÁTICA")
    print("="*70)
    print(f"📂 Monitoreando: {ruta_origen}")
    print(f"💾 Guardando en: {RUTA_DESTINO_BASE}")
    print(f"🗄️  Subiendo automáticamente a BD")
    print("\n   Presiona 'Q' en la ventana de OpenCV para detener")
    print("="*70 + "\n")

    # Iniciar hilo de visualización
    threading.Thread(target=hilo_visualizacion, daemon=True).start()

    # Configurar y iniciar Observer
    event_handler = ManejadorAOI(ruta_origen)
    observer = Observer()
    observer.schedule(event_handler, ruta_origen, recursive=False)
    observer.start()

    # Mantener el programa corriendo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario")
    finally:
        print("🛑 Deteniendo vigilancia...")
        observer.stop()
        observer.join()
        print("✅ Vigilancia finalizada.\n")


if __name__ == "__main__":
    main()
