import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import utils.request_handler as rh

from constants.others import file_upload_type
from constants.files import atiknakit_failed_uploads, uploaded_files, FAILED_GPS_UPLOADS
from constants.folders import PATH_TO_UPLOAD
from constants.urls import (URL_LOCATION_UPLOAD, URL_IMAGE_INFO_UPLOAD,
                            URL_CDN_UPLOAD, IMAGE_PROCESSING_API_CACA_GARBAGE_URL, IMAGE_PROCESSING_API_GARBAGE_URL)

from tools import write_json, get_hostname, read_json, get_directory_size


def upload_failed_locations(file_path):
    location_json = read_json(file_path)
    response = rh.post(url=URL_LOCATION_UPLOAD + get_hostname(), json=location_json, timeout=10)
    if response.status_code == 200:
        logging.info(f"{file_path} uploaded")
        os.remove(file_path)
    else:
        logging.warning(f"{file_path} upload warning: {response.status_code}")


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
            write_json(my_file_data, PATH_TO_UPLOAD + uploaded_files)

            response = rh.post(url=URL_IMAGE_INFO_UPLOAD + vehicle_id, json=file_data)
            if not response.status_code == 200:
                logging.warning(f"Video Name couldn't uploaded! Status Code: {response.status_code}")
                write_json(file_data, PATH_TO_UPLOAD + atiknakit_failed_uploads)

            os.remove(file_path)

        else:
            logging.warning(f"Video file couldn't uploaded! Status Code: {response.status_code}")


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
            "location_id": self.garbage_id,
            "lat": self.lat,
            "lng": self.lng,
            "date": self.date_and_time.strftime("%Y-%m-%d %H:%M:%S"),
            "uploader_id": get_hostname(),
            "upload_type": "garbagedevice",
        }


def upload_image_to_api(file_path):
    file_name = os.path.basename(file_path)
    file = {"image": (file_name, open(file_path, "rb").read())}
    file_data = ImageInfo(file_path)
    if file_data.device_type == "garbage":
        response = rh.post(
            IMAGE_PROCESSING_API_GARBAGE_URL,
            files=file,
            params=file_data.to_dict(),
            timeout=10,
        )
    elif file_data.device_type == "caca-garbage":
        response = rh.post(
            IMAGE_PROCESSING_API_CACA_GARBAGE_URL,
            files=file,
            params=file_data.to_dict(),
            timeout=10,
        )
    else:
        logging.warning(f"Unknown device type: {file_data.device_type}")
        return False
    if response.status_code == 200:
        os.remove(file_path)
        return True
    else:
        logging.warning(f"Image file couldn't uploaded! Status Code: {response.status_code}: {response.text}")
        time.sleep(10)
        return False


class FileUploader(threading.Thread):
    def __init__(self, folder_path=PATH_TO_UPLOAD):
        threading.Thread.__init__(self, daemon=True, name="FileUploader")
        self.folder_path = folder_path

        self._running = False
        self.start()

    def run(self):
        self._running = True
        logging.info(f"Starting File Uploader...")

        while self._running:

            if rh.check_connection():

                file_list = sorted(list(Path(self.folder_path).glob("*")))
                if len(file_list) > 1:
                    logging.info(f"{len(file_list)} files to upload. "
                                 f"Total size: {get_directory_size(self.folder_path)}")
                uploaded_file_count = 0
                start_time = time.time()
                for file_path in file_list:
                    if os.path.getsize(file_path) != 0:

                        if rh.check_connection():

                            if file_path.suffix == ".jpg":
                                uploaded_file_count += 1 if upload_image_to_api(file_path) else 0

                            elif file_path.name.endswith(FAILED_GPS_UPLOADS):
                                upload_failed_locations(file_path)

                        else:
                            logging.warning("No Internet Connection!")
                            break

                    else:
                        logging.warning(
                            f"Image File size is too small! File: {file_path}\tSize: {os.path.getsize(file_path)}")
                        os.remove(file_path)
                if uploaded_file_count > 0:
                    logging.info(f"{uploaded_file_count} files uploaded in {time.time() - start_time:.2f} seconds.")
            time.sleep(60)

    def stop(self):
        self._running = False
        logging.info("Stopping File Uploader...")
