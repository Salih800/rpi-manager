import os
import json
import logging
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

from constants.folders import path_to_upload
from constants.files import device_config_file


def read_json(json_file):
    try:
        data = json.load(open(json_file, "r"))
        return data

    except json.decoder.JSONDecodeError as json_error:
        logging.warning(f"JSONDecodeError happened at {json_file}: {json_error.pos}. Trying to save the file...")
        if json_error.pos == 0:
            data = []
        else:
            data = json.loads(open(json_file).read()[:json_error.pos])
        logging.info(f"{len(data)} file info saved.")
        return data

    except:
        logging.error(f"Error happened while reading {json_file}", exc_info=True)


def write_json(json_data, json_file):
    json_file_path = os.path.split(json_file)[0]
    if not os.path.isdir(json_file_path):
        os.makedirs(json_file_path)
    try:
        if not os.path.isfile(json_file):
            data = [json_data]
        else:
            data = read_json(json_file)
            data.append(json_data)
        json.dump(data, open(json_file, "w"))

    except:
        logging.error(f"Error happened while writing {json_file}", exc_info=True)


def get_hostname():
    import socket
    return socket.gethostname()


def get_device_config():
    device_configs = json.load(open(device_config_file))
    return device_configs[get_hostname()]


# calculate distance between two gps locations in meters
def calculate_distance(location1, location2):
    import math
    lat1, lon1 = location1["lat"], location1["lng"]
    lat2, lon2 = location2["lat"], location2["lng"]
    radius = 6371e3
    phi1 = lat1 * math.pi / 180
    phi2 = lat2 * math.pi / 180
    delta_phi = (lat2 - lat1) * math.pi / 180
    delta_lambda = (lon2 - lon1) * math.pi / 180
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


# reboot system if error happened
def restart_system(error_type, error_msg):
    logging.error(f"{error_type}: {error_msg}")
    logging.error("Rebooting the system!")
    time.sleep(5)
    os.system("sudo reboot")
    sys.exit(1)


# check given location between list of locations and return the closest location in meters and index
def check_location_and_speed(gps_data, locations, maximum_distance=50, speed_limit=5, on_the_move=False):
    min_distance = float("inf")
    closest_location = None

    for loc in locations:
        distance = calculate_distance(gps_data.gps_location, loc)
        if distance < min_distance:
            min_distance = distance
            closest_location = loc
    if maximum_distance > min_distance:
        if on_the_move:
            if gps_data.speed_in_kmh > speed_limit:
                return closest_location["id"]
        else:
            if gps_data.speed_in_kmh < speed_limit:
                return closest_location["id"]


def restart_program():
    logging.info("Restarting the program...")
    os.execl(sys.executable, sys.executable, *sys.argv)


# check given file is bigger than given size in kb
def check_file_size(file_path, size):
    if os.path.isfile(file_path):
        if os.path.getsize(file_path) <= size:
            logging.warning(f"File size is less than 10kb. Removing file: {file_path}")
            os.remove(file_path)
            return False
        else:
            if not os.path.isdir(path_to_upload):
                os.makedirs(path_to_upload)
            shutil.move(file_path, path_to_upload)
        return True
    else:
        logging.warning(f"{file_path} is not a file.")
        return False


# return a list of running threads
def get_running_threads():
    return [t.name for t in threading.enumerate()]


# check system time with gps time and if it is more than 3 minutes different, update system time
def check_system_time(gps_local_time):
    system_time = datetime.now()
    if abs(system_time - gps_local_time) > timedelta(minutes=1):
        os.system("sudo date -s '{}'".format(gps_local_time))
        logging.info(f"System time updated to {gps_local_time}")


# install repo requirements if not installed
def install_requirements():
    if subprocess.call(["pip", "install", "-r", "requirements.txt"]) == 0:
        logging.info("Requirements installed.")
        return True
    else:
        logging.error("Requirements installation failed.")
        return False


def update_repo():
    logging.info("Trying to update repo...")
    try:
        stdout = subprocess.check_output("git pull").decode()
        if stdout.startswith("Already"):
            logging.info("Repo is already up to date.")
            return False
        else:
            logging.info("Repo is updated.")
            install_requirements()
            return True

    except subprocess.CalledProcessError as stderr:
        logging.warning(stderr, exc_info=True)
