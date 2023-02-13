import logging
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import utils.request_handler as rh

from constants.numbers import mb
from constants.others import file_upload_type
from constants.files import atiknakit_failed_uploads, atiknakit_failed_locations, uploaded_files
from constants.folders import path_to_upload, log_folder
from constants.urls import URL_LOCATION_UPLOAD, URL_IMAGE_INFO_UPLOAD, URL_CDN_UPLOAD, RPI_API_URL

from tools import write_json, get_hostname, read_json, calculate_distance, get_directory_size, get_vehicle_id


def upload_gps_data(new_gps_location, old_gps_location=None):
    if old_gps_location is not None:
        if calculate_distance(old_gps_location.gps_location, new_gps_location.gps_location) < 20:
            return
    location_upload_url = URL_LOCATION_UPLOAD + get_vehicle_id()
    logging.info(f"Uploading GPS data to server: {location_upload_url}")
    response = rh.post(url=location_upload_url, json=new_gps_location.data_to_upload())

    if response.status_code == 200:
        logging.info(f"GPS data uploaded to server successfully: {new_gps_location.data_to_upload()}")
    else:
        logging.warning(f"GPS data upload to server failed with status code {response.status_code}!")
        write_json(new_gps_location.data_to_upload(), path_to_upload + "_failed_gps_uploads.json")


def upload_image(file_path):
    file_name = os.path.basename(file_path)
    image_data = ImageInfo(file_path)
    with open(file_path, 'rb') as img:
        files = {'file': (file_name, img, 'multipart/form-data', {'Expires': '0'})}

        url_to_upload = (URL_CDN_UPLOAD + f"type={file_upload_type}"
                                          f"&date={image_data.date}"
                                          f"&time={image_data.time}")
        response = rh.post(url=url_to_upload, files=files, timeout=30)

    if response.status_code == 200:
        if response.json()["status"] == "success":
            # detection_result = GarbageModel().detect(file_path)
            detection_result = []
            detection_count = len(detection_result)

            uploaded_file = response.json()["filename"]

            file_data = {"file_name": uploaded_file,
                         "date": f"{image_data.date_and_time}",
                         "lat": image_data.lat, "lng": image_data.lng,
                         "id": image_data.garbage_id,
                         "detection": detection_count}

            my_file_data = {"vehicle_id": image_data.vehicle_id,
                            "device_type": image_data.device_type,
                            "file_id": uploaded_file,
                            "date": f"{image_data.date_and_time}",
                            "lat": image_data.lat, "lng": image_data.lng,
                            "location_id": image_data.garbage_id,
                            "detection_count": detection_count,
                            "result_list": detection_result}

            write_json(my_file_data, path_to_upload + uploaded_files)

            response = rh.post(url=URL_IMAGE_INFO_UPLOAD + image_data.vehicle_id,
                               json=file_data,
                               timeout=10)
            if not response.status_code == 200:
                logging.warning(f"Image Name couldn't uploaded! Status Code: {response.status_code}")
                write_json(file_data, path_to_upload + atiknakit_failed_uploads)

            os.remove(file_path)
        else:
            logging.warning(f"AtıkNakit Image Upload Failed! Status Code: {response.status_code}")

    else:
        logging.warning(f"CDN Image Upload Failed! Status Code: {response.status_code}")


def upload_failed_uploads(file_path):
    images_json = read_json(file_path)
    response = rh.post(url=URL_IMAGE_INFO_UPLOAD + get_vehicle_id(), json=images_json)
    if response.status_code == 200:
        logging.info(f"{file_path} uploaded.")
        os.remove(file_path)
    else:
        logging.warning(f"{file_path} upload warning: {response.status_code}")


def upload_failed_locations(file_path):
    location_json = read_json(file_path)
    response = rh.post(url=URL_LOCATION_UPLOAD + get_vehicle_id(), json=location_json, timeout=10)
    if response.status_code == 200:
        logging.info(f"{file_path} uploaded")
        os.remove(file_path)
    else:
        logging.warning(f"{file_path} upload warning: {response.status_code}")


