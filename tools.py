import os
import json
import logging
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
import cv2

from constants.folders import PATH_TO_UPLOAD
from constants.files import device_config_file

from utils.size_converter import SizeConverter


def read_json(json_file):
    try:
        if not os.path.isfile(json_file):
            return []
        if os.path.getsize(json_file) == 0:
            return []
        else:
            return json.load(open(json_file, "r"))
    except json.decoder.JSONDecodeError as json_error:
        logging.error(f"JSONDecodeError happened at {json_file}: {json_error.pos}. "
                      f"Trying to backup the file...", exc_info=True)
        backup_file = json_file.replace(".json", "_backup.json")
        shutil.move(json_file, backup_file)
        logging.info(f"Backup file created: {backup_file}")
        return []


def write_json(json_data, json_file):
    try:
        json_file_path = os.path.split(json_file)[0]
        os.makedirs(json_file_path, exist_ok=True)
        data = read_json(json_file)
        if json_data not in data:
            data.append(json_data)
        else:
            logging.warning(f"JSON data already exists in {json_file} file: {json_data}")
            return
        json.dump(data, open(json_file, "w"))
    except:
        logging.exception(f"Error happened while writing to '{json_file}' file.")


def get_hostname() -> str:
    import socket
    return socket.gethostname()


def get_vehicle_id() -> str:
    return get_device_config()["vehicle_id"]


def get_device_config(hostname=get_hostname()):
    device_configs = json.load(open(device_config_file))
    try:
        return device_configs[hostname]
    except KeyError:
        logging.error(f"Device config for {get_hostname()} not found in {device_config_file}.")
        return device_configs["default"]
    # raise KeyError("Device config not found.")


# calculate distance between two gps locations in meters
def calculate_distance(location1, location2) -> float:
    import math
    lat1, lon1 = float(location1["lat"]), float(location1["lng"])
    lat2, lon2 = float(location2["lat"]), float(location2["lng"])
    radius = 6371e3
    phi1 = lat1 * math.pi / 180
    phi2 = lat2 * math.pi / 180
    delta_phi = (lat2 - lat1) * math.pi / 180
    delta_lambda = (lon2 - lon1) * math.pi / 180
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


# reboot system if error happened
def restart_system(error_type, error_message) -> None:
    logging.info(f"{error_type}: {error_message}")
    logging.info("Rebooting the system!")
    time.sleep(5)
    os.system("sudo reboot")
    sys.exit(1)


# check given location between list of locations and return the closest location in meters and index
def check_locations(gps_data, locations):
    min_distance = float("inf")
    closest_location = None

    for loc in locations:
        distance = calculate_distance(gps_data.gps_location, loc)
        if distance < min_distance:
            min_distance = distance
            closest_location = loc

    return min_distance, closest_location["id"]


def restart_service():
    logging.info("Restarting the service...")
    os.system("sudo systemctl restart rpi-manager.service")


# check given file is bigger than given size in kb
def check_file_size(file_path, size):
    if os.path.isfile(file_path):
        if os.path.getsize(file_path) <= size:
            logging.warning(f"File size is less than 10kb. Removing file: {file_path}")
            os.remove(file_path)
            return False
        else:
            os.makedirs(PATH_TO_UPLOAD, exist_ok=True)
            shutil.move(file_path, PATH_TO_UPLOAD + os.path.basename(file_path))
        return True
    else:
        logging.warning(f"{file_path} is not a file.")
        return False


# return a list of running threads
def get_running_threads():
    return [t.name for t in threading.enumerate()]


# check system time with gps time and if it is more than 3 seconds different, update system time
def check_system_time(gps_local_time):
    system_time = datetime.now()
    if abs(system_time - gps_local_time) > timedelta(seconds=3):
        os.system("sudo date -s '{}'".format(gps_local_time))
        logging.info(f"System time updated to {gps_local_time}")


# install repo requirements if not installed
def install_requirements():
    if subprocess.call(["pip3", "install", "-qr", "requirements.txt"]) == 0:
        logging.info("Requirements installed.")
        return True
    else:
        logging.error("Requirements installation failed.")
        return False


def update_repo():
    # logging.info("Trying to update repo...")
    try:
        stdout = subprocess.check_output(["git", "pull"]).decode()
        if stdout.startswith("Already"):
            logging.info("Repo is already up to date.")
            return False
        else:
            logging.info("Repo is updated.")
            install_requirements()
            restart_service()
            return True

    except subprocess.CalledProcessError as stderr:
        logging.warning(stderr)
        return False


def get_directory_size(directory):
    """Returns the `directory` size in bytes."""
    total = SizeConverter(0)
    try:
        # print("[+] Getting the size of", directory)
        for entry in os.scandir(directory):
            if entry.is_file():
                # if it's a file, use stat() function
                total.bytes += entry.stat().st_size
            elif entry.is_dir():
                # if it's a directory, recursively call this function
                try:
                    total.bytes += get_directory_size(entry.path).bytes
                    # print("[+] {} size: {}".format(entry.path, total))
                except FileNotFoundError:
                    pass
    except NotADirectoryError:
        # if `directory` isn't a directory, get the file size then
        return os.path.getsize(directory)
    except PermissionError:
        # if for whatever reason we can't open the folder, return 0
        return 0
    return total


def draw_text(img,
              text,
              pos=(0, 0),
              text_color=(255, 255, 255),
              text_size=2.0,
              text_thickness=1,
              text_bg_color=(0, 0, 0)
              ):
    font = cv2.FONT_HERSHEY_SIMPLEX
    x, y = pos
    (w, h), b = cv2.getTextSize(text, font, text_size, text_thickness)
    cv2.rectangle(img, (x, y), (x + w, y - h - b), text_bg_color, -1)
    cv2.putText(img, text, (x, y - 5), font, text_size, text_color, text_thickness)


def decode_fourcc(fourcc):
    return ''.join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)])


def send_system_command(command):
    try:
        logging.info(f"Sending command: {command}")
        os.system(command)
    except Exception as e:
        logging.error(e, exc_info=True)
        time.sleep(5)
