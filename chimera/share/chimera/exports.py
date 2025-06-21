"""keep track of export file formats for 3D scenes"""

# add new built-in formats at end of this file

def register(type, glob, suffix, command, notes=None):
	"""register new export file type
	
	The glob and suffix arguments are the same as Save dialogs.
	command is the python command with a filename to save exported data.
	notes are additional information to display in export dialog in HTML.
	"""
	_exportInfo[type] = {
		'glob': glob,
		'suffix': suffix,
		'command': command,
		'notes': notes
	}

def getFilterInfo():
	"""get list of export file types in the right format for a Save dialog"""
	fileTypes = _exportInfo.keys()
	fileTypes.sort()
	filterInfo = [
		(i, _exportInfo[i]['glob'], _exportInfo[i]['suffix'])
		for i in fileTypes
	]
	return filterInfo

def getNotes(name):
	"""Get the (html) notes for a particular export file type"""
	notes = _exportInfo[name]['notes']
	if not notes:
		notes = "<i>No additional information available.</i>"
	return notes

def doExportCommand(name, filename):
	"""Export the scene to filename with the given export file type"""
	import chimera
	if chimera.nogui and chimera.opengl_platform() != 'OSMESA':
		raise chimera.UserError, "Need graphics to export data (or use headless Linux version)"
	import replyobj
	replyobj.status("Exporting %s data to %s" % (name, filename))
	_exportInfo[name]['command'](filename)
	replyobj.status("Finished exporting %s." % filename)

def x3dConvert(program, filename):
	"""Helper function for X3D converters that runs an external progam
	with chimera X3D piped to standard input and with a "-o filename"
	arguments for where to save the output.
	"""
	import chimera
	title=""
	from CGLutil.findExecutable import findExecutable
	path = findExecutable(program)
	if path is None:
		raise chimera.NonChimeraError("Unable to find executable '%s' program needed to convert X3D output" % program)
	try:
		from SubprocessMonitor import Popen, PIPE
		cmd = [path, '-o', filename]
		proc = Popen(cmd, stdin=PIPE)
		chimera.viewer.x3dWrite(proc.stdin, 0, title,
                                        ' ' + chimera.version.release)
		proc.stdin.close()
		returncode = proc.wait()
		if returncode == 1:
			raise chimera.NonChimeraError("Error writing %s"
							% (filename))
		elif returncode != 0:
			raise RuntimeError("'%s' exited with error code %d"
							% (path, returncode))
	except chimera.error, v:
		raise chimera.UserError(v)
_x3dConvert = x3dConvert

# default "built-in" export information support

def _x3d(filename):
	import chimera
	title=""
	try:
		chimera.viewer.x3dWrite(filename, title,
                                        ' ' + chimera.version.release)
	except IOError, v:
		raise chimera.NonChimeraError("Error writing x3d file: " + str(v))
	except chimera.error, v:
		raise chimera.UserError(v)

def _exportSTL(filename):
	# Determine endian-ness
	import struct
	if struct.pack("h", 1) == "\000\001":
		big_endian = 1
	else:
		big_endian = 0
	if big_endian:
		import chimera
		raise chimera.NonChimeraError("Only support STL output on little-endian computers")
	return x3dConvert("x3d2stl", filename)

from chimerax import export_cx
_exportInfo = {
	'VRML': {
		'glob': ('*.wrl', '*.vrml'),
		'suffix': ".wrl",
		'command': lambda filename: x3dConvert("x3d2vrml", filename),
		'notes': "Exports scene in"
			" <a href='http://www.web3d.org/x3d/vrml/'>VRML97</a>"
			" (<i>a.k.a.</i>, VRML 2.0) format."
			"  Not supported: hither/yon clipping, per-model"
			" clipping planes, depth-cueing, stereo,"
			" dashed lines."
	},
	"POV-Ray": {
		'glob': "*.pov",
		'suffix': ".pov",
		'command': lambda filename: x3dConvert("x3d2pov", filename),
		'notes': "Export scene in the"
			" <a href='http://www.povray.org'>POV-Ray</a>"
			" scene description language." 
			"  Not supported: hither/yon clipping,"
			" depth-cueing, stereo, dashed lines."
	},
	"RenderMan": {
		'glob': "*.rib",
		'suffix': ".rib",
		'command': lambda filename: x3dConvert("x3d2RM", filename),
		'notes': "Export scene in"
			" <a href='http://www.renderman.org'>RenderMan</a>"
			" Interface Bytestream."
			"  Not supported: stereo, dashed lines."
	},
	"X3D": {
		'glob': "*.x3d",
		'suffix': ".x3d",
		'command': _x3d,
		'notes': "Export scene in the"
			" <a href='http://www.web3d.org/x3d/'>X3D</a>"
			" XML-enabled 3D file format."
			"  Not supported: hither/yon clipping, per-model"
			" clipping planes, depth-cueing."
			"  Although there are annotations for everything but"
			" stereo."
	},
	"STL": {
		'glob': "*.stl",
		'suffix': ".stl",
		'command': _exportSTL,
		'notes': "Export scene in the binary"
		" <a href='http://en.wikipedia.org/wiki/STL_(file_format)'>"
			"STL</a> triangle file format."
			"  Not supported: hither/yon clipping, per-model"
			" clipping planes, color, points, lines, text,"
			" and stereo."
	},
	"ChimeraX": {
		'glob': "*.py",
		'suffix': ".py",
		'command': export_cx,
		'notes': "Export scene as a Python file that can be opened in"
		" <a href='http://www.cgl.ucsf.edu/chimerax'>UCSF ChimeraX</a>."
			" Currently only atomic models are exported."
	}
}
