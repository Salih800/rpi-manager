from datetime import datetime

from utils.serial_connection import SerialConnection
from threading import Thread
from constants.gps_commands import *


# convert decimal degrees to degrees, minutes and seconds
def dd2dms(dd):
    dd = float(dd)
    mnt, sec = divmod(dd * 3600, 60)
    deg, mnt = divmod(mnt, 60)
    return round(deg * 100 + mnt + sec / 100, 4)


class Server(SerialConnection, Thread):
    def __init__(self, port, baudrate, timeout):
        Thread.__init__(self, daemon=True, name="Server")
        SerialConnection.__init__(self, port, baudrate, timeout)

        self.running = True
        self.start()

    def run(self):
        while self.running:
            data = self.read_data(startswith="")
            print(f"Server: {data}")
            if data.startswith(POWER_UP):
                self.send_command(OK)
            elif data.startswith(GET_GPS_DATA):
                gps_location = "41.082763305556,28.785443305556".split(",")
                lat, lng = map(dd2dms, gps_location)
                local_time = datetime.now().strftime("%H%M%S.%f")
                local_date = datetime.now().strftime("%d%m%y")
                fix_data = MANUEL_FIX_DATA.format(local_time, lat, lng, local_date)
                self.send_command(GPS_DATA + fix_data)
                self.send_command(LINE)
                self.send_command(OK)
            else:
                print(f"Server: Unknown command: {data}")


if __name__ == '__main__':
    server = Server(port="/dev/pts/4", baudrate=115200, timeout=5)
    server.join()
