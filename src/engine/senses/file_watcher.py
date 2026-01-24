import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from loguru import logger
import os

class LucyFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            logger.info(f"📁 Nuevo archivo detectado: {filename}")
            # Disparar un ciclo cognitivo en Lucy
            if self.callback:
                self.callback(f"He detectado un nuevo archivo en mi área de vigilancia: {filename}. ¿Qué debo hacer con él?")

class FileWatcher:
    def __init__(self, watch_dir: str, callback):
        self.watch_dir = watch_dir
        self.callback = callback
        self.observer = Observer()
        
        if not os.path.exists(watch_dir):
            os.makedirs(watch_dir, exist_ok=True)

    def start(self):
        logger.info(f"👁️ Iniciando vigilancia de archivos en: {self.watch_dir}")
        event_handler = LucyFileHandler(self.callback)
        self.observer.schedule(event_handler, self.watch_dir, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("👁️ Vigilancia de archivos detenida.")
