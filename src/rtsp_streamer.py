# import logging
from threading import Thread
import subprocess
# from queue import Queue

import numpy as np
import psutil


def check_process(pid):
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name'])
            if pinfo['pid'] == pid:
                return True
            else:
                continue
        except psutil.NoSuchProcess:
            pass
    return False


def writer(path, width, height, fps=25):
    command = ["ffmpeg", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{width}x{height}", "-r", f"{fps}", "-i", "pipe:",
               "-b:v", "2M", "-pix_fmt", "yuv420p", "-loglevel", "error",
               "-f", "rtsp", "-rtsp_transport", "tcp", path]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


class RTSPStreamer(Thread):
    def __init__(self, parent, path):
        Thread.__init__(self, daemon=True, name="RTSPStreamer")
        self.running = True

        self._parent = parent

        self.path = path

        self.writer = None

        # self.writer_queue = Queue(maxsize=30)

        self.running = True
        self.start()

    def write(self, frame):
        self.start_writer()
        self.writer.stdin.write(
            frame
            .astype(np.uint8)
            .tobytes()
        )

    # def put_frame(self, frame):
    #     self.writer_queue.put(frame)

    def run(self):
        while self.running:
            # frame = self.writer_queue.get()
            frame = self._parent.camera_manager.get_frame()
            if frame is None:
                self.stop()
            self.write(frame)

    def start_writer(self):
        if self.writer is not None:
            if not check_process(self.writer.pid):
                return
        else:
            settings = self._parent.camera_manager.get_camera_info()
            self.writer = writer(self.path,
                                 settings["width"],
                                 settings["height"],
                                 settings["fps"])

    def stop_writer(self):
        if self.writer is not None:
            self.writer.stdin.close()
            self.writer.wait()
            self.writer = None

    def stop(self):
        self.running = False
        self.stop_writer()