def upload_json_to_gdrive(file_path):
    if os.path.getsize(file_path) / 1024 >= 500:
        logging.info(f"Trying to upload {file_path}")
        uploaded_files_date = datetime.now().strftime("%Y-%m-%d")
        uploaded_files_time = datetime.now().strftime("%H-%M-%S")
        uploaded_files_name = f"{uploaded_files_date}_{uploaded_files_time}_{get_hostname()}.json"
        shutil.copy(file_path, uploaded_files_name)
        rclone_call = subprocess.check_call(
            ["rclone", "move", uploaded_files_name, f"gdrive:Python/ContainerFiles/files/"])
        if os.path.isfile(uploaded_files_name):
            os.remove(uploaded_files_name)
            logging.info(f"Rclone failed with {rclone_call}")
        else:
            logging.info(f"'uploaded_files.json' uploaded to gdrive. Rclone returned: {rclone_call}")
            os.remove(file_path)


def copy_log_file_to_uploads():
    vehicle_id = get_vehicle_id()
    log_file = log_folder + vehicle_id + ".log"
    if os.path.getsize(log_file) >= mb:
        log_file_upload = f"{path_to_upload}{datetime.now().strftime('%y%m%d-%H%M%S')}_{vehicle_id}.log"
        logging.info(f"Trying to copy {log_file_upload}...")
        if not os.path.isdir(path_to_upload):
            os.makedirs(path_to_upload)
        shutil.copy(log_file, log_file_upload)
        with open(log_file, 'w'):
            pass
        logging.info(f"{log_file_upload} copied to {path_to_upload} folder.")


def upload_log_to_gdrive(file_path):
    logging.info(f"Trying to upload {file_path}")
    rclone_call = subprocess.check_call(["rclone", "move", file_path, f"gdrive:Python/ContainerFiles/logs/"])
    if os.path.isfile(file_path):
        logging.info(f"Rclone failed with {rclone_call}")
    else:
        logging.info(f"{file_path} uploaded to gdrive. Rclone returned: {rclone_call}")
        os.remove(file_path)


def upload_video(file_path):
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as video:
        files = {'file': (file_name, video, 'multipart/form-data', {'Expires': '0'})}

        date_of_file = datetime.strptime(file_name.split(",,")[0], "%Y-%m-%d__%H-%M-%S")
        file_date = date_of_file.strftime("%Y-%m-%d")
        file_time = date_of_file.strftime("%H:%M:%S")

        url_to_upload = URL_CDN_UPLOAD + f"type={file_upload_type}&date={file_date}&time={file_time}"
        response = rh.post(url=url_to_upload, files=files)

    if response.status_code == 200:
        if response.json() == "success":
            uploaded_file = response.json()["filename"]

            vehicle_id, device_type, file_date, file_location, file_id = file_name[:-4].split("_")
            file_lat, file_lng = file_location.split(",")

            file_data = {"file_name": uploaded_file, "date": f"{date_of_file}",
                         "lat": file_lat, "lng": file_lng, "id": file_id}

            my_file_data = {"device_name": vehicle_id, "device_type": device_type, "file_id": uploaded_file,
                            "date": f"{date_of_file}", "lat": file_lat, "lng": file_lng, "location_id": file_id}
            write_json(my_file_data, path_to_upload + uploaded_files)

            response = rh.post(url=URL_IMAGE_INFO_UPLOAD + vehicle_id, json=file_data)
            if not response.status_code == 200:
                logging.warning(f"Video Name couldn't uploaded! Status Code: {response.status_code}")
                write_json(file_data, path_to_upload + atiknakit_failed_uploads)

            os.remove(file_path)

        else:
            logging.warning(f"Video file couldn't uploaded! Status Code: {response.status_code}")


