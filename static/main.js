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
			$("#files").hide();
		}
}


function update_grid(grid_id, target, history_skip=false) {
	$("#" + grid_id).jsGrid("option", "data", []);
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

				ret.forEach(x => $("#" + grid_id).jsGrid("insertItem", x) );

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

