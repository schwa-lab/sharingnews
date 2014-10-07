$(window).load(function() {
  $('.resizable').each(function() {
  	var el = this;
  	$(el).resizable({
  	  alsoResize: $('iframe', el)
  	});
  });
});
$.fn.enterKey = function (fnc) {
    return this.each(function () {
        $(this).keypress(function (ev) {
            var keycode = (ev.keyCode ? ev.keyCode : ev.which);
            if (keycode == '13') {
                fnc.call(this, ev);
            }
        })
    })
}
