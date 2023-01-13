# import logging
import time
import threading

from src.camera_manager import CameraManager


class Streamer(threading.Thread):
    def __init__(self,
                 server=None,
                 streaming_width=720,
                 make_blurring=False):

        threading.Thread.__init__(self, daemon=True, name="Streamer")

        self.streaming = False
        self.server = server
        
        self.streaming_width = streaming_width

        self.cm = CameraManager()

        self.total_bytes_sent = 0
        self.frame_sent = 0
        self.start_time = 0
        self.sending_frame = False

        self.make_blurring = make_blurring

    def send_frame(self, frame):
        self.sending_frame = True
        # try:
        self.server.sendall(frame)
        self.total_bytes_sent += len(frame)
        self.frame_sent += 1
        # except:
        #     logging.error("Error while sending frame", exc_info=True)
        #     time.sleep(5)

        self.sending_frame = False

    def run(self):
        self.start_time = time.time()
        self.streaming = True

        while self.streaming:
            frame = self.cm.get_streaming_frame(streaming_width=self.streaming_width)
            if frame is not None:
                if not self.sending_frame:
                    threading.Thread(target=self.send_frame, daemon=True, args=(frame,)).start()
