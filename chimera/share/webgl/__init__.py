import os
GLSL = [os.path.join(__path__[0], x) for x in [
	'default.fs.glsl',
	'offset.vs.glsl',
	'cylinder.vs.glsl',
	'nolight.vs.glsl',
]]
HTML = os.path.join(__path__[0], 'index.html')
JAVASCRIPT = [os.path.join(__path__[0], x) for x in [
	'vsphere.js', 'molview.js'
]]

_USE_THREAD = False	# TODO: figure out why this deadlocks

def write_json(output):
	import chimera
	if _USE_THREAD:
		# x3dWrite doesn't give up the GIL, but, x3dOuput,
		# a Python file object, does.
		import os, threading
		(read, write) = os.pipe()
		x3dInput = os.fdopen(read, 'rb')
		x3dOutput = os.fdopen(write, 'wb')

		# consume piped X3D output in separate thread
		def consume(x3dInput=x3dInput, output=output):
			from . import x3d2json
			import xml.etree.cElementTree as ET
			json = x3d2json.JSON(output)
			ET.parse(x3dInput, parser=ET.XMLParser(target=json))

		consumer = threading.Thread(target=consume)
		consumer.start()
	else:
		import tempfile
		x3dOutput = tempfile.TemporaryFile()

	title = ""
	try:
		clipping = chimera.viewer.clipping
		chimera.viewer.clipping = True	# want hither/yon planes
		chimera.viewer.x3dWrite(x3dOutput, 0, title)
	finally:
		chimera.viewer.clipping = clipping
	if _USE_THREAD:
		x3dOutput.close()    # explicitly close so consumer can finish
		consumer.join()
	else:
		x3dOutput.seek(0)
		from . import x3d2json
		import xml.etree.cElementTree as ET
		json = x3d2json.JSON(output)
		ET.parse(x3dOutput, parser=ET.XMLParser(target=json))
		x3dOutput.close()

	output.flush()

def write_webgl(path):
	import chimera
	output = open(path, 'w')
	width, height = chimera.viewer.windowSize
	# write html preamble
	_inlinefile(HTML, output, {
		'@WIDTH@': width, '@HEIGHT@': height
	})
	# write shaders
	for glsl in GLSL:
		if glsl.endswith('.vs.glsl'):
			shtype = "x-shader/x-vertex"
		elif glsl.endswith('.fs.glsl'):
			shtype = "x-shader/x-fragment"
		else:
			continue
		shid = os.path.basename(glsl)[0:-5]
		output.write('<script id="%s" type="%s">\n' % (shid, shtype))
		_inlinefile(glsl, output)
		output.write('</script>\n')
	# write data
	output.write('<script>\n')
	print >> output, "var json = "
	write_json(output)
	# write gui
	for js in JAVASCRIPT:
		_inlinefile(js, output)
	output.write('</script>\n')
	output.close()

def _inlinefile(filename, output, subsitutions={}):
	with open(filename) as f:
		for line in f.readlines():
			for key, value in subsitutions.items():
				line = line.replace(key, str(value))
			output.write(line)
	output.flush()

def _htmlEscape(s, quotes=False):
	"""Make string safe for HTML

	Expand unicode characters into their corresponding
	HTML codepoint name"""
	if not isinstance(s, unicode):
		s = s.decode('utf-8')
	QUOTES = set([ord('"'), ord("'")])
	import htmlentitydefs as hd
	expand = [ord(c) for c in s]
	if quotes:
		for i in range(len(expand)):
			c = expand[i]
			if c in hd.codepoint2name:
				expand[i] = u'&%s;' % hd.codepoint2name[c]
			else:
				expand[i] = unichr(c)
	else:
		for i in range(len(expand)):
			c = expand[i]
			if c in hd.codepoint2name and c not in QUOTES:
				expand[i] = u'&%s;' % hd.codepoint2name[c]
			else:
				expand[i] = unichr(c)
	return u''.join(expand).encode('ascii', 'xmlcharrefreplace')

def write_notebook(title="Chimera Notebook", directory=None):
	import chimera
	if directory is None:
		if chimera.nogui:
			raise ValueError, "Need explicit directory in nogui mode\n"
		from OpenSave import SaveModal
		# TODO: add title field to save dialog
		sm = SaveModal(title="WebGL Notebook", dirsOnly=True,
							historyID='notebook')
		pathsAndTypes = sm.run(chimera.tkgui.app)
		sm.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise ValueError, 'No file chosen'
		directory = pathsAndTypes[0][0]
	from Animate.Scenes import scenes
	names = scenes.names()
	write_scenes(names, title, directory)

