from utils.serial_connection import SerialConnection
from threading import Thread
from constants.gps_commands import *


class Server(SerialConnection, Thread):
    def __init__(self, port, baudrate, timeout):
        Thread.__init__(self, daemon=True, name="Server")
        SerialConnection.__init__(self, port, baudrate, timeout)

        self.running = True
        self.start()

    def run(self):
        while self.running:
            self.read_data(startswith="")
            if self.read_data(startswith=POWER_UP):
                self.send_command(OK)
            elif self.read_data(startswith=GET_GPS_DATA):
                self.send_command(GPS_DATA + NO_FIX_DATA)
                self.send_command(LINE)
                self.send_command(OK)


if __name__ == '__main__':
    server = Server(port="/dev/pts/3", baudrate=115200, timeout=5)
    server.join()
