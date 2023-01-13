import logging
import threading
import time

from src.camera_manager import CameraManager
from utils.device_config import DeviceConfig
from src.gps_manager import GPSReader
# from src.server_listener import Listener
from tools import check_location_and_speed
from utils.file_uploader import upload_gps_data
from utils.garbage_list_getter import read_garbage_list


class VehicleController(threading.Thread, DeviceConfig):
    def __init__(self, is_enough_space):
        threading.Thread.__init__(self, daemon=True, name="VehicleController")
        DeviceConfig.__init__(self)

        self.camera_manager = None
        self.gps_reader = None

        # self.server_listener = Listener(streaming_width=self.streaming_width)
        # self.file_uploader = FileUploader()

        self.is_enough_space = is_enough_space

        self.garbage_list = read_garbage_list()

        self.running = True
        self.start()

    def start_gps_reader(self):
        if self.gps_reader is not None:
            if self.gps_reader.is_alive():
                return
        self.gps_reader = GPSReader(port=self.gps_settings.port,
                                    baudrate=self.gps_settings.baudrate,
                                    timeout=self.gps_settings.timeout)

    def stop_gps_reader(self):
        if self.gps_reader is not None:
            if self.gps_reader.is_alive():
                self.gps_reader.stop()

    def start_camera_manager(self):
        if self.camera_manager is not None:
            if self.camera_manager.is_alive():
                return
        self.camera_manager = CameraManager(settings=self.camera_settings)

    def stop_camera_manager(self):
        if self.camera_manager is not None:
            if self.camera_manager.is_alive():
                self.camera_manager.stop()

    def run(self) -> None:
        self.running = True
        old_gps_data = None
        logging.info("Starting Vehicle Controller...")
        logging.info(f"{self}")

        while self.running:
            # if not self.server_listener.is_alive():
            #     self.server_listener = Listener(streaming_width=self.streaming_width)

            # if not self.file_uploader.is_alive():
            #     self.file_uploader = FileUploader()
            #     self.file_uploader.start()

            if self.is_enough_space():
                self.start_gps_reader()
                self.start_camera_manager()

                gps_data = self.gps_reader.get_gps_data()
                if gps_data.is_valid():

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
                                        f"{gps_data.spkm}kmh_"
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
        self.stop_camera_manager()
        self.stop_gps_reader()
        # self.server_listener.stop()
        # self.file_uploader.stop()
