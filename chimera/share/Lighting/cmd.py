# chimera lighting command
#
#	lighting mode [mode]
#		If no argument, show the current mode, otherwise, set it.
#		mode can be one of ambient, single, two-point, three-point
#	lighting brightness [brightness]
#		If no argument, show the current brightness, otherwise, set it.
#		brightness must be > 0
#	lighting contrast [contrast]
#		If no argument, show the current contrast, otherwise, set it.
#		contrast must be >= 0 and <= 1
#	lighting ratio [ratio]
#		If no argument, show the current ratio, otherwise, set it.
#		ratio must be >= 1
#	lighting key|fill|back color [color_spec]
#	lighting key|fill|back direction [x y z]
#	lighting key|fill|back specular_intensity [intensity]
#		change specific light properties
#	lighting restore name
#		restore named lighting style
#	lighting save name
#		save current settings in named lighting style
#	lighting delete name
#		delete named lighting style
#	lighting sharpness [sharpness]
#	lighting reflectivity [reflectivity]

from Midas import MidasError, convertColor
from Midas.midas_text import doExtensionFunc, keyword_match, first_arg
from chimera import replyobj
import Lighting

# CmdInfo is initialized at the end of this file

def lighting(cmdName, args):
	name, args = first_arg(args)
	if not name:
		raise MidasError("need at least one argument to %s" % cmdName)
	subcmd = keyword_match(name, CMDS)
	if not CmdInfo[subcmd][1] or args:
		CmdInfo[subcmd][2](CMDS[subcmd], args)
	else:
		CmdInfo[subcmd][1](CMDS[subcmd])

def mode(cmdName):
	replyobj.status("Current lighting mode is %s" % Lighting.mode(), log=True)

def setMode(cmdName, arg):
	MODES = Lighting.MODES
	mode = MODES[keyword_match(arg, MODES)]
	Lighting.setMode(mode)

def brightness(cmdName):
	replyobj.status("Current brightness is %s" % Lighting.brightness(), log=True)

def setBrightness(cmdName, arg):
	try:
		brightness = float(arg)
	except ValueError:
		raise MidasError('expecting a number for brightness')
	try:
		Lighting.setBrightness(brightness)
	except ValueError, e:
		raise MidasError(str(e))

def contrast(cmdName):
	mode = Lighting.mode()
	if mode == Lighting.AMBIENT:
		replyobj.status("Not applicable", log=True)
		return
	replyobj.status("Current contrast is %s" % Lighting.contrast(),
								log=True)

def setContrast(cmdName, arg):
	try:
		contrast = float(arg)
	except ValueError:
		raise MidasError('expecting a number for contrast')
	try:
		Lighting.setContrast(contrast)
	except ValueError, e:
		raise MidasError(str(e))

def ratio(cmdName):
	mode = Lighting.mode()
	if mode in (Lighting.AMBIENT, Lighting.ONE):
		replyobj.status("Not applicable", log=True)
		return
	maxr = Lighting.maximum_ratio(Lighting.contrast())
	if mode == Lighting.ONE:
		msg = "Effective key-fill ratio is %s" % maxr
	else:
		ratio = Lighting.ratio()
		msg = "Current key-fill ratio is %s" % ratio
		if ratio > maxr:
			msg += " (limited to %s)" % maxr
	replyobj.status(msg, log=True)

def setRatio(cmdName, arg):
	try:
		ratio = float(arg)
	except ValueError:
		raise MidasError('expecting a number for key-fill ratio')
	try:
		Lighting.setRatio(ratio)
	except ValueError, e:
		raise MidasError(str(e))

def lightColor(light):
	color = Lighting.lightColor(light)
	replyobj.status("%s light color is (%g, %g, %g)" % ((light,) + color), log=True)

def setLightColor(light, args):
	Lighting.setLightColor(light, convertColor(args))

def lightDirection(light):
	dir = Lighting.lightDirection(light)
	replyobj.status("%s light direction is (%g, %g, %g)" % ((light,) + dir), log=True)

