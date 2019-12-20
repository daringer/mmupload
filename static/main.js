"use strict";


/** back + forward + reload button handling **/
/*function add_history_entry(action) {
	history.pushState(action, null, null);
}
window.addEventListener("popstate", function(ev) {
	var action = ev.state;
	if (action != null) {

		console.log(action);

		var func = window[action[0]];
		var args = action.slice(1);
		func(...args);

		$(".addedMenuNavBarItem").remove();
		console.log("executing 'back' history: func(...args)");
	} else {
		window.history.back();
	}
});
*/


function get_filename(path) {
   return new String(path).substring(path.lastIndexOf("/") + 1);
}

function get_dirname(path) {
	 if (path.lastIndexOf("/") == -1)
			return path;
   return new String(path).substring(0, path.lastIndexOf("/"));
}

function join_paths(...paths) {
	var out = new String();
	for(var p of paths)
		out += "/" + p
	while(out.indexOf("//") != -1)
		out = out.replace("//", "/")
	return out;
}


function show_message(msg, error=false) {
	if (msg == "None")
		return;

	var el = document.createElement("div");
	var ic = document.createElement("img");
	$(ic).attr("src", url_prefix + "/local/icons/svg/exclamation.svg");
	$(ic).css({
		position: "relative",
		left: "-2px",
		top: "7px"
	});
	$(el).text(msg).attr("class", (error) ? "err" : "info").hide();
	$(el).prepend(ic);
	$("#flash").prepend(el);
	$(el).fadeIn(1000, function() {
		$(el).fadeOut(15000, function() {
			$(el).remove();
		});
	});
}

function show_error(msg) {
	show_message(msg, true);
}

function readable_size(size) {
	var unit_idx = 0;
	var units = {0: "B", 1: "KB", 2: "MB", 3: "GB"};
	var out_size = size;
	while (out_size > 1024 || unit_idx == 0) {
		out_size = out_size / 1024.;
		unit_idx++;
	}
	return out_size.toFixed(3) + " " + units[unit_idx];
}

function show_preview(path) {
	if (!path.indexOf("/") > -1)
		path = "/" + path;

	$("#previewbox").fadeIn("slow");
	$("#previewbox img").attr("src", join_paths(url_prefix, "/get/download/", path));
}

function show_editor(path, readonly=false, newfile=false) {
	if (!path.indexOf("/") > -1)
		path = "/" + path;

	//$("#editorbox").css("visibility", "visible").show();

	$("form[name=editor] label").text(path);
	$("form[name=editor] label").attr("class", "unchanged");

	if (newfile) {
			$("#editorbox").slideDown("slow");
			$("form[name=editor] label").attr("class", "unchanged");
			$("#editorbox").css({display: "block", visibility: "visible"});
			editor.focus();
	} else {
		$.ajax({
			type: "GET",
			url: url_prefix + "/get/raw" + path,
			error: function(ret) {
				show_error(ret.msg);
			},
			success: function(ret) {
				if (ret.state == "fail") {
					ret.msgs.forEach(msg => show_error(msg));
					return;
				}
				$("#editorbox").slideDown("slow");
				editor.focus();
				$("form[name=editor] input[name=contents]").val(ret);
				$("#editorbox").css({display: "block", visibility: "visible"});
				editor.$readOnly = readonly;
				editor.setValue(ret);
				editor.clearSelection();
				editor.focus();
				editor_target = path;
				$("form[name=editor] label").attr("class", "unchanged");
			}
		});
	}
}


function update_active_directory(target) {
	$("#curpath").empty();

	var l = document.createElement("label");
	$(l).text("current path: ");
	$("#curpath").append(l);

	var prepath = url_prefix + "/dir";

	if (target != ".")
		var toks = target.split("/");
	else
		var toks = [""];

	if (toks.length > 0 && toks[0] != "")
		toks = [""].concat(toks);

	for(var tok of toks) {
		var el = document.createElement("a");
		$(el).attr("href", prepath + tok);
		if (tok == "")
			$(el).text("[root]");
		else
			$(el).text(tok);

		$("#curpath").append(el);
		$("#curpath").append(" / ");
		prepath = prepath + tok + "/";
	}
	current_dir = target;

	if (current_dir != "") {
		$("#upload").show();
		$("#files").show();
	} else {
		$("#upload").hide();
		//$("#files").hide();
		/*$("#files").attr("width", "10%");*/
		//$("#files").text("");

		//$("#dirs").attr("display", "block");
	}
}

function show_mode(mymode) {
	// set icon-visibility mode for all items
	let p_modes = ["edit", "rename", "delete", "preview"];
	let a_modes = ["confirm", "cancel"];
	if (a_modes.indexOf(mymode) > -1)
		Object.keys(uid2item).forEach((uid) => show_ctrls(uid, a_modes, p_modes));
	else
		Object.keys(uid2item).forEach((uid) => show_ctrls(uid, p_modes, a_modes));
}

function show_ctrls(uid, show_ops, hide_ops) {
	// set icon-visibility mode for specific item (uid)
	for (let my_mode of show_ops)
		$("#iconbox_" + uid + "_" + my_mode).show();
	for (let my_mode of hide_ops)
		$("#iconbox_" + uid + "_" + my_mode).hide();
}

