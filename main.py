import logging
import time

from constants.numbers import UPDATE_WAIT_TIME

from src.system_checker import SystemChecker
from src.vehicle_controller import VehicleController

from src.file_uploader import FileUploader
from utils.garbage_list_getter import update_garbage_list
import utils.request_handler as rh

from tools import (restart_service, get_running_threads,
                   update_repo, restart_system)


def main():
    system_checker = SystemChecker()
    file_uploader = FileUploader()
    vehicle_controller = VehicleController(system_checker.is_enough_space)

    update_time = 0

    while True:
        logging.info("Running threads: {}".format(get_running_threads()))
        logging.info(f"{system_checker}")
        if not system_checker.is_alive():
            system_checker = SystemChecker()

        connection = rh.check_connection()
        logging.info(f"check_connection: {connection}")

        if system_checker.is_enough_memory():
            if system_checker.is_enough_space():
                if time.time() - update_time > UPDATE_WAIT_TIME:
                    update_time = time.time()
                    if update_repo() or update_garbage_list():
                        restart_service()

                if not vehicle_controller.is_alive():
                    vehicle_controller = VehicleController(system_checker.is_enough_space)
                    logging.info(f"Vehicle controller started.")

                if not file_uploader.is_alive():
                    file_uploader = FileUploader()

            else:
                if vehicle_controller.is_alive():
                    vehicle_controller.stop()
                logging.warning("Not enough space on disk.")
        else:
            restart_system(error_type="memory", error_message="Not enough memory")

        time.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s | %(filename)s | %(pathname)s | %(threadName)s | %(module)s | %(funcName)s | %(message)s',
    )
    update_repo()
    main()
