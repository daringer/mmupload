import sys
import os

from flask import Flask, render_template, request, flash, redirect, Response
from werkzeug import secure_filename

from flask import Blueprint, render_template
main = Blueprint("main", __name__, template_folder="pages")

from flask_uploads import UploadSet, configure_uploads, ALL

from urllib.parse import quote, urlparse

import yaml
import re

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
app.config["UPLOADS_DEFAULT_DEST"] = cfg["file_destination"]
app.register_blueprint(main, url_prefix="/")

upload_sets = {}
for cat_id in cfg["category"].keys():
    #app.config[f"UPLOADS_{cat_id}_DEST"] = \
    #  os.path.join(cfg["file_destination"], cat_id)

    upload_sets[cat_id] = UploadSet(cat_id, ALL)

configure_uploads(app, upload_sets.values())


@app.route("/", methods=["GET", "POST"])
def upload():
    cfg = yaml.load(open(config_path))
    if request.method == "POST" and "target" in request.files:
        cat_id = request.form.get("cat_id")
        fset = upload_sets.get(cat_id)
        filename = fset.save(request.files["target"])
        flash(f"Saved to category: {cat_id}")
        return redirect("/")

    return render_template("tmpl.html",
        show_categories=True, show_upload=True,
        categories=cfg["category"].keys(), file_id=""
    )

@app.route("/cat", methods=["POST"])
def cat_new():
    cfg = yaml.load(open(config_path))
    if not "new_cat_name" in request.form:
        flash("new category id not provided")
        return redirect("/")

    cat_id = request.form.get("new_cat_name")
    pat = re.compile("^[a-zA-Z0-9-_]+$")
    if not pat.match(cat_id):
        flash("only [a-zA-Z0-9-_] are allowed as category_id, no whitespace!")
        return redirect("/")

    if len(cat_id) < 1:
        flash("the category must have at least 3 chars...")
        return redirect("/")

    if cat_id in cfg["category"]:
        flash(f"cat with id: {cat_id} already exists, try another")
        return redirect("/")

    cfg.setdefault("category", {}).setdefault(cat_id, {});
    yaml.dump(cfg, open(config_path, "w"))
    upload_sets[cat_id] = UploadSet(cat_id, ALL)
    configure_uploads(app, upload_sets.values())
    return redirect("/")

@app.route("/cat/<cat_id>/del", methods=["GET"])
def cat_del(cat_id):
    cfg = yaml.load(open(config_path))

    if cat_id not in cfg["category"]:
        flash(f"tried deletion of non-exising category: {cat_id}")
        return redirect("/")

    cat_dir = os.path.join(cfg["file_destination"], cat_id)
    if not os.path.exists(cat_dir):
        flash("category directory does not exist, bad but ok for deletion...")

    elif len(os.listdir(cat_dir)) > 0:
        flash(f"cannot delete cat_id: {cat_id} -> not empty")
        return redirect("/")

    del cfg["category"][cat_id]
    del upload_sets[cat_id]
    configure_uploads(app, upload_sets.values())
    yaml.dump(cfg, open(config_path, "w"))
    flash(f"deleted category: {cat_id}")
    return redirect("/")

@app.route("/cat/<cat_id>/show", methods=["GET"])
def cat_show(cat_id):

    cat_dir = os.path.join(cfg["file_destination"], cat_id)
    if not os.path.exists(cat_dir):
        flash(f"category: {cat_id} is empty...")
        return redirect("/")

    return render_template("tmpl.html",
        show_upload=True, show_files=True,
        categories=cfg["category"].keys(),
        files=os.listdir(cat_dir), #[(file_id, quote(file_id)) for file_id in os.listdir(cat_dir)],
        cat_id=cat_id
    )

@app.route("/cat/<cat_id>/get/<file_id>", methods=["GET"])
def get_file(cat_id, file_id):
    cat_dir = os.path.join(cfg["file_destination"], cat_id)
    full_path = os.path.join(cat_dir, file_id)
    content = open(full_path).read()
    return Response(content, mimetype="octet/stream")

@app.route("/get/<file_id>", methods=["GET"])
def get_pub_file(file_id):
  pass


#@app.route('/photo/<id>')
#def show(id):
#    photo = Photo.load(id)
#    if photo is None:
#        abort(404)
#    url = photos.url(photo.filename)
#    return render_template('show.html', url=url, photo=photo)




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
