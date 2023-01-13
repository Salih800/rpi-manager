import logging
from threading import Thread
from utils.serial_connection import SerialConnection
from utils.gps_data import GPSData
from constants.gps_commands import *


class GPSNotPoweredUpError(Exception):
    """ Exception raised when the GPS is not powered up. """
    pass


class GPSReader(SerialConnection, Thread):
    def __init__(self, port, baudrate, timeout):
        Thread.__init__(self, daemon=True, name="Client")
        SerialConnection.__init__(self, port, baudrate, timeout)

        self._gps_data = GPSData(GPS_DATA + NO_FIX_DATA)

        self.running = True
        self.start()

    def run(self):
        logging.info("Starting GPS Reader...")
        self.send_command(POWER_UP)
        if self.read_data(startswith=OK):
            while self.running:
                self.send_command(GET_GPS_DATA)
                self._gps_data = GPSData(self.read_data(startswith=GPS_DATA))
        else:
            raise GPSNotPoweredUpError()

    def stop(self):
        self.running = False
        self._serial.close()

    def get_gps_data(self):
        return self._gps_data

    def get_drawable_gps_data(self):
        return self._gps_data.to_camera()
