import time
import os
import cv2
import shutil
import numpy as np
import threading
import queue
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURACIÓN ---

# Asegúrate de que estas rutas sean correctas y accesibles
RUTA_RAIZ_BASE = r"\\MXSRKIM001\Share\Digitalization\Test01_AOI_ImageRecolect\Data_ML"
RUTA_DESTINO_BASE = r"C:\Digitalizacion\Python\Vigilante\Img"
# Rutas actualizadas según tu requerimiento
TIEMPO_EXPOSICION_PANEL_MS = 5000  # Tiempo para ver el panel completo
COLUMNAS_PANEL = 4                

# Cola para enviar datos del hilo de procesamiento al hilo de la interfaz
cola_visualizacion = queue.Queue()

def es_imagen_valida(ruta_img):
    """Analiza si la imagen es útil (no blanca/ruido)."""
    try:
        img_gris = cv2.imread(ruta_img, cv2.IMREAD_GRAYSCALE)
        if img_gris is None: return False
        promedio, desviacion = cv2.meanStdDev(img_gris)
        return not (promedio > 240 or desviacion < 8)
    except Exception as e:
        print(f"Error al analizar {ruta_img}: {e}")
        return False

def hilo_visualizacion():
    """Hilo dedicado exclusivamente a gestionar la ventana de OpenCV."""
    nombre_ventana = "Visor AOI - Panel de Lote"
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
    """Construye la imagen del panel para ser enviada al hilo de visor."""
    if not lista_rutas: return None
    
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

    if not imagenes_panel: return None

    num_imgs = len(imagenes_panel)
    filas = (num_imgs + COLUMNAS_PANEL - 1) // COLUMNAS_PANEL
    while len(imagenes_panel) < filas * COLUMNAS_PANEL:
        imagenes_panel.append(np.zeros((TH, TW, 3), dtype=np.uint8))

    filas_imgs = []
    for i in range(filas):
        fila = np.hstack(imagenes_panel[i*COLUMNAS_PANEL : (i+1)*COLUMNAS_PANEL])
        filas_imgs.append(fila)
    
    return np.vstack(filas_imgs)

