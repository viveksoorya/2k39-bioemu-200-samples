# Copyright (c) 2000 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: bgprefs.py 39151 2013-10-11 23:01:06Z pett $

"""
background preferences
"""
import chimera
from chimera import preferences
from chimera import tkoptions
from chimera.paletteoptions import GradientOption
from chimera.imageoptions import ImageOpacityOption, PrefImageOpacityOption

BACKGROUND = "Background"
BG_METHOD = "Background method"
BG_COLOR = "Background color"
BG_GRADIENT = "Background gradient"
BG_IMAGE = "Background image"
#LENS_PROFILE = "Draw lens borders"
#LENS_COLOR = "Lens border color"

class MethodOption(tkoptions.SymbolicEnumOption):
	values = (chimera.LensViewer.Solid, chimera.LensViewer.Gradient,
						chimera.LensViewer.Image)
	labels = ('solid', 'gradient', 'image')

def _backgroundMethodCB(option):
	method = option.get()
	try:
		chimera.viewer.backgroundMethod = method
	except ValueError, e:
		from chimera import replyobj
		replyobj.error(str(e))

def _backgroundColorCB(option):
	rgba = option.get()
	if not rgba:
		color = None
	else:
		color = chimera.MaterialColor(*rgba)
	import Midas
	Midas.background(color=color, setMethod=False)

def _backgroundGradientCB(option):
	palette, opacity = option.get()
	chimera.viewer.backgroundGradient = palette, opacity, 0, 0

def _backgroundImageCB(option):
	image, scale, tiling, opacity = option.get()
	chimera.viewer.backgroundImage = image, scale, tiling, opacity, 0, 0

#def _drawBorderCB(option):
#	border = option.get()
#	chimera.viewer.lensBorder = border

#def _borderColorCB(option):
#	rgba = option.get()
#	if not rgba:
#		color = None
#	else:
#		color = chimera.MaterialColor(*rgba)
#	chimera.viewer.lensBorderColor = color

_bgImageCache = None # need to get back Image that was saved
def _saveBGImage((image, scale, tiling, opacity)):
	global _bgImageCache
	import os
	filename = 'bgimage.png'
	pf = os.path.split(preferences.preferences.filename())
	path = os.path.join(*(pf[0:-1] + (filename,)))
	if image is not None:
		image.save(path)
	else:
		try:
			os.remove(filename)
		except OSError:
			pass
		filename = None
	_bgImageCache = image
	return (filename, scale, tiling, opacity)

def _restoreBGImage((filename, scale, tiling, opacity)):
	global _bgImageCache
	if filename is None:
		image = None
		_bgImageCache = None
	else:
		import os
		pf = os.path.split(preferences.preferences.filename())
		path = os.path.join(*(pf[0:-1] + (filename,)))
		if _bgImageCache is not None:
			image = _bgImageCache
		else:
			try:
				from PIL import Image
				image = Image.open(path)
			except IOError:
				image = None
			_bgImageCache = image
	return (image, scale, tiling, opacity)

