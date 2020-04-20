
function show_error(msg) {
	show_message(msg, 1000, 15000, true);
}

function show_message(msg, fade_in=1000, fade_out=15000, error=false) {
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
	$(el).html(msg).attr("class", (error) ? "err" : "info").hide();
	$(el).prepend(ic);
	$("#flash").prepend(el);
	$(el).fadeIn(1000, function() {
		$(el).fadeOut(15000, function() {
			$(el).remove();
		});
	});
}


