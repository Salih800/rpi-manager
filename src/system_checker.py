import logging
import os
import threading
import shutil
import time
import psutil
from datetime import timedelta

from utils.size_converter import SizeConverter


class SystemChecker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, daemon=True, name="SystemChecker")

        self.total_memory = 0
        self.used_memory = 0
        self.free_memory = 0
        self.available_memory = 0
        self.used_memory_percent = 0

        self.cpu_usage = 0
        self.system_start_time = time.time()
        self.proces_memory = 0

        self.total_disk = 0
        self.used_disk = 0
        self.free_disk = 0
        self.disk_usage_percent = 0
        self.start()

    def __str__(self):
        return (f"System Info: "
                f"Process Memory: {self.proces_memory} | "
                f"Memory Usage: {self.used_memory_percent}% | "
                f"CPU: {self.cpu_usage}% | "
                f"Disk Usage: {self.disk_usage_percent}% | "
                f"System Uptime: {self.get_system_uptime()}")

    def is_enough_memory(self, percent=90) -> bool:
        return self.used_memory_percent <= percent

    def is_enough_space(self, percent=90) -> bool:
        return self.disk_usage_percent <= percent

    def get_process_memory(self):
        self.proces_memory = SizeConverter(psutil.Process(os.getpid()).memory_info().rss)

    def get_system_memory(self):
        memory = psutil.virtual_memory()

        self.total_memory = SizeConverter(memory.total)
        self.available_memory = SizeConverter(memory.available)
        self.used_memory = SizeConverter(memory.used)
        self.free_memory = SizeConverter(memory.free)
        self.used_memory_percent = memory.percent

    def get_disk_usage(self):
        total, used, free = shutil.disk_usage("/")
        self.total_disk = SizeConverter(total)
        self.used_disk = SizeConverter(used)
        self.free_disk = SizeConverter(free)

        self.disk_usage_percent = round(used / total * 100, 1)

    def get_cpu_usage(self):
        self.cpu_usage = psutil.cpu_percent(interval=1)

    def run(self) -> None:
        logging.info("Starting System Checker...")
        while True:
            self.get_system_memory()
            self.get_process_memory()
            self.get_disk_usage()
            self.get_cpu_usage()
            time.sleep(1)

    def get_system_uptime(self):
        return timedelta(seconds=(time.time() - self.system_start_time))
