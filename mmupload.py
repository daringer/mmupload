import sys
import os
from functools import wraps

import hashlib
import mimetypes

from flask import Flask, render_template, request, flash, redirect, Response, \
    url_for, send_file, Blueprint, render_template, jsonify

from werkzeug.utils import secure_filename

main = Blueprint("main", __name__, template_folder="pages")

from urllib.parse import quote, urlparse
from uuid import uuid4 as create_uid

import yaml

from mmpy.flask_simple_rest import FlaskSimpleRest, get_rest_decorator

from file_db import FileDB, FileDBError
from utils import load_config
from gen_pass import make_pass

# where to find the .yaml config file
YAML_CFG_PATH = sys.argv[1]
cfg = load_config(YAML_CFG_PATH)

# global url prefix, if mmupload is located in a sub-directory
URL_PREFIX = cfg.get("url_prefix", "/")
if URL_PREFIX == "/":
    URL_PREFIX = ""

STATIC_URL_PREFIX = cfg.get("static_url_prefix")

# flask init
app = Flask(__name__)
app.secret_key = cfg["secret_key"]
app.register_blueprint(main, url_prefix="/")

filedb = FileDB(cfg["file_destination"], YAML_CFG_PATH)

rest = get_rest_decorator(app)

####
#### utils
####

def render_page(dirname, msgs=None, editor_target=None, tmpl="tmpl.html"):
    """returns: [view-ready-object] with primary page rendered with existing data"""
    parent = os.path.dirname(dirname)
    return render_template(tmpl,
        editor_target=editor_target,
        parent_dir="" if dirname == "" else os.path.basename(parent),
        parent_path="" if dirname == "" else parent,
        base_dir=dirname if dirname != "" else ".",
        base_dir_name=os.path.basename(dirname if dirname != "" else "."),
        messages=msgs if msgs is not None else [],
        url_prefix=URL_PREFIX
    )

def _file_get_helper(target, raw=False):
    """returns: [view-ready-object] handling file-get a.k.a. file downloading"""
    try:
        fn = filedb.safe_get_file_path(target)
        mime_info = mimetypes.guess_type(fn)
        if raw:
            out = None
            with open(fn, "r") as fd:
                out = fd.read()
            return jsonify({"data": out, "target": target, "action": "get_raw",
                            "mimetype": mime_info[0]})
        else:
            if STATIC_URL_PREFIX:
                return Response(mimetype=mime_info[0],
                        headers={"X-Accel-Redirect":
                                 os.path.join(STATIC_URL_PREFIX, target)})
            else:
                return send_file(fn, mimetype=mime_info[0], as_attachment=True)

    except FileDBError as e:
        return jsonify({"state": "fail", "msg": repr(e), "target": target,
                        "action": "get"})

def check_auth_global(username, password):
    return username == cfg["user"] and cfg["pwd"] == make_pass(password)

def http_authenticate():
    return Response("No access!", 401, {
      "WWW-Authenticate": 'Basic realm="Login Required"'}
    )

# decorator for authenticated access
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth_global(auth.username, auth.password):
            return http_authenticate()
        return f(*args, **kwargs)
    return decorated

#def check_auth_shared(share, username, password):
#    return username == cfg["user"] and cfg["pwd"] == make_pass(password)
#requires_zone_auth = requires_auth

# dummy decorator for non-authenticated access
def no_auth(f):
    return f

####
#### endpoints
####

#@rest.get("/local/<path:target>")
@app.route("/local/<path:target>")
#@requires_auth
def get_static(target=""):
    if ".." in target:
        return;

    p = os.path.join("static", target)
    data = None
    with open(p, "r") as fd:
        data = fd.read()
    mime_info = mimetypes.guess_type(p)
    return Response(data, mimetype=mime_info[0])

@app.route("/local/icon/<string:icon>")
def get_icon(icon):
    if ".." in icon:
        return;

    p = os.path.join("static", "icons", "svg", icon + ".svg")
    data = None
    with open(p, "r") as fd:
        data = fd.read()
    mime_info = mimetypes.guess_type(p)
    return Response(data, mimetype=mime_info[0])

@app.route("/")
@app.route("/dir/")
@app.route("/dir/<path:dirname>")
@requires_auth
def show(dirname=""):
    #return render_page(dirname, msgs=[request.args.get("msg")])
    #print (list(request.args), request.args.get("msg"))
    return render_page(dirname, msgs=[request.args.get("msg")])

@app.route("/err/<int:code>")
def custom_err(code):
   desc = {
     404: "Not Found",
     403: "Not Allowed",
   }.get(code, "")
   return render_template("custom_err.html", err_code=code, err_desc=desc)


@rest.post("/new/")
@rest.post("/new/<path:dirname>")
@requires_auth
def create(dirname=""):
    state = "ok"
    try:
        # creating new directory
        if request.form.get("what") == "create" and \
          len(request.form.get("new_dirname").strip()) > 0:
            new_dirname = request.form.get("new_dirname")
            filedb.create_dir(dirname, new_dirname)
            msg = f"directory created: {new_dirname}"

        # uploading some file
        elif request.form.get("what") == "upload":
            app.config["UPLOADS_FILES_DEST"] = filedb.get_path(dirname)
            req_file = request.files.get("target")
            if not req_file:
                msg = f"Error: no uploaded file found..."
                state = "fail"
            else:
                filename = filedb.create_file(dirname, req_file)
                msg = f"Saved to: {filename}"

        elif request.form.get("what") in ["save", "savenew"]:
            app.config["UPLOADS_FILES_DEST"] = filedb.get_path(dirname)
            if filedb.isfile(os.path.join(dirname, request.form.get("filename"))):
                filename = filedb.update_file(dirname,
                    request.form.get("filename"), request.form.get("data"))
                msg = f"Updated file: {filename}"
            else:
                filename = filedb.create_raw_file(dirname,
                    request.form.get("filename"), request.form.get("data"))
                msg = f"Created file: {filename}"
        else:
            msg = "invalid request"
            state = "fail"
    except FileDBError as e:
        msg = repr(e)
        state = "fail"
    return jsonify({"dirname": dirname, "msgs": [msg], "state": state})

