"""
Lighting module -- provide high level interface to lighting

4 types of lighting are supported:
	1. Ambient only
	2. A single light will ambient fill
	3. Separate key and fill lights (without ambient)
	4. Separate key, fill, and back lights (without ambient)
"""
#
#	In the two light (key and fill) interface:
#
#		scale = brightness / ratio
#		fill_brightness = scale - ambient
#		key_brightness = 1 - scale
#
#	except the light's brightness is increased when off-center:
#
#		adjust = 2 - abs(light_direction * eye_direction)
#
#	The single light interface replaces the fill light with an
#	(omnidirectional) ambient light.
#
import chimera, chimera.preferences

# Styles
SystemDefault = "Chimera default"
UserDefault = "User default"

# Modes
AMBIENT = 'ambient'
ONE = 'single'		# key + ambient
TWO = 'two-point'	# key + fill
THREE = 'three-point'	# key + fill + back/rim
MODES = (AMBIENT, ONE, TWO, THREE)

MODE = 'mode'
BRIGHTNESS = 'brightness'
CONTRAST = 'contrast'
RATIO = 'ratio'
KEY = 'key'
FILL = 'fill'
BACK = 'back'
_DIR = 0
_COLOR = 1
_SPEC = 2

MATERIAL = 'material'
_SHARP = 0
#_COLOR = 1
_REFLECT = 2

_OPENGL_DEFAULT_AMBIENT = 0.2	# OpenGL default of 0.2 ambient light

def get():
	if chimera.nogui:
		return None
	import controller
	return controller.singleton()

_prefs = chimera.preferences.addCategory("Lighting",
					chimera.preferences.HiddenCategory)

def preferences():
	# Return hidden preference category so someone else
	# manipulate it
	return _prefs

_systemDefault = {}
_params = {}

def mode():
	return _params[MODE]

def setMode(mode, _do_update=True):
	if mode == _params[MODE]:
		return
	_params[MODE] = mode
	viewer = chimera.viewer
	if mode == AMBIENT:
		viewer.backLight = None
		viewer.fillLight = None
		viewer.keyLight = None
	elif mode == ONE:
		viewer.backLight = None
		viewer.fillLight = None
		key = viewer.keyLight = chimera.DirectionalLight()
		key.direction = chimera.Vector(*_params[KEY][_DIR])
		key.color = chimera.MaterialColor(*_params[KEY][_COLOR])
		key.specularScale = _params[KEY][_SPEC]
	elif mode == TWO:
		viewer.backLight = None
		fill = viewer.fillLight = chimera.DirectionalLight()
		fill.direction = chimera.Vector(*_params[FILL][_DIR])
		fill.color = chimera.MaterialColor(*_params[FILL][_COLOR])
		fill.specularScale = _params[FILL][_SPEC]
		key = viewer.keyLight = chimera.DirectionalLight()
		key.direction = chimera.Vector(*_params[KEY][_DIR])
		key.color = chimera.MaterialColor(*_params[KEY][_COLOR])
		key.specularScale = _params[KEY][_SPEC]
	elif mode == THREE:
		back = viewer.backLight = chimera.DirectionalLight()
		back.direction = chimera.Vector(*_params[BACK][_DIR])
		back.color = chimera.MaterialColor(*_params[BACK][_COLOR])
		back.specularScale = _params[BACK][_SPEC]
		fill = viewer.fillLight = chimera.DirectionalLight()
		fill.direction = chimera.Vector(*_params[FILL][_DIR])
		fill.color = chimera.MaterialColor(*_params[FILL][_COLOR])
		fill.specularScale = _params[FILL][_SPEC]
		key = viewer.keyLight = chimera.DirectionalLight()
		key.direction = chimera.Vector(*_params[KEY][_DIR])
		key.color = chimera.MaterialColor(*_params[KEY][_COLOR])
		key.specularScale = _params[KEY][_SPEC]
	else:
		raise ValueError('unknown lighting mode')
	if _do_update:
		_updateLights()

