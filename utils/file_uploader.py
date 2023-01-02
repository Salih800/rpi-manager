import glob
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime

from src.request_handler import RequestApi
from src.Yolov5Model import Yolov5Model
from tools import write_json, get_hostname, read_json, calculate_distance

from constants.others import file_upload_type
from constants.files import atiknakit_failed_uploads, atiknakit_failed_locations, uploaded_files
from constants.folders import path_to_upload, log_folder
from constants.urls import url_location_upload, url_image_info_upload, url_cdn_upload


def upload_gps_data(new_gps_location, old_gps_location=None):
    if old_gps_location is not None:
        if calculate_distance(old_gps_location.gps_location, new_gps_location.gps_location) > 20:
            logging.info(f"GPS data is more than 20 meters different from old gps data, uploading to server!")
            response = RequestApi.post(url=url_location_upload + get_hostname(), json=new_gps_location.data_to_upload())
        else:
            return
    else:
        response = RequestApi.post(url=url_location_upload + get_hostname(), json=new_gps_location.data_to_upload())

    if response.status_code == 200:
        logging.info(f"GPS data uploaded to server successfully!")
    else:
        logging.warning(f"GPS data upload to server failed with status code {response.status_code}!")
        write_json(new_gps_location.data_to_upload(), path_to_upload + "_failed_gps_uploads.json")


def upload_image(file_path):
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as img:
        files = {'file': (file_name, img, 'multipart/form-data', {'Expires': '0'})}

        date_of_file = datetime.strptime(file_name.split("_")[1], "%y%m%d-%H%M%S")
        file_date = date_of_file.strftime("%Y-%m-%d")
        file_time = date_of_file.strftime("%H:%M:%S")

        url_to_upload = url_cdn_upload + f"type={file_upload_type}&date={file_date}&time={file_time}"
        response = RequestApi.post(url=url_to_upload, files=files, timeout=30)

    if response.status_code == 200:
        if response.json()["status"] == "success":
            model = Yolov5Model()
            detection_result = model.detect(file_path)
            detection_count = len(detection_result)

            uploaded_file = response.json()["filename"]

            hostname, device_type, file_date, file_location, file_id = file_name[:-4].split("_")
            file_lat, file_lng = file_location.split(",")

            file_data = {"file_name": uploaded_file, "date": f"{date_of_file}", "lat": file_lat,
                         "lng": file_lng, "id": file_id, "detection": detection_count}

            my_file_data = {"device_name": hostname, "device_type": device_type,
                            "file_id": uploaded_file,
                            "date": f"{date_of_file}", "lat": file_lat, "lng": file_lng,
                            "location_id": file_id,
                            "detection_count": detection_count, "result_list": detection_result}

            write_json(my_file_data, path_to_upload + uploaded_files)

            response = RequestApi.post(url=url_image_info_upload + hostname, json=file_data, timeout=10)
            if not response.status_code == 200:
                logging.warning(f"Image Name couldn't uploaded! Status Code: {response.status_code}")
                write_json(file_data, path_to_upload + atiknakit_failed_uploads)

            os.remove(file_path)
        else:
            logging.warning(f"Image file couldn't uploaded! Status Code: {response.status_code}: {response.json()}")

    else:
        logging.warning(f"Image file couldn't uploaded! Status Code: {response.status_code}")


def upload_failed_uploads(file_path):
    images_json = read_json(file_path)
    response = RequestApi.post(url=url_image_info_upload + get_hostname(), json=images_json)
    if response.status_code == 200:
        logging.info(f"{file_path} uploaded.")
        os.remove(file_path)
    else:
        logging.warning(f"{file_path} upload warning: {response.status_code}")


def upload_failed_locations(file_path):
    location_json = read_json(file_path)
    response = RequestApi.post(url=url_location_upload + get_hostname(), json=location_json)
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
    log_file = log_folder + get_hostname() + ".log"
    if os.path.getsize(log_file) / (1024 * 1024) >= 1:
        log_file_upload = f"{path_to_upload}{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{get_hostname()}.log"
        logging.info(f"Trying to copy {log_file_upload}...")
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

        url_to_upload = url_cdn_upload + f"type={file_upload_type}&date={file_date}&time={file_time}"
        response = RequestApi.post(url=url_to_upload, files=files)

    if response.status_code == 200:
        if response.json() == "success":
            uploaded_file = response.json()["filename"]

            hostname, device_type, file_date, file_location, file_id = file_name[:-4].split("_")
            file_lat, file_lng = file_location.split(",")

            file_data = {"file_name": uploaded_file, "date": f"{date_of_file}",
                         "lat": file_lat, "lng": file_lng, "id": file_id}

            my_file_data = {"device_name": hostname, "device_type": device_type, "file_id": uploaded_file,
                            "date": f"{date_of_file}", "lat": file_lat, "lng": file_lng, "location_id": file_id}
            write_json(my_file_data, path_to_upload + uploaded_files)

            response = RequestApi.post(url=url_image_info_upload + hostname, json=file_data)
            if not response.status_code == 200:
                logging.warning(f"Video Name couldn't uploaded! Status Code: {response.status_code}")
                write_json(file_data, path_to_upload + atiknakit_failed_uploads)

            os.remove(file_path)

        else:
            logging.warning(f"Video file couldn't uploaded! Status Code: {response.status_code}")


def upload_files(folder_path=path_to_upload):
    while True:
        copy_log_file_to_uploads()
        file_list = glob.glob(folder_path)
        logging.info(f"{len(file_list)} files to upload.")
        for file_path in file_list:
            if os.path.getsize(file_path) != 0:
                if file_path.endswith(".jpg"):
                    upload_image(file_path)

                elif file_path.endswith(".mp4"):
                    upload_video(file_path)

                elif file_path.endswith(atiknakit_failed_uploads):
                    upload_failed_uploads(file_path)

                elif file_path.endswith(atiknakit_failed_locations):
                    upload_failed_locations(file_path)

                elif file_path.endswith(uploaded_files):
                    upload_json_to_gdrive(file_path)

            else:
                logging.warning(f"Image File size is too small! File: {file_path}\tSize: {os.path.getsize(file_path)}")
                os.remove(file_path)

        time.sleep(10)