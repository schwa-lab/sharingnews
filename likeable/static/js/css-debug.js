function _template(str, tpl) {
  if (!str) return '';
  var split = str.split(/\s+/).filter(function(s){return s;})
  var out = '';
  for (var i = 0; i < split.length; i++) {
    out += tpl.replace('{}', split[i]);
  }
  return out;
}
function compileSelector(node) {
  if (!node)
    return '';
  var classes = _template(node.className, '.{}');
  var properties = _template(node.getAttribute('property'), '[property~="{}"]');
  var itemprop = _template(node.getAttribute('itemprop'), '[itemprop~="{}"]');
  var id = node.getAttribute('id');
  var prefix = node.parentElement ? compileSelector(node.parentElement) + ' > ' : '';
  return prefix + node.tagName + classes + properties + itemprop + (id ? '#' + id : '');
}

var attrs = ['content', 'datetime', 'title', 'rel'];
document.addEventListener('click', function(evt) {
  var msg = compileSelector(evt.target);
  // HACK?
  if (msg.indexOf('#cssdebugmetalisting') != -1)
    return false;
  for (var i = 0; i < attrs.length; i++) {
    var val = evt.target.getAttribute(attrs[i]);
    if (val) {
      msg += '\\n' + attrs[i] + ' :: ' + val;
    }
  }
  alert(msg);
  return false;
}, false);

(function() {
    var metas = document.getElementsByTagName('meta');
    var dl = document.createElement('dl')
    dl.setAttribute('id', 'cssdebugmetalisting');
    for (var i = 0; i < metas.length; i++) {
        var descr = []
        var content = ''
        for (var j = 0; j < metas[i].attributes.length; j++) {
            var a = metas[i].attributes[j];
            if (a.name == 'content') {
                content = a.value;
            } else {
                descr.push(a.name + '="' + a.value + '"');
            }
        }
        var dt = document.createElement('dt');
        dt.appendChild(document.createTextNode('[' + descr.join(', ') + ']::attr(content)'));
        dl.appendChild(dt);
        var dd = document.createElement('dd');
        dd.appendChild(document.createTextNode(content));
        dl.appendChild(dd);
    }
    var body = document.getElementsByTagName('body')[0];
    body.insertBefore(dl, body.childNodes[0]);
})()
