"""
Management of the actual files on the filesystem level.

- By providing `root_dir` during construction the resulting instance will try
  to make sure non (intentionally) invalid path is being processed and/or
  handled in any ways.

-

"""

import os
import sys
import re

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

    def __init__(self, root_dir):
        self.root_dir = root_dir

    def get_contents(self, dirname=""):
        if dirname != "":
            if not self.name_pat.match(dirname):
                raise InvalidName(f"{dirname} (need: {self.raw_name_pat})")
            if not self.isdir(dirname):
                raise DirNotExisting(dirname)
        return os.listdir(os.path.join(self.root_dir, dirname))

    def get_dirs(self, dirname):
        return [p for p in self.get_contents(dirname)
                if self.isdir(os.path.join(dirname, p))]

    def get_files(self, dirname):
        return [p for p in self.get_contents(dirname)
                if self.isfile(os.path.join(dirname, p))]

    def get_path(self, rel_path):
        if rel_path.startswith("/"):
            rel_path = os.path.relpath(rel_path, self.root_dir)
        if rel_path.startswith("/") or ".." in rel_path:
            raise InvalidPath(rel_path)
        return os.path.join(self.root_dir, rel_path)

    def get_size(self, rel_path):
        if self.isdir(rel_path):
            #raise NotImplementedError(f"directory size for: {rel_path}")
            return sum(os.path.getsize(os.path.join(dpath, fn))
              for dpath, dirs, files in os.walk(self.get_path(rel_path))
              for fn in files)

        elif self.isfile(rel_path):
            return os.path.getsize(self.get_path(rel_path))
        raise FileDBError("unknown item passed to get_size())")

    def isdir(self, rel_path):
        return os.path.isdir(self.get_path(rel_path))

    def isfile(self, rel_path):
        return os.path.isfile(self.get_path(rel_path))

    def isroot(self, path):
        return os.path.abspath(self.root_dir) \
                == os.path.abspath(self.get_path(path))

    def move_path(self, old_path, new_path):
        """rename/move `old_path` to `new_path`, os.rename() is very careful"""
        if self.isroot(old_path) or self.isroot(new_path):
            raise NotMovingRootDir((old_path, new_path))

        os.rename(self.get_path(old_path), self.get_path(new_path))

    def create_dir(self, dirname, new_dir):
        if not self.name_pat.match(new_dir):
            raise InvalidName(f"{new_dir} (need: {self.raw_name_pat})")
        if new_dir in self.get_contents(dirname):
            raise DirAlreadyExists(new_dir)
        return os.makedirs(self.get_path(os.path.join(dirname, new_dir)))

    def update_file(self, dirname, filename, contents):
        target = os.path.join(dirname, filename)
        path = self.get_path(target)
        if not self.isfile(path):
            raise FileNotExisting(target)

        with open(path, "w") as fd:
            fd.write(contents)

        return path

    def create_file(self, dirname, data):
        target = os.path.join(dirname, data.filename)
        if target in self.get_contents(dirname):
            raise FileAlreadyExists(target)

        path = self.get_path(target)
        if self.isdir(path) or self.isfile(path):
            raise FileAlreadyExists(target)

        data.save(path)
        return path

    def delete_file(self, path):
        if not self.isfile(path):
            raise FileNotExisting(path)
        return os.unlink(self.get_path(path))

    def delete_dir(self, dirname):
        if not self.isdir(dirname):
            raise DirNotExisting(dirname)
        if len(self.get_contents(dirname)) > 0:
            raise DirNotEmpty(self.get_path(dirname))
        if self.isroot(dirname):
            raise NotDeletingRootDir()
        return os.rmdir(self.get_path(dirname))

    def get_file(self, rel_path, as_iter=False):
        path = self.get_path(rel_path)
        if not self.isfile(rel_path):
            raise NotAFileError(path)

        if as_iter:
            return (line for line in open(path))
        else:
            return open(path).read()

