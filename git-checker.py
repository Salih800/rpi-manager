import subprocess
import time
import os
import sys


def update_repo():
    is_updated = False
    print("Trying to update repo...")
    try:
        stdout = subprocess.check_output("git pull").decode()
        if stdout.startswith("Already"):
            print("Repo is already up to date.")
        else:
            is_updated = True
            print("Repo is updated.")

    except subprocess.CalledProcessError as stderr:
        print(stderr)

    if is_updated:
        restart_program()


def restart_program():
    print("Restarting the program...")
    os.execl(sys.executable, sys.executable, *sys.argv)


def main():
    print("hello")
    while True:
        update_repo()
        time.sleep(10)


if __name__ == "__main__":
    main()



