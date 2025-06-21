import chimera
from tkoptions import Option, SymbolicEnumOption, EnumOption, FloatOption
from PIL import Image, ImageTk
import Tkdnd
import Tkinter as Tk
import tkFont
import Pmw, Tix
from chimera.baseDialog import Close, ModelessDialog
from chimera import dialogs, palettes

class PaletteSource:
	def __init__(self, widget):
		if not hasattr(self, 'palette'):
			raise ValueError('Palette source must have palette attribute')
		widget.bind('<ButtonPress>', self.ps_dragStart)
		self.__widget = widget

	def ps_dragStart(self, event):
		Tkdnd.dnd_start(self, event)

	def dnd_end(self, target, event):
		# we've dropped on a target
		pass

class PaletteTarget:
	def dnd_accept(self, source, event):
		# as a target, do we accept a drag attempt?
		if hasattr(source, "palette"):
			return self
		return None
	
	def dnd_motion(self, source, event):
		# drag motion over us as target
		pass
	
	def dnd_enter(self, source, event):
		# drag enters us as target
		pass
	
	def dnd_leave(self, source, event):
		# drag leaves us as target
		pass
	
	def dnd_commit(self, source, event):
		# drop over us
		self.showPalette(palette=source._palette)

class _PaletteInterior(Tk.Canvas, PaletteSource):
	def __init__(self, master, palette, *args, **kw):
		Tk.Canvas.__init__(self, master, *args, **kw)
		PaletteSource.__init__(self, self)
		self._palette = palette
		self._startEvent = None

	def __getattr__(self, name):
		# rgb/rgba tracked in containing well
		if name == "palette":
			try:
				return self._palette
			except:
				return None
		raise AttributeError, "Unknown attribute '%s'" % name

	def ps_dragStart(self, event):
		if self._palette != None:
			self._startEvent = event
			PaletteSource.ps_dragStart(self, event)
		else:
			if event.state % 2 == 1:
				# 'shift' key depressed
				self._palette.activate(exclusive=0) 
			else:
				self._palette.activate(exclusive=1) 

	def dnd_end(self, target, event):
		if (target is None
		  and self._startEvent is not None
		  and event is not None):
			if (event.type == "5"	# ButtonRelease
			  and event.x_root == self._startEvent.x_root
			  and event.y_root == self._startEvent.y_root):
				self._palette.edgeClick(event)
		self._startEvent = None

