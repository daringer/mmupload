"use strict";

/** back + forward + reload button handling **/
function add_history_entry(action) {
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

function show_message(msg, error=false) {
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
			/*$("#files").attr("width", "10%");
			$("#files").text("");*/

			//$("#dirs").attr("display", "block");
		}
}


function update_grid(grid_id, target, history_skip=false) {
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
				if (!history_skip)
						add_history_entry(["update_grid", grid_id, target, true]);

				if (grid_id == "dirs" && (target != "" && target != ".")) {
					var parent_url = target.split("/").slice(0, -1).join("/");
					$("#" + grid_id).jsGrid("insertItem",
						{"name": "..", "path": parent_url});
				}

				// update size
			  ret = ret.map(x => {
					x.size = readable_size(x.size);
					x.name = `<a id="${x.uid}_name" class=uniquelink>${x.name}</a>`;
					x.ctrl_rename = `<a id="${x.uid}_rename" class=uniquelink>rename</a>`;
					x.ctrl_delete = `<a id="${x.uid}_delete" class=uniquelink>delete</a>`;
					x.ctrl_edit = `<a id="${x.uid}_edit" class=uniquelink>edit</a>`;
					x.ctrl_preview = `<a id="${x.uid}_preview" class=uniquelink>preview</a>`;
					return x;
				});

				ret.forEach(x => {
					$("#" + grid_id).jsGrid("insertItem", x).then(function(e) {
						$("#" + x.uid + "_name").closest("td").click({x: x, func: update_grid, grid_id: grid_id},
							function(e) {
								if (e.data.grid_id == "dirs") {
									e.data.func("dirs", e.data.x.path);
									e.data.func("files", e.data.x.path, true);
								} else {
									window.location = e.data.x.click_url;
								}
						});
						$("#" + x.uid + "_name").text($(x.name).text());
						x.name = $(x.name).text();
						$("#" + x.uid + "_rename").click({x: x, func: update_grid, grid_id: grid_id},
							function(e) {
									alert("iodsfj");
									$("#" + e.data.grid_id).jsGrid("editItem", x);
							}
						);

						$("#" + x.uid + "_delete").click({x: x, func: update_grid, grid_id: grid_id},
							function(e) {
							$("#" + e.data.grid_id).jsGrid("deleteItem", x);
						});
						$("#" + x.uid + "_edit").click({x: x, func: update_grid, grid_id: grid_id},
						function(e) {
							alert("...");
						});
						$("#" + x.uid + "_preview").click({x: x, func: update_grid, grid_id: grid_id},
							function(e) {
							alert("...");
						});

						// insert to jsgrid
					});
				});

				if ($("#dirs table tbody tr:first td:first").text() == "..") {
					$("#dirs table tbody tr:first td:last").text("");
					$("#dirs table tbody tr:first td:first").click(function(e) {
						update_grid("files", current_dir.split("/").slice(0, -1).join("/"));
						update_grid("dirs", current_dir.split("/").slice(0, -1).join("/"));
					});

				}


				/*if (grid_id == "files") {
					var el = document.createElement("a");
					$(el).text("edit").attr("href", "#").click(function(ev) {
						alert("kciked edit");
						ev.preventDefault();
					});
					ret.forEach(x => $("#dirs tbody tr:last td:last").append(el));
				}*/
			}
	});
}

