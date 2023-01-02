import json
import logging
import os.path

import src.request_handler as rh
from constants.files import garbage_location_list_file
from constants.urls import url_garbage_locations
from tools import get_vehicle_id


def update_garbage_list(url=url_garbage_locations, vehicle_id=get_vehicle_id(), timeout=5):
    garbage_location_list = []
    response = rh.get(url + vehicle_id, timeout=timeout)

    if response.status_code == 200:
        garbage_locations = response.json()['garbageLocations']
        if len(garbage_locations) == 0:
            logging.warning("No garbage locations found")
            return False

        for location in garbage_locations:
            lat, lng, coord_id = location
            garbage_location_list.append({"id": coord_id, "lat": lat, "lng": lng})

        if read_garbage_list() == garbage_location_list:
            return False

        json.dump(garbage_location_list, open(garbage_location_list_file, 'w'))

        logging.info(f"Garbage Locations list updated. Total Garbage Container: {len(garbage_location_list)}")

        return True

    else:
        logging.warning(f"Couldn't get garbage locations. Status Code: {response.status_code}")
        return False


def read_garbage_list():
    if not os.path.isfile(garbage_location_list_file):
        logging.warning(f"{garbage_location_list_file} not found.")
        return []

    return json.load(open(garbage_location_list_file, 'r'))


if __name__ == "__main__":
    update_garbage_list()
