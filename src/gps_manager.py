import logging
import time
from threading import Thread
from utils.serial_connection import SerialConnection
from utils.gps_data import GPSData
from constants.gps_commands import *


class GPSNotPoweredUpError(Exception):
    """ Exception raised when the GPS is not powered up. """
    pass


class GPSReader(SerialConnection, Thread):
    def __init__(self, parent, port, baudrate, timeout):
        Thread.__init__(self, daemon=True, name="GPSReader")
        SerialConnection.__init__(self, port, baudrate, timeout)

        self._parent = parent

        self._gps_data = GPSData(GPS_DATA + NO_FIX_DATA)

        self.running = True
        self.start()

    def run(self):
        logging.info(f"Starting GPS Reader...")
        logging.info(f"Port: {self._serial.port}, Baudrate: {self._serial.baudrate}, Timeout: {self._serial.timeout}")
        self.send_command(POWER_UP)
        data = self.read_until(expected=OK)
        if data.startswith(OK):
            while self.running:
                self.send_command(GET_GPS_DATA)
                try:
                    self._gps_data = GPSData(self.read_until(expected=GPS_DATA))
                except Exception as e:
                    logging.warning(f"GPSReader: {e}")
                    self._gps_data = GPSData(GPS_DATA + NO_FIX_DATA)
                    time.sleep(1)
        else:
            raise GPSNotPoweredUpError()

    def stop(self):
        self.running = False
        self._serial.close()

    def get_gps_data(self):
        return self._gps_data

    def get_drawable_gps_data(self):
        return self._gps_data.to_camera()
