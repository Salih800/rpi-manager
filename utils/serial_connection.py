import logging

import serial
import time


class SerialConnection:
    class Decorators:
        @classmethod
        def ensure_open(cls, func):
            def wrapper(self, *args, **kwargs):
                try:
                    if not self.is_open():
                        self.open()
                except serial.SerialException as e:
                    logging.error(f"SerialConnection: {e}")
                    time.sleep(10)
                    return "ERROR"
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

        self._serial = serial.Serial(baudrate=self.baudrate,
                                     timeout=self.timeout,
                                     write_timeout=self.write_timeout,
                                     )
        self._serial.port = self.port

    @Decorators.ensure_open
    def send_command(self, command):
        self._serial.write(command.encode())
        time.sleep(0.5)

    @Decorators.ensure_open
    def read_data(self):
        return self._serial.readline().decode("utf-8", errors="ignore")

    @Decorators.ensure_open
    def read_until(self, expected="$GPSACP"):
        while True:
            data = self.read_data()
            logging.warning(f"SerialConnection: {data.encode()} | {expected.encode()}")
            if not data:
                logging.warning(f"SerialConnection: No data received.")
                self.close()
                break
            if data.startswith(expected):
                return data


    @Decorators.ensure_open
    def close(self):
        logging.info(f"Closing serial connection...")
        time.sleep(10)
        self._serial.close()

    def open(self):
        logging.info(f"Opening serial connection...")
        self._serial.open()

    def is_open(self):
        return self._serial.is_open
