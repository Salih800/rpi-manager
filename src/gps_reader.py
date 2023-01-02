import threading
import time

import serial
import pynmea2
import logging
from datetime import datetime, timedelta

from src.singleton import Singleton
from tools import restart_system, check_system_time


class EmptyGPSDataError(Exception):
    """ Exception raised when there is no GPS data available. """
    pass


class InvalidGPSDataError(Exception):
    """ Exception raised when the GPS data is invalid. """
    pass


class GPSReader(threading.Thread, metaclass=Singleton):
    def __init__(self, port, baudrate=9600, bytesize=8, timeout=1, stopbits=serial.STOPBITS_ONE):
        threading.Thread.__init__(self, daemon=True, name="GPSReader")

        self.running = False

        self.serial = serial.Serial(port=port, baudrate=baudrate, bytesize=bytesize, timeout=timeout, stopbits=stopbits)

        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.timeout = timeout
        self.stopbits = stopbits

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

    def get_serial_data(self):
        return self.serial.readlines()[-1].decode()

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
        self.speed_in_kmh = round(data.spd_over_grnd * self.knots_to_kmh, 3)
        self.local_date = datetime.strptime(self.gps_date + " " + self.gps_time,
                                            '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
        self.local_date_str = self.local_date.strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        return f"GPS Reader: {self.port}"

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
            try:
                with serial.Serial(port=self.port,
                                   baudrate=self.baudrate,
                                   bytesize=self.bytesize,
                                   timeout=self.timeout,
                                   stopbits=self.stopbits) as serial_port:

                    parse_error_count = 0
                    invalid_gps_count = 0
                    empty_gps_count = 0

                    max_error_count = 100

                    while self.running:
                        try:
                            gps_data = serial_port.readline().decode('utf-8', errors='replace')

                            if len(gps_data) < 1:
                                raise EmptyGPSDataError("No GPS data available!")

                            for msg in pynmea2.NMEAStreamReader().next(gps_data):
                                parsed_data = pynmea2.parse(str(msg))

                                if parsed_data.sentence_type == "RMC":

                                    if parsed_data.status == "A":
                                        self.gps_valid = True
                                        self.parse_gps_data(parsed_data)
                                        check_system_time(self.local_date)

                                        parse_error_count = 0
                                        invalid_gps_count = 0
                                        empty_gps_count = 0

                                        continue

                                    else:
                                        raise InvalidGPSDataError("GPS data is invalid!")

                        except pynmea2.nmea.ParseError:
                            parse_error_count += 1
                            if parse_error_count >= max_error_count:
                                logging.warning(f"Parse Error happened {parse_error_count} times!")
                                break

                        except InvalidGPSDataError:
                            invalid_gps_count += 1
                            if invalid_gps_count >= max_error_count:
                                logging.warning(f"Invalid GPS data happened {invalid_gps_count} times!")
                                break

                        except EmptyGPSDataError:
                            empty_gps_count += 1
                            if empty_gps_count >= max_error_count:
                                logging.warning(f"Empty GPS data happened {empty_gps_count} times!")
                                break

                        except:
                            logging.error("Unexpected GPS Parse error:", exc_info=True)
                            time.sleep(60)
                            break

                        self.gps_valid = False

            except serial.serialutil.SerialException:
                logging.error("Serial Exception:", exc_info=True)
                time.sleep(60)
                restart_system(error_type="GPS error", error_message="Couldn't find the GPS Device!")

            except:
                logging.error("Unexpected GPS error:", exc_info=True)
                time.sleep(60)

            self.gps_valid = False

    def stop(self):
        self.running = False
        logging.info("Stopping GPS Reader...")
        time.sleep(1)


# parse gps data as a class
class GPSData:
    def __init__(self, gps_data: GPSReader):
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