default_label_font = None
def initialize():
	backgroundPreferences = [{
		BG_COLOR: (
			tkoptions.RGBAOption, None, _backgroundColorCB
		),
	}]
	backgroundPreferencesOrder = [
			BG_COLOR
	]
	if isinstance(chimera.viewer, chimera.LensViewer):
		# change initial default gradient from None
		from chimera import palettes
		default_gradient = palettes.getPaletteByName("Chimera default")
		chimera.viewer.backgroundGradient = default_gradient, 1, 0, 0

		backgroundPreferences.extend([{
			BG_METHOD: (
				MethodOption, chimera.viewer.Solid,
							_backgroundMethodCB
			),
			BG_GRADIENT: (
				GradientOption, (default_gradient, 1),
				_backgroundGradientCB, { "noneOkay": True }
			),
			#LENS_PROFILE: (
			#	tkoptions.BooleanOption, chimera.viewer.lensBorder,
			#	_drawBorderCB
			#),
			#LENS_COLOR: (
			#	tkoptions.RGBAOption, chimera.viewer.lensBorderColor.rgba(),
			#	_borderColorCB, { "noneOkay": False }
			#)
		},
		PrefImageOpacityOption, {
			BG_IMAGE: (
				ImageOpacityOption, (None, 1, 0, 1),
				_backgroundImageCB, { 'noneOkay': True, },
				{ 'imageFilename': 'bgimage.png' }
			)
		}])
		backgroundPreferencesOrder[0:0] = [BG_METHOD]
		backgroundPreferencesOrder[2:2] = [BG_GRADIENT, BG_IMAGE]
	preferences.register(BACKGROUND, backgroundPreferences,
				onDisplay=_bgPrefDisp, onHide=_bgPrefHide)
	preferences.setOrder(BACKGROUND, backgroundPreferencesOrder)

	if not chimera.nogui:
		# Fix initialize resize background color
		import Midas
		Midas.background(color=chimera.viewer.background, setMethod=False)

_bgPrefHandler = None

def _bgPrefDisp(event=None):
	global _bgPrefHandler
	if _bgPrefHandler is None:
		_bgPrefHandler = chimera.triggers.addHandler("Viewer",
					_bgPrefUpdate, None)
	_bgPrefUpdate("Viewer", None, None)

def _bgPrefHide(event=None):
	global _bgPrefHandler
	if _bgPrefHandler is not None:
		chimera.triggers.deleteHandler("Viewer", _bgPrefHandler)
		_bgPrefHandler = None

def _bgPrefUpdate(trigger, closure, changed):
	if changed is not None and chimera.viewer not in changed.modified:
		return
	from initprefs import PREF_SELECTION, HMETHOD, HCOLOR
	_bgCheckOpt(BACKGROUND, BG_METHOD, chimera.viewer.backgroundMethod)
	_bgCheckColor(BACKGROUND, BG_COLOR, chimera.viewer.background)
	_bgCheckGradient(BACKGROUND, BG_GRADIENT, chimera.viewer.backgroundGradient),
	_bgCheckImage(BACKGROUND, BG_IMAGE, chimera.viewer.backgroundImage),
	_bgCheckOpt(PREF_SELECTION, HMETHOD, chimera.viewer.highlight)
	_bgCheckColor(PREF_SELECTION, HCOLOR, chimera.viewer.highlightColor)
	#_bgCheckOpt(BACKGROUND, LENS_PROFILE, chimera.viewer.lensBorder)
	#_bgCheckColor(BACKGROUND, LENS_COLOR, chimera.viewer.lensBorderColor)

def _bgCheckColor(cat, opt, c):
	oc = preferences.get(cat, opt)
	if c is None:
		if oc is not None:
			preferences.set(cat, opt, None)
	else:
		nc = c.rgba()
		if oc != nc:
			preferences.set(cat, opt, nc)

def _bgCheckOpt(cat, opt, b):
	ob = preferences.get(cat, opt)
	if ob != b:
		preferences.set(cat, opt, b)

def _bgCheckGradient(cat, opt, bg):
	from chimera import palettes
	palette, opacity, angle, offset = bg
	ob = preferences.get(cat, opt)
	if ob != (palette, opacity):
		preferences.set(cat, opt, (palette, opacity))

def _bgCheckImage(cat, opt, bi):
	image, scale, tiling, opacity, angle, offset = bi
	ob = preferences.get(cat, opt)
	if ob != (image, scale, tiling, opacity):
		preferences.set(cat, opt, (image, scale, tiling, opacity))

# monkey patch LensViewer to change backgroundGradient to take a Palette
# and backgroundImage to take an image

def power2(i):
	"""return smallest power of 2 greater than or equal to argument"""
	if i < 0:
		raise ValueError("need non-negative integer")
	p2 = 1
	while p2 < i:
		p2 <<= 1	# assume two's complement arithmetic
	return p2

