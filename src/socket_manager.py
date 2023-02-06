import socket
import json
from threading import Thread
from time import sleep
import logging
# import subprocess

from constants.urls import ATKNAKIT_SOCKET_SERVER


class SocketManager(Thread):
    class Decorators:
        @staticmethod
        def check_connection(func):
            def wrapper(self, *args, **kwargs):
                if not self._sock:
                    self.connect()
                return func(self, *args, **kwargs)
            return wrapper

    def __init__(self,
                 parent,
                 ip=ATKNAKIT_SOCKET_SERVER["ip"],
                 port=ATKNAKIT_SOCKET_SERVER["port"]):
        super().__init__(daemon=True, name=self.__class__.__name__)
        self.ip = ip
        self.port = port

        self._parent = parent
        self._running = False

        self._sock = None
        self._sock_file = None

        self.start()

    def run(self):
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
            self.disconnect()
            sleep(30)

    def _init_socket(self):
        if not self._sock:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock_file = self._sock.makefile()
            if self._sock:
                logging.info(f"Socket created successfully")
            else:
                logging.warning(f"Socket creation failed")

    def connect(self):
        self._init_socket()
        self._sock.connect((self.ip, self.port))
        self.send_data({"id": self._parent.vehicle_id})
        logging.info(f"Connected to {self.ip}:{self.port}")

    def disconnect(self):
        if self._sock:
            self._sock.close()
            self._sock = None
            self._sock_file = None
            logging.info(f"Disconnected from {self.ip}:{self.port}")

    @Decorators.check_connection
    def read_data(self):
        data = self._sock_file.readline()
        return json.loads(data)

    @Decorators.check_connection
    def send_data(self, data):
        message = (json.dumps(data) + '\n').encode()
        self._sock.sendall(message)

    def stop(self):
        self._running = False
        self.disconnect()


if __name__ == "__main__":
    class Vehicle:
        def __init__(self):
            self.vehicle_id = "rpi-1"
            self.stream = None

        def start_stream(self):
            if self.stream:
                if self.stream.poll() is None:
                    return
                else:
                    self.stream.kill()
            command = 'ffplay -f dshow -i video="HD Webcam" -loglevel error'
            print(f"Starting stream: {command}")
            # self.stream = subprocess.Popen(command, shell=True)

    vehicle = Vehicle()
    sock = SocketManager(vehicle,
                         ip=ATKNAKIT_SOCKET_SERVER["ip"],
                         port=ATKNAKIT_SOCKET_SERVER["port"])
    sleep(1)
    while True:
        # try:
        #     sock.send_data({"stream": True,
        #                     "client_id": vehicle.vehicle_id})
        # except ConnectionResetError:
        #     print(f"Connection closed by server!")
        #     sock.disconnect()
        # except OSError as e:
        #     print(f"Server not found!: {e}")
        #     sock.disconnect()
        sleep(1)
