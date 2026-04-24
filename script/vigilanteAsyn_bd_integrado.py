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

try:
    from app.config import SessionLocal
    from app.services.aoi_service import save_aoi_image
except ImportError:
    print("⚠️ Advertencia: No se detectaron los módulos de base de datos de 'app'.")

# --- CONFIGURACIÓN ---
# Ruta donde se centralizarán las imágenes procesadas
RUTA_DESTINO_BASE = r"C:\Digitalizacion\Python\DB_ConnecrionTest\data\traning_images"
COLUMNAS_PANEL = 4

# Cola para enviar datos del hilo de procesamiento al hilo de la interfaz
cola_visualizacion = queue.Queue()


# --- FUNCIONES DE VALIDACIÓN MEJORADAS ---

def es_imagen_valida(ruta_img: str) -> bool:
    """
    Valida que la imagen sea útil mediante análisis de bordes (Canny) y brillo.
    Evita imágenes blancas con ruido/manchas.
    """
    try:
        img_gris = cv2.imread(ruta_img, cv2.IMREAD_GRAYSCALE)
        if img_gris is None:
            return False
        
        # 1. Análisis de Bordes (Canny) - Detecta si hay formas reales
        bordes = cv2.Canny(img_gris, 50, 150)
        densidad_bordes = np.sum(bordes > 0) / bordes.size
        
        # 2. Análisis Global: Promedio y Desviación
        promedio, desviacion = cv2.meanStdDev(img_gris)
        promedio = float(promedio[0][0])
        desviacion = float(desviacion[0][0])
        
        # FILTRO DE RUIDO/BLANCO:
        # Si la imagen es muy blanca (>235) y casi no tiene bordes, es basura.
        if promedio > 235 and densidad_bordes < 0.002:
            return False
            
        # Si la imagen es casi plana (desviación baja) y muy blanca, es basura.
        if promedio > 230 and desviacion < 15:
            return False

        # Si el promedio está en rango de pieza gris (40-200), suele ser útil.
        if 40 < promedio < 200:
            return True

        return True
    except Exception as e:
        print(f"❌ Error al analizar {ruta_img}: {e}")
        return False


# --- EXTRACCIÓN DE METADATOS Y BASE DE DATOS ---

def extraer_informacion_de_ruta(ruta_completa: str) -> dict:
    """Extrae fecha, modelo y pallet basándose en la estructura de carpetas."""
    info = {'fecha_captura': None, 'modelo_material': None, 'pallet': None, 'nombre_falla': None}
    try:
        ruta_normalizada = ruta_completa.replace('\\', '/')
        partes_ruta = ruta_normalizada.split('/')
        
        for i, parte in enumerate(partes_ruta):
            if len(parte) == 4 and parte.isdigit() and parte.startswith(('2', '1')):
                try:
                    if i + 2 < len(partes_ruta):
                        info['fecha_captura'] = date(int(parte), int(partes_ruta[i+1]), int(partes_ruta[i+2]))
                        if i + 4 < len(partes_ruta): info['modelo_material'] = partes_ruta[i+4]
                        if i + 5 < len(partes_ruta): info['pallet'] = partes_ruta[i+5]
                        break
                except: continue
        
        info['nombre_falla'] = os.path.splitext(os.path.basename(ruta_completa))[0]
    except Exception as e:
        print(f"   ⚠️ Error en metadatos: {e}")
    return info

def guardar_imagen_en_bd(ruta_relativa, nombre_archivo, info_ruta) -> bool:
    """Registra la imagen en PostgreSQL."""
    try:
        db = SessionLocal()
        registro = save_aoi_image(
            db, nombre_archivo, ruta_relativa,
            fecha_captura=info_ruta['fecha_captura'],
            modelo_material=info_ruta['modelo_material'],
            pallet=info_ruta['pallet'],
            nombre_falla=info_ruta['nombre_falla'],
            es_entrenamiento=True
        )
        db.close()
        return True
    except Exception as e:
        print(f"   ❌ Error BD: {e}")
        return False

# --- PROCESAMIENTO DE IMÁGENES ---