class ManejadorAOI(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            ruta_carpeta = event.src_path
            nombre_lote = os.path.basename(ruta_carpeta)
            print(f"\n📂 Lote detectado: {nombre_lote}")
            time.sleep(3.0) 
            self.procesar_y_almacenar_lote(ruta_carpeta, nombre_lote)

    def procesar_y_almacenar_lote(self, directorio, nombre_lote):
        imagenes_encontradas = []
        for root, _, files in os.walk(directorio):
            for file in files:
                if file.lower().endswith(".jpg"):
                    imagenes_encontradas.append(os.path.join(root, file))
        
        rutas_guardadas = []
        for ruta_origen in imagenes_encontradas:
            if es_imagen_valida(ruta_origen):
                # CAMBIO CLAVE: Se guarda directamente en la carpeta destino sin subcarpetas
                nombre_archivo = os.path.basename(ruta_origen)
                ruta_final = os.path.join(RUTA_DESTINO_BASE, nombre_archivo)
                
                try:
                    # Si el archivo ya existe, le añade un timestamp para no sobrescribir
                    if os.path.exists(ruta_final):
                        ts = int(time.time())
                        nombre_sin_ext, ext = os.path.splitext(nombre_archivo)
                        ruta_final = os.path.join(RUTA_DESTINO_BASE, f"{nombre_sin_ext}_{ts}{ext}")
                    
                    shutil.copy2(ruta_origen, ruta_final)
                    rutas_guardadas.append(ruta_final)
                except Exception as e:
                    print(f"❌ Error al copiar {nombre_archivo}: {e}")

        if rutas_guardadas:
            print(f"✅ {len(rutas_guardadas)} imagenes almacenadas en carpeta unica. Generando panel...")
            panel = generar_grid_panel(rutas_guardadas)
            if panel is not None:
                cola_visualizacion.put(panel)

def obtener_ruta_dia():
    hoy = datetime.now()
    return os.path.join(RUTA_RAIZ_BASE, hoy.strftime("%Y"), hoy.strftime("%m"), hoy.strftime("%d"))

if __name__ == "__main__":
    os.makedirs(RUTA_DESTINO_BASE, exist_ok=True)
    
    ruta_monitoreo = obtener_ruta_dia()
    
    if not os.path.exists(ruta_monitoreo):
        print(f"⚠️ La ruta de hoy no existe aun: {ruta_monitoreo}")
        print("Esperando a que se cree la carpeta del dia...")
        # Intentamos crearla localmente para el test, o simplemente esperamos
        try:
            os.makedirs(ruta_monitoreo, exist_ok=True)
        except: pass

    print(f"🚀 Vigilante Multihilo iniciado (Modo Carpeta Unica).")
    print(f"📂 Monitoreando: {ruta_monitoreo}")
    print(f"💾 Guardando todo en: {RUTA_DESTINO_BASE}")

    threading.Thread(target=hilo_visualizacion, daemon=True).start()

    event_handler = ManejadorAOI()
    observer = Observer()
    observer.schedule(event_handler, ruta_monitoreo, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo vigilancia...")
    finally:
        observer.stop()
        observer.join()
        print("Vigilancia finalizada.")
'''
import time
import os
import cv2
import shutil
import numpy as np
import threading
import queue
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

RUTA_RAIZ_BASE = r"\\MXSRKIM001\Share\Digitalization\Test01_AOI_ImageRecolect\Data_ML"
RUTA_DESTINO_BASE = r"C:\Digitalizacion\Python\Vigilante\Data_ML"
TIEMPO_EXPOSICION_PANEL_MS = 5000  # Tiempo para ver el panel completo
COLUMNAS_PANEL = 3                

# Cola para enviar datos del hilo de procesamiento al hilo de la interfaz
cola_visualizacion = queue.Queue()

def es_imagen_valida(ruta_img):
    """Analiza si la imagen es útil (no blanca/ruido)."""
    try:
        img_gris = cv2.imread(ruta_img, cv2.IMREAD_GRAYSCALE)
        if img_gris is None: return False
        promedio, desviacion = cv2.meanStdDev(img_gris)
        return not (promedio > 240 or desviacion < 8)
    except Exception as e:
        print(f"Error al analizar {ruta_img}: {e}")
        return False

def hilo_visualizacion():
    """Hilo dedicado exclusivamente a gestionar la ventana de OpenCV."""
    nombre_ventana = "Visor AOI - Panel de Lote"
    cv2.namedWindow(nombre_ventana, cv2.WINDOW_AUTOSIZE)
    
    ultima_actualizacion = 0
    mostrando_panel = False

    while True:
        try:
            # Revisar si hay un nuevo panel para mostrar (sin bloquear)
            try:
                panel_final = cola_visualizacion.get_nowait()
                cv2.imshow(nombre_ventana, panel_final)
                ultima_actualizacion = time.time()
                mostrando_panel = True
            except queue.Empty:
                pass

            # Mantener la ventana viva procesando eventos de Windows
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            # Si ya pasó el tiempo de exposición, podríamos limpiar la ventana o dejarla
            if mostrando_panel and (time.time() - ultima_actualizacion) > (TIEMPO_EXPOSICION_PANEL_MS / 1000.0):
                # Opcional: podrías poner una imagen negra o simplemente dejar la última
                pass
            
            # Verificación de si la ventana fue cerrada manualmente
            if cv2.getWindowProperty(nombre_ventana, cv2.WND_PROP_VISIBLE) < 1 and mostrando_panel:
                # Si se cerró, la volvemos a crear para el siguiente lote
                cv2.namedWindow(nombre_ventana, cv2.WINDOW_AUTOSIZE)
                mostrando_panel = False

        except Exception as e:
            print(f"Error en hilo de visor: {e}")
            time.sleep(1)

    cv2.destroyAllWindows()

def generar_grid_panel(lista_rutas):
    """Construye la imagen del panel para ser enviada al hilo de visor."""
    if not lista_rutas: return None
    
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

    if not imagenes_panel: return None

    num_imgs = len(imagenes_panel)
    filas = (num_imgs + COLUMNAS_PANEL - 1) // COLUMNAS_PANEL
    while len(imagenes_panel) < filas * COLUMNAS_PANEL:
        imagenes_panel.append(np.zeros((TH, TW, 3), dtype=np.uint8))

    filas_imgs = []
    for i in range(filas):
        fila = np.hstack(imagenes_panel[i*COLUMNAS_PANEL : (i+1)*COLUMNAS_PANEL])
        filas_imgs.append(fila)
    
    return np.vstack(filas_imgs)

class ManejadorAOI(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            ruta_carpeta = event.src_path
            nombre_lote = os.path.basename(ruta_carpeta)
            print(f"\n📂 Lote detectado: {nombre_lote}")
            time.sleep(3.0) 
            self.procesar_y_almacenar_lote(ruta_carpeta, nombre_lote)

    def procesar_y_almacenar_lote(self, directorio, nombre_lote):
        imagenes_encontradas = []
        for root, _, files in os.walk(directorio):
            for file in files:
                if file.lower().endswith(".jpg"):
                    imagenes_encontradas.append(os.path.join(root, file))
        
        rutas_guardadas = []
        for ruta_origen in imagenes_encontradas:
            if es_imagen_valida(ruta_origen):
                rel_path = os.path.relpath(ruta_origen, RUTA_RAIZ_BASE)
                ruta_final = os.path.join(RUTA_DESTINO_BASE, rel_path)
                os.makedirs(os.path.dirname(ruta_final), exist_ok=True)
                try:
                    shutil.copy2(ruta_origen, ruta_final)
                    rutas_guardadas.append(ruta_final)
                except Exception as e:
                    print(f"❌ Error al copiar {os.path.basename(ruta_origen)}: {e}")

        if rutas_guardadas:
            print(f"✅ {len(rutas_guardadas)} imágenes listas. Enviando al panel...")
            panel = generar_grid_panel(rutas_guardadas)
            if panel is not None:
                cola_visualizacion.put(panel)

def obtener_ruta_dia():
    hoy = datetime.now()
    return os.path.join(RUTA_RAIZ_BASE, hoy.strftime("%Y"), hoy.strftime("%m"), hoy.strftime("%d"))

if __name__ == "__main__":
    os.makedirs(RUTA_DESTINO_BASE, exist_ok=True)
    ruta_monitoreo = obtener_ruta_dia()
    os.makedirs(ruta_monitoreo, exist_ok=True)
    
    print(f"🚀 Vigilante Multinúcleo iniciado.")
    print(f"📂 Monitoreando: {ruta_monitoreo}")

    # Iniciar el hilo de la interfaz gráfica
    threading.Thread(target=hilo_visualizacion, daemon=True).start()

    event_handler = ManejadorAOI()
    observer = Observer()
    observer.schedule(event_handler, ruta_monitoreo, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCerrando...")
        observer.stop()
        observer.join()

'''