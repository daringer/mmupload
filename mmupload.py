import sys
import os
from functools import wraps

import hashlib


from flask import Flask, render_template, request, flash, redirect, Response, url_for
from flask import Blueprint, render_template

from werkzeug import secure_filename

main = Blueprint("main", __name__, template_folder="pages")

from urllib.parse import quote, urlparse

import yaml

from file_db import FileDB, FileDBError

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

filedb = FileDB(cfg["file_destination"])


def make_pass(pwd):
    return hashlib.sha256(pwd.encode("utf-8") + b"//SALT//" +
                          app.secret_key.encode("utf-8")).hexdigest()

def check_auth_global(username, password):
    print(make_pass(password))
    return username == cfg["user"] and cfg["pwd"] == make_pass(password)

def check_auth_shared(share, username, password):
    return username == cfg["user"] and cfg["pwd"] == make_pass(password)

def http_authenticate():
    return Response("No access!", 401, {
      "WWW-Authenticate": 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth_global(auth.username, auth.password):
            return http_authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route("/new/", methods=["POST"])
@app.route("/new/<path:dirname>", methods=["POST"])
@requires_auth
def create(dirname=""):
    try:
        if "new_dirname" in request.form:
            new_dirname = request.form.get("new_dirname")
            filedb.create_dir(dirname, new_dirname)
            flash(f"directory created: {new_dirname}")
        elif "target" in request.files:
            app.config["UPLOADS_FILES_DEST"] = filedb.get_path(dirname)
            filename = filedb.create_file(dirname, request.files["target"])
            flash(f"Saved to: {filename}")
        else:
            flash("invalid request")
    except FileDBError as e:
        flash(repr(e))
    return redirect(url_for("show", dirname=dirname))

@app.route("/")
@app.route("/dir/")
@app.route("/dir/<path:dirname>")
@requires_auth
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

@app.route("/del/<path:target>", methods=["GET"])
@requires_auth
def delete(target):
    try:
        if filedb.isdir(target):
            filedb.delete_dir(target)
            flash(f"deleted dir: {target}")
        elif filedb.isfile(target):
            filedb.delete_file(target)
            flash(f"deleted file: {target}")
        else:
            raise ValueError(target)
    except FileDBError as e:
        flash(repr(e))
    return redirect(url_for("show", dirname=os.path.dirname(target)))


@app.route("/get/<path:target>", methods=["GET"])
@requires_auth
def get_file(target):
    try:
      content = filedb.get_file(target)
      return Response(content, mimetype="octet/stream")
    except FileDBError as e:
      flash(repr(e))
      return redirect(url_for("show", dirname=os.path.dirname(target)))


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
