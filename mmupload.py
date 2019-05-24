import sys
import os

from flask import Flask, render_template, request, flash, redirect, Response, url_for
from werkzeug import secure_filename

from flask import Blueprint, render_template
main = Blueprint("main", __name__, template_folder="pages")

#from flask_uploads import UploadSet, configure_uploads, ALL

from urllib.parse import quote, urlparse

import yaml
import re

class FileDBError(Exception): pass
class InvalidName(FileDBError): pass
class DirAlreadyExists(FileDBError): pass
class DirNotExisting(FileDBError): pass
class FileNotExisting(FileDBError): pass
class DirNotEmpty(FileDBError): pass
class NotDeletingRootDir(FileDBError): pass
class NotAFileError(FileDBError): pass

class FileDB:

    raw_name_pat = "^[a-zA-Z0-9-_/]+$"
    name_pat = re.compile(raw_name_pat)

    def __init__(self, root_dir, rel_dir=""):
        self.root_dir = root_dir
        self.rel_dir = rel_dir
        self.base_dir = root_dir

    def get_contents(self, dirname=""):
        if dirname != "":
            if not self.name_pat.match(dirname):
                raise InvalidName(f"{dirname} (need: {self.raw_name_pat})")
            if not self.isdir(dirname):
                raise DirNotExisting(dirname)
        return os.listdir(os.path.join(self.base_dir, dirname))

    def get_dirs(self, dirname):
        return [p for p in self.get_contents(dirname)
                if self.isdir(os.path.join(dirname, p))]

    def get_files(self, dirname):
        return [p for p in self.get_contents(dirname)
                if self.isfile(os.path.join(dirname, p))]

    def get_path(self, rel_path):
        return os.path.join(self.base_dir, rel_path)

    def isdir(self, rel_path):
        return os.path.isdir(self.get_path(rel_path))

    def isfile(self, rel_path):
        return os.path.isfile(self.get_path(rel_path))

    def create_dir(self, dirname, new_dir):
        if not self.name_pat.match(new_dir):
            raise InvalidName(f"{name} (need: {self.raw_name_pat})")
        if new_dir in self.get_dirs(dirname):
            raise DirAlreadyExists(new_dir)
        return os.makedirs(self.get_path(os.path.join(dirname, new_dir)))

    def create_file(self, dirname, data):
        path = self.get_path(os.path.join(dirname, data.filename))
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
        if os.path.abspath(self.root_dir) == os.path.abspath(self.get_path(dirname)):
            raise NotDeletingRootDir()
        return os.rmdir(self.get_path(dirname))

    def get_file(self, rel_path):
        path = self.get_path(rel_path)
        if not self.isfile(rel_path):
          raise NotAFileError(path)
        return open(path).read()

# determine config file path
config_path = f"/srv/flask/{os.getlogin()}/mmupload/mmupload.yaml"
if not os.path.exists(config_path):
    print (f"target path not found: {config_path}")
    print ("trying inside current workdir")
    config_path = "mmupload.yaml"
    if not os.path.exists(config_path):
        print (f"no configuration file found {config_path} -> exiting...")
        sys.exit(1)

cfg = yaml.load(open(config_path))

app = Flask(__name__)
app.secret_key = cfg["secret_key"]

app.register_blueprint(main, url_prefix="/")

filedb = FileDB(cfg["file_destination"], "")


@app.route("/up/<path:dirname>", methods=["POST"])
def upload(dirname):

    if not "target" in request.files:
      flash(repr(NotAFileError()))
      return redirect(url_for("show", dirname=dirname))

    app.config["UPLOADS_FILES_DEST"] = filedb.get_path(dirname)

    filename = filedb.create_file(dirname, request.files["target"])
    flash(f"Saved to: {filename}")
    return redirect(url_for("show", dirname=dirname))

@app.route("/")
@app.route("/dir/")
@app.route("/dir/<path:dirname>")
def show(dirname=""):
    #print (filedb.get_dirs(dirname))
    #print (filedb.get_files(dirname))
    parent = os.path.dirname(dirname)
    return render_template("tmpl.html",
        show_dirs=True, show_upload=True if dirname != "" else False, show_files=True,
        dirs=sorted(map(lambda d: (d, os.path.join(dirname, d)), filedb.get_dirs(dirname))),
        files=sorted(map(lambda f: (f, os.path.join(dirname, f)), filedb.get_files(dirname))),
        parent_dir="" if dirname == "" else os.path.basename(parent),
        parent_path="" if dirname == "" else parent,
        base_dir=dirname if dirname != "" else ".",
        base_dir_name=os.path.basename(dirname if dirname != "" else ".")
    )

@app.route("/new_dir/", methods=["POST"])
@app.route("/new_dir/<path:dirname>", methods=["POST"])
def create_dir(dirname=""):

    if not "new_dirname" in request.form:
        flash("new dirname not provided")
        return redirect("/")

    new_dirname = request.form.get("new_dirname")
    filedb.create_dir(dirname, new_dirname)
    flash(f"directory created: {new_dirname}")
    return redirect(url_for("show", dirname=dirname))

@app.route("/del_dir/<path:dirname>", methods=["GET"])
def delete_dir(dirname):
    try:
        filedb.delete_dir(dirname)
        flash(f"deleted directory: {dirname}")
    except FileDBError as e:
      flash(repr(e))
    return redirect(url_for("show", dirname=os.path.dirname(dirname)))

@app.route("/del_file/<path:target>", methods=["GET"])
def delete_file(target):
    try:
        filedb.delete_file(target)
        flash(f"deleted file: {target}")
    except FileDBError as e:
      flash(repr(e))
    return redirect(url_for("show", dirname=os.path.dirname(target)))


@app.route("/get/<path:target>", methods=["GET"])
def get_file(target):
    content = filedb.get_file(target)
    return Response(content, mimetype="octet/stream")


#@app.route("/get/<file_id>", methods=["GET"])
#def get_pub_file(file_id):
#  pass


#@app.route('/photo/<id>')
#def show(id):
#    photo = Photo.load(id)
#    if photo is None:
#        abort(404)
#    url = photos.url(photo.filename)
#    return render_template('show.html', url=url, photo=photo)




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