def write_scenes(names=[], title="Chimera Notebook", directory=None):
	import os, Midas
	try:
		os.mkdir(directory)
	except OSError as e:
		# it's normal that the directory already exists
		import errno
		if e.errno != errno.EEXIST:
			raise

	from Animate.Scenes import scenes
	# save current view as as scene
	curname = scenes.append().name
	try:
		# iterate through scenes:
		import chimera
		w, h = chimera.viewer.windowSize
		tnw = int(w / 4)
		tnh = int(h / 4)
		done = set()
		these_scenes = []
		for name in names:
			sc = scenes.getScene_by_name(name)
			if sc:
				these_scenes.append(sc)
		for sc in these_scenes:
			if sc.name in done:
				continue
			scenes.show(sc.name)
			# Wait for updates to settle down
			Midas.wait(1)
			# save thumbnail
			fn = os.path.join(directory, '%s_tn.png' % sc.name)
			Midas.copy(file=fn, format="PNG", width=tnw, height=tnh)
			# save full size image
			fn = os.path.join(directory, '%s.png' % sc.name)
			Midas.copy(file=fn, format="PNG")
			# save single webgl file
			fn = os.path.join(directory, '%s.html' % sc.name)
			Midas.export(filename=fn, format='WebGL')
			done.add(sc.name)
	finally:
		# restore "current" scene and delete it
		scenes.show(curname)
		scenes.remove(curname)

	# write out index.html
	fn = os.path.join(directory, 'index.html')
	f = open(fn, 'w')
	t = _htmlEscape(title)
	sceneNames = list()
	descriptions = list()
	for sc in these_scenes:
		sceneNames.append(_htmlEscape(sc.name))
		descriptions.append(_htmlEscape(sc.description))
	sceneList = "      var images = [ %s ];" % ", ".join([ repr(n) for n in sceneNames ])
	descList = "      var descriptions = [ %s ];" % ", ".join([ repr(d) for d in descriptions ])
	f.write(
"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Final//EN">
<!-- vi: sw=2:
-->
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    <script type="text/javascript" src="http://www.cgl.ucsf.edu/chimera/webgl/PhiloGL-1.3.0.js"></script>
    <script>
	var borderStyle = "2px solid";
	var lastSelected = null;
	var keyframes = new Array();

	function finishLoad()
	{
		var div = document.getElementById("keyframes");
		for (var i = 0; i < images.length; ++i) {
			var img = document.createElement("img");
			img.src = images[i] + "_tn.png";
			img.style.border = borderStyle + "#f0f0f0";
			img.addEventListener("click", function(){show_in_main(this);});
			img.description = descriptions[i];
			div.appendChild(img);
			keyframes.push(img)
		}
		if (keyframes.length > 0)
			show_in_main(keyframes[0]);
		document.addEventListener("keydown", handle_keys, false);
		var button = document.getElementById("button");
		button.addEventListener("click", toggleMain, false);
	}

	function show_in_main(element)
	{
		// Show image
		var base = element.src.replace(/_tn\.png$/, "").replace(/.*\//, "");
		var div = document.getElementById("main");
		var img = document.createElement("img");
		img.src = base + ".png";
		while (div.firstChild)
			div.removeChild(div.firstChild);
		div.appendChild(img);
		// Show description
		var p = document.getElementById("description");
		p.innerHTML = element.description;
		// Update button text
		var button = document.getElementById("button");
		button.innerHTML = "Load 3D Data";
		// Update borders
		if (lastSelected)
			lastSelected.style.border = borderStyle + "#f0f0f0";
		lastSelected = element;
		lastSelected.style.border = borderStyle + "#00ff00";
	}

	function loadWebGL()
	{
		// Display graphics (if main div is displaying image)
		var div = document.getElementById("main");
		var element_list = div.getElementsByTagName("img");
		if (element_list.length == 0)
			return;
		var img = element_list[0];
		var obj = document.createElement("object");
		obj.data = img.src.replace(/.png$/, ".html");
		obj.width = img.width + 30;
		obj.height = img.height + 30;
		while (div.firstChild)
			div.removeChild(div.firstChild);
		div.appendChild(obj);
		// Update button text
		var button = document.getElementById("button");
		button.innerHTML = "Load Image";
	}

	function loadImage()
	{
		if (lastSelected)
			show_in_main(lastSelected);
	}

	function toggleMain()
	{
		var button = document.getElementById("button");
		if (button.innerHTML == "Load Image")
			loadImage();
		else
			loadWebGL();
	}

	var left_arrow = 37;
	var right_arrow = 39;
	var key_l = 76;
	var key_i = 73;

	function handle_keys(event)
	{
		if (!event)
			var event = window.event;
		var code = 0;
		if (event.keyCode)
			code = event.keyCode;
		else if (event.which)
			code = event.which;
		switch (code) {
		  case left_arrow:
			var n = current_keyframe_index();
			if (n == -1)
				show_in_main(keyframes[keyframes.length - 1]);
			else if (n > 0)
				show_in_main(keyframes[n - 1]);
			break;
		  case right_arrow:
			var n = current_keyframe_index();
			if (n == -1)
				show_in_main(keyframes[0]);
			else if (n < keyframes.length - 1)
				show_in_main(keyframes[n + 1]);
		  	break;
		  case key_i:
			loadImage();
			break;
		  case key_l:
		  	loadWebGL();
			break;
		  default:
		  	return true;
		}
		event.preventDefault();
		return false;
	}

	function current_keyframe_index()
	{
		for (var i = 0; i < keyframes.length; ++i)
			if (lastSelected == keyframes[i])
				return i;
		return -1;
	}
    </script>
    <script>%s\n%s</script>
    <title>%s</title>
  </head>

  <body onload="finishLoad()">
    <h1>%s</h1>
    <div id="keyframes"
        style="overflow:auto; white-space:nowrap; background-color:#f0f0f0">
    </div>
    <p align="center">
    	click thumbnail or press left- and right-arrow to select view;
	press &quot;l&quot; to load 3D data;
	press &quot;i&quot; to load image</p>
    <div align="center">
      <button id="button" type="button"></button>
    </div>
    <div align="center" id="main">
    </div>
    <div align="center">
      <p id="description"/>
    </div>
  </body>
</html>
""" % (sceneList, descList, t, t))