def _updateLights():
	brightness = _params[BRIGHTNESS]
	contrast = _params[CONTRAST]
	if _params[MODE] == AMBIENT:
		chimera.viewer.ambient = brightness
	elif _params[MODE] == ONE:
		ambient = chimera.viewer.ambient = (1 - contrast) * brightness
		eye_dir = chimera.Vector(0, 0, 1)
		key = chimera.viewer.keyLight
		adjust = 2 - abs(key.direction * eye_dir)
		key.diffuseScale = (brightness - ambient) * adjust
		if key.diffuseScale < 1e-6:
			# prevent from disappearing in interface
			key.diffuseScale = 1e-6
	elif _params[MODE] in (TWO, THREE):
		ratio = _params[RATIO]
		maxr = maximum_ratio(contrast)
		if ratio > maxr:
			ratio = maxr
		eye_dir = chimera.Vector(0, 0, 1)
		ambient = chimera.viewer.ambient = (1 - contrast) * brightness
		scale = brightness / ratio
		key = chimera.viewer.keyLight
		fill = chimera.viewer.fillLight

		# F = fill.diffuseScale + ambient
		# K = key.diffuseScale + ambient
		# F = brightness / ratio
		# ratio = K / F
		# With lights in eye direction:
		#   brightness = fill.diffuseScale + key.diffuseScale + ambient
		# (The above equation insures that the brightness doesn't
		# change appreciatively when switching between single and two
		# light modes.)
		fill.diffuseScale = (brightness - ratio * ambient) / (ratio + 1)
		key.diffuseScale = (brightness - ambient - fill.diffuseScale)

		# adjust values are used to maintain a constant
		# brightness as the lights are moved around.
		adjust = 2 - abs(fill.direction * eye_dir)
		fill.diffuseScale *= adjust
		if fill.diffuseScale < 1e-6:
			# prevent from disappearing in interface
			fill.diffuseScale = 1e-6
		adjust = 2 - abs(key.direction * eye_dir)
		key.diffuseScale *= adjust
		if key.diffuseScale < 1e-6:
			# prevent from disappearing in interface
			key.diffuseScale = 1e-6

def brightness():
	return _params[BRIGHTNESS]

def setBrightness(brightness, _do_update=True):
	if brightness < 0:
		raise ValueError("brightness must be >= 0")
	if brightness == _params[BRIGHTNESS]:
		return
	_params[BRIGHTNESS] = brightness
	if _do_update:
		_updateLights()

def contrast():
	return _params[CONTRAST]

def setContrast(contrast, _do_update=True):
	if contrast < 0 or contrast > 1:
		raise ValueError("contrast must be between 0 and 1 inclusive")
	if contrast == _params[CONTRAST]:
		return
	_params[CONTRAST] = contrast
	if _do_update:
		_updateLights()

def maximum_ratio(contrast):
	if contrast >= 1:
		return float("inf")	# larger than any reasonable value
	if contrast < 0:
		return 1
	return 1 / (1 - contrast)

def ratio():
	return _params[RATIO]

def setRatio(ratio, clamp=False, _do_update=True):
	maxr = maximum_ratio(_params[CONTRAST])
	if ratio < 1:
		if not clamp:
			raise ValueError("ratio must be >= 1")
		ratio = 1
	if clamp and ratio > maxr:
		ratio = maxr
	if ratio == _params[RATIO]:
		return
	_params[RATIO] = ratio
	if _do_update:
		_updateLights()

def _getLight(light, ambientOkay=False):
	mode = _params[MODE]
	if light == KEY and (ambientOkay or mode != AMBIENT):
		return chimera.viewer.keyLight
	if light == FILL and mode != AMBIENT:
		return chimera.viewer.fillLight
	if light == BACK and mode != AMBIENT:
		return chimera.viewer.backLight
	return None

def lightColor(name):
	try:
		return _params[name][_COLOR]
	except KeyError:
		raise ValueError('unknown light: %s' % name)

def setLightColor(name, color):
	if not isinstance(color, chimera.MaterialColor):
		color = chimera.MaterialColor(*color)
	try:
		_params[name][_COLOR] = color.rgba()[:3]
	except KeyError:
		raise ValueError('unknown light: %s' % name)
	light = _getLight(name, ambientOkay=True)
	if light:
		light.color = color

def lightDirection(name):
	try:
		return _params[name][_DIR]
	except KeyError:
		raise ValueError('unknown light: %s' % name)

def setLightDirection(name, dir, _do_update=True):
	if not isinstance(dir, chimera.Vector):
		dir = chimera.Vector(*dir)
	dir.normalize()
	try:
		_params[name][_DIR] = dir.data()
	except KeyError:
		raise ValueError('unknown light: %s' % name)
	if _do_update:
		_updateLights()
	light = _getLight(name)
	if light:
		light.direction = dir

def lightSpecularIntensity(name):
	try:
		return _params[name][_SPEC]
	except KeyError:
		raise ValueError('unknown light: %s' % name)

def setLightSpecularIntensity(name, i):
	try:
		_params[name][_SPEC] = i
	except KeyError:
		raise ValueError('unknown light: %s' % name)
	light = _getLight(name)
	if light:
		light.specularScale = i

def sharpness():
	return _params[MATERIAL][_SHARP]

def setSharpness(sharpness):
	if sharpness == _params[MATERIAL][_SHARP]:
		return
	if sharpness < 0 or sharpness > 128:
		raise ValueError("sharpness must be between 0 and 128 inclusive")
	_params[MATERIAL][_SHARP] = sharpness
	_updateMaterials()

