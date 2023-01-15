import logging

import serial
import time


class SerialConnection:
    class Decorators:
        @classmethod
        def ensure_open(cls, func):
            def wrapper(self, *args, **kwargs):
                if not self._serial.is_open:
                    self._serial.open()
                return func(self, *args, **kwargs)
            return wrapper

    def __init__(self,
                 port,
                 baudrate,
                 timeout,
                 bytesize=serial.EIGHTBITS,
                 parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE
                 ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.write_timeout = timeout

        self._serial = serial.Serial(port=self.port,
                                     baudrate=self.baudrate,
                                     timeout=self.timeout,
                                     write_timeout=self.write_timeout,
                                     )

    @Decorators.ensure_open
    def send_command(self, command):
        self._serial.write(command.encode())

    @Decorators.ensure_open
    def read_data(self):
        return self._serial.readline().decode("utf-8", errors="ignore")

    @Decorators.ensure_open
    def read_until(self, expected="$GPSACP"):
        data = self.read_data()
        while not data.startswith(expected):
            data = self.read_data()
            if not data:
                logging.warning(f"SerialConnection: No data received.")
        return data
