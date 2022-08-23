import threading
import time

import serial
import pynmea2
import logging
from datetime import datetime, timedelta

from tools import restart_system, check_system_time


class EmptyGPSDataError(Exception):
    """ Exception raised when there is no GPS data available. """
    pass


class InvalidGPSDataError(Exception):
    """ Exception raised when the GPS data is invalid. """
    pass


class GPSReader(threading.Thread):
    def __init__(self, port, baudrate=9600, bytesize=8, timeout=1, stopbits=serial.STOPBITS_ONE):
        threading.Thread.__init__(self, daemon=True, name="GPSReader")

        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.timeout = timeout
        self.stopbits = stopbits

        self.gps_valid = False

        self.knots_to_kmh = 1.852

        self.lat = None
        self.lng = None
        self.gps_location = None
        self.gps_time = None
        self.gps_date = None
        self.spd_over_grnd = None
        self.speed_in_kmh = None
        self.local_date = None
        self.local_date_str = None

    def data_to_upload(self):
        return {"date": self.local_date.strftime("%Y-%m-%d %H:%M:%S"),
                "lat": str(self.lat),
                "lng": str(self.lng),
                "speed": str(self.speed_in_kmh)}

    def parse_gps_data(self, data):
        self.lat = data.latitude
        self.lng = data.longitude
        self.gps_location = (self.lat, self.lng)
        self.gps_date = str(data.datestamp)
        self.gps_time = str(data.timestamp)[:8]
        self.spd_over_grnd = data.spd_over_grnd
        self.speed_in_kmh = round(data.spd_over_grnd * self.knots_to_kmh, 3)
        self.local_date = datetime.strptime(self.gps_date + " " + self.gps_time,
                                            '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
        self.local_date_str = self.local_date.strftime("%Y-%m-%d %H:%M:%S")

    def get_gps_data(self):
        return GPSData(self)

    def run(self):
        while True:
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

                    while True:
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
                                        continue

                                    else:
                                        self.gps_valid = False
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
                            time.sleep(5)
                            break

                        self.gps_valid = False

            except serial.serialutil.SerialException:
                logging.error("Serial Exception:", exc_info=True)
                time.sleep(60)
                restart_system("error", "Couldn't find the GPS Device!")

            except:
                logging.error("Unexpected GPS error:", exc_info=True)
                time.sleep(60)

            self.gps_valid = False


# parse gps data as a class
class GPSData:
    def __init__(self, gps_data: GPSReader):
        self.lat = gps_data.lat
        self.lng = gps_data.lng
        self.spd_over_grnd = gps_data.spd_over_grnd
        self.speed_in_kmh = gps_data.speed_in_kmh
        self.gps_location = gps_data.gps_location
        self.local_date = gps_data.local_date
        self.local_date_str = gps_data.local_date_str
