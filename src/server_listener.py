import logging
import time
from threading import Thread
import socket

from src.streamer import Streamer
import utils.request_handler as rh

from tools import get_vehicle_id

from constants.others import alive_byte
from constants.urls import URL_ATIKNAKIT_SERVER
from constants.numbers import atiknakit_server_port, atiknakit_server_timeout, socket_buffer_size, mb


class Listener(Thread):
    """
    Listener for the server.
    """
    def __init__(self,
                 vehicle_id=get_vehicle_id(),
                 streaming_width=640,
                 host=URL_ATIKNAKIT_SERVER,
                 port=atiknakit_server_port,
                 buff_size=socket_buffer_size,
                 alive_msg=alive_byte,
                 server_timeout=atiknakit_server_timeout):

        Thread.__init__(self, daemon=True, name="Listener")

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.vehicle_id = vehicle_id
        self.streaming_width = streaming_width

        self.host = host
        self.port = port
        self.buff_size = buff_size
        self.alive_msg = alive_msg
        self.server_timeout = server_timeout

        self.listening = False
        self.start()

    def run(self) -> None:
        self.listening = True
        logging.info("Starting Listener...")

        while self.listening:
            if rh.check_connection():
                streamer = Streamer()
                try:
                    server_address = (self.host, self.port)
                    logging.info("Trying to connect to Streaming Server")

                    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.server.connect(server_address)
                    self.server.settimeout(self.server_timeout)

                    id_message = bytes("$id" + self.vehicle_id + "$", "utf-8")
                    self.server.sendall(id_message)

                    logging.info(f"Id message sent to the Server: {id_message}")
                    self.server.sendall(self.alive_msg)

                    while self.listening:
                        server_msg = self.server.recv(self.buff_size)

                        if server_msg != b"":
                            data_orig = server_msg.decode("utf-8")
                            merge_msg = False
                            messages = []
                            new_msg = ""
                            for d in data_orig:
                                if d == "$":
                                    if not merge_msg:
                                        merge_msg = True
                                        continue
                                    else:
                                        merge_msg = False
                                        messages.append(new_msg)
                                        new_msg = ""
                                if merge_msg:
                                    new_msg += d

                            for command in messages:
                                if command == "start":
                                    if not streamer.streaming:
                                        logging.info("Start stream command received.")
                                        streamer = Streamer(server=self.server,
                                                            streaming_width=self.streaming_width)
                                        streamer.start()
                                    else:
                                        logging.warning(f"Stream was already {streamer.streaming}!")

                                elif command == "stop":
                                    if streamer.streaming:
                                        streamer.streaming = False
                                        stream_end_time = time.time() - streamer.start_time
                                        logging.info("Stop stream command received.")
                                        logging.info(f"Streamed {streamer.frame_sent} frames and "
                                                     f"total {round(streamer.total_bytes_sent / mb, 2)}MB"
                                                     f" in {round(stream_end_time, 1)} seconds")
                                    else:
                                        logging.warning(f"Stream was already {streamer.streaming}!")

                                elif command == "k":
                                    if not streamer.streaming:
                                        self.server.sendall(self.alive_msg)

                                else:
                                    logging.warning(f"Unknown message from server: {command}")
                                    time.sleep(5)
                        else:
                            logging.warning(
                                f"Empty byte from Server. Closing the connection!: Server Message: {server_msg}")
                            self.listening = False
                            self.server.close()
                            break

                except socket.timeout:
                    logging.error("Server timeout in 60 seconds! Closing the connection.")
                    time.sleep(5)
                except ConnectionRefusedError as cre:
                    logging.error(f"Connection Refused! Probably server is not online..: {cre}")
                    time.sleep(5)
                except ConnectionAbortedError as cae:
                    logging.error(f"Connection closed by Client!: {cae}")
                    time.sleep(5)
                except ConnectionResetError as cse:
                    logging.error(f"Connection closed by server!: {cse}")
                    time.sleep(5)
                # except:
                #     logging.error(f"Unexpected error from Listener:", exc_info=True)
                #     time.sleep(60)

                self.listening = False
                streamer.streaming = False

            else:
                logging.warning("No connection to the server. Waiting for connection...")
                time.sleep(60)

    def stop(self):
        self.listening = False
        self.server.close()
        logging.info("Stopping Listener...")
        time.sleep(1)
