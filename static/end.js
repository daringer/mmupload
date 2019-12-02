"use strict";

var MyCtrlField = function(config) {
	jsGrid.Field.call(this, config);
};

MyCtrlField.prototype = new jsGrid.Field({

	grid_id: "dirs",  // or dir

	editing: false,
	inserting: false,
	sorting: false,
	filtering: false,

	itemTemplate: function(value, item) {
			return this.render_contents(item);
	},

	render_contents: function(item) {
		let base_url = "/local/icon/";
		let suffix = ".svg";

		let	ctrl_items = [
				["edit",    "pencil"],
				["rename",  "rename-box"],
				["delete",  "delete"],
				["preview", "magnify"],
				["confirm", "check"],
				["cancel",  "close"]
			];
		var htmls = ctrl_items.map((data, idx) =>
				"<div class=iconbox id='iconbox_" + item.uid + "_" + data[0] +
						"' onclick='ctrl_action(\"" + item.uid + "\", \"" + data[0] + "\");'" +
					  "  onload='show_mode(\"" + item.active_mode + "\");' >" +
				"<img src='" + base_url + data[1] + "' class='icon' alt='" +
									data[0] + "' />" +
			  "<span class=tooltip>" + data[0] + "</span>" +
			  "</div>"
		);
		return htmls.join("");
	}

});

jsGrid.fields.myctrl = MyCtrlField;

var dir_grid = $("#dirs").jsGrid({

    width: "100%",

    editing: true,
    sorting: true,

		confirmDeleting: false,

    fields: [
      { name: "name", title: "Directory Name", type: "text", width: 300 },
   		{ name: "path", type: "text", visible: false},
	  	{ name: "mimetype", type: "text", visible: false},
      { name: "move_url", type: "text", visible: false},
      { name: "delete_url", type: "text", visible: false},
      { name: "click_url", type: "text", visible: false},
			{ name: "size", title: "Tree Size", type: "text", align: "left",
				readOnly: true, editing: false, visible: false},
  		{ name: "ctrl", title: "", type: "myctrl", grid_id: "dirs", width: 150}
    ],

		rowClick: function(args) {},

		onItemEditing: function(args) {
				//focus_cell.closest("input").focus();
			  // @TODO: focus name cell HERE!!!
		},

		// before updating is done in grid
		onItemUpdating: function(args) {
				if (args.item.name != "")
						$.ajax({
							type: "POST",
							data: {new_target: args.item.name},
							url: args.item.move_url,
							error: function() {
								show_message("error moving", true);
							},
							success: function(ret) {
								show_message(ret["msg"]);
								update_grid("dirs", current_dir, true);
							}
				})
		},

		// before deletion is done in grid
    onItemDeleting: function(args) {
			$.ajax({
				type: "POST",
				url: args.item.delete_url,
				error: function() {
					show_message("error deleting path", true);
				},
				success: function(ret) {
					show_message(ret["msg"]);
				}
			});
		},

		onItemDeleted: function(args) {
			/*args.grid.render().then(function() {
				show_mode(args.item.active_mode);
			});*/
		}

});

var file_grid = $("#files").jsGrid({

    width: "100%",

    editing: true,
    sorting: true,
		confirmDeleting: false,

    fields: [
      { name: "name", title: "Name", type: "text", width: 500 },
      { name: "path", type: "text", visible: false},
      { name: "short", title: "Public short-url", type: "text", width: 200},
      /* { name: "zones", type: "text", visible: false}, */
			{ name: "mimetype", type: "text", visible: false},
      { name: "move_url", type: "text", visible: false},
      { name: "delete_url", type: "text", visible: false},
      { name: "click_url", type: "text", visible: false},
			{ name: "size", title: "Size", type: "text", align: "left", readOnly: true, editing: false},
  		{ name: "ctrl", title: "", type: "myctrl", grid_id: "files", width: 180}
    ],

		rowClick: function(args) {},

		// before updating is done in grid
		onItemUpdating: function(args) {
				if (args.item.name != "")
						$.ajax({
							type: "POST",
							data: { new_target: args.item.name, new_short: args.item.short },
							url: args.item.move_url,
							error: function() { show_error("error moving"); },
							success: function(ret) {
								show_message(ret["msg"]);
								update_grid("files", current_dir, true);
							}
						});
		},
		// before deletion is done in grid
    onItemDeleting: function(args) {
			$.ajax({
				type: "POST",
				url: args.item.delete_url,
				error: function() {
					show_error("error deleting path");
				},
				success: function(ret) {
					show_message(ret["msg"]);
				}
			});
		}
});

$(function() {
	update_grid("dirs", current_dir);
	update_grid("files", current_dir, true);

	/* editor stuff */

	$("#editorbox").hide();

	var editor = ace.edit("editor");
  editor.setTheme("ace/theme/twilight");
  //editor.session.setMode("ace/mode/javascript");

	$("form[name=editor] input[name=what]").click(function(ev) {
			$("form[name=editor] input[name=data]").val(editor.getValue());
	});
	$("form[name=editor] input[name=clear]").click(function(ev) {
			editor.setValue("");
	});
	$("form[name=editor] input[name=hide]").click(function(ev) {
			editor.setValue("");
			$("#editorbox").hide();
			$("form[name=newpaste] input[name=what]").show();
	});

	$("form[name=newpaste] input[name=what]").click(function(ev) {
		$("#editorbox").show();
		editor.focus();
		$("form[name=newpaste] input[name=what]").hide();
		return false;
	});

	/* new-dir stuff */

	$("form[name=newdir]").submit(function(ev) {
		ev.preventDefault();

		var newdir_name = $("form[name=newdir] input[name=new_dirname]").val();
		$.ajax({
			type: "POST",
			data: { what: "create", new_dirname: newdir_name },
			url: $("form[name=newdir]").attr("action"),
			error: function() {
				show_message(`failed creation directory: {newdir_name}`);
			},
			success:  function(ret) {
				ret.msgs.forEach(show_message);
				update_grid("dirs", ret.dirname);
				update_active_directory(ret.dirname);

				// clear input text field for directory
				$("form[name=newdir] input[type=text]").val("");
			}
		});
	});

	/* upload stuff */

	$("#upload").ajaxForm(function(ret) {
  	show_message("file uploaded successfully");
		update_grid("files", current_dir);

		// clear upload file name field
		$("form[name=upload] input[type=file]").val("");
  });

});


