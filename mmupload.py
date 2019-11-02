import sys
import os
from functools import wraps

import hashlib
import mimetypes

from flask import Flask, render_template, request, flash, redirect, Response, url_for, send_file
from flask import Blueprint, render_template, jsonify

from werkzeug.utils import secure_filename

main = Blueprint("main", __name__, template_folder="pages")

from urllib.parse import quote, urlparse

import yaml

from file_db import FileDB, FileDBError

from gen_pass import make_pass

URL_PREFIX = "/mmupload"

def load_config(config_path):
    """load config in given 'config_path', on any error fail critical & exit!"""
    if not os.path.exists(config_path):
        print("config path: {config_path} not found, exiting...")
        sys.exit(1)
    cfg = yaml.safe_load(open(config_path))

    if "file_destination" not in cfg:
        print("you must set 'file_destintion' to a writable path (dir), exiting...")
        sys.exit(1)

    if not os.path.exists(cfg["file_destination"]) \
      or not os.path.isdir(cfg["file_destination"]):
        print ("your 'file_destination' is not existing or not r/w/x + (dir)")
        # @todo: writeable check missing...
        sys.exit(1)

    if not "secret_key" in cfg:
        print ("'secret_key' missing in configuration, exiting...")
        sys.exit(1)

    if not "user" in cfg or not "pwd" in cfg:
        print ("no 'user' and 'pwd' provided in configuration, exiting...")
        sys.exit(1)

    return cfg

cfg = load_config(sys.argv[1])

app = Flask(__name__)
app.secret_key = cfg["secret_key"]
app.register_blueprint(main, url_prefix="/")

filedb = FileDB(cfg["file_destination"])


####
#### utils
####

def render_page(dirname, msgs=None, editor_target=None):
    parent = os.path.dirname(dirname)
    return render_template("tmpl.html",
        editor_target=editor_target,
        parent_dir="" if dirname == "" else os.path.basename(parent),
        parent_path="" if dirname == "" else parent,
        base_dir=dirname if dirname != "" else ".",
        base_dir_name=os.path.basename(dirname if dirname != "" else "."),
        messages=msgs if msgs is not None else [],
        url_prefix=URL_PREFIX
    )

def check_auth_global(username, password):
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
requires_zone_auth = requires_auth


####
#### endpoints
####

@app.route("/local/<path:target>", methods=["GET"])
@requires_auth
def get_static(target=""):
    p = os.path.join("static", target)
    data = None
    with open(p, "r") as fd:
        data = fd.read()
    mime_info = mimetypes.guess_type(p)
    return Response(data, mimetype=mime_info[0])

@app.route("/new/", methods=["POST"])
@app.route("/new/<path:dirname>", methods=["POST"])
@requires_auth
def create(dirname=""):
    try:
        if request.form.get("what") == "create" and \
          len(request.form.get("new_dirname").strip()) > 0:
            new_dirname = request.form.get("new_dirname")
            filedb.create_dir(dirname, new_dirname)
            msg = f"directory created: {new_dirname}"

        elif request.form.get("what") == "upload":
            app.config["UPLOADS_FILES_DEST"] = filedb.get_path(dirname)
            filename = filedb.create_file(dirname, request.files["target"])
            msg = f"Saved to: {filename}"

        elif request.form.get("what") == "save":
            app.config["UPLOADS_FILES_DEST"] = filedb.get_path(dirname)
            filename = filedb.update_file(dirname,
              request.form.get("filename"), request.form.get("contents"))
            msg = f"Updated file: {filename}"

        else:
            msg = "invalid request"
    except FileDBError as e:
        msg = repr(e)
    return jsonify({"dirname": dirname, "msgs": [msg]})

@app.route("/")
@app.route("/dir/")
@app.route("/dir/<path:dirname>")
@requires_auth
def show(dirname=""):
    return render_page(dirname)

@app.route("/list/<string:what>/")
@app.route("/list/<string:what>/<path:dirname>")
@requires_auth
def ls(what, dirname=""):
    raw_list = map(lambda p: {"name": p, "path": os.path.join(dirname, p)},
        filedb.get_dirs(dirname) if what == "dirs" else \
        filedb.get_files(dirname))

    data = list(map(lambda dct: {
          "name": dct["name"],
          "path": dct["path"],
          "size": filedb.get_size(dct["path"]),
          "delete_url": url_for("delete", target=dct["path"]),
          "move_url": url_for("move", target=dct["path"]),
          "click_url": url_for("ls", what=what, dirname=dct["path"]) \
            if what == "dirs" else url_for("get_file", target=dct["path"])
        }, raw_list))

    data = {"data": data, "upload_url": url_for("create", dirname=dirname)}
    return jsonify(data)

