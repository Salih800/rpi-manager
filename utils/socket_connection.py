import socket
import json
import logging


class SocketConnection:
    class Decorators:
        @staticmethod
        def check_connection(func):
            def wrapper(self, *args, **kwargs):
                if not self._sock:
                    self.connect()
                return func(self, *args, **kwargs)
            return wrapper

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

        self._sock = None
        self._sock_file = None

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
