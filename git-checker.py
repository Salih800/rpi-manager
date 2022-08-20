import subprocess
import time
import os
import sys

from myutils.logger_setter import set_logger
from myutils.IdLogger import IdLogger


set_logger()
logger = IdLogger("git-checker")


def update_repo():
    is_updated = False
    logger.info("Trying to update repo...")
    try:
        stdout = subprocess.check_output("git pull").decode()
        if stdout.startswith("Already"):
            logger.info("Repo is already up to date.")
        else:
            is_updated = True
            logger.info("Repo is updated.")

    except subprocess.CalledProcessError as stderr:
        logger.info(stderr)

    if is_updated:
        restart_program()


def restart_program():
    logger.info("Restarting the program...")
    os.execl(sys.executable, sys.executable, *sys.argv)


def main():
    logger.info("1232141243")
    while True:
        update_repo()
        time.sleep(10)


if __name__ == "__main__":
    main()



