from PyQt5.QtCore import QThread, pyqtSignal
import time
from tor_manager import TorManager
from db.db_handler import DBHandler
from config import TOR_PATH, TOR_CONTROL_PORT, TOR_PASSWORD

class StartupWorker(QThread):
    status_update = pyqtSignal(str, int)  # message, progress
    finished = pyqtSignal(object, object)  # tor_mgr, db
    error = pyqtSignal(str)

    def run(self):
        try:
            self.status_update.emit("Starting Tor network...", 10)
            tor_mgr = TorManager(tor_path=TOR_PATH, control_port=TOR_CONTROL_PORT, password=TOR_PASSWORD)
            tor_mgr.start_tor()
            self.status_update.emit("Waiting for Tor to bootstrap...", 30)
            if not tor_mgr.wait_for_tor_bootstrap(timeout=60):
                self.error.emit("Tor failed to bootstrap in time.")
                return
            self.status_update.emit("Tor network ready. Connecting to database...", 50)
            db = DBHandler()
            db.init_db()
            self.status_update.emit("Database ready. Launching Libra UI...", 80)
            time.sleep(0.5)
            self.finished.emit(tor_mgr, db)
        except Exception as e:
            self.error.emit(str(e))
