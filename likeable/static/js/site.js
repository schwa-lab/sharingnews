$(window).load(function() {
  $('.resizable').each(function() {
  	var el = this;
  	$(el).resizable({
  	  alsoResize: $('iframe', el)
  	});
  });
});
