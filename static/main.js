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


function show_message(msg, error=false) {
		if (msg == "None")
			return;

		var el = document.createElement("div");
		$(el).text(msg).attr("class", (error) ? "err" : "info").hide();
		$("#flash").append(el);
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


}

function show_editor(path) {
	$.ajax({
		type: "GET",
		url: url_prefix + "/get/raw" + path,
		error: function(ret) { show_error(ret.msg); },
		success: function(ret) {
			$("form[name=editor] input[name=contents]").val(ret);
			editor.setValue(ret);
			editor.clearSelection();
			$("form[name=editor] input[name=what]").click(function(ev) {
				$("form[name=editor] input[name=contents]").val(editor.getValue());
				//ev.preventDefault();
				//alert($("form[name=editor] input[name=contents]").val());
			});
		}
	});

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
	} else {
		x.last_mode = null;
		x.active_mode = op;
		show_ctrls(x.uid, ask_modes, primary_modes);
	}

	if (x.active_mode == "rename") {
		if(uid_editing && (uid_editing != x.uid && x.last_mode == null))
			ctrl_action(uid_editing, "cancel");
		//let focus_cell = $("#" + x.uid + "_name").closest("td");
		$("#" + uid2grid_id[uid]).jsGrid("editItem", x);
		show_ctrls(uid, ask_modes, primary_modes);
		uid_editing = uid;

	} else if (x.active_mode == "delete") {
		uid_editing = uid;

	}

	if (x.last_mode == "edit") {
			alert("confirm edit");
	}

	if (x.active_mode == "preview") {
		alert("confirm preview");
	}

	if (x.active_mode == null) {
		if (x.last_mode == "delete") {
			if (op == "confirm") {
				$("#" + uid2grid_id[uid]).jsGrid("deleteItem", x).done(function() {
					update_grid(uid2grid_id[uid], current_dir);
					show_ctrls(uid, primary_modes, ask_modes);
				});
			} else {
				show_ctrls(uid, ask_modes, primary_modes);
			}
		}

		else if (x.last_mode == "rename") {

			if (op == "confirm")
				$("#" + uid2grid_id[uid]).jsGrid("updateItem");
			else {
				$("#" + uid2grid_id[uid]).jsGrid("cancelEdit");
				show_ctrls(uid, primary_modes, ask_modes);
			}
			x.last_mode = null;

		}
	}

}

function update_grid(grid_id, target) {
	//$("#" + grid_id).jsGrid("option", "data", []);

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
								if (e.data.grid_id == "dirs") {
									//e.data.func("dirs", e.data.x.path);
									//e.data.func("files", e.data.x.path, true);
									window.location = $("#" + e.data.x.uid + "_name").attr("href");
								} else {
									window.location = e.data.x.click_url;
								}
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
						/*update_grid("files", current_dir.split("/").slice(0, -1).join("/"));
						update_grid("dirs", current_dir.split("/").slice(0, -1).join("/"));*/
						window.location = "/dir/" + current_dir.split("/").slice(0, -1).join("/");
					});

				}


			}
	});
}