@app.route("/edit/<path:target>", methods=["GET"])
@requires_auth
def edit(target):
    return render_page(dirname=os.path.dirname(target), editor_target=target)

@app.route("/move/<path:target>", methods=["POST"])
@requires_auth
def move(target):
    old_parent = os.path.dirname(target)
    new_target = os.path.join(old_parent, request.form.get("new_target"))
    try:
        filedb.move_path(target, new_target)
    except OSError as e:
        return jsonify({"msg": repr(e), "state": "fail"})
    return jsonify({"msg": f"'{target}' moved to '{new_target}'", "state": "ok"})

@app.route("/del/<path:target>", methods=["POST"])
@requires_auth
def delete(target):
    try:
        if filedb.isdir(target):
            filedb.delete_dir(target)
        elif filedb.isfile(target):
            filedb.delete_file(target)
        else:
            raise ValueError(target)
    except FileDBError as e:
        return jsonify({"msg": repr(e), "state": "fail"})
    return jsonify({"msg": f"'{target}' deleted", "state": "ok"})

def file_get_helper(target, raw=False):
    try:
        fn = filedb.get_path(target)
        mime_info = mimetypes.guess_type(fn)
        if raw:
            out = None
            with open(fn, "r") as fd:
                out = fd.read()
            return out
        else:
            return send_file(fn, mimetype=mime_info[0])

    except FileDBError as e:
        msg = repr(e)
        return render_page(os.path.dirnane(target), [msg])


#@app.route("/s/<zone>/<s_id>", methods=["POST", "GET", "DELETE"])
#@app.route("/s/<zone>", methods=["POST", "DELETE"])
@app.route("/s/x/<s_id>",   methods=["GET"])
@app.route("/s/x",          methods=["POST", "DELETE"])
@requires_zone_auth
def safe_shorties(zone, s_id=None):
    return shorties(zone, s_id)

@app.route("/s/pub/<s_id>", methods=["GET"])
@app.route("/s/pub",        methods=["POST", "DELETE"])
def shorties(zone, s_id=None):
    if request.method == "POST":

        new_shorty = request.form.get("new_shorty").strip()

        if not filedb.name_pat.match(new_shorty):
            flash("illegal shorty, need {filedb.raw_name_pat} (minus slash '/')")

        elif "/" in new_shorty:
            flash("no slashes allowed inside shorties")

        elif new_shorty in cfg["shorties"][zone]:
            flash("shorty already exists, please try another one")

        elif zone in cfg["shorties"] and len(new_shorty) > 4:
            #shorty_url = "/s/{zone}/{new_shorty}"
            shorty_url = url_for("shorties",  zone=zone, s_id=new_shorty)
            flash("shorty created, url: {shorty_url}")
            cfg["shorties"][zone][new_shorty] = target
            ########################
            # @TODO: database is dirty, need save!(!)
            ########################

    elif request.method == "DELETE":
        s_id = request.form.get("old_shorty")
        if zone in cfg["shorties"] and s_id in cfg["shorties"][zone]:
            del cfg["shorties"][zone][s_id]
            flash("removed shorty: {s_id} in zone: {zone}")
            ########################
            # @TODO: database is dirty, need save!(!)
            ########################
            ########################
            ########################
    else:
        # path is always relative! no abs-paths inside the DB
        path = cfg["shorties"].get(zone, {}).get(s_id)
        if not path:
            flash("invalid")
            # @TODO @TODO
            # @TODO: return redirect() <- to a 404 error page"
            # @TODO @TODO
            return file_get_helper(path)


############
## just write / load database
## add 404 for the errors, they shall not be forwarded on misses
## yeah and what about the frontend ...


@app.route("/get/download/<path:target>", methods=["GET"])
@requires_auth
def get_file(target):
    return file_get_helper(target)

@app.route("/get/raw/<path:target>", methods=["GET"])
@requires_auth
def get_raw_file(target):
    return jsonify(file_get_helper(target, raw=True))

@app.route("/get/<path:target>", methods=["GET"])
def get_file_short(target):
    return get_file(target)

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
    URL_PREFIX = ""
    app.run(host='0.0.0.0', port=5001, debug=True)