def procesar_archivo_individual(ruta_origen):
    """Procesa una sola imagen: valida, copia y sube a BD."""
    if not es_imagen_valida(ruta_origen):
        return None

    nombre_archivo = os.path.basename(ruta_origen)
    ruta_final = os.path.join(RUTA_DESTINO_BASE, nombre_archivo)

    # Evitar sobreescribir con el mismo nombre
    if os.path.exists(ruta_final):
        ts = int(time.time() * 1000)
        n, e = os.path.splitext(nombre_archivo)
        ruta_final = os.path.join(RUTA_DESTINO_BASE, f"{n}_{ts}{e}")
        nombre_archivo = os.path.basename(ruta_final)

    try:
        shutil.copy2(ruta_origen, ruta_final)
        
        # Preparar datos para BD
        proyecto_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            ruta_rel = os.path.relpath(ruta_final, proyecto_root)
        except:
            ruta_rel = ruta_final
            
        info = extraer_informacion_de_ruta(ruta_origen)
        if guardar_imagen_en_bd(ruta_rel, nombre_archivo, info):
            return ruta_final
    except Exception as e:
        print(f"   ❌ Error procesando {nombre_archivo}: {e}")
    
    return None

# --- VISOR ---

def hilo_visualizacion():
    nombre_ventana = "Visor AOI - Vigilante"
    cv2.namedWindow(nombre_ventana, cv2.WINDOW_AUTOSIZE)
    while True:
        try:
            panel = cola_visualizacion.get(timeout=1)
            cv2.imshow(nombre_ventana, panel)
        except queue.Empty: pass
        if (cv2.waitKey(1) & 0xFF) == ord('q'): break
    cv2.destroyAllWindows()

def actualizar_visor(rutas):
    if not rutas: return
    TW, TH = 250, 200
    imgs = []
    for r in rutas[-12:]: # Mostrar máximo las últimas 12
        im = cv2.imread(r)
        if im is not None:
            im = cv2.resize(im, (TW, TH))
            cv2.putText(im, os.path.basename(r)[:15], (5, TH-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,0), 1)
            imgs.append(im)
    
    if not imgs: return
    filas = (len(imgs) + COLUMNAS_PANEL - 1) // COLUMNAS_PANEL
    while len(imgs) < filas * COLUMNAS_PANEL:
        imgs.append(np.zeros((TH, TW, 3), dtype=np.uint8))
    
    res = np.vstack([np.hstack(imgs[i*COLUMNAS_PANEL:(i+1)*COLUMNAS_PANEL]) for i in range(filas)])
    cola_visualizacion.put(res)

# --- OBSERVER ---

class ManejadorAOI(FileSystemEventHandler):
    def on_created(self, event):
        # Monitorear archivos creados en cualquier subnivel
        if not event.is_directory and event.src_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            time.sleep(1.0) # Un poco más de tiempo para asegurar que el archivo de red se cierre
            res = procesar_archivo_individual(event.src_path)
            if res:
                print(f"✨ Nueva imagen detectada en subcarpeta: {os.path.basename(res)}")
                actualizar_visor([res])

def sincronizacion_inicial(ruta_origen):
    """
    Escanea la carpeta al inicio para procesar lo que ya existe, 
    buscando profundamente en todas las subcarpetas.
    """
    print(f"\n🔍 Iniciando escaneo profundo de subcarpetas...")
    archivos_procesados = []
    
    # os.walk recorre automáticamente todas las subcarpetas
    for root, _, files in os.walk(ruta_origen):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                ruta_full = os.path.join(root, f)
                res = procesar_archivo_individual(ruta_full)
                if res:
                    archivos_procesados.append(res)
                    if len(archivos_procesados) % 5 == 0:
                        print(f"   ⏳ Procesados {len(archivos_procesados)} archivos encontrados en subcarpetas...")

    if archivos_procesados:
        print(f"✅ Sincronización completa: {len(archivos_procesados)} archivos añadidos desde las subcarpetas.")
        actualizar_visor(archivos_procesados)
    else:
        print("ℹ️ No se encontraron archivos válidos en ninguna subcarpeta durante el escaneo.")

# --- MAIN ---

if __name__ == "__main__":
    os.makedirs(RUTA_DESTINO_BASE, exist_ok=True)
    
    root = Tk()
    root.withdraw()
    ruta_monitoreo = askdirectory(title="Selecciona Carpeta Raíz de ORIGEN")
    root.destroy()

    if ruta_monitoreo:
        print(f"🚀 Iniciando Vigilante Recursivo en: {ruta_monitoreo}")
        
        threading.Thread(target=hilo_visualizacion, daemon=True).start()

        # FASE 1: Procesar recursivamente lo que ya existe
        sincronizacion_inicial(ruta_monitoreo)

        # FASE 2: Monitorear cambios futuros de forma recursiva
        event_handler = ManejadorAOI()
        observer = Observer()
        # El parámetro recursive=True permite detectar archivos en cualquier profundidad de subcarpeta
        observer.schedule(event_handler, ruta_monitoreo, recursive=True)
        observer.start()

        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()