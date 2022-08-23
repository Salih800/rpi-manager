import logging
import threading
import time

from src.device_config import DeviceConfig
from src.camera_manager import CameraManager
from src.gps_reader import GPSReader

from utils.logger_setter import set_logger
from utils.file_uploader import upload_gps_data, upload_files

from tools import check_location_and_speed, restart_program, get_running_threads, update_repo
from utils.garbage_list_getter import update_garbage_list, read_garbage_list


def main():
    if DeviceConfig().device_type in ["garbage", "garbage-caca"]:
        device_thread = threading.Thread(target=garbage_main, daemon=True, name="garbage_main")
    elif DeviceConfig().device_type == "cavus":
        device_thread = threading.Thread(target=cavus_main, daemon=True, name="cavus_main")
    else:
        raise Exception("Device type not found")

    device_thread.start()

    threading.Thread(target=upload_files, daemon=True, name="uploader").start()

    while True:
        if update_repo() or update_garbage_list():
            restart_program()

        logging.info("Running threads: {}".format(get_running_threads()))

        time.sleep(3600)


def garbage_main():
    cm = CameraManager(camera_port=DeviceConfig().camera_port,
                       width=DeviceConfig().camera_width,
                       height=DeviceConfig().camera_height,
                       fourcc=DeviceConfig().camera_fourcc)

    device_config = DeviceConfig()

    garbage_list = read_garbage_list()

    gps_reader = GPSReader(device_config.gps_port)
    gps_reader.start()

    old_gps_data = None
    while True:
        if gps_reader.gps_valid:
            gps_data = gps_reader.get_gps_data()

            detected_location_id = check_location_and_speed(gps_data=gps_data,
                                                            locations=garbage_list,
                                                            on_the_move=False,
                                                            speed_limit=device_config.speed_limit,
                                                            maximum_distance=device_config.maximum_garbage_distance)

            if detected_location_id is not None:
                filename = (f"{device_config.hostname}_"
                            f"{device_config.device_type}_"
                            f"{gps_data.local_date_str}_"
                            f"{gps_data.lat},{gps_data.lng}_"
                            f"{detected_location_id}.jpg")
                cm.take_picture_action(photo_name=filename)

            upload_gps_data(new_gps_location=gps_data, old_gps_location=old_gps_data)
            old_gps_data = gps_data

        time.sleep(0.1)


if __name__ == "__main__":
    set_logger(DeviceConfig().hostname)
    logging.info("Program started")
    main()