# def upload_files(folder_path=path_to_upload):
#     while True:
#         copy_log_file_to_uploads()
#         file_list = glob.glob(folder_path)
#         logging.info(f"{len(file_list)} files to upload.")
#         for file_path in file_list:
#             if os.path.getsize(file_path) != 0:
#                 if file_path.endswith(".jpg"):
#                     upload_image(file_path)
#
#                 elif file_path.endswith(".mp4"):
#                     upload_video(file_path)
#
#                 elif file_path.endswith(atiknakit_failed_uploads):
#                     upload_failed_uploads(file_path)
#
#                 elif file_path.endswith(atiknakit_failed_locations):
#                     upload_failed_locations(file_path)
#
#                 elif file_path.endswith(uploaded_files):
#                     upload_json_to_gdrive(file_path)
#
#             else:
#                 logging.warning(f"Image File size is too small! "
#                                 f"File: {file_path}\tSize: {os.path.getsize(file_path)}")
#                 os.remove(file_path)
#
#         time.sleep(10)


class ImageInfo:
    def __init__(self, image_path):
        self.file_data = Path(image_path).stem.split("_")
        self.vehicle_id = self.file_data[0]
        self.device_type = self.file_data[1]
        self.date_and_time = datetime.strptime(self.file_data[2], "%y%m%d-%H%M%S")
        self.date = self.date_and_time.strftime("%Y-%m-%d")
        self.time = self.date_and_time.strftime("%H:%M:%S")
        self.lat, self.lng = self.file_data[3].split(",")
        self.speed = float(self.file_data[4].strip("kmh"))
        self.garbage_id = self.file_data[5]

    def to_dict(self):
        return {
            "garbage_id": self.garbage_id,
            "lat": self.lat,
            "lng": self.lng,
            "time": self.time,
            "date": self.date,
            "vehicle_id": self.vehicle_id
        }


def upload_image_to_api(file_path):
    file_name = os.path.basename(file_path)
    file = {"file": (file_name, open(file_path, "rb").read())}
    response = rh.post(RPI_API_URL + "upload", files=file, timeout=10)
    if response.status_code == 200:
        os.remove(file_path)
        return True
    else:
        logging.warning(f"Image file couldn't uploaded! Status Code: {response.status_code}: {response.text}")
        time.sleep(10)
        return False


def upload_log_to_api(file_path):
    file_name = os.path.basename(file_path)
    file = {"file": (file_name, open(file_path, "rb").read())}
    response = rh.post(RPI_API_URL + "upload", files=file, timeout=30)
    if response.status_code == 200:
        os.remove(file_path)
        return True
    else:
        logging.warning(f"Log file couldn't uploaded! Status Code: {response.status_code}: {response.text}")
        time.sleep(10)
        return False


class FileUploader(threading.Thread):
    def __init__(self, folder_path=path_to_upload):
        threading.Thread.__init__(self, daemon=True, name="FileUploader")
        self.folder_path = folder_path

        self.running = False
        self.start()

    def run(self):
        self.running = True
        logging.info(f"Starting File Uploader...")

        while self.running:
            copy_log_file_to_uploads()

            if rh.check_connection():

                file_list = list(Path(self.folder_path).glob("*"))
                if len(file_list) > 1:
                    logging.info(f"{len(file_list)} files to upload. "
                                 f"Total size: {get_directory_size(self.folder_path)}")
                for file_path in file_list:
                    if os.path.getsize(file_path) != 0:

                        if rh.check_connection():

                            if file_path.suffix == ".jpg":
                                upload_image_to_api(file_path)

                            elif file_path.suffix == ".log":
                                upload_log_to_api(file_path)

                            # elif file_path.suffix == ".mp4":
                            #     upload_video(file_path)
                            #
                            # elif file_path.name.endswith(atiknakit_failed_uploads):
                            #     upload_failed_uploads(file_path)

                            elif file_path.name.endswith(atiknakit_failed_locations):
                                upload_failed_locations(file_path)

                            # elif file_path.endswith(uploaded_files):
                            #     upload_json_to_gdrive(file_path)

                        else:
                            logging.warning("No Internet Connection!")
                            break

                    else:
                        logging.warning(
                            f"Image File size is too small! File: {file_path}\tSize: {os.path.getsize(file_path)}")
                        os.remove(file_path)

            time.sleep(60)

    def stop(self):
        self.running = False
        logging.info("Stopping File Uploader...")
