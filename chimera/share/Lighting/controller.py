# LightingController
#
#	Manager for the lighting user interface that is added to the
#	Viewing dialog.  The manager is a singleton (unless explicitly
#	created otherwise) and uses the Chimera "Lighting" category,
#	a.k.a LightingController.Name.
#
#	The interface has controls for various lighting modes and
#	material shininess.


import Lighting
from Lighting import SystemDefault, UserDefault

def singleton():
	# We have to stash our singleton in the viewing module
	# because it is first created in ChimeraExtension.py
	# and we cannot store it as a module global variable then
	# because that module gets destroyed once
	# ChimeraExtension.py terminates.
	from chimera import viewing
	if not hasattr(viewing, "lightingController"):
		viewing.lightingController = LightingController()
	#print "Lighting singleton:", viewing.lightingController
	return viewing.lightingController

MAX_RATIO = 10.0  # maximum value of ratio slider

class LightingController:

	# This class should have a singleton instance.

	Name = "Lighting"

	from chimera import tkoptions
	class _ModeOption(tkoptions.SymbolicEnumOption):
		values = [
			Lighting.AMBIENT, Lighting.ONE, Lighting.TWO,
			Lighting.THREE
		]
		labels = values

	def __init__(self, singleton=True):
		self.dialog = None
		self.master = None
		self.trackLights = None
		self.trackViewers = None
		self.trackMaterials = None
		self.skipRatioUpdate = False
		if singleton:
			global _singleton
			_singleton = self

	Interface_Lights = 'Intensity'
	Interface_Shininess = 'Shininess'
	def create(self, dialog, master):
		from chimera import tkoptions
		from chimera.preferences import saveui
		import Tkinter, Pmw
		from CGLtk.color.ColorPanel import _tkColorName
		try:
			from _LightViewer import LightViewer
			keyColor = _tkColorName(LightViewer.keyColor)
			fillColor = _tkColorName(LightViewer.fillColor)
			backColor = _tkColorName(LightViewer.backColor)
		except ImportError:
			keyColor = "#000"
			fillColor = "#000"
			backColor = "#000"
		self.dialog = dialog
		self.master = master
		self.saveui = saveui.SaveUI(master, self)
		self.interfaceVar = Tkinter.StringVar(master)
		self.interfaceVar.set(self.Interface_Lights)
		w = Pmw.Group(master, tag_pyclass = Tkinter.Menubutton,
				tag_indicatoron=True,
				tag_relief=Tkinter.RAISED,
				tag_borderwidth=2,
				tag_textvariable=self.interfaceVar)
		w.pack(side=Tkinter.LEFT, fill='y', pady=3)

		mb = w.component("tag")
		self.interfaceMenu = Tkinter.Menu(mb, tearoff=Tkinter.NO)
		mb.config(menu=self.interfaceMenu)
		self.interfaceMenu.add_radiobutton(
				label=self.Interface_Lights,
				variable=self.interfaceVar,
				value=self.Interface_Lights,
				command=self._chooseInterface)
		self.interfaceMenu.add_radiobutton(
				label=self.Interface_Shininess,
				variable=self.interfaceVar,
				value=self.Interface_Shininess,
				command=self._chooseInterface)

		self.mainFrame = Tkinter.Frame(w.interior())
		self.mainFrame.pack(side=Tkinter.LEFT)
		self.mainFrame.pack_forget()
		import itertools
		row = itertools.count()
		f = self.mainFrame
		mode = Lighting.mode()
		self.mode = self._ModeOption(f, row.next(), 'mode',
							mode, self._modeCB)

		from chimera.tkoptions import FloatScaleOption
		self.brightness = FloatScaleOption(f, row.next(), 'brightness',
				Lighting.brightness(),
				self._setBrightness,
				multirow=True, min=0, scale_from=0, scale_to=2,
				scale_resolution=-0.05, scale_digits=24)
		row.next() # for multirow

		self.contrast = FloatScaleOption(f, row.next(), 'contrast',
				Lighting.contrast(), self._setContrast,
				multirow=True, min=0, max=1,
				scale_from=0, scale_to=1,
				scale_resolution=-0.05, scale_digits=24)
		row.next() # for multirow

		self.ratio = FloatScaleOption(f, row.next(), 'key-fill ratio',
				Lighting.ratio(),
				self._setRatio, multirow=True,
				min=1, scale_from=1, scale_to=MAX_RATIO,
				scale_resolution=-0.25, scale_digits=24)
				#balloon="TV news: 1.5, Sitcom: 2"
				#",\nDrama: 4, Action Sequence: 8")
				#",\nHorror movie: 10, Film Noir: 16")
		row.next() # for multirow

		self.highlightFrame = Tkinter.Frame(w.interior())
		self.highlightFrame.pack(side=Tkinter.LEFT)
		self.highlightFrame.pack_forget()
		row = itertools.count()
		f = Tkinter.Frame(self.highlightFrame)
		f.pack(side=Tkinter.LEFT)

		self.sharpness = FloatScaleOption(f, row.next(), "sharpness",
				Lighting.sharpness(), self._setSharpness,
				multirow=True, min=0, max=128,
				scale_from=0, scale_to=128)
		row.next() # for multirow

		self.reflectivity = FloatScaleOption(f, row.next(),
				"reflectivity", Lighting.reflectivity(),
				self._setSharpness, multirow=True,
				min=0, scale_from=0.0, scale_to=10.0,
				scale_resolution=0.1)
		row.next() # for multirow

		self.shinyColor = tkoptions.ColorOption(f, row.next(),
					"color", Lighting.shinyColor(),
					self._setSharpness, noneOkay=False)

		f = Tkinter.Frame(master)
		f.pack(expand=Tkinter.TRUE, fill=Tkinter.BOTH, ipadx=5, ipady=5)
		f.grid_rowconfigure(0, weight=1)
		f.grid_columnconfigure(0, weight=1)
		f.grid_columnconfigure(1, weight=1)
		f.grid_columnconfigure(2, weight=1)
		f.grid_columnconfigure(3, weight=1)
		g = self._makeGraphics(f)
		g.grid(row=0, columnspan=4, sticky=Tkinter.NSEW, padx=1, pady=1)
		r = 1
		t = Tkinter.Label(f, text="key light:")
		t.grid(row=r, column=0, sticky=Tkinter.E)
		c = Tkinter.Frame(f, background=keyColor)
		c.grid(row=r, column=1, sticky=Tkinter.NSEW, padx=3, pady=2)
		self.keyinfo = (r, 0, t, c)
		t = Tkinter.Label(f, text="fill light:")
		t.grid(row=r, column=2, sticky=Tkinter.E)
		c = Tkinter.Frame(f, background=fillColor)
		c.grid(row=r, column=3, sticky=Tkinter.NSEW, padx=3, pady=2)
		self.fillinfo = (r, 2, t, c)

		self._chooseInterface()
		self._modeCB(self.mode, _force=True)

	def showInterface(self, which):
		self.interfaceVar.set(which)
		self._chooseInterface()

	def update(self):
		# update widgets with current values
		if Lighting.mode() != self.mode.get():
			self.mode.set(Lighting.mode())
			self._modeCB(self.mode, _force=True)
		brightness = Lighting.brightness()
		if brightness != self.brightness.get():
			self.brightness.set(brightness)
		contrast = Lighting.contrast()
		maxr = Lighting.maximum_ratio(contrast)
		if contrast != self.contrast.get():
			self.contrast.set(contrast)
			self.ratio.update_max(None,
				maxr if maxr < MAX_RATIO else MAX_RATIO)
		ratio = Lighting.ratio()
		if ratio != self.ratio.get():
			new_ratio = ratio if ratio < maxr else maxr
			if new_ratio != self.ratio.get():
				self.skipRatioUpdate = True
				self.ratio.set(new_ratio)
		sharpness = Lighting.sharpness()
		if sharpness != self.sharpness.get():
			self.sharpness.set(sharpness)
		reflectivity = Lighting.reflectivity()
		if reflectivity != self.reflectivity.get():
			self.reflectivity.set(reflectivity)
		shinyColor = Lighting.shinyColor()
		if shinyColor != self.shinyColor.get():
			self.shinyColor.set(shinyColor)

	def map(self):
		import chimera
		self._updateSharpness()
		if not self.trackLights:
			self.trackLights = chimera.triggers.addHandler(
						"Light",
						self._trackLights, None)
		if not self.trackViewers:
			self.trackViewers = chimera.triggers.addHandler(
						"Viewer",
						self._trackViewers, None)
		if not self.trackMaterials:
			self.trackMaterials = chimera.triggers.addHandler(
						"Material",
						self._trackMaterials, None)

	def unmap(self):
		import chimera
		if self.trackLights:
			chimera.triggers.deleteHandler("Light",
					self.trackLights)
			self.trackLights = None
		if self.trackViewers:
			chimera.triggers.deleteHandler("Viewer",
					self.trackViewers)
			self.trackViewers = None
		if self.trackMaterials:
			chimera.triggers.deleteHandler("Material",
					self.trackMaterials)
			self.trackMaterials = None

	def _makeGraphics(self, master):
		try:
			from _LightViewer import LightViewer
		except ImportError:
			self.viewer = None
			return None
		import Tkinter
		import chimera
		import Togl
		f = Tkinter.Frame(master, bd=3, relief=Tkinter.SUNKEN)
		self.drag = False
		self.viewer = v = LightViewer(chimera.viewer)
		kw = {
			'width': 100, 'height': 100,
			'double': True, 'rgba': True, 'depth': True,
			"multisample": chimera.multisample,
			'createcommand': v.createCB,
			'reshapecommand': v.reshapeCB,
			'displaycommand': v.displayCB,
			'destroycommand': v.destroyCB,
		}
		try:
			self.graphics = Togl.Togl(f, **kw)
		except Tkinter.TclError, what:
			# assume that failures are secondary to the SideView
			# failing and suppress backtraces so they are not
			# reported as bugs
			e = str(what)
			text = ("Unable to create lighting graphics window.\n"
				"Please update your video/graphics\n"
				"driver, and/or upgrade your graphics card.\n"
				"(%s)") % e
			self.graphics = Tkinter.Label(f, text=text,
					bg='black', fg='white')
			return
		else:
			self.graphics.bind('<ButtonPress-1>', self._press)
			self.graphics.bind('<Button1-Motion>', self._drag)
			self.graphics.bind('<ButtonRelease-1>', self._release)
		self.graphics.pack(expand=Tkinter.TRUE, fill=Tkinter.BOTH)
		return f

	def _press(self, e):
		if self.drag:
			return
		self.drag = self.viewer.dragStart(e.x, e.y)

	def _drag(self, e):
		if self.drag:
			self.viewer.dragMotion(e.x, e.y)
			#self.saveui.setItemChanged(True)

	def _release(self, e):
		if self.drag:
			self.viewer.dragEnd()
			self.drag = False

	def _trackLights(self, trigger, closure, lights):
		import chimera
		foundOne = False
		from Lighting import KEY, FILL, BACK, _DIR
		for light in lights.modified:
			if light == chimera.viewer.keyLight:
				l = KEY
			elif light == chimera.viewer.fillLight:
				l = FILL
			elif light == chimera.viewer.backLight:
				l = BACK
			else:
				continue
			foundOne = True
			# viewer interface only changes the light direction
			Lighting._params[l][_DIR] = light.direction.data()
		if foundOne and self.viewer:
			Lighting._updateLights()
			self.saveui.setItemChanged(True)
			self.viewer.postRedisplay()

	def _trackViewers(self, trigger, closure, viewers):
		import chimera
		if chimera.viewer not in viewers.modified:
			return
		#if 'attribute changed' not in viewer.modified:
		#	return
		self.update()
		if self.viewer:
			self.viewer.postRedisplay()

	def _trackMaterials(self, trigger, closure, materials):
		import chimera
		mat = chimera.Material.lookup("default")
		if mat not in materials.modified:
			return
		self._updateSharpness()
		if self.viewer:
			self.viewer.postRedisplay()

	def _modeCB(self, option, _force=False):
		mode = option.get()
		if not _force and mode == Lighting.mode():
			return
		Lighting.setMode(mode)
		import Tkinter
		if mode == Lighting.AMBIENT:
			self.contrast.disable()
			self.ratio.disable()
			self.keyinfo[2].grid_forget()
			self.keyinfo[3].grid_forget()
			self.fillinfo[2].grid_forget()
			self.fillinfo[3].grid_forget()
		elif mode == Lighting.ONE:
			self.contrast.enable()
			self.contrast.update_min(0)
			self.ratio.disable()
			self._update_max_ratio()
			self.keyinfo[2].grid_forget()
			self.keyinfo[3].grid_forget()
			self.fillinfo[2].grid_forget()
			self.fillinfo[3].grid_forget()
		elif mode == Lighting.TWO:
			self.contrast.enable()
			self.ratio.enable()
			self._update_max_ratio()
			self.keyinfo[2].grid(row=self.keyinfo[0],
					column=self.keyinfo[1],
					sticky=Tkinter.E, padx=3)
			self.keyinfo[3].grid(row=self.keyinfo[0],
					column=self.keyinfo[1] + 1,
					sticky=Tkinter.NSEW, padx=1, pady=1)
			self.fillinfo[2].grid(row=self.fillinfo[0],
					column=self.fillinfo[1],
					sticky=Tkinter.E, padx=3)
			self.fillinfo[3].grid(row=self.fillinfo[0],
					column=self.fillinfo[1] + 1,
					sticky=Tkinter.NSEW, padx=1, pady=1)
		elif mode == Lighting.THREE:
			self.contrast.enable()
			self.ratio.enable()
			self._update_max_ratio()
			self.keyinfo[2].grid(row=self.keyinfo[0],
					column=self.keyinfo[1],
					sticky=Tkinter.E, padx=3)
			self.keyinfo[3].grid(row=self.keyinfo[0],
					column=self.keyinfo[1] + 1,
					sticky=Tkinter.NSEW, padx=1, pady=1)
			self.fillinfo[2].grid(row=self.fillinfo[0],
					column=self.fillinfo[1],
					sticky=Tkinter.E, padx=3)
			self.fillinfo[3].grid(row=self.fillinfo[0],
					column=self.fillinfo[1] + 1,
					sticky=Tkinter.NSEW, padx=1, pady=1)
		# disable/enable Shininess panel elements
		if mode == Lighting.AMBIENT:
			self.sharpness.disable()
			self.reflectivity.disable()
			self.shinyColor.disable()
		else:
			self.sharpness.enable()
			self.reflectivity.enable()
			self.shinyColor.enable()
		self._chooseInterface()
		if self.viewer:
			self.viewer.postRedisplay()
		self.saveui.setItemChanged(True)

	def _updateSharpness(self):
		import chimera
		mat = chimera.Material.lookup("default")
		self.sharpness.set(mat.shininess)
		self.shinyColor.set(Lighting.shinyColor())
		self.reflectivity.set(Lighting.reflectivity())

	def _chooseInterface(self, value=None):
		if value is None:
			value = self.interfaceVar.get()
		if value == self.Interface_Lights:
			try:
				from _LightViewer import LightViewer
				self.viewer.mode = LightViewer.All
			except ImportError:
				pass
			self.highlightFrame.pack_forget()
			self.mainFrame.pack()
		elif value == self.Interface_Shininess:
			try:
				from _LightViewer import LightViewer
				self.viewer.mode = LightViewer.Shininess
			except ImportError:
				pass
			self.mainFrame.pack_forget()
			self.highlightFrame.pack()

	def _setBrightness(self, *ignore):
		brightness = self.brightness.get()
		if brightness is None:
			return
		Lighting.setBrightness(brightness)

	def _setContrast(self, *ignore):
		contrast = self.contrast.get()
		if contrast is None:
			return
		self.skipRatioUpdate = True
		Lighting.setContrast(contrast)
		if self.mode.get() != Lighting.AMBIENT:
			self._update_max_ratio()

	def _update_max_ratio(self):
		contrast = self.contrast.get()
		maxr = Lighting.maximum_ratio(contrast)
		self.ratio.update_max(None,
			maxr if maxr < MAX_RATIO else MAX_RATIO)
		ratio = Lighting.ratio()
		mode = self.mode.get()
		if mode != Lighting.ONE:
			self.ratio.set(ratio if ratio < maxr else maxr)
		else:
			self.skipRatioUpdate = True
			self.ratio.enable()
			self.ratio.set(maxr)
			self.ratio.disable()

	def _setRatio(self, *ignore):
		ratio = self.ratio.get()
		if ratio is None or self.skipRatioUpdate:
			self.skipRatioUpdate = False
			return
		try:
			Lighting.setRatio(ratio)
		except ValueError:
			r = Lighting.ratio()
			self.ratio.set(r)

	def _setSharpness(self, opt=None):
		Lighting.setMaterial(self.sharpness.get(),
				self.shinyColor.get().rgba()[:3],
				self.reflectivity.get())
		self.saveui.setItemChanged(True)

	# Save and restore methods

	def setFromParams(self, p):
		# backwards compatibility
		Lighting._setFromParams(p)

	# Callback functions used by SaveUI

	def saveui_label(self):
		return "Lighting Settings"

	def saveui_presetItems(self):
		return [ SystemDefault ]

	def saveui_defaultItem(self):
		if UserDefault in Lighting.preferences():
			return UserDefault
		return SystemDefault

	def saveui_userItems(self):
		return Lighting.preferences().keys()

	def saveui_select(self, name):
		Lighting.restore(name)

	def saveui_save(self, name):
		Lighting.save(name)
		return True

	def saveui_delete(self, name):
		Lighting.delete(name)
		return True

	# Callback functions used by ViewDialog

	def save(self):
		self.saveui.saveAs(UserDefault, confirm=False)

	def restore(self):
		if UserDefault in Lighting.preferences():
			self.saveui.entryfield.setvalue(UserDefault)
			self.saveui.entryfield.invoke()
		else:
			self.saveui.entryfield.setvalue(SystemDefault)
			self.saveui.entryfield.invoke()

	def reset(self):
		self.saveui.entryfield.setvalue(SystemDefault)
		self.saveui.entryfield.invoke()

def display():
	from chimera.extension.StdTools import raiseViewingTab
	controller = singleton()
	raiseViewingTab(controller.Name)
	controller.showInterface(controller.Interface_Lights)