class PaletteWell(PaletteTarget):

	Width = 128
	Height = 22	# same effective default as a ColorWell

	def __init__(self, master, palette=None, callback=None, noneOkay=False):
		self._callback = callback
		self._enabled = True
		self._active = False
		self._palette = ()	# nonsense value that is different
		self.noneOkay = noneOkay

		edgewidth = int((min(self.Width, self.Height) + 2) / 12) + 2
		borderwidth = int(min(self.Width + edgewidth,
					self.Height + edgewidth) / 15) + 1

		self._frame = Tk.Frame(master, borderwidth=borderwidth,
				highlightthickness=0, relief=Tk.RAISED)
		self._activeBG = 'white'
		self._inactiveBG = self._frame['bg']

		# use a Frame around the well interior so that the relief
		# doesn't interfere with the interior's canvas coordinate
		# system
		f = Tk.Frame(self._frame, highlightthickness=0,
				borderwidth=borderwidth, relief=Tk.SUNKEN)
		f.pack(padx=edgewidth, pady=edgewidth)

		self._interior = _PaletteInterior(f, self,
				width=self.Width, height=self.Height,
				highlightthickness=0, selectborderwidth=0,
				borderwidth=0)
		self._interior.pack()
		self._frame.bind('<Button-1>', self.edgeClick)
		self.showPalette(palette=palette, doCallback=False)

	def _wellNoPalette(self):
		self._interior.delete(Tk.ALL)
		self._interior.config(bg='#a0a0a0')
		kwds = dict(fill='#d0d0d0', disabledfill='#707070', width=0)
		midX = self.Width / 2
		midY = self.Height / 2
		self._interior.create_rectangle(0, 0, midX, midY, **kwds)
		self._interior.create_rectangle(midX, midY,
				self.Width, self.Height, **kwds)
		noText = "No"
		fontsize = -self.Height / 2	# use pixels rather than points
		font = tkFont.Font(family="Helvetica", weight=tkFont.BOLD,
				size=fontsize)
		self._interior.create_text(midX, midY,
				text=noText, fill='black', disabledfill='gray',
				font=font)
		self._interior.configure(width=self.Width)

	def edgeClick(self, event):
		if not self._enabled:
			return
		if self._active:
			if event.state %2 == 1:
				# 'shift' key depressed
				self.deactivate()
			else:
				# Nothing happens, even if there are more
				# than one well selected.  Alternative is
				# pass
				dialogs.display(PaletteEditor.name)
		else:
			if event.state %2 == 1:
				# 'shift' key depressed
				self.activate(exclusive=False)
			else:
				self.activate(exclusive=True)

	def deactivate(self, notifyEditor=True):
		if self._active:
			if notifyEditor:
				editor = dialogs.find(PaletteEditor.name)
				if editor:
					editor.deregister(self, notifyWell=False)
			self._active = False
			self._frame['bg'] = self._inactiveBG

	def activate(self, exclusive=True, notifyEditor=True):
		if not self._enabled:
			return
		if not self._active:
			editor = dialogs.find(PaletteEditor.name, create=True)
			if notifyEditor:
				editor.register(self, exclusive=exclusive)
				editor._setPalette(self._palette)
			editor.enter()
			self._active = True
			self._frame['bg'] = self._activeBG

	def enable(self):
		self._enabled = True
		self.interior.itemconfigure(Tk.ALL, state=Tk.NORMAL)

	def disable(self):
		self._enabled = False
		self.deactivate()
		self._interior.itemconfigure(Tk.ALL, state=Tk.DISABLED)

	def showPalette(self, palette=None, notifyEditor=True, doCallback=True):
		if palette == self._palette:
			return
		if palette == None:
			if not self.noneOkay:
				raise ValueError('Must show a palette')
			self._palette = palette
			if self._callback != None and doCallback:
				self._callback(None)
			if notifyEditor:
				editor = dialogs.find(PaletteEditor.name)
				if editor:
					editor._setPalette(None)

			self._wellNoPalette()
			return

		self._interior.delete(Tk.ALL)
		self._palette = palette
		if self._callback != None and doCallback:
			self._callback(palette)
			if notifyEditor:
				editor = dialogs.find(PaletteEditor.name)
				if editor:
					editor._setPalette(None)

		image = palette.image(self.Width, self.Height)
		self._image = ImageTk.PhotoImage(image)
		self._interior.create_image(0, 0, image=self._image,
								anchor=Tk.NW)
		self._interior.configure(width=image.size[0])

	def grid(self, *args, **kw):
		self._frame.grid(*args, **kw)

	def pack(self, *args, **kw):
		self._frame.pack(*args, **kw)

# utility functions for interfacing gradients to preferences save mechanism
# reused in simple session saving
def gradientToPref(gradient):
	palette, opacity = gradient
	if palette is None:
		return None, opacity
	return palette.pref(), opacity

def prefToGradient(pref):
	from chimera import palettes
	if pref[0] is None:
		return pref
	if pref[0][0]:
		return palettes.getPaletteByName(pref[0][0]), pref[1]
	return palettes.Palette(*pref[0]), pref[1]

class GradientOption(Option, PaletteTarget):

	prefConv = (gradientToPref, prefToGradient)

	def _addOption(self, noneOkay=False, **kw):
		if self.default is None:
			self._palette = None
			opacity = 1
		else:
			self._palette, opacity = self.default
		if isinstance(self._palette, basestring):
			p = palettes.getPaletteByName(self._palette)
			if p is None:
				raise ValueError('Non-existent palette: %s' % self._palette)
			self._palette = p

		self._option = Tk.Frame(self._master)

		self._well = PaletteWell(self._option, palette=self._palette,
				callback=self._updatePalette, noneOkay=noneOkay)
		self._well.grid()

		self.opacity = FloatOption(self._option, 0, 'opacity', opacity,
				self._set, startCol=2, min=0, max=1)

	def _updatePalette(self, palette):
		self._palette = palette
		self._set()

	def get(self):
		return self._palette, self.opacity.get()

	def set(self, value):
		if value == None:
			palette = None
			opacity = 1
		else:
			palette, opacity = value
			if isinstance(palette, basestring):
				p = palettes.getPaletteByName(palette)
				if p is None:
					raise ValueError('Non-existent palette: %s' % palette)
				palette = p
		self._well.showPalette(palette)
		self.opacity.set(opacity)
		self._palette = palette

	def enable(self):
		if self._label:
			self._label.config(state=Tk.NORMAL)
		self._well.enable()
		self.opacity.enable()

	def disable(self):
		if self._label:
			self._label.config(state=Tk.DISABLED)
		self._well.disable()
		self.opacity.disable()

