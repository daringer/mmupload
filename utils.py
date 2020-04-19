import os
import sys
import yaml
from datetime import datetime as dt
from datetime import timedelta as td

def load_config(config_path):
    """load config in given 'config_path', on any error fail critical & exit!"""
    if not os.path.exists(config_path):
        print("config path: {config_path} not found, exiting...")
        sys.exit(1)
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
    for token, props in cfg.setdefault("upload_tokens", {}).items():
        if dt.now() - props["created"] > td(weeks=1):
            invalidate.append(token)
    for token in invalidate:
        del cfg["upload_tokens"][token]

    return cfg

def save_config(cfg, config_path):
    cfg.setdefault("upload_tokens", {})
    cfg.setdefault("zones", {"pub": {}})
    cfg.setdefault("paths", {})
    with open(config_path, "w") as fd:
        yaml.safe_dump(cfg, fd)