def setLightDirection(light, args):
	# args should be a xyz 3-tuple
	try:
		x, y, z = [float(x) for x in args.split()]
	except ValueError:
		raise MidasError("expected x y z values")
	try:
		Lighting.setLightDirection(light, (x, y, z))
	except ValueError, e:
		raise MidasError(str(e))

def lightSpecularIntensity(light):
	i = Lighting.lightSpecularIntensity(light)
	replyobj.status("%s light specular intensity is %s" % (light, i), log=True)

def setLightSpecularIntensity(light, args):
	try:
		i = float(args)
	except ValueError:
		raise MidasError("expecting a number between 0 and 1 inclusive")
	Lighting.setLightSpecularIntensity(light, i)

def _light(cmdName, args):
	light = cmdName
	name, args = first_arg(args)
	if not name:
		raise MidasError("need at least one argument to %s" % cmdName)
	subcmd = keyword_match(name, LIGHT_CMDS)
	if args:
		LightCmdInfo[subcmd][2](light, args)
	else:
		LightCmdInfo[subcmd][1](light)

def quality(cmdName):
	replyobj.status("light quality command has been retired", log=True)

def setQuality(cmdName, arg):
	replyobj.status("light quality command has been retired", log=True)

def sharpness(cmdName):
	s = Lighting.sharpness()
	replyobj.status("material sharpness is %s" % s, log=True)

def setSharpness(cmdName, arg):
	try:
		sharpness = float(arg)
	except ValueError:
		raise MidasError('expecting a number for sharpness')
	try:
		Lighting.setSharpness(sharpness)
	except ValueError, e:
		raise MidasError(str(e))

def reflectivity(cmdName):
	r = Lighting.reflectivity()
	replyobj.status("material reflectivity is %s" % r, log=True)

def setReflectivity(cmdName, arg):
	try:
		reflectivity = float(arg)
	except ValueError:
		raise MidasError('expecting a number for reflectivity')
	try:
		Lighting.setReflectivity(reflectivity)
	except ValueError, e:
		raise MidasError(str(e))

def restore(cmdname, style):
	style = style.strip('"')
	import chimera
	if (style != Lighting.SystemDefault
	and style not in Lighting.preferences()):
		raise MidasError("unknown lighting style: %s" % style)
	if not chimera.nogui:
		controller = Lighting.get()
		if controller.dialog:
			controller.saveui.entryfield.setvalue(style)
			controller.saveui.entryfield.invoke()
			return
	Lighting.restore(style)

def save(cmdname, style):
	style = style.strip('"')
	Lighting.save(style)
	import chimera
	if not chimera.nogui:
		controller = Lighting.get()
		if controller.dialog:
			controller.saveui.entryfield.setvalue(style)
			controller.saveui.updateComboList(selectCurrent=False)

def delete(cmdname, style):
	style = style.strip('"')
	Lighting.delete(style)
	import chimera
	if not chimera.nogui:
		controller = Lighting.get()
		if controller.dialog:
			controller.saveui.updateComboList(selectCurrent=False)

CmdInfo = (
	(Lighting.MODE, mode, setMode),
	(Lighting.BRIGHTNESS, brightness, setBrightness),
	(Lighting.CONTRAST, ratio, setContrast),
	(Lighting.RATIO, ratio, setRatio),
	(Lighting.KEY, None, _light),
	(Lighting.FILL, None, _light),
	(Lighting.BACK, None, _light),
	('quality', quality, setQuality),
	('sharpness', sharpness, setSharpness),
	('reflectivity', reflectivity, setReflectivity),
	('restore', None, restore),
	('save', None, save),
	('delete', None, delete),
)
CMDS = [x[0] for x in CmdInfo]

LightCmdInfo = (
	('color', lightColor, setLightColor),
	('direction', lightDirection, setLightDirection),
	('specular_intensity', lightSpecularIntensity, setLightSpecularIntensity),
)
LIGHT_CMDS = [x[0] for x in LightCmdInfo]
