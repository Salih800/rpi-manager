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

from constants.folders import path_to_upload
from constants.files import device_config_file

from utils.size_converter import SizeConverter


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


def write_json(json_data, json_file):
    json_file_path = os.path.split(json_file)[0]
    if not os.path.isdir(json_file_path):
        os.makedirs(json_file_path)
    if not os.path.isfile(json_file):
        data = [json_data]
    else:
        data = read_json(json_file)
        data.append(json_data)
    json.dump(data, open(json_file, "w"))


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
def restart_system(error_type, error_message) -> None:
    logging.info(f"{error_type}: {error_message}")
    logging.info("Rebooting the system!")
    time.sleep(5)
    os.system("sudo reboot")
    sys.exit(1)


# check given location between list of locations and return the closest location in meters and index
def check_location_and_speed(gps_data,
                             locations,
                             maximum_distance=50,
                             speed_limit=5,
                             on_the_move=False):
    min_distance = float("inf")
    closest_location = None

    for loc in locations:
        distance = calculate_distance(gps_data.gps_location, loc)
        if distance < min_distance:
            min_distance = distance
            closest_location = loc
    logging.info(f"Closest location: {closest_location}, distance: {min_distance}")
    if min_distance < maximum_distance:
        if on_the_move:
            if gps_data.spkm > speed_limit:
                return closest_location["id"]
        else:
            if gps_data.spkm < speed_limit:
                return closest_location["id"]


def restart_program():
    logging.info("Restarting the program...")
    exit(0)
    # os.execl(sys.executable, sys.executable, *sys.argv)


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


# check system time with gps time and if it is more than 3 seconds different, update system time
def check_system_time(gps_local_time):
    system_time = datetime.now()
    if abs(system_time - gps_local_time) > timedelta(seconds=3):
        os.system("sudo date -s '{}'".format(gps_local_time))
        logging.info(f"System time updated to {gps_local_time}")


# install repo requirements if not installed
def install_requirements():
    if subprocess.call(["pip3", "install", "-r", "requirements.txt"]) == 0:
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
            return True

    except subprocess.CalledProcessError as stderr:
        logging.warning(stderr, exc_info=True)
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