def _setTextureOpacity(texture, opacity):
	mat = texture.baseMaterial
	if mat.opacity == opacity:
		return
	default = chimera.Material.lookup("default")
	if mat is default:
		mat = chimera.Material('')
		texture.baseMaterial = mat
	mat.opacity = opacity

def _backgroundGradient(self):
	texture, width, angle, offset = chimera.viewer._backgroundGradient
	if texture:
		opacity = texture.baseMaterial.opacity
	else:
		opacity = 1
	return self._bgGradient, opacity, angle, offset

def _setBackgroundGradient(self, (palette, opacity, angle, offset)):
	if palette == None:
		chimera.viewer._backgroundGradient = None, 0, angle, offset
		self._bgGradient = palette
		return
	texture, width = palette.texture()
	chimera.viewer._backgroundGradient = texture, width, angle, offset
	self._bgGradient = palette
	_setTextureOpacity(texture, opacity)

chimera.LensViewer._bgGradient = None
chimera.LensViewer._backgroundGradient = chimera.LensViewer.backgroundGradient
chimera.LensViewer.backgroundGradient = property(_backgroundGradient,
	_setBackgroundGradient, None, "(Palette, float opacity, float angle, float offset)")

def _backgroundImage(self):
	texture, xscale, yscale, tiling, angle, offset = chimera.viewer._backgroundImage
	if texture:
		opacity = texture.baseMaterial.opacity
	else:
		opacity = 1
	return self._bgImage, self._bgScale, tiling, opacity, angle, offset

def _setBackgroundImage(self, (image, scale, tiling, opacity, angle, offset)):
	if image == self._bgImage and scale == self._bgScale:
		texture = chimera.viewer._backgroundImage[0]
		texture, xscale, yscale, _, _, _ = chimera.viewer._backgroundImage
		chimera.viewer._backgroundImage = texture, xscale, yscale, tiling, angle, offset
		if not texture:
			return
		_setTextureOpacity(texture, opacity)
		return
	if image == None:
		chimera.viewer._backgroundImage = None, 1, 1, tiling, angle, offset
		self._bgImage = None
		self._bgScale = 1
		return
	from PIL import Image
	try:
		# PIL image origin is top-left, OpenGL origin is bottom-left
		teximage = image.transpose(Image.FLIP_TOP_BOTTOM)
	except:
		# On any error, act as if the image is missing
		chimera.viewer._backgroundImage = None, 1, 1, tiling, angle, offset
		self._bgImage = None
		self._bgScale = 1
		return
	# make RGBA for consistency
	if teximage.mode != 'RGBA':
		teximage = teximage.convert('RGBA')
	max_tex_size = chimera.opengl_getInt("maximum texture size")
	width, height = teximage.size
	p2width = power2(width)
	if p2width > max_tex_size:
		p2width = max_tex_size
	p2height = power2(height)
	if p2height > max_tex_size:
		p2height = max_tex_size
	if width == p2width and height == p2height:
		xscale = yscale = 1
	else:
		xscale = float(width) / p2width
		yscale = float(height) / p2height
		teximage = teximage.resize((p2width, p2height), Image.BICUBIC)
	texture = chimera.Texture('', chimera.Texture.RGBA,
			chimera.Texture.UnsignedByte, p2width, p2height)
	size = p2width * p2height * 4
	memmap = chimera.memoryMap(texture.startEditing(), size, texture.type())
	memmap[:] = [ord(c) for c in teximage.tostring()]
	texture.finishEditing()

	xscale *= scale
	yscale *= scale
	chimera.viewer._backgroundImage = texture, xscale, yscale, tiling, angle, offset
	self._bgImage = image
	self._bgScale = scale
	_setTextureOpacity(texture, opacity)

chimera.LensViewer._bgImage = None
chimera.LensViewer._bgScale = 1.0
chimera.LensViewer._backgroundImage = chimera.LensViewer.backgroundImage
chimera.LensViewer.backgroundImage = property(_backgroundImage,
	_setBackgroundImage, None, "(Image, float scale, tiling, float opacity, float angle, float offset)")
