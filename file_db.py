"""
Management of mmupload-handled files on the filesystem level.

"""

import os
import sys
import re

from utils import load_config, save_config

class FileDBError(OSError): pass
class InvalidName(FileDBError): pass
class InvalidPath(FileDBError): pass
class DirAlreadyExists(FileDBError): pass
class FileAlreadyExists(FileDBError): pass
class DirNotExisting(FileDBError): pass
class FileNotExisting(FileDBError): pass
class DirNotEmpty(FileDBError): pass
class NotDeletingRootDir(FileDBError): pass
class NotMovingRootDir(FileDBError): pass
class NotAFileError(FileDBError): pass

class FileDB:

    raw_name_pat = "^[a-zA-Z0-9-_/]+$"
    name_pat = re.compile(raw_name_pat)

    public_zone_name = "pub"

    def __init__(self, root_dir, yaml_cfg_path):
        self.root_dir = root_dir
        self.yaml_cfg_path = yaml_cfg_path

    ### YAML - config related
    def update_path_in_yaml(self, old_rel_path, new_rel_path):
        """returns: None, update/rename path within yaml"""
        cfg = load_config(self.yaml_cfg_path)
        if old_rel_path in cfg.setdefault("paths", {}):
            del cfg.setdefault("paths", {})[old_rel_path]
            cfg.setdefault("paths", {})[new_rel_path] = {}
        save_config(cfg, self.yaml_cfg_path) ##### <<<<<< wwaaaaaas

    def get_path_zones(self, rel_path):
        """returns: list of zones `rel_path` is member of"""
        return self.load_path_meta(rel_path).get("zones", [])

    def get_zones(self):
        """returns: dict of existing / available zones overall"""
        return load_config(self.yaml_cfg_path).get("zones", {})

    def is_path_public(self, rel_path):
        """returns: dict keeping all meta-data for `rel_path`"""
        return self.public_zone_name in self.get_path_zones(rel_path)

    def save_path_meta(self, rel_path, meta=None):
        """returns: true, if `meta` changed and `rel_path` and its meta are saved"""
        if meta is None or not isinstance(meta, dict):
            # @fixme: more verbose fail?!
            return None

        db_meta = self.load_path_meta(rel_path)
        if db_meta != meta:
            cfg = load_config(self.yaml_cfg_path)
            cfg.setdefault("paths", {})[rel_path] = meta
            save_config(cfg, self.yaml_cfg_path)
            return True
        return False

    def load_path_meta(self, rel_path):
        """returns: dict keeping all meta-data for `rel_path`"""
        cfg = load_config(self.yaml_cfg_path)

        # not in "paths" => no yaml entry => no meta for 'rel_path'
        return {} if rel_path not in cfg.get("paths", {}) else \
                cfg.get("paths", {})[rel_path]

    ################################

    def get_contents(self, dirname=""):
        """returns: filelist of given `dirname` (relative to `base_dir` path)"""
        if dirname != "":
            if not self.name_pat.match(dirname):
                raise InvalidName(f"{dirname} (need: {self.raw_name_pat})")
            if not self.isdir(dirname):
                raise DirNotExisting(dirname)
        return os.listdir(os.path.join(self.root_dir, dirname))

    def get_dirs(self, dirname):
        """returns: list of dir-names within `dirname`"""
        return [p for p in self.get_contents(dirname)
                if self.isdir(os.path.join(dirname, p))]

    def get_files(self, dirname):
        """returns: list of file-names within `dirname`"""
        return [p for p in self.get_contents(dirname)
                if self.isfile(os.path.join(dirname, p))]

    def safe_get_file_path(self, rel_path):
        """returns: safe get_path() for files, ensures existance"""
        out = self.get_path(rel_path)
        if not self.exists(rel_path):
            raise FileNotExisting()
        if not self.isfile(rel_path):
            raise NotAFileError(rel_path)
        return out

    def get_path(self, rel_path):
        """returns: full-path to access `rel_path` via filesystem"""
        if rel_path == "/":
            return ""
        if rel_path.startswith("/"):
            rel_path = os.path.relpath(rel_path, self.root_dir)
        if rel_path.startswith("/") or ".." in rel_path:
            raise InvalidPath(rel_path)

        return os.path.join(self.root_dir, rel_path)

    def get_size(self, rel_path):
        """returns: size for path for files and dirs (full tree recursive)"""
        if self.isdir(rel_path):
            #raise NotImplementedError(f"directory size for: {rel_path}")
            return sum(os.path.getsize(os.path.join(dpath, fn))
              for dpath, dirs, files in os.walk(self.get_path(rel_path))
              for fn in files)

        elif self.isfile(rel_path):
            return os.path.getsize(self.get_path(rel_path))
        raise FileDBError("unknown item passed to get_size())")

    def exists(self, rel_path):
        """returns: `true` if `rel_path` exists"""
        return os.path.exists(self.get_path(rel_path))

    def isdir(self, rel_path):
        """returns: `true` if `rel_path` is a directory"""
        return os.path.isdir(self.get_path(rel_path))

    def isfile(self, rel_path):
        """returns: `true` if `rel_path` is a file"""
        return os.path.isfile(self.get_path(rel_path))

    def isroot(self, path):
        """returns: `true` if `rel_path` is equal to our `root_dir` / data base-dir"""
        return os.path.abspath(self.root_dir) \
                == os.path.abspath(self.get_path(path))

    def move_path(self, old_path, new_path):
        """rename/move `old_path` to `new_path`, os.rename() is very careful"""
        if self.isroot(old_path) or self.isroot(new_path):
            raise NotMovingRootDir((old_path, new_path))

        os.rename(self.get_path(old_path), self.get_path(new_path))

    def create_dir(self, dirname, new_dir):
        """returns: ret-code of os.makedirs -> OS-lvl feedback"""
        if not self.name_pat.match(new_dir):
            raise InvalidName(f"{new_dir} (need: {self.raw_name_pat})")
        if new_dir in self.get_contents(dirname):
            raise DirAlreadyExists(new_dir)
        return os.makedirs(self.get_path(os.path.join(dirname, new_dir)))

    def update_file(self, dirname, filename, contents):
        """returns: `path`, updated with `contents` => direct py (path must exist)"""
        target = os.path.join(dirname, filename)
        path = self.get_path(target)
        if not self.isfile(path):
            raise FileNotExisting(target)

        with open(path, "w") as fd:
            fd.write(contents)

        return path

    def create_raw_file(self, dirname:str , filename:str , raw_data: str):
        """returns: `path`, `raw_data` written to => direct py (new path)"""
        target = os.path.join(dirname, filename)
        if target in self.get_contents(dirname):
            raise FileAlreadyExists(target)

        path = self.get_path(target)
        if self.isdir(path) or self.isfile(path):
            raise FileAlreadyExists(target)

        with open(path, "w") as fd:
            fd.write(raw_data)
        return path

    def create_file(self, dirname: str, data: str):
        """returns: `path`, `data` written to => flask's file-mgmt (new path)"""
        target = os.path.join(dirname, data.filename)
        if target in self.get_contents(dirname):
            raise FileAlreadyExists(target)

        path = self.get_path(target)
        if self.isdir(path) or self.isfile(path):
            raise FileAlreadyExists(target)

        data.save(path)
        return path

    def delete_file(self, path):
        """returns: OS-lvl ret-code from `os.unlink()`"""
        if not self.isfile(path):
            raise FileNotExisting(path)
        return os.unlink(self.get_path(path))

    def delete_dir(self, dirname):
        """returns: OS-lvl ret-code from `os.rmdir()`"""
        if not self.isdir(dirname):
            raise DirNotExisting(dirname)
        if len(self.get_contents(dirname)) > 0:
            raise DirNotEmpty(self.get_path(dirname))
        if self.isroot(dirname):
            raise NotDeletingRootDir()
        return os.rmdir(self.get_path(dirname))

    def get_file(self, rel_path, as_iter=False):
        """returns: either plain full file contents or a generator for each line"""
        path = self.get_path(rel_path)
        if not self.isfile(rel_path):
            raise NotAFileError(path)

        if as_iter:
            return (line for line in open(path))
        else:
            return open(path).read()

