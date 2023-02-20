from threading import Thread
import time
import logging
import os

import cv2

import utils.request_handler as rh
from constants.files import FAILED_GPS_UPLOADS
from constants.urls import URL_LOCATION_UPLOAD

from utils.garbage_list_getter import read_garbage_list

from tools import check_locations, check_file_size, calculate_distance, write_json, get_hostname

from constants.numbers import MAX_PHOTO_COUNT, JPG_SAVE_QUALITY, MINIMUM_PHOTO_SIZE
from constants.folders import RECORDED_FILES, PATH_TO_UPLOAD


class Recorder(Thread):
    def __init__(self, parent):
        Thread.__init__(self, daemon=True, name="Recorder")
        self._parent = parent

        self._running = True
        self.old_gps_data = None
        self.garbage_list = read_garbage_list()
        self.last_picture_save = 0
        self.location_log_time = 0
        self.saved_frame_count = 0
        self.passed_frame_count = 0
        self.failed_frame_count = 0
        self.last_location_id = None

        self.start()

    def save_picture(self, photo_name, location_id):
        if self.last_location_id != location_id:
            self.last_location_id = location_id

            if self.saved_frame_count > 0:
                logging.info(f"Saved {self.saved_frame_count} photos. In location {self.last_location_id}")
            if self.passed_frame_count > 0:
                logging.warning(f"Passed {self.passed_frame_count} photos. In location {self.last_location_id}")
            if self.failed_frame_count > 0:
                logging.error(f"Failed {self.failed_frame_count} photos. In location {self.last_location_id}")

            self.saved_frame_count = 0
            self.passed_frame_count = 0

        if self.saved_frame_count <= MAX_PHOTO_COUNT:
            frame = self._parent.camera_manager.get_frame()
            if frame is not None:
                os.makedirs(RECORDED_FILES, exist_ok=True)
                cv2.imwrite(RECORDED_FILES + photo_name, frame, [cv2.IMWRITE_JPEG_QUALITY, JPG_SAVE_QUALITY])
                if check_file_size(RECORDED_FILES + photo_name, MINIMUM_PHOTO_SIZE):
                    self.saved_frame_count += 1
            else:
                self.failed_frame_count += 1
        else:
            if self.passed_frame_count == 0:
                logging.warning(f"Maximum photo count reached for this location! Location-id: {location_id}")
            self.passed_frame_count += 1

    def upload_gps_data(self, new_gps_location):
        if self.old_gps_data is not None:
            if calculate_distance(self.old_gps_data.gps_location, new_gps_location.gps_location) < 20:
                return
        self.old_gps_data = new_gps_location
        if not rh.check_connection():
            write_json(new_gps_location.data_to_upload(), PATH_TO_UPLOAD + FAILED_GPS_UPLOADS)
            return
        location_upload_url = URL_LOCATION_UPLOAD + get_hostname()
        # logging.info(f"Uploading GPS data to server: {location_upload_url}")
        response = rh.post(url=location_upload_url, json=new_gps_location.data_to_upload(), timeout=5)

        if response.status_code == 200:
            logging.info(f"GPS data uploaded to server successfully: {new_gps_location.data_to_upload()}")
        else:
            logging.warning(f"GPS data upload to server failed with status code {response.status_code}!")
            write_json(new_gps_location.data_to_upload(), PATH_TO_UPLOAD + FAILED_GPS_UPLOADS)

    def run(self) -> None:
        while self._running:
            gps_data = self._parent.gps_reader.get_gps_data()
            if gps_data.is_valid():
                Thread(target=self.upload_gps_data, args=(gps_data,), name="gps_upload").start()

                min_distance, closest_location_id = check_locations(
                    gps_data=gps_data,
                    locations=self.garbage_list
                )

                if time.time() - self.location_log_time > 60:
                    logging.info(f"Closest location: {closest_location_id} | "
                                 f"Distance: {int(min_distance)} meters | "
                                 f"Speed: {gps_data.spkm} km/h")
                    self.location_log_time = time.time()

                if time.time() - self.last_picture_save >= 2:
                    self.last_picture_save = time.time()
                    if (min_distance < self._parent.max_loc_dist and
                            gps_data.spkm < self._parent.speed_limit):
                        filename = (
                            f"{self._parent.vehicle_id}_"
                            f"{self._parent.device_type}_"
                            f"{gps_data.local_date_str}_"
                            f"{gps_data.lat},{gps_data.lng}_"
                            f"{gps_data.spkm}kmh_"
                            f"{closest_location_id}.jpg"
                        )

                        # self.save_picture(
                        #     photo_name=filename,
                        #     location_id=closest_location_id
                        # )
            # else:
            time.sleep(1)

    def stop(self):
        logging.info("Stopping recorder...")
        self._running = False