class InterpolationOption(SymbolicEnumOption):
	values = (palettes.DISCRETE, palettes.HLS, palettes.RGB)
	labels = ('discrete', 'HLS', 'RGB')

SEQUENTIAL = 'sequential'
DIVERGING = 'diverging'
QUALITATIVE = 'qualitative'
class NatureOption(EnumOption):
	values = (SEQUENTIAL, DIVERGING, QUALITATIVE)

	def __init__(self, *args, **kw):
		if 'balloon' not in kw:
			kw['balloon'] = \
"""sequential: ordered data
diverging: emphasis midrange and extremes
qualitative: best for nominal or categorical data"""
		EnumOption.__init__(self, *args, **kw)

class PaletteEditor(ModelessDialog):
	name = "Palette Editor"
	buttons = [ "No Palette", Close ]
	help = 'UsersGuide/palette.html'

	counts = list(range(2, 12 + 1))
	preview_width = 128

	def __init__(self, *args, **kw):
		self.currentPalette = self.saveui_defaultItem()
		self._activeWells = set()
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, master):
		import itertools
		row = itertools.count()

		default_item = palettes.getPaletteByName(self.currentPalette)

		from chimera.preferences import saveui
		f = Tk.Frame(master)
		self.saveui = saveui.SaveUI(f, self)
		f.grid(row=row.next(), column=0, columnspan=3, sticky=Tk.EW,
							padx=2, pady=2)
		self._interp = InterpolationOption(master, row.next(),
				'Interpolation', default_item.interpolation,
				self._preview)
		self._previewImage = Tk.Label(master, width=self.preview_width,
				relief=Tk.SUNKEN, borderwidth=2)
		self._previewImage.grid(row=row.next(), columnspan=2, padx=1,
				pady=1, sticky=Tk.NS)
		self.image = None

		self.nb = Tix.NoteBook(master)
		self.nb.grid(row=row.next(), sticky=Tk.NSEW, columnspan=2)

		# Preset page
		self.nb.add('pPresets', label='Presets', underline=0)
		page = self.nb.page('pPresets')
		self._nature = NatureOption(page, row.next(),
				'Type', SEQUENTIAL, self._showPresetChoices)
		r = row.next()
		count = Tk.Label(page, text="Number of colors:")
		count.grid(row=r, column=0, sticky=Tk.E)
		self._pcount = Pmw.ComboBox(page, fliparrow=1,
				labelpos=Tk.W, label_text='', history=0,
				entryfield_entry_width=3,
				entryfield_validate={
					'validator': 'numeric',
					'min': 2, 'max': 12
				},
				entryfield_errorbackground='red',
				selectioncommand=self._showPresetChoices,
				entryfield_command=self._showPresetChoices)
		self._pcount.setlist(self.counts)
		self._pcount.grid(row=r, column=1, sticky=Tk.W)
		self._pcount.selectitem(self.counts.index(3))
		self._pchoices = Tk.Canvas(page, height=self.preview_width + 4,
				highlightthickness=0, selectborderwidth=0,
				borderwidth=0)
		self._pchoices.grid(row=row.next(), columnspan=2)
		from HtmlText import HtmlText
		self.info = HtmlText(page, wrap=Tk.WORD, width=40, height=5, relief=Tk.FLAT)
		self.info.insert(Tk.END,
'''<font size="-2">
If a preset color scheme is used, please cite:<br>
<blockquote>
Brewer, Cynthia A., 2011. 
<a href="http://www.ColorBrewer.org">http://www.ColorBrewer.org</a>, accessed 19 May 2011.
</blockquote></font>''')
		self.info.grid(row=row.next(), columnspan=2, sticky=Tk.NSEW)
		self.info.bind('<Configure>', self.__wrapInfo)

		# Custom page
		self.nb.add('pCustom', label='Custom', underline=0)
		page = self.nb.page('pCustom')
		page.columnconfigure(0, weight=1)
		page.columnconfigure(1, weight=1)
		r = row.next()
		count = Tk.Label(page, text="Number of colors:")
		count.grid(row=r, column=0, sticky=Tk.E)
		self._count = Pmw.ComboBox(page, fliparrow=1,
				labelpos=Tk.W, label_text='', history=0,
				entryfield_entry_width=3,
				entryfield_validate={
					'validator': 'numeric',
					'min': 2, 'max': 16
				},
				entryfield_errorbackground='red',
				selectioncommand=self._updateColorCount,
				entryfield_command=self._updateColorCount)
		self._count.setlist(self.counts)
		self._count.grid(row=r, column=1, sticky=Tk.W)
		self._count.selectitem(self.counts.index(len(default_item.rgbas)))
		self._colorFrame = Tk.Frame(page)
		self._colorFrame.grid(row=row.next(), columnspan=2,
				padx=1, pady=1)
		self.colors = []
		from CGLtk.color.ColorWell import ColorWell
		for i, rgba in enumerate(default_item.rgbas):
			cw = ColorWell(self._colorFrame, callback=self._preview)
			cw.grid(row=0, column=i, padx=1)
			cw.showColor(rgba, doCallback=0)
			self.colors.append(cw)

		self._preview(name=self.currentPalette)
		self._showPresetChoices()

	def __wrapInfo(self, event):
		lines = self.info.tk.call(self.info._w, 'count', '-displaylines', '0.0', Tk.END)
		self.info.config(height=int(lines)-2)

	def _updateColorCount(self, *args):
		count = int(self._count.get())
		curcount = len(self.colors)
		if count == curcount:
			return
		if count < curcount:
			remove = self.colors[count:]
			self.colors = self.colors[0:count]
			for w in remove:
				w.destroy()
		else:
			from CGLtk.color.ColorWell import ColorWell
			while curcount < count:
				cw = ColorWell(self._colorFrame,
							callback=self._preview)
				cw.grid(row=0, column=curcount, padx=1)
				rgba = self.colors[-1].rgba
				cw.showColor(rgba, doCallback=0)
				self.colors.append(cw)
				curcount += 1
		self._preview()

	def _preview(self, option=None, name=None, makeCallback=True, *args):
		self.currentPalette = name
		import math
		from PIL import ImageDraw
		width = self.preview_width
		rgbas = [c.rgba for c in self.colors]
		count = len(rgbas)
		self.image = Image.new('RGBA', (width, 16))
		draw = ImageDraw.Draw(self.image)
		interpolation = self._interp.get()
		discrete = interpolation == palettes.DISCRETE
		for i in range(width):
			if i == width - 1:
				c0 = c1 = chimera.MaterialColor(*rgbas[-1])
				fract = 1
			elif discrete:
				pos = int(i / float(width - 1) * (count))
				c0 = c1 = chimera.MaterialColor(*rgbas[pos])
				fract = 0
			else:
				pos = i / float(width - 1) * (count - 1)
				ci = int(pos)
				c0 = chimera.MaterialColor(*rgbas[ci])
				c1 = chimera.MaterialColor(*rgbas[ci + 1])
				fract = math.modf(pos)[0]
			if interpolation == palettes.HLS:
				color = chimera.MaterialColor(c0, c1, fract).rgba()
			else:
				color = [(x * (1 - fract) + y * fract) for x, y in zip(c0.rgba(), c1.rgba())]
			rgba = tuple(int(c * 255) for c in color)
			draw.line([(i, 0), (i, 15)], fill=rgba)
		image = ImageTk.PhotoImage(self.image)
		self._previewImage.configure(image=image)
		self._previewImage._image = image
		if makeCallback:
			p = None
			if name:
				p = palettes.getPaletteByName(name)
			if not p:
				p = palettes.Palette(None, rgbas, self._interp.get())
			for well in self._activeWells:
				well.showPalette(palette=p, notifyEditor=False)

	def _showPresetChoices(self, option=None):
		type = self._nature.get()
		min = max = None
		for p in palettes._allPalettes.values():
			if type == p.preset:
				name, count = p.name.rsplit('-')
				count = int(count)
				if min is None:
					min = max = count
				elif count < min:
					min = count
				elif count > max:
					max = count
		current = int(self._pcount.get())
		if current < min:
			self._pcount.selectitem(self.counts.index(min))
			current = min
		elif current > max:
			self._pcount.selectitem(self.counts.index(max))
			current = max
		self._pcount.configure(entryfield_validate={
				'validator': 'numeric', 'min': min, 'max': max})
		# show choices
		choices = []
		for p in palettes._allPalettes.values():
			if p.preset == type and len(p.rgbas) == current:
				choices.append(p)
		import colorsys
		def colorkey(p):
			h, l, s = colorsys.rgb_to_hls(*p.rgbas[-1][0:3])
			if s == 0:
				return -1
			return h
		choices.sort(key=colorkey)
		self._pchoices.delete(Tk.ALL)
		self._presetImages = []
		image_width = 16
		for i, p in enumerate(choices):
			image = p.image(self.preview_width, height=image_width).transpose(Image.ROTATE_90)
			image = ImageTk.PhotoImage(image)
			self._presetImages.append(image)
			self._pchoices.create_image(2 + i * (image_width + 3), 2,
				tag=p.name, image=image, anchor=Tk.NW)
			self._pchoices.tag_bind(p.name, '<ButtonRelease>',
				lambda e, name=p.name: self._choosePalette(name))
		self._pchoices.configure(width=4 + (i + 1) * (image_width + 3))

	def register(self, well, exclusive=True):
		if exclusive:
			self._deactivateWells()
		self._activeWells.add(well)
		self.checkNoneOkay()

	def deregister(self, well, notifyWell=True):
		if well not in self._activeWells:
			return
		if notifyWell:
			well.deactivate(notifyEditor=False)
		self._activeWells.remove(well)
		self.checkNoneOkay()

	def checkNoneOkay(self):
		noneState = Tk.NORMAL
		for well in self._activeWells:
			if not well.noneOkay:
				noneState = Tk.DISABLED
				break
		try:
			noneButton = self.buttonWidgets['No Palette']
			noneButton.config(state=noneState)
		except Tk.TclError:
			# We must have been destroyed already and
			# an orphaned PaletteWell is trying to go away
			pass

	def _deactivateWells(self):
		while self._activeWells:
			well = self._activeWells.pop()
			well.deactivate(notifyEditor=False)

	def NoPalette(self):
		for well in self._activeWells:
			well.showPalette(palette=None, notifyEditor=False)

	def Close(self):
		self._deactivateWells()
		ModelessDialog.Close(self)

	def _choosePalette(self, name):
		p = palettes.getPaletteByName(name)
		items = self.saveui.combo.get(0, Tk.END)
		self.saveui.combo.selectitem(items.index(name), setentry=1)
		interp = self._interp.get()
		if p.interpolation != interp:
			p = palettes.Palette(None, p.rgbas, interp)
		self._setPalette(p, False)
	
	def _setPalette(self, p, update=True):
		if p is None:
			# TODO: currently should never happen
			return

		self._interp.set(p.interpolation)
		self._count.selectitem(self.counts.index(len(p.rgbas)))
		self._updateColorCount()
		for rgba, cw in zip(p.rgbas, self.colors):
			cw.showColor(rgba, doCallback=0)
		self._preview(name=p.name)
		if not update:
			return
		if not p.preset:
			self.nb.raise_page('pCustom')
		elif p.preset == 'default':
			pass
		else:
			self._nature.set(p.preset)
			self._pcount.selectitem(self.counts.index(len(p.rgbas)))
			self._showPresetChoices(self)
			self.nb.raise_page('pPresets')

	def saveui_label(self):
		return "Palette"

	def saveui_presetItems(self):
		all = palettes._allPalettes
		return [all[x].name for x in all if all[x].preset]

	def saveui_userItems(self):
		all = palettes._allPalettes
		return [all[x].name for x in all if not all[x].preset]

	def saveui_defaultItem(self):
		return 'Chimera default'

	def saveui_select(self, name):
		p = palettes.getPaletteByName(name)
		if not p:
			return
		self._setPalette(p)

	def saveui_save(self, name):
		# named palettes are automatically saved
		rgbas = [c.rgba for c in self.colors]
		palettes.Palette(name, rgbas, self._interp.get())
		return True	# successful

	def saveui_delete(self, name):
		p = palettes.getPaletteByName(name)
		if p:
			palettes.removePalette(p)
		self.currentPalette = None
		return True	# successful

dialogs.register(PaletteEditor.name, PaletteEditor)

def _restore_session(data):
	# place holder, just in case ealier daily build sessions were made
	pass
