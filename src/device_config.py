from src.singleton import Singleton
from tools import get_device_config, get_hostname


# create a class for device config that has parameters
# for device type, hostname, gps_port, camera_port, camera_resolution
class DeviceConfig(metaclass=Singleton):
    def __init__(self):
        config = get_device_config()
        self.hostname = get_hostname()
        self.device_type = config["device_type"]
        self.hostname = config["hostname"]
        self.gps_port = config["gps_port"]
        self.camera_port = config["camera_port"]
        self.camera_fourcc = config["camera_fourcc"]
        self.camera_width = config["camera_width"]
        self.camera_height = config["camera_height"]
        self.streaming_width = config["streaming_width"]
        self.maximum_garbage_distance = config["maximum_garbage_distance"]
        self.speed_limit = config["speed_limit"]
