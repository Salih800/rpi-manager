import base64
import shutil
from datetime import datetime
import logging
import os
import time
import cv2
import imutils
import threading
from cv2 import imwrite as my_imwrite

from src.singleton import Singleton
from constants.folders import path_to_upload, recorded_files
from tools import check_file_size


# fourcc to integer
def fourcc_to_int(fourcc):
    return cv2.VideoWriter_fourcc(*fourcc)


class CameraManager(threading.Thread, metaclass=Singleton):
    def __init__(self, camera_port=0, width=1280, height=720, fourcc='MJPG'):
        threading.Thread.__init__(self, daemon=True, name="CameraManager")

        self.taking_video = False
        self.camera_port = camera_port
        self.camera_width = width
        self.camera_height = height
        self.fourcc = fourcc_to_int(fourcc)

        self.saved_frame_count = 0

        self.camera = None
        self.get_camera()

    def get_camera(self):
        logging.info(f"Trying to get camera {self.camera_port} ...")
        start_time = time.time()
        self.camera = cv2.VideoCapture(self.camera_port)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        self.camera.set(cv2.CAP_PROP_FOURCC, self.fourcc)
        logging.info(f"Camera {self.camera_port} is opened in {round(time.time() - start_time, 2)} seconds.")
        logging.info(f"Camera info: {self.get_camera_info()}")

    def get_camera_info(self):
        return {"width": self.camera.get(cv2.CAP_PROP_FRAME_WIDTH),
                "height": self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT),
                "fourcc": self.camera.get(cv2.CAP_PROP_FOURCC),
                "fps": self.camera.get(cv2.CAP_PROP_FPS)}

    def run(self) -> None:

        while True:
            try:
                if self.camera.isOpened():
                    time.sleep(0.5)
                    pass

                else:
                    time.sleep(10)
                    self.get_camera()

            except:
                logging.error("Error while opening camera!", exc_info=True)
                time.sleep(10)
                self.get_camera()

    def get_frame(self):
        if not self.camera.isOpened():
            self.get_camera()
        ret, frame = self.camera.read()
        if ret:
            return frame
        else:
            logging.warning("Error while reading frame")
            return None

    def get_streaming_frame(self, streaming_width=640):
        frame = self.get_frame()

        if frame is not None:
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 2
            color = (255, 0, 0)

            date_org = (streaming_width - 150, 20)
            time_org = (streaming_width - 130, 45)

            date = datetime.now().strftime("%Y-%m-%d")
            time_now = datetime.now().strftime("%H:%M:%S")

            frame = imutils.resize(frame, width=streaming_width)

            frame = cv2.putText(frame, str(date), date_org, font,
                                font_scale, color, thickness, cv2.LINE_AA)
            frame = cv2.putText(frame, str(time_now), time_org, font,
                                font_scale, color, thickness, cv2.LINE_AA)

            encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            bosluk = b"$"
            message = bosluk + base64.b64encode(buffer) + bosluk
            return message

        else:
            return None

    def take_picture_action(self, photo_name):
        frame = self.get_frame()
        if frame is not None:
            if not os.path.isdir(recorded_files):
                os.makedirs(recorded_files)
            my_imwrite(recorded_files + photo_name, frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if check_file_size(recorded_files + photo_name, 10 * 1024):
                self.saved_frame_count += 1

    def take_video_action(self, file_name):
        self.taking_video = True
        video_file_path = recorded_files + file_name
        cap_info = self.get_camera_info()
        out = cv2.VideoWriter(video_file_path, fourcc_to_int(cap_info["fourcc"]),
                              cap_info["fps"], (cap_info["width"], cap_info["height"]))

        logging.info(f'Recording Video...')
        start_of_video_record = time.time()
        frame_count = 0

        while self.taking_video:
            frame = self.get_frame()
            if frame is not None:
                out.write(imutils.resize(frame, width=cap_info["width"]))
                frame_count = frame_count + 1
                video_duration = time.time() - start_of_video_record
                if frame_count >= 60 * cap_info["fps"] or video_duration >= 60:
                    logging.warning(f"Frame count is too high! {frame_count} frames "
                                    f"{round(video_duration, 2)} seconds. "
                                    f"Ending the record...")

        out.release()

        if os.path.isfile(video_file_path):
            video_record_time = round(time.time() - start_of_video_record, 2)
            file_size = round(os.path.getsize(video_file_path) / (1024 * 1024), 2)
            if file_size < (1 / 1024):
                logging.warning(f"Recorded file size is too small! Size: {file_size}MB")
                os.remove(video_file_path)
            else:
                logging.info(
                    f"Recorded video Size: {file_size}MB in {video_record_time} seconds "
                    f"and Total {frame_count} frames: {file_name}")
                shutil.move(video_file_path, path_to_upload)

        else:
            logging.warning(f"Opencv couldn't find the file: {video_file_path}")