function ctrl_action(uid, op) {
	let primary_modes = ["rename", "delete", "edit", "preview"];
	let ask_modes = ["confirm", "cancel"];
	let all_modes = primary_modes.concat(ask_modes);

	if (!uid in uid2item) {
		show_error("uid: " + uid + " not found...");
		return;
	}

	var x = uid2item[uid];

	if (ask_modes.indexOf(op) > -1) {
		x.last_mode = x.active_mode;
		x.active_mode = null;
		show_ctrls(x.uid, primary_modes, ask_modes);
	} else { //if (op == "delete" || op == "rename") {
		x.last_mode = null;
		x.active_mode = op;
		if (["delete", "rename", null].indexOf(op) > -1)
			show_ctrls(x.uid, ask_modes, primary_modes);
	}

	if (x.active_mode == "rename") {
		if(uid_editing && (uid_editing != x.uid && x.last_mode == null))
			ctrl_action(uid_editing, "cancel");
		//let focus_cell = $("#" + x.uid + "_name").closest("td");
		$("#" + uid2grid_id[uid]).jsGrid("editItem", x);
		show_ctrls(uid, ask_modes, primary_modes);
		uid_editing = uid;

		$("#iconbox_" + uid + "_confirm").parent().parent().
			css("background-color", "#bababc");

	} else if (x.active_mode == "delete") {
		uid_editing = uid;

		/* load file into editor for ... I guess editing */
	} else if (x.active_mode == "edit") {
		show_editor(x.path);
		show_ctrls(uid, primary_modes, ask_modes);
	}

	if (x.active_mode == "preview") {
		if (x.mimetype === null) {
			show_error("no mimetype, thus no preview!");
			return;
		}
		let main_mime = x.mimetype.substr(0, 5);
		if (["text/", "plain"].indexOf(main_mime) > -1) {
			show_editor(x.path, true);
			show_ctrls(uid, primary_modes, ask_modes);
		} else if (main_mime == "image") {
			show_preview(x.path);
			show_ctrls(uid, primary_modes, ask_modes);
		}	else
			show_error(`mimetype: ${x.mimetype} not yet preview-able...`);
	}

	if (x.active_mode == null) {

		if (x.last_mode == "delete") {
			if (op == "confirm") {
				$("#" + uid2grid_id[uid]).jsGrid("deleteItem", x).done(function() {
					//if (uid2grid_id[uid] != "dirs") @FIXME: do not update full tbl here!
						update_grid(uid2grid_id[uid], current_dir);
					show_ctrls(uid, primary_modes, ask_modes);
				});
			} else
				show_ctrls(uid, primary_modes, ask_modes);

		}	else if (x.last_mode == "rename") {

			if (op == "confirm")
				$("#" + uid2grid_id[uid]).jsGrid("updateItem");
			else {
				$("#" + uid2grid_id[uid]).jsGrid("cancelEdit");
				show_ctrls(uid, primary_modes, ask_modes);
				$("#iconbox_" + uid + "_confirm").parent().parent().
					css("background-color", "unset");
			}
			x.last_mode = null;
		}
	}

}

function update_grid(grid_id, target) {
	//$("#" + grid_id).jsGrid("option", "data", []);

	if (target == null && grid_id == "files")
		target = current_dir;

	if (grid_id == "dirs")
		update_active_directory(target);

	var myurl = url_prefix + "/list/" + grid_id + "/" + target;

	$.ajax({
		type: "GET",
		url: myurl,
		error: function() {
			show_message("error getting files within 'get_dir()'", true);
		},
		success: function(ret) {
			$("#" + grid_id).jsGrid("option", "data", []);
			$("#upload form").attr("action", ret.upload_url);
			$("#newdir form").attr("action", ret.upload_url);

			ret = ret.data;

			if (grid_id == "dirs" && (target != "" && target != ".")) {
				var parent_url = target.split("/").slice(0, -1).join("/");
				$("#" + grid_id).jsGrid("insertItem",
					{"name": "..", "path": parent_url});
			}

			// update size
			ret = ret.map(x => {
				// human-readable
				x.size = readable_size(x.size);
				// set once to be able to identify <td> containing name
				x.name = `<a href="${x.visit_url}" id="${x.uid}_name" class=uniquelink>${x.name}</a>`;
				// active_mode != null, if some intermediate state is active
				// -> confirm: edit, rename, delete + preview
				x.active_mode = null;
				x.last_mode = null;
				x.ctrl = null;
				return x;
			});

			ret.forEach(x => {
				$("#" + grid_id).jsGrid("insertItem", x).then(function(e) {

					$("#" + x.uid + "_name").closest("td").click(
						{x: x, func: update_grid, grid_id: grid_id}, function(e) {
							if (e.data.grid_id == "dirs")
								window.location = $("#" + e.data.x.uid + "_name").attr("href");
							else
								window.location = e.data.x.click_url;
						});

					$("#" + x.uid + "_name").text($(x.name).text());
					x.name = $(x.name).text();

					uid2item[x.uid] = x;
					uid2grid_id[x.uid] = grid_id;

					show_ctrls(x.uid, [], ["confirm", "cancel"]);

				});
			});

			if ($("#dirs table tbody tr:first td:first").text() == "..") {
				$("#dirs table tbody tr:first td:last").text("");
				$("#dirs table tbody tr:first td:first").click(function(e) {
					window.location = url_prefix + "/dir/" + current_dir.split("/").slice(0, -1).join("/");
				});

			}


		}
	});
}

