import logging
import time
import threading
from datetime import datetime, timedelta
import subprocess as sp

from src.singleton import Singleton


class EmptyGPSDataError(Exception):
    """ Exception raised when there is no GPS data available. """
    pass


class InvalidGPSDataError(Exception):
    """ Exception raised when the GPS data is invalid. """
    pass


class GPSReader(threading.Thread, metaclass=Singleton):
    def __init__(self):
        threading.Thread.__init__(self, daemon=True, name="GPSReader")

        self.running = False

        self.gps_valid = False

        self.knots_to_kmh = 1.852

        self.lat = None
        self.lat_dir = None
        self.lng = None
        self.lng_dir = None
        self.gps_location = None
        self.direction = None
        self.gps_time = None
        self.gps_date = None
        self.spd_over_grnd = None
        self.speed_in_kmh = None
        self.local_date = None
        self.local_date_str = None

        self.start()

    # def get_serial_data(self):
    #     return self.serial.readlines()[-1].decode()

    def data_to_upload(self):
        return {"date": self.local_date.strftime("%Y-%m-%d %H:%M:%S"),
                "lat": str(self.lat),
                "lng": str(self.lng),
                "speed": str(self.speed_in_kmh)}

    def parse_gps_data(self, data):
        self.lat = data.latitude
        self.lat_dir = data.lat_dir
        self.lng = data.longitude
        self.lng_dir = data.lon_dir
        self.gps_location = (self.lat, self.lng)
        self.direction = "None" if data.true_course is None else data.true_course
        self.gps_date = data.datestamp.strftime("%Y-%m-%d")
        self.gps_time = data.timestamp.strftime("%H:%M:%S")
        self.spd_over_grnd = data.spd_over_grnd
        self.speed_in_kmh = round(data.spd_over_grnd * self.knots_to_kmh, 1)
        self.local_date = datetime.strptime(self.gps_date + " " + self.gps_time,
                                            '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
        self.local_date_str = self.local_date.strftime("%y%m%d-%H%M%S")

    # def __str__(self):
    #     return f"GPS Reader: {self.port}"

    def get_gps_data(self):
        return GPSData(self)

    def get_drawable_gps_data(self):
        if self.gps_valid:
            return (f"{round(self.lat, 6)}{self.lat_dir},{round(self.lng, 6)}{self.lng_dir},"
                    f"{str(int(self.direction)).zfill(3)},"
                    f"{str(int(self.speed_in_kmh)).zfill(3)}kmh")
        else:
            return None

    def run(self):
        self.running = True
        logging.info(f"Starting {self}...")

        while self.running:
            # self.read_gps_data()
            time.sleep(1)

    def read_gps_data(self):
        proc = sp.Popen(["gnss.connection", "execute", "gnss_location"], stdout=sp.PIPE, stderr=sp.PIPE)  # shell=True
        stdout, stderr = proc.communicate()
        if stderr:
            logging.error(stderr.decode("utf-8", "ignore"))
            self.gps_valid = False
            raise EmptyGPSDataError
        else:
            gps_data = stdout.decode("utf-8", "ignore").split(",")
            if len(gps_data) != 8:
                logging.error(f"Invalid GPS data: {gps_data}")
                self.gps_valid = False
                raise InvalidGPSDataError
            else:
                self.gps_valid = True
                logging.info(f"GPS data: {gps_data}")
                # self.parse_gps_data(data=gps_data)

    def stop(self):
        self.running = False
        logging.info("Stopping GPS Reader...")
        time.sleep(1)


# parse gps data as a class
class GPSData:
    def __init__(self, gps_data):
        self.lat = gps_data.lat
        self.lat_dir = gps_data.lat_dir
        self.lng = gps_data.lng
        self.lng_dir = gps_data.lng_dir
        self.direction = gps_data.direction
        self.spd_over_grnd = gps_data.spd_over_grnd
        self.speed_in_kmh = gps_data.speed_in_kmh
        self.gps_location = gps_data.gps_location
        self.local_date = gps_data.local_date
        self.local_date_str = gps_data.local_date_str
