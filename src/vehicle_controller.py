import logging
import threading
import time

from src.camera_manager import CameraManager
from src.device_config import DeviceConfig
from src.gps_reader import GPSReader
from src.server_listener import Listener
from tools import check_location_and_speed
from utils.file_uploader import upload_gps_data
from utils.garbage_list_getter import read_garbage_list


class VehicleController(threading.Thread, DeviceConfig):
    def __init__(self, is_enough_space):
        threading.Thread.__init__(self, daemon=True, name="VehicleController")
        DeviceConfig.__init__(self)

        self.camera_manager = CameraManager(camera_port=self.camera_port,
                                            camera_rotation=self.camera_rotation,
                                            width=self.camera_width,
                                            height=self.camera_height,
                                            fourcc=self.camera_fourcc)

        self.running = False

        self.server_listener = Listener(streaming_width=self.streaming_width)
        # self.file_uploader = FileUploader()
        self.gps_reader = GPSReader(port=self.gps_port)

        self.is_enough_space = is_enough_space

        self.garbage_list = read_garbage_list()
        self.start()

    def run(self) -> None:
        self.running = True
        old_gps_data = None
        logging.info("Starting Vehicle Controller...")
        logging.info(f"{self}")

        while self.running:
            if not self.server_listener.is_alive():
                self.server_listener = Listener(streaming_width=self.streaming_width)

            # if not self.file_uploader.is_alive():
            #     self.file_uploader = FileUploader()
            #     self.file_uploader.start()

            if not self.gps_reader.is_alive():
                self.gps_reader = GPSReader(port=self.gps_port)
                print(self.gps_reader, self.gps_port)
                self.gps_reader.start()
                time.sleep(1)

            if self.is_enough_space():
                if self.gps_reader.gps_valid:
                    gps_data = self.gps_reader.get_gps_data()

                    threading.Thread(target=upload_gps_data,
                                     daemon=True, name="gps-uploader",
                                     args=(gps_data, old_gps_data)).start()
                    old_gps_data = gps_data

                    if self.device_type in ["garbage", "garbage-caca"]:
                        detected_location_id = check_location_and_speed(gps_data=gps_data,
                                                                        locations=self.garbage_list,
                                                                        speed_limit=self.speed_limit,
                                                                        on_the_move=False,
                                                                        maximum_distance=self.maximum_garbage_distance)

                        if detected_location_id is not None:
                            filename = (f"{self.vehicle_id}_"
                                        f"{self.device_type}_"
                                        f"{gps_data.local_date_str}_"
                                        f"{gps_data.lat},{gps_data.lng}_"
                                        f"{gps_data.speed_in_kmh}kmh_"
                                        f"{detected_location_id}.jpg")

                            self.camera_manager.start_picture_save(photo_name=filename,
                                                                   location_id=detected_location_id)

                    elif self.device_type == "cavus":
                        detected_location_id = check_location_and_speed(gps_data=gps_data,
                                                                        locations=self.garbage_list,
                                                                        speed_limit=self.speed_limit,
                                                                        on_the_move=True,
                                                                        maximum_distance=self.maximum_garbage_distance)
                        if detected_location_id is not None:
                            filename = (f"{self.vehicle_id}_"
                                        f"{gps_data.local_date_str}_"
                                        f"{gps_data.lat},{gps_data.lng}_"
                                        f"{detected_location_id}.mp4")

                            if not self.camera_manager.taking_video:
                                self.camera_manager.start_video_save(video_name=filename)
                        else:
                            self.camera_manager.taking_video = False

                    else:
                        logging.error("Unknown device type {}".format(self.device_type))
                        raise Exception("Unknown device type {}".format(self.device_type))

            time.sleep(1)

    def stop(self) -> None:
        logging.info("Stopping Vehicle Controller...")
        self.running = False
        self.camera_manager.release()
        self.server_listener.stop()
        # self.file_uploader.stop()
        self.gps_reader.stop()
