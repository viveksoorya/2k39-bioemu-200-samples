import chimera

# types of color palette interpolation
DISCRETE = 0
HLS = 1
RGB = 2

_allPalettes = {}
_allTextures = {}
_savedPrefs = {}	# replaced by preferences dictionary

PALETTE_CATEGORY = "Palettes"
NAMED_PALETTES = "named palettes"

class Palette:

	def __init__(self, name, rgbas, interpolation, preset=None, fromSaved=False):
		if name:
			pname = name.lower()
		else:
			pname = None
		if pname in _allPalettes:
			former = _allPalettes[pname]
			if former.preset:
				raise ValueError("can not change palette preset")
			if former._texture:
				texture = former._texture[0]
				del _allTextures[texture]
				former._texture = None	# remove reference
		self.name = name
		self.rgbas = list(rgbas)
		for i in range(len(self.rgbas)):
			if len(self.rgbas[i]) < 4:
				self.rgbas[i] = list(self.rgbas[i]) + [1]
		self.interpolation = interpolation
		self.preset = preset
		self._texture = None
		if not name:
			return
		_allPalettes[pname] = self
		if preset:
			return
		_savedPrefs[pname] = self.rgbas, self.interpolation
		if not fromSaved:
			if not preset:
				from chimera import preferences
				preferences.save()
			chimera.triggers.activateTrigger(NAMED_PALETTES, name)

	def texture(self):
		"""return (texture, width) where width is actual width"""
		if not self._texture:
			self._texture = palette2texture(self.rgbas,
							self.interpolation)
			_allTextures[self._texture[0]] = self
		return self._texture

	def image(self, maxwidth, height):
		return palette2image(self.rgbas, self.interpolation, maxwidth, height)

	def pref(self):
		return self.name, self.rgbas, self.interpolation

	def __repr__(self):
		return '%s.%s(%r, %r, %r)' % (__name__, self.__class__.__name__,
				self.name, self.rgbas, self.interpolation)

def getPaletteByName(name):
	if name:
		pname = name.lower()
	else:
		pname = None
	return _allPalettes.get(pname, None)

def getPaletteByTexture(texture):
	return _allTextures.get(texture, None)

def removePalette(palette):
	if palette.preset:
		raise ValueError("can not remove palette presets")
	if palette._texture:
		del _allTextures[palette._texture[0]]
		palette._texture = None
	if not palette.name:
		return
	pname = palette.name.lower()
	del _allPalettes[pname]
	del _savedPrefs[pname]
	from chimera import preferences
	preferences.save()
	chimera.triggers.activateTrigger(NAMED_PALETTES, palette.name)

# initialize palette presets
def _initPresets():
	from colorbrewer import ColorBrewer
	for name in ColorBrewer:
		type, min, max = ColorBrewer[name]['_info']
		for i in range(min, max + 1):
			rgbas = ColorBrewer[name][i]
			Palette('%s-%d' % (name, i), rgbas, DISCRETE, preset=type.lower())
	Palette('Chimera default', ((1, 1, 1, 1), (0, 0, 1, 1)), HLS, preset='default')

_initPresets()

def _expandPalette(rgbas, interpolation=DISCRETE, maxwidth=128):
	import math
	count = len(rgbas)
	discrete = interpolation == DISCRETE
	if not discrete:
		width = maxwidth - maxwidth % count
	else:
		import bgprefs
		width = count
		maxwidth = bgprefs.power2(width)

	colors = [()] * width
	for i in range(width):
		if i == width - 1:
			colors[i] = rgbas[-1]
			break
		if discrete:
			pos = int(i / float(width - 1) * (count))
			colors[i] = rgbas[pos]
			continue
		pos = i / float(width - 1) * (count - 1)
		ci = int(pos)
		c0 = chimera.MaterialColor(*rgbas[ci])
		c1 = chimera.MaterialColor(*rgbas[ci + 1])
		fract = math.modf(pos)[0]
		if interpolation == HLS:
			color = chimera.MaterialColor(c0, c1, fract).rgba()
		else:
			color = [(x * (1 - fract) + y * fract) for x, y in zip(c0.rgba(), c1.rgba())]
		colors[i] = color
	return colors, width, maxwidth


def palette2texture(rgbas, interpolation=DISCRETE, maxwidth=128):
	colors, width, maxwidth = _expandPalette(rgbas, interpolation, maxwidth)
	texture = chimera.Texture("", chimera.Texture.RGBA,
					chimera.Texture.UnsignedByte, maxwidth)
	size = maxwidth * 4
	memmap = chimera.memoryMap(texture.startEditing(), size, texture.type())
	for i in range(width):
		rgba = [int(c * 255 + 0.5) for c in colors[i]]
		memmap[i * 4: (i + 1) * 4] = rgba
	for i in range(width, maxwidth):
		memmap[i * 4: (i + 1) * 4] = rgba
	texture.finishEditing()
	if interpolation == DISCRETE:
		texture.filters = (chimera.Texture.Nearest, chimera.Texture.Nearest)
	else:
		texture.filters = (chimera.Texture.Linear, chimera.Texture.Linear)
	return texture, width

def palette2image(rgbas, interpolation, maxwidth, height):
	colors, width, newmaxwidth = _expandPalette(rgbas, interpolation, maxwidth)
	from PIL import Image, ImageDraw
	image = Image.new('RGBA', (width, height))
	pix = image.load()
	for x in range(width):
		pix[x, 0] = tuple(int(c * 255 + 0.5) for c in colors[x])
	region = image.crop((0, 0, width, 1))
	for y in range(1, height):
		image.paste(region, (0, y))
	if maxwidth // width > 1:
		newwidth = maxwidth - maxwidth % width
		image = image.resize((newwidth, height), Image.NEAREST)
	return image

def _save_session(trigger, closure, file):
	"""convert data to session data"""
	if not _savedPrefs:
		return
	# save restoring code in session
	restoring_code = (
"""
def restorePalettes():
	from chimera import palettes
	palettes._restore_session(%s)
try:
	restorePalettes()
except:
	reportRestoreError('Error restoring Palettes')
""")
	file.write(restoring_code % _savedPrefs)

def _restore_session(data):
	for name in data:
		rgbas, interpolation = data[name]
		try:
			Palette(name, rgbas, interpolation)
		except ValueError:
			# TODO? log that preset couldn't be overridden
			pass

def initialize():
	from chimera import preferences
	pref = preferences.addCategory(PALETTE_CATEGORY,
						preferences.HiddenCategory)
	global _savedPrefs
	_savedPrefs = pref.setdefault(NAMED_PALETTES, {})
	chimera.triggers.addTrigger(NAMED_PALETTES)
	for p in _savedPrefs:
		rgbas, interpolation = _savedPrefs[p]
		Palette(p, rgbas, interpolation, fromSaved=True)

	import SimpleSession
	chimera.triggers.addHandler(SimpleSession.SAVE_SESSION, _save_session, None)
