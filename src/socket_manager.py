from threading import Thread
from time import sleep
import logging

from constants.urls import ATKNAKIT_SOCKET_SERVER

from utils.socket_connection import SocketConnection


class SocketManager(Thread, SocketConnection):
    def __init__(self, parent, ip=ATKNAKIT_SOCKET_SERVER["ip"], port=ATKNAKIT_SOCKET_SERVER["port"]):
        super().__init__(daemon=True, name=self.__class__.__name__)
        SocketConnection.__init__(self, ip, port)

        self._parent = parent
        self._running = False

        self.start()

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                data = self.read_data()
                logging.info(f"Received: {data}")
                if "stream" in data.keys():
                    if data["stream"]:
                        self._parent.camera_manager.start_streamer()
                    else:
                        self._parent.camera_manager.stop_streamer()
                else:
                    logging.warning(f"Unknown data received: {data}")

            except ConnectionResetError:
                logging.warning(f"Connection closed by server!")
            except OSError as e:
                logging.warning(f"Couldn't connect to server!: {e}")
            except Exception as e:
                logging.error(f"Socket error: {e}", exc_info=True)
            else:
                continue
            self.disconnect()
            sleep(30)

    def connect(self):
        super().connect()
        self.send_data({"id": self._parent.hostname})

    def stop(self):
        self._running = False
        self.disconnect()

