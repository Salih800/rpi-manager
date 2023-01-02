from tools import get_device_config, get_hostname


class DeviceConfig:
    def __init__(self, hostname=get_hostname()):
        config = get_device_config(hostname)
        self.hostname = hostname
        self.vehicle_id = config["vehicle_id"]
        self.device_type = config["device_type"]
        self.gps_port = config["gps_port"]
        self.camera_port = config["camera_port"]
        self.camera_rotation = config["camera_rotation"]
        self.camera_fourcc = config["camera_fourcc"]
        self.camera_width = config["camera_width"]
        self.camera_height = config["camera_height"]
        self.streaming_width = config["streaming_width"]
        self.maximum_garbage_distance = config["maximum_garbage_distance"]
        self.speed_limit = config["speed_limit"]

    def __str__(self):
        return (f"Hostname: {self.hostname} | "
                f"Vehicle Id: {self.vehicle_id} | "
                f"Device Type: {self.device_type}")
