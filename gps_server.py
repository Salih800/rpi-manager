from datetime import datetime, timezone

from utils.serial_connection import SerialConnection
from threading import Thread
from constants.gps_commands import *
from utils.gps_data import dd2ddm


class Server(SerialConnection, Thread):
    def __init__(self, port, baudrate, timeout):
        Thread.__init__(self, daemon=True, name="Server")
        SerialConnection.__init__(self, port, baudrate, timeout)

        self.running = True
        self.start()

    def run(self):
        while self.running:
            data = self.read_data()
            print(f"{datetime.now().strftime('%H:%M:%S')}: {data.encode()}")
            if not data:
                self.close()
            elif data.startswith(AT):
                self.send_command(OK)
            elif data.startswith(POWER_UP):
                self.send_command(OK)
            elif data.startswith(GET_GPS_DATA):
                gps_location = "40.78843793216758,29.44000664126109".split(",")
                lat, lng = map(dd2ddm, gps_location)
                local_time = datetime.utcnow().strftime("%H%M%S.%f")
                local_date = datetime.now().strftime("%d%m%y")
                fix_data = MANUEL_FIX_DATA.format(local_time, lat, lng, local_date)
                self.send_command(GPS_DATA + fix_data)
                self.send_command(LINE)
                self.send_command(OK)


if __name__ == '__main__':
    server = Server(port="/dev/pts/3", baudrate=115200, timeout=5)
    server.join()