def reflectivity():
	return _params[MATERIAL][_REFLECT]

def setReflectivity(reflectivity):
	if reflectivity == _params[MATERIAL][_REFLECT]:
		return
	if reflectivity < 0:
		raise ValueError('reflectivity must be non-negative')
	_params[MATERIAL][_REFLECT] = reflectivity
	_updateMaterials()

def shinyColor():
	return chimera.MaterialColor(*_params[MATERIAL][_COLOR])

def setShinyColor(color):
	_params[MATERIAL][_COLOR] = color.rgba()[:3]
	_updateMaterials()

def material():
	return _params[MATERIAL]

def setMaterial(sharpness, specular_color, reflectivity):
	s, sc, r = _params[MATERIAL]
	if sharpness == s and specular_color == sc and reflectivity == r:
		return
	# repeat error checking from setSharpness and setReflectivity
	if sharpness < 0 or sharpness > 128:
		raise ValueError("sharpness must be between 0 and 128 inclusive")
	if reflectivity < 0:
		raise ValueError('reflectivity must be non-negative')
	_params[MATERIAL] = [sharpness, specular_color, reflectivity]
	_updateMaterials()

def _updateMaterials():
	sharpness, specular_color, reflectivity = _params[MATERIAL]
	mat = chimera.Material.lookup("default")
	mat.shininess = sharpness
	mat.specular = tuple(x * reflectivity for x in specular_color)

	# _surface models don't use default material,
	# so set their material
	import _surface
	for m in chimera.openModels.list(modelTypes=[_surface.SurfaceModel], hidden=True):
		#m.material = mat
		m.material.shininess = mat.shininess
		m.material.specular = mat.specular

def _postGraphicsFunc():
	# create defaults after graphics is initialized
	chimera.viewer.keyLight = None		# make exist for NoGuiViewer 
	chimera.viewer.fillLight = None		# make exist for NoGuiViewer 
	chimera.viewer.backLight = None		# make exist for NoGuiViewer 
	chimera.viewer.ambient = 0		# make exist for NoGuiViewer 
	global _systemDefault, _params
	mat = chimera.Material.lookup("default")
	rgb, reflect = _normalizedColor(mat.specular)
	from math import sin, cos, radians, sqrt
	a15 = radians(15)
	fill_direction = chimera.Vector(sin(a15), sin(a15), cos(a15))
	a45 = radians(45)
	key_direction = chimera.Vector(-sin(a45 / 2), sin(a45), cos(a45))
	back_direction = chimera.Vector(sin(a45 / 2), sin(a45), -cos(a45))
	brightness = 1.16
	_systemDefault = {
		MODE: TWO,
		BRIGHTNESS: brightness,
		#CONTRAST: 1 - _OPENGL_DEFAULT_AMBIENT / brightness,
		CONTRAST: 0.83,
		RATIO: 1.25,
		KEY: [
			key_direction.data(),
			(1, 1, 1),		# color
			1.0			# specular
		],
		FILL: [
			fill_direction.data(),
			(1, 1, 1),		# color
			0.0			# specular
		],
		BACK: [
			back_direction.data(),
			(1, 1, 1),		# color
			0.0			# specular
		],
		MATERIAL: [mat.shininess, rgb, reflect],
	}
	import copy
	_params = copy.deepcopy(_systemDefault)
	_params[MODE] = 'uninitialized'
	if UserDefault in _prefs:
		_setFromParams(_prefs[UserDefault])
	else:
		_setFromParams(_systemDefault)
	import SimpleSession
	chimera.triggers.addHandler(SimpleSession.SAVE_SESSION, _saveSession,
									None)

def _calculateBrightnessRatio(key, fill, ambient):
	# compute brightness and ratio from light settings
	eye_dir = chimera.Vector(0, 0, 1)
	fadjust = 2 - abs(fill.direction * eye_dir)
	fd = fill.diffuseScale / fadjust
	kadjust = 2 - abs(key.direction * eye_dir)
	kd = key.diffuseScale / kadjust
	brightness = fd + kd + ambient
	if brightness < 0:
		brightness = 0
	ratio = (kd + ambient) / (fd + ambient)
	if ratio < 1:
		ratio = 1
	maxr = maximum_ratio(1 - ambient)
	if ratio > maxr:
		ratio = maxr
	return brightness, ratio

