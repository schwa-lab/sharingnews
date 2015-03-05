$(window).load(function() {
  $('.resizable').each(function() {
  	var el = this;
  	$(el).resizable({
  	  alsoResize: $('iframe', el)
  	});
  });
});
$.fn.enterKey = function (fnc, mod) {
    return this.each(function () {
        $(this).keypress(function (ev) {
            var keycode = (ev.keyCode ? ev.keyCode : ev.which);
            if ((keycode == '13' || keycode == '10') && (!mod || ev[mod + 'Key'])) {
                fnc.call(this, ev);
            }
        })
    })
}

String.prototype.lpad = function(padString, length) {
    var str = this;
    while (str.length < length)
        str = padString + str;
    return str;
}
