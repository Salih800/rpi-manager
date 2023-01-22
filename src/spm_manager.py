import time
from threading import Thread
import logging

from utils import spm2_conn


settings = {"port": 1, "address": 8}


class SpmManager(Thread):
    def __init__(self):
        Thread.__init__(self, daemon=True, name="SPMManager")
        self._spm = None
        self._settings = settings
        self._is_running = False

        self.start()

    def run(self):
        logging.info("SpmManager: started")
        self._is_running = True
        while self._is_running:
            try:
                self._spm = spm2_conn.SPM2Conn()
                self._spm.init(self._settings)
                while self._is_running:
                    res = self._spm.heartbeat()
                    logging.info(f"SpmManager: SPM heartbeat: {res}")
                    time.sleep(60)
            except Exception as e:
                logging.error(f"SpmManager: {e}", exc_info=True)
        self.stop()

    def stop(self):
        logging.info("SpmManager: stopped")
        self._is_running = False
        self._spm.close()
        self._spm = None
