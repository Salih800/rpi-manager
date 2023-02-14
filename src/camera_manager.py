# import base64
import shutil
import logging
import os
import time
from datetime import datetime
from threading import Thread

from constants.numbers import (max_photo_count, minimum_photo_size, max_video_duration,
                               minimum_video_size, jpg_save_quality)
# from constants.others import byte_seperator
from constants.folders import path_to_upload, recorded_files
from constants.urls import URL_STREAM

from utils.singleton import Singleton
from utils.camera_tools import *

from tools import check_file_size, decode_fourcc, draw_text

import cv2
import imutils


class CameraManager(Thread, metaclass=Singleton):
    def __init__(self, parent, settings):
        Thread.__init__(self, daemon=True, name="CameraManager")

        self._parent = parent

        self.port = settings.port
        self.rotation = settings.rotation
        self.width = settings.width
        self.height = settings.height
        self.fourcc = cv2.VideoWriter_fourcc(*settings.fourcc)

        self.saved_frame_count = 0
        self.passed_frame_count = 0
        self.location_id = None
        self.taking_video = False

        self._last_frame = None
        self._virtual_camera = None
        self._virtual_port = None
        self._running = False

        self.streamer = None
        self.camera = None

        self.start()

    def start_virtual_camera(self):
        if self._virtual_camera is not None:
            if self._virtual_camera.poll() is None:
                # logging.warning("Virtual camera is already running!")
                return
        virtual_cameras = create_virtual_cameras()
        if virtual_cameras is None:
            time.sleep(10)
            return
        if len(virtual_cameras) == 0:
            logging.error("No virtual camera found!")
            time.sleep(10)
            return

        self._virtual_port = f"/dev/{virtual_cameras[0]}"
        self._virtual_camera = stream_to_virtual_camera(self.port, self._virtual_port, self.width, self.height)
        time.sleep(5)
        if self._virtual_camera is None:
            time.sleep(10)
            self.stop_virtual_camera()

    def stop_virtual_camera(self):
        if self._virtual_camera is not None:
            self._virtual_camera.kill()
            self._virtual_camera = None
        self._virtual_port = None
        remove_virtual_cameras()

    def start_streamer(self):
        if self.streamer is not None:
            if self.streamer.poll() is None:
                # logging.warning("Streamer is already running!")
                return
        if self._virtual_port is None:
            logging.error("Virtual camera is not running!")
            return
        stream_url = URL_STREAM + "autopi-1"
        self.streamer = stream_to_rtsp(self._virtual_port, stream_url)

    def stop_streamer(self):
        if self.streamer is not None:
            logging.info("Stopping streamer...")
            self.streamer.kill()
            self.streamer = None

    def run(self):
        logging.info("Starting camera manager...")
        self._running = True
        log_time = 0
        while self._running:
            self.start_virtual_camera()
            self.start_streamer()
            if self.get_camera():
                ret, frame = self.camera.read()
                if ret:
                    if time.time() - log_time > 60:
                        logging.info(f"Camera {self.port} is running.")
                        log_time = time.time()
                    frame = imutils.rotate(frame, self.rotation)
                    update_exposure(self.port, frame)
                    # self.draw_date_time(frame)
                    self.draw_gps_data(frame)
                    self._last_frame = frame
                    # cv2.imshow("Camera", frame)
                    # if cv2.waitKey(1) & 0xFF == ord('q'):
                    #     break
                    # self.put_to_stream_queue()
                else:
                    self._last_frame = None
                    logging.warning("Camera read failed!")
                    self.camera.release()
            else:
                time.sleep(1)

    # def put_to_stream_queue(self):
    #     frame = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
    #     self._parent.streamer.put_frame(frame)

    @staticmethod
    def draw_date_time(frame):
        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw_text(frame, date_time, (15, 25), text_size=0.5, text_thickness=1)

    def draw_gps_data(self, frame):
        gps_data = self._parent.gps_reader.get_drawable_gps_data()
        if gps_data is not None:
            width, height = frame.shape[1], frame.shape[0]
            draw_text(frame, gps_data, (15, height - 15), text_size=0.5, text_thickness=1)

    def stop(self):
        self._running = False
        self.release()
        self.stop_streamer()
        self.stop_virtual_camera()

    def get_camera(self):
        if self.camera is not None:
            if self.camera.isOpened():
                return True
        self._last_frame = None
        logging.info(f"Trying to get camera {self._virtual_port}...")
        start_time = time.time()
        if self._virtual_port is not None:
            self.camera = cv2.VideoCapture(self._virtual_port)
            # self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            # self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            # self.camera.set(cv2.CAP_PROP_FOURCC, self.fourcc)
            if self.camera.isOpened():
                logging.info(f"Camera {self._virtual_port} is opened in {round(time.time() - start_time, 2)} seconds.")
                logging.info(f"Camera info: {self.get_camera_info()}")
                return True
            else:
                logging.warning(f"Camera {self._virtual_port} is not opened!")
                time.sleep(10)
                raise
        else:
            logging.warning("Virtual camera is not started!")
            time.sleep(10)
        return False

    def get_camera_info(self):
        return {"width": int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fourcc": decode_fourcc(self.camera.get(cv2.CAP_PROP_FOURCC)),
                "fps": round(self.camera.get(cv2.CAP_PROP_FPS), 2)}

    def get_frame(self):
        return self._last_frame

    def get_rtsp_frame(self):
        frame = self.get_frame()
        return frame[:, :, ::-1]  # BGR to RGB

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

    # def get_streaming_frame(self, streaming_width=720):
    #     frame = self.get_frame()
    #
    #     if frame is not None:
    #         frame = cv2.resize(frame, (streaming_width, int(streaming_width * frame.shape[0] / frame.shape[1])))
    #         encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpg_save_quality])
    #
    #         message = byte_seperator + base64.b64encode(buffer) + byte_seperator
    #         return message
    #
    #     else:
    #         return None

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
                cv2.imwrite(recorded_files + photo_name, frame, [cv2.IMWRITE_JPEG_QUALITY, jpg_save_quality])
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

    def release(self):
        self.taking_video = False
        if self.camera.isOpened():
            self.camera.release()
            self.camera = None
        logging.info("Camera released")
