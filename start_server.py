import os
import shutil

from server.czar import CzarServer


def main():
    if not os.path.exists("config"):
        print("Config folder not found, copying from config_sample...")
        shutil.copytree("config_sample", "config")

    server = CzarServer()
    server.start()


if __name__ == "__main__":
    print("Czar - an Attorney Online server")
    try:
        main()
    except KeyboardInterrupt:
        print("Keyboard interrupt detected, closing server...")
    except SystemExit:
        if os.name == "nt":
            input("(Press Enter to exit)")
