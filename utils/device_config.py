from tools import get_device_config, get_hostname


class Dict2Class(object):

    def __init__(self, my_dict):
        for key in my_dict:
            setattr(self, key, my_dict[key])


class DeviceConfig:
    def __init__(self, hostname=get_hostname()):
        config = get_device_config(hostname)
        self.hostname = hostname
        self.vehicle_id = config["vehicle_id"]
        self.device_type = config["device_type"]
        self.max_loc_dist = config["maximum_garbage_distance"]
        self.speed_limit = config["speed_limit"]
        self.gps_settings = Dict2Class(config["gps_settings"])
        self.camera_settings = Dict2Class(config["camera_settings"])
        self.stream_settings = Dict2Class(config["stream_settings"])

    def __str__(self):
        return (f"Hostname: {self.hostname} | "
                f"Vehicle Id: {self.vehicle_id} | "
                f"Device Type: {self.device_type}")
