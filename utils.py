import os
import sys
import yaml
from datetime import datetime as dt
from datetime import timedelta as td
from time import sleep

import fcntl


class PathLocker:
    def __init__(self, path_to_lock):
        self.path_to_lock = path_to_lock
        self.fp = None

    def __enter__ (self):
        return
        if os.path.exists(self.path_to_lock):
            #print(f"locking {self.path_to_lock}")
            self.fp = open(self.path_to_lock, "rb")
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)

    def __exit__ (self, _type, value, tb):
        if self.fp:
            #print(f"unlocking {self.path_to_lock}")
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            self.fp.close()


def load_config(config_path):
    """load config in given 'fconfig_path', on any error fail critical & exit!"""

    if not os.path.exists(config_path):
        print("config path: {config_path} not found, exiting...")
        sys.exit(1)


    with PathLocker(config_path):
        cfg = yaml.safe_load(open(config_path, "r"))

    if not cfg:
        print(f"cannot load config ({config_path}), exiting...")
        sys.exit(1)


    # fatal: no "file_destination" set ...
    if "file_destination" not in cfg:
        print("you must set 'file_destintion' to a writable path (dir), exiting...")
        sys.exit(1)

    # fatal: 'file_destination' invalid
    if not os.path.exists(cfg["file_destination"]) \
      or not os.path.isdir(cfg["file_destination"]):
        print ("your 'file_destination' is not existing or not r/w/x + (dir)")
        # @todo: writeable check missing...
        sys.exit(1)

    # fatal: no 'secret_key'
    if not "secret_key" in cfg:
        print ("'secret_key' missing in configuration, exiting...")
        sys.exit(1)

    # fatal: no 'user' and/or 'pwd'
    if not "user" in cfg or not "pwd" in cfg:
        print ("no 'user' and 'pwd' provided in configuration, exiting...")
        sys.exit(1)

    # ensure public zone in config
    cfg.setdefault("zones", {})["pub"] = {}

    # finally check and remove expired tokens
    invalidate = []
    expire_in = td(weeks=1)
    #expire_in = td(seconds=1)
    for token, props in cfg.setdefault("upload_tokens", {}).items():
        if dt.now() - props["created"] > expire_in:
            invalidate.append(token)
    for token in invalidate:
        del cfg["upload_tokens"][token]

    if len(invalidate) > 0:
        with PathLocker(config_path):
            save_config(cfg, config_path)

    return cfg

def save_config(cfg, config_path):


    cfg.setdefault("upload_tokens", {})
    cfg.setdefault("zones", {"pub": {}})
    cfg.setdefault("paths", {})

    with PathLocker(config_path):
        with open(config_path, "w") as fd:
            yaml.safe_dump(cfg, fd)




