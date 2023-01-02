import logging
import time

from constants.numbers import update_wait_time

from src.system_checker import SystemChecker
from src.vehicle_controller import VehicleController

from utils.file_uploader import FileUploader
from utils.logger_setter import set_logger
from utils.garbage_list_getter import update_garbage_list

from tools import restart_program, get_running_threads, update_repo, restart_system, get_vehicle_id


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

        if system_checker.is_enough_memory():
            if system_checker.is_enough_space():
                if time.time() - update_time > update_wait_time:
                    update_time = time.time()
                    if update_repo() or update_garbage_list():
                        restart_program()

                if not vehicle_controller.is_alive():
                    vehicle_controller = VehicleController(system_checker.is_enough_space)
                    logging.info(f"Vehicle controller started: {vehicle_controller}")

                if not file_uploader.is_alive():
                    file_uploader = FileUploader()

            else:
                if vehicle_controller.is_alive():
                    vehicle_controller.stop()
                logging.info("Not enough space")
        else:
            restart_system(error_type="memory", error_message="Not enough memory")

        time.sleep(60)


if __name__ == "__main__":
    vehicle_id = get_vehicle_id()
    set_logger(vehicle_id)
    logging.info("Program started")
    main()
