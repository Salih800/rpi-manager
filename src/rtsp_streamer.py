import logging
from threading import Thread
import subprocess
# from queue import Queue

# import time
import numpy as np
import psutil
from constants.urls import url_stream


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


def writer(path, width, height, fps=25, loglevel='warning'):
    logging.info(f"Starting writer: {path} @ {width}x{height} @ {fps}fps")
    command = ["ffmpeg", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{width}x{height}",
               "-r", f"{fps}",
               "-i", "pipe:",
               "-vf", f"fps={fps}",
               "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
               # "-vf", ("drawtext=x=10:y=10:fontsize=24:fontcolor=white:"
               #         "text='%{localtime\:%Y-%m-%d %H.%M.%S}':box=1:boxcolor=black@1"),
               "-pix_fmt", "yuv420p", "-loglevel", loglevel,
               "-f", "rtsp", "-rtsp_transport", "tcp", path]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


class RTSPStreamer(Thread):
    def __init__(self, parent, settings):
        Thread.__init__(self, daemon=True, name="RTSPStreamer")
        self.running = True

        self._parent = parent

        self.url = url_stream + settings.path

        self.writer = None

        # self.writer_queue = Queue(maxsize=30)

        self.running = True
        self.start()

    def write(self, frame):
        self.start_writer()
        try:
            self.writer.stdin.write(
                frame
                .astype(np.uint8)
                .tobytes()
            )
        except BrokenPipeError:
            self.stop_writer()
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
            # start_time = time.time()
            frame = self._parent.camera_manager.get_frame()
            # get_time = time.time() - start_time
            if frame is None:
                self.stop()
                break
            self.write(frame)
            # write_time = time.time() - start_time - get_time
            # logging.info(f"Get frame: {get_time:.4f}s, "
            #              f"Write frame: {write_time:.4f}s, "
            #              f"Total: {get_time + write_time:.4f}s")

    def start_writer(self):
        # start_time = time.time()
        if self.writer is not None:
            # if not check_process(self.writer.pid):
            #     return
            return
        else:
            settings = self._parent.camera_manager.get_camera_info()
            self.writer = writer(self.url,
                                 settings["width"],
                                 settings["height"],
                                 settings["fps"])
        # logging.info(f"Writer started in {time.time() - start_time:.4f}s")

    def stop_writer(self):
        if self.writer is not None:
            self.writer.stdin.close()
            self.writer.wait()
            self.writer = None

    def stop(self):
        self.running = False
        self.stop_writer()