def _setFromParams(p):
	if MODE not in p:
		p = _valueFromV1Params(p)
	elif RATIO not in p:
		p = _valueFromV2Params(p)
	setBrightness(p[BRIGHTNESS], _do_update=False)
	setContrast(p[CONTRAST], _do_update=False)
	setRatio(p[RATIO], clamp=True, _do_update=False)
	_setLightParams(KEY, p[KEY], _do_update=False)
	_setLightParams(FILL, p[FILL], _do_update=False)
	if BACK in p:
		_setLightParams(BACK, p[BACK], _do_update=False)
	setMaterial(*p[MATERIAL])
	setMode(p[MODE], _do_update=False)
	_updateLights()

def _setLightParams(name, values, _do_update=True):
	setLightDirection(name, values[_DIR], _do_update=_do_update)
	setLightColor(name, values[_COLOR])
	setLightSpecularIntensity(name, values[_SPEC])

def restore(style):
	if style == SystemDefault:
		_setFromParams(_systemDefault)
	elif style in _prefs:
		_setFromParams(_prefs[style])
	else:
		raise ValueError("unknown lighting style: %s" % style)

def save(style):
	import copy
	_prefs[style] = copy.deepcopy(_params)
	_prefs.saveToFile()

def delete(style):
	del _prefs[style]
	_prefs.saveToFile()

def _saveSession(trigger, closure, f):
		print >> f, \
"""
def restoreLightController():
	import Lighting
	Lighting._setFromParams(%s)
try:
	restoreLightController()
except:
	reportRestoreError("Error restoring lighting parameters")
""" % _params

def _normalizedColor(rgb, brightness=None):
	# Given rgb may have components > 1.  In this case scale to
	# produce maximum color component of 1.
	b = max(rgb)
	if brightness is None:
		if b <= 1:
			return rgb, 1.0
	elif b < brightness:
		# Only use the given brightness if it is high enough to
		# yield a specular color with components <= 1
		b = brightness
	return tuple([ c / b for c in rgb ]), b

#
# Code to restore version 1 light parameters from previously saved lights
#
# "key" and "fill" lights are:
#	( active, diffuseColor, diffuseScale, specularColor, specularScale, dir)
#
# "shininess" is (mat.shininess, mat.specular)
#		or (mat.shininess, mat.specular, reflectivity)
#
def _valueFromV1Params(p):
	key = p['key']
	fill = p['fill']
	class TmpLight:
		pass
	k = TmpLight()
	k.direction = chimera.Vector(*key[5])
	k.diffuseScale = key[2]
	f = TmpLight()
	f.direction = chimera.Vector(*fill[5])
	f.diffuseScale = fill[2]
	brightness, ratio = _calculateBrightnessRatio(k, f, _OPENGL_DEFAULT_AMBIENT)
	if 'shininess' in p:
		params = p['shininess']
		if len(params) == 3:
			sharpness, specular_color, reflectivity = params
		else:
			sharpness, specular_color = params
			reflectivity = 1
		rgb, reflect = _normalizedColor(specular_color, reflectivity)
	else:
		sharpness, rgb, reflect = _systemDefault[MATERIAL]
	value = {
		BRIGHTNESS: brightness,
		CONTRAST: 1 - _OPENGL_DEFAULT_AMBIENT / brightness,
		RATIO: ratio,
		KEY: [key[5], key[1], key[4]],
		FILL: [fill[5], fill[1], fill[4]],
		# skip BACK
		MATERIAL: [sharpness, rgb, reflect],
	}
	if key[0] and fill[0]:
		value[MODE] = TWO
	elif key[0] or fill[0]:
		value[MODE] = ONE
	else:
		value[MODE] = AMBIENT
	return value
#
# Code to restore version 2 light parameters from previously saved lights
#
# The meaning of contrast changed to no longer be the key-fill ratio, but
# a 0-1 value that sets the minimum amount of (ambient) light, and ratio
# is the key-fill ratio.  There was also a bug that caused extra directional
# fill light, so when updating, calculate revised values.

def _valueFromV2Params(p):
	class TmpLight:
		pass
	k = TmpLight()
	k.direction = chimera.Vector(*p[KEY][_DIR])
	f = TmpLight()
	f.direction = chimera.Vector(*p[FILL][_DIR])
	scale = p[BRIGHTNESS] / (p[CONTRAST] + 1)
	eye_dir = chimera.Vector(0, 0, 1)
	adjust = 2 - abs(f.direction * eye_dir)
	f.diffuseScale = (scale * adjust) - _OPENGL_DEFAULT_AMBIENT
	adjust = 2 - abs(k.direction * eye_dir)
	k.diffuseScale = (p[BRIGHTNESS] - scale) * adjust
	brightness, ratio = _calculateBrightnessRatio(k, f, _OPENGL_DEFAULT_AMBIENT)
	p.update({
		BRIGHTNESS: brightness,
		CONTRAST: 1 - _OPENGL_DEFAULT_AMBIENT / brightness,
		RATIO: ratio,
	})
	return p
