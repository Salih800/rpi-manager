import logging
from threading import Thread
import time

from src.camera_manager import CameraManager
from src.gps_manager import GpsReader
from src.spm_manager import SpmManager
from src.socket_manager import SocketManager
from src.recorder import Recorder

from utils.device_config import DeviceConfig


class VehicleController(Thread, DeviceConfig):
    def __init__(self, is_enough_space):
        Thread.__init__(self, daemon=True, name="VehicleController")
        DeviceConfig.__init__(self)

        self.camera_manager = None
        self.gps_reader = None
        self.rtsp_streamer = None
        self.spm_manager = None
        self.socket_manager = None
        self.recorder = None

        self.is_enough_space = is_enough_space

        self._running = True
        self.start()

    def start_recorder(self):
        if self.recorder is not None:
            if self.recorder.is_alive():
                return
        self.recorder = Recorder(parent=self)

    def stop_recorder(self):
        if self.recorder is not None:
            if self.recorder.is_alive():
                self.recorder.stop()

    def start_socket_manager(self):
        if self.socket_manager is not None:
            if self.socket_manager.is_alive():
                return
        self.socket_manager = SocketManager(parent=self)

    def stop_socket_manager(self):
        if self.socket_manager is not None:
            if self.socket_manager.is_alive():
                self.socket_manager.stop()

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
                                    settings=self.gps_settings)

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

    def run(self) -> None:
        logging.info("Starting Vehicle Controller...")
        logging.info(f"{self}")

        while self._running:

            if self.is_enough_space():
                self.start_spm_manager()
                self.start_gps_reader()
                self.start_camera_manager()
                # self.start_socket_manager()
                self.start_recorder()

            time.sleep(1)

    def stop(self) -> None:
        logging.info("Stopping Vehicle Controller...")
        self._running = False
        self.stop_recorder()
        # self.stop_socket_manager()
        self.stop_camera_manager()
        self.stop_gps_reader()
        self.stop_spm_manager()
