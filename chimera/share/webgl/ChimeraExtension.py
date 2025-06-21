def write_webgl(path):
	import webgl 
	webgl.write_webgl(path)

webgl_descrip = 'Experimental.  Export scene in <a href="http://en.wikipedia.org/wiki/HTML5">HTML 5</a> format with embedded <a href="http://en.wikipedia.org/wiki/WebGL">WebGL</a>.'

def write_json(path):
	import webgl 
	output = open(path, 'w')
	webgl.write_json(output)
	output.close()

json_descrip = 'Export scene in <a href="http://en.wikipedia.org/wiki/JSON">JSON</a> file format that is suitable for Chimera\'s WebGL stub viewer.'

def write_scenes(path):
	import webgl 
	webgl.write_scenes(path)

scenes_descrip = 'Experimental.  Export all saved scenes as a table in <a href="http://en.wikipedia.org/wiki/HTML5">HTML 5</a> format with embedded <a href="http://en.wikipedia.org/wiki/WebGL">WebGL</a> hidden by static images.'

from chimera import exports
exports.register('WebGL', '*.html', '.html', write_webgl, webgl_descrip)
#exports.register('JSON', '*.json', '.json', write_json, json_descrip)
#exports.register('WebGL Notebook', '*.nb', '.nb', write_scenes, scenes_descrip)
