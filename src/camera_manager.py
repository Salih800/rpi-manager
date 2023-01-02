import base64
import shutil
# from datetime import datetime
import logging
import os
import time

# from constants.files import arial_font
from constants.numbers import (max_photo_count, minimum_photo_size, max_video_duration,
                               minimum_video_size, jpg_save_quality)
from constants.others import byte_seperator
# from src.gps_reader import GPSReader
from src.singleton import Singleton
from constants.folders import path_to_upload, recorded_files
from tools import check_file_size

# from PIL import Image, ImageDraw, ImageFont

from threading import Thread
import cv2
from cv2 import imwrite as my_imwrite


class CameraManager(Thread, metaclass=Singleton):
    def __init__(self, camera_port=0, camera_rotation=0, width=1280, height=720, fourcc='MJPG'):
        Thread.__init__(self, daemon=True, name="camera_manager")

        self.camera_port = camera_port
        self.camera_rotation = camera_rotation
        self.camera_width = width
        self.camera_height = height
        self.fourcc = cv2.VideoWriter_fourcc(*fourcc)

        self.saved_frame_count = 0
        self.passed_frame_count = 0
        self.location_id = None
        self.taking_video = False
        self.last_frame = None

        self.camera = None
        # self.get_drawable_gps_data = GPSReader().get_drawable_gps_data # todo: implement GPSReader
        # self.get_camera()
        self.start()

    def run(self):
        self.get_camera()
        while True:
            if not self.camera.isOpened():
                self.get_camera()
                time.sleep(1)
                continue
            ret, frame = self.camera.read()
            if ret:
                self.last_frame = cv2.rotate(frame, self.camera_rotation)
            else:
                self.last_frame = None
                logging.warning("Camera read failed!")
                self.camera.release()

    def get_camera(self):
        if self.camera is not None:
            if self.camera.isOpened():
                return
        self.last_frame = None
        logging.info(f"Trying to get camera {self.camera_port} ...")
        start_time = time.time()
        self.camera = cv2.VideoCapture(self.camera_port)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        self.camera.set(cv2.CAP_PROP_FOURCC, self.fourcc)
        if self.camera.isOpened():
            logging.info(f"Camera {self.camera_port} is opened in {round(time.time() - start_time, 2)} seconds.")
            logging.info(f"Camera info: {self.get_camera_info()}")
        else:
            logging.warning(f"Camera {self.camera_port} is not opened!")

    def get_camera_info(self):
        return {"width": int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fourcc": self.camera.get(cv2.CAP_PROP_FOURCC),
                "fps": int(self.camera.get(cv2.CAP_PROP_FPS))}

    def get_frame(self):
        return self.last_frame

    # def get_frame(self):
    #     if not self.camera.isOpened():
    #         self.get_camera()
    #
    #     ret, frame = self.camera.read()
    #     if ret:
    #         frame = cv2.rotate(frame, self.camera_rotation)
    #         # frame = cv2.rotate(frame, angle=self.camera_rotation)
    #         # drawable_gps_data = self.get_drawable_gps_data()
    #
    #         # if drawable_gps_data is not None:
    #         #     frame = self.draw_text_and_rectangle(frame, drawable_gps_data, 20, frame.shape[0] - 40)
    #
    #         # frame = self.draw_text_and_rectangle(frame, datetime.now().strftime("%Y-%m-%d  %H:%M:%S"), 20, 20)
    #         return frame
    #
    #     else:
    #         logging.warning("Error while reading frame")
    #         time.sleep(1)
    #         return None

    def get_streaming_frame(self, streaming_width=720):
        frame = self.get_frame()

        if frame is not None:
            frame = cv2.resize(frame, (streaming_width, int(streaming_width * frame.shape[0] / frame.shape[1])))
            encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpg_save_quality])

            message = byte_seperator + base64.b64encode(buffer) + byte_seperator
            return message

        else:
            return None

    def start_picture_save(self, photo_name, location_id):
        Thread(target=self.save_picture, daemon=True, name="save_picture", args=(photo_name, location_id)).start()

    def start_video_save(self, video_name):
        Thread(target=self.save_video, daemon=True, name="save_video", args=(video_name,)).start()

    def save_picture(self, photo_name, location_id):
        if self.location_id != location_id:
            self.location_id = location_id

            if self.saved_frame_count > 0:
                logging.info(f"Saved {self.saved_frame_count} photos. In location {self.location_id}")
            if self.passed_frame_count > 0:
                logging.info(f"Passed {self.passed_frame_count} photos. In location {self.location_id}")

            self.saved_frame_count = 0
            self.passed_frame_count = 0

        if self.saved_frame_count <= max_photo_count:
            frame = self.get_frame()
            if frame is not None:
                if not os.path.isdir(recorded_files):
                    os.makedirs(recorded_files)
                my_imwrite(recorded_files + photo_name, frame, [cv2.IMWRITE_JPEG_QUALITY, jpg_save_quality])
                if check_file_size(recorded_files + photo_name, minimum_photo_size):
                    self.saved_frame_count += 1
        else:
            if self.passed_frame_count == 0:
                logging.warning(f"Maximum photo count reached for this location! : {location_id}")
            self.passed_frame_count += 1

    def save_video(self, video_name):
        self.taking_video = True
        video_file_path = recorded_files + video_name
        cap_info = self.get_camera_info()
        out = cv2.VideoWriter(video_file_path, self.fourcc,
                              cap_info["fps"], (cap_info["width"], cap_info["height"]))

        logging.info(f'Recording Video...')
        start_of_video_record = time.time()
        frame_count = 0

        while self.taking_video:
            frame = self.get_frame()
            if frame is not None:
                out.write(cv2.resize(frame, (cap_info["width"], cap_info["height"])))
                frame_count = frame_count + 1
                video_duration = time.time() - start_of_video_record
                if frame_count >= max_video_duration * cap_info["fps"] or video_duration >= max_video_duration:
                    logging.warning(f"Frame count is too high! {frame_count} frames "
                                    f"{round(video_duration, 2)} seconds. "
                                    f"Ending the record...")
                    self.taking_video = False

        out.release()

        if os.path.isfile(video_file_path):
            video_record_time = round(time.time() - start_of_video_record, 2)
            file_size = round(os.path.getsize(video_file_path) / (1024 * 1024), 2)
            if file_size < minimum_video_size:
                logging.warning(f"Recorded file size is too small! Size: {file_size}MB")
                os.remove(video_file_path)
            else:
                logging.info(
                    f"Recorded video Size: {file_size}MB in {video_record_time} seconds "
                    f"and Total {frame_count} frames: {video_name}")
                shutil.move(video_file_path, path_to_upload)

        else:
            logging.warning(f"OpenCV couldn't find the file: {video_file_path}")

    # draw a rectangle filled with black color that has a size of given text
    # and draw given text to on this rectangle
    # using pillow library
    # @staticmethod
    # def draw_text_and_rectangle(frame, text, x=0, y=0,
    # font_scale=15, img_color=(255, 255, 255), rect_color=(0, 0, 0)):
    #     font = ImageFont.truetype(arial_font, font_scale)
    #     img = Image.fromarray(frame)
    #     draw = ImageDraw.Draw(img)
    #
    #     w, h = font.getsize(text)
    #     w, h = w + 1, h + 1
    #
    #     draw.rectangle((x, y, x + w, y + h), fill=rect_color)
    #
    #     draw.text((x, y), text, fill=img_color, font=font)
    #
    #     return CV.pil_to_np(img)

    @staticmethod
    def show_frame(frame, window_name="Frame", wait_time=1):
        cv2.imshow(window_name, frame)
        cv2.waitKey(wait_time)

    def release(self):
        self.taking_video = False
        if self.camera.isOpened():
            self.camera.release()
        logging.info("Camera released")
