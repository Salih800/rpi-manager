import logging
import threading
import time

from utils.device_config import DeviceConfig
from utils.garbage_list_getter import read_garbage_list

from src.camera_manager import CameraManager
from src.gps_manager import GpsReader
from src.file_uploader import upload_gps_data
from src.rtsp_streamer import RtspStreamer
from src.spm_manager import SpmManager
# from src.server_listener import Listener

from tools import check_locations


class VehicleController(threading.Thread, DeviceConfig):
    def __init__(self, is_enough_space):
        threading.Thread.__init__(self, daemon=True, name="VehicleController")
        DeviceConfig.__init__(self)

        self.camera_manager = None
        self.gps_reader = None
        self.rtsp_streamer = None
        self.spm_manager = None

        # self.server_listener = Listener(streaming_width=self.streaming_width)
        # self.file_uploader = FileUploader()

        self.is_enough_space = is_enough_space

        self.garbage_list = read_garbage_list()

        self.running = True
        self.start()

    def start_spm_manager(self):
        if self.spm_manager is not None:
            if self.spm_manager.is_alive():
                return
        self.spm_manager = SpmManager()

    def stop_spm_manager(self):
        if self.spm_manager is not None:
            if self.spm_manager.is_alive():
                self.spm_manager.stop()

    def start_gps_reader(self):
        if self.gps_reader is not None:
            if self.gps_reader.is_alive():
                return
        self.gps_reader = GpsReader(parent=self,
                                    port=self.gps_settings.port,
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
        self.camera_manager = CameraManager(parent=self,
                                            settings=self.camera_settings)

    def stop_camera_manager(self):
        if self.camera_manager is not None:
            if self.camera_manager.is_alive():
                self.camera_manager.stop()

    def start_streamer(self):
        if self.rtsp_streamer is not None:
            if self.rtsp_streamer.is_alive():
                return
        self.rtsp_streamer = RtspStreamer(parent=self,
                                          settings=self.stream_settings)

    def stop_streamer(self):
        if self.rtsp_streamer is not None:
            if self.rtsp_streamer.is_alive():
                self.rtsp_streamer.stop()

    def run(self) -> None:
        self.running = True
        old_gps_data = None
        logging.info("Starting Vehicle Controller...")
        logging.info(f"{self}")

        location_log_time = 0

        while self.running:
            # if not self.server_listener.is_alive():
            #     self.server_listener = Listener(streaming_width=self.streaming_width)

            # if not self.file_uploader.is_alive():
            #     self.file_uploader = FileUploader()
            #     self.file_uploader.start()

            if self.is_enough_space():
                self.start_gps_reader()
                self.start_spm_manager()
                # self.start_camera_manager()
                # self.start_streamer()

                gps_data = self.gps_reader.get_gps_data()
                if gps_data.is_valid():

                    threading.Thread(target=upload_gps_data,
                                     daemon=True, name="gps-uploader",
                                     args=(gps_data, old_gps_data)).start()
                    old_gps_data = gps_data

                    min_distance, closest_location_id = check_locations(gps_data=gps_data, locations=self.garbage_list)

                    if time.time() - location_log_time > 60:
                        logging.info(f"Closest location: {closest_location_id}, Distance: {int(min_distance)} meters")
                        location_log_time = time.time()

                    if (min_distance < self.max_loc_dist and
                            gps_data.spkm < self.speed_limit):
                        filename = (f"{self.vehicle_id}_"
                                    f"{self.device_type}_"
                                    f"{gps_data.local_date_str}_"
                                    f"{gps_data.lat},{gps_data.lng}_"
                                    f"{gps_data.spkm}kmh_"
                                    f"{closest_location_id}.jpg")

                        self.camera_manager.start_picture_save(photo_name=filename, location_id=closest_location_id)

            time.sleep(1)

    def stop(self) -> None:
        logging.info("Stopping Vehicle Controller...")
        self.running = False
        self.stop_camera_manager()
        self.stop_gps_reader()
        self.stop_spm_manager()
        # self.server_listener.stop()
        # self.file_uploader.stop()