@rest.get("/list/<string:what>/")
@rest.get("/list/<string:what>/<path:dirname>")
@requires_auth
def ls(what, dirname=""):
    raw_list = map(lambda p: {
            "name": p,
            "path": os.path.join(dirname, p),
            "meta": filedb.load_path_meta(os.path.join(dirname, p))
        },
        filedb.get_dirs(dirname) if what == "dirs" else \
        filedb.get_files(dirname))

    get_mime = lambda tar: mimetypes.guess_type(filedb.get_path(tar))[0]
    data = list(map(lambda dct: {
          "name": dct["name"],
          "path": dct["path"],
          "uid": str(create_uid())[:8],
          "mimetype": get_mime(dct["path"]),
          "size": filedb.get_size(dct["path"]),
          "zones": dct["meta"].get("zones", []),
          "delete_url": url_for("delete", target=dct["path"]),
          "move_url": url_for("move", target=dct["path"]),
          "click_url": url_for("ls", what=what, dirname=dct["path"]) \
            if what == "dirs" else url_for("get_file", target=dct["path"]),
          "visit_url": url_for("show", dirname=dct["path"]) \
            if what == "dirs" else url_for("get_file", target=dct["path"]),
        }, raw_list))

    data = {"data": data, "upload_url": url_for("create", dirname=dirname)}
    return jsonify(data)

@rest.get("/edit/<path:target>")
@requires_auth
def edit(target):
    return render_page(dirname=os.path.dirname(target), editor_target=target)

@rest.post("/move/<path:target>")
@requires_auth
def move(target):
    old_parent = os.path.dirname(target)
    new_target = os.path.join(old_parent, request.form.get("new_target"))
    try:
        filedb.move_path(target, new_target)
        filedb.update_path_in_yaml(target, new_target)
    except OSError as e:
        return jsonify({"msg": repr(e), "state": "fail"})

    return jsonify({"msg": f"'{target}' moved to '{new_target}'", "state": "ok"})

@rest.get("/meta/<path:target>")
@requires_auth
def show_meta(target):
    meta = filedb.get_meta_from_yaml(target)
    return jsonify({"state": "ok", "meta": meta})

@rest.post("/meta/<path:target>/del/<key>")
@requires_auth
def del_meta_property(target, key):
    meta = filedb.load_path_meta(target)
    if key in meta:
        del meta[key]
        res = filedb.save_path_meta(target, meta)
        # @fixme: handle error :(
        return jsonify({"state": "ok", "msg": f"deleted meta key: {key}", "meta": meta})

    return jsonify({"state": "fail", "msg": f"meta key not found: {key}"})

@rest.post("/meta/<path:target>/set/<key>/<value_type>/<value>")
@requires_auth
def set_meta_property(target, key, value_type, value=None):
    if value_type in ["string", "path"]:
        pass
    elif value_type == "list":
        value = value.split(",")
    elif value_type == "dict":
        value = dict(x.split(":") for x in value.split(","))
    else:
        return jsonify({"msg": f"internal error (meta set)", "state": "fail"})

    meta = filedb.load_path_meta(target)
    meta[key] = value

    res = filedb.save_path_meta(target, meta)
    dct = {"meta": meta}
    if res:
        dct.update({"state": "ok", "msg": f"meta-data updated for {target}"})
    elif res is False:
        dct.update({"state": "ok", "msg": f"no need to update meta-data for {target}"})
    else:
        dct.update({"state": "fail", "msg": f"failed updating meta-data for {target}"})

    return jsonify(dct)

@rest.get("/meta/<path:target>/get/<key>")
@requires_auth
def get_meta_property(target, key):
    meta = filedb.load_path_meta(target)
    return jsonify({"state": "ok", "target": target, "meta": meta})


#@app.route("/zones")
#@app.route("/zones/<zone>/add")
#@app.route("/zones/<zone>/edit")
#@app.route("/zones/<zone>/del")

@rest.post("/del/<path:target>")
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

@rest.get("/get/download/<path:target>")
def get_file(target):
    auth_wrap = no_auth if filedb.is_path_public(target) else requires_auth
    def _get():
        return _file_get_helper(target)
    return auth_wrap(_get)()

@rest.get("/get/raw/<path:target>")
def get_raw_file(target):
    auth_wrap = no_auth if filedb.is_path_public(target) else requires_auth
    def _get():
        try:
            return _file_get_helper(target, raw=True)
        except UnicodeDecodeError as e:
            return jsonify({"state": "fail", "msgs":
                ["Failed to load file as unicode...",
                 repr(e)[:50]] })
    return auth_wrap(_get)()

@rest.get("/get/<path:target>")
def get_file_short(target):
    return get_file(target)


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
