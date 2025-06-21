import chimera
from tkoptions import Option, SymbolicEnumOption, FloatOption
from PIL import Image, ImageTk
import Tkdnd
import Tkinter as Tk
import tkFont

class ImageSource:
	def __init__(self, widget):
		if not hasattr(self, 'image'):
			raise ValueError('Image source must have image attribute')
		widget.bind('<ButtonPress>', self.im_dragStart)
		self.__widget = widget

	def im_dragStart(self, event):
		Tkdnd.dnd_start(self, event)

	def dnd_end(self, target, event):
		# we've dropped on a target
		pass

class ImageTarget:
	def dnd_accept(self, source, event):
		# as a target, do we accept a drag attempt?
		if hasattr(source, "image"):
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
		self.showImage(image=source._image)

class _ImageInterior(Tk.Canvas, ImageSource):
	def __init__(self, master, image, *args, **kw):
		Tk.Canvas.__init__(self, master, *args, **kw)
		ImageSource.__init__(self, self)
		self._image = image
		self._startEvent = None

	def __getattr__(self, name):
		# rgb/rgba tracked in containing well
		if name == "image":
			try:
				return self._image
			except:
				return None
		raise AttributeError, "Unknown attribute '%s'" % name

	def im_dragStart(self, event):
		if self._image != None:
			self._startEvent = event
			ImageSource.im_dragStart(self, event)
		else:
			#if event.state % 2 == 1:
			#	# 'shift' key depressed
			#	self._image.activate(exclusive=0) 
			#else:
			#	self._image.activate(exclusive=1) 
			pass

	def dnd_end(self, target, event):
		if (target is None
		  and self._startEvent is not None
		  and event is not None):
			if (event.type == "5"	# ButtonRelease
			  and event.x_root == self._startEvent.x_root
			  and event.y_root == self._startEvent.y_root):
				self._image.edgeClick(event)
		self._startEvent = None

class ImageWell(ImageTarget):

	Width = 64
	Height = 64

	def __init__(self, master, image=None, callback=None, noneOkay=False):
		self._callback = callback
		self._enabled = True
		self._image = ()	# nonsense value that is different
		self.noneOkay = noneOkay

		edgewidth = 0
		borderwidth = 2
		#edgewidth = int((min(self.Width, self.Height) + 2) / 12) + 2
		#borderwidth = int(min(self.Width + edgewidth,
		#			self.Height + edgewidth) / 15) + 1

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

		self._interior = _ImageInterior(f, self,
				width=self.Width, height=self.Height,
				highlightthickness=0, selectborderwidth=0,
				borderwidth=0)
		self._interior.pack()
		self._frame.bind('<Button-1>', self.edgeClick)
		self.showImage(image=image, doCallback=False)

	def edgeClick(self, event):
		if not self._enabled:
			return
		from OpenSave import OpenModal
		om = OpenModal(title="Background Image")
		pathsAndTypes = om.run(chimera.tkgui.app)
		om.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise chimera.UserError, 'No file chosen for background image'
		path = pathsAndTypes[0][0]
		try:
			self.showImage(Image.open(path))
		except IOError, e:
			from chimera import replyobj
			replyobj.error(str(e))

	def _wellNoImage(self):
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
		self._interior.configure(width=self.Width, height=self.Height)

	def enable(self):
		self._enabled = True
		self._frame['bg'] = self._activeBG
		self.interior.itemconfigure(Tk.ALL, state=Tk.NORMAL)

	def disable(self):
		self._enabled = False
		self._frame['bg'] = self._inactiveBG
		self._interior.itemconfigure(Tk.ALL, state=Tk.DISABLED)

	def showImage(self, image=None, doCallback=True):
		if image == self._image:
			return
		if image == None:
			if not self.noneOkay:
				raise ValueError('Must show a image')
			self._image = image
			if self._callback != None and doCallback:
				self._callback(None)

			self._wellNoImage()
			return

		self._interior.delete(Tk.ALL)
		self._image = image
		if self._callback != None and doCallback:
			self._callback(image)

		im = self._image.copy()
		im.thumbnail((self.Width, self.Height), Image.ANTIALIAS)
		self._thumbnail = ImageTk.PhotoImage(im)
		self._interior.create_image(0, 0, image=self._thumbnail,
								anchor=Tk.NW)
		width, height = im.size
		self._interior.configure(width=width, height=height)

	def grid(self, *args, **kw):
		self._frame.grid(*args, **kw)

	def pack(self, *args, **kw):
		self._frame.pack(*args, **kw)

# image tiling -- probably will be C++ constants
STRETCHED = chimera.LensViewer.Stretched
TILED = chimera.LensViewer.Tiled
ZOOMED = chimera.LensViewer.Zoomed
CENTERED = chimera.LensViewer.Centered

class TilingOption(SymbolicEnumOption):
	values = (ZOOMED, STRETCHED, TILED, CENTERED)
	labels = ('zoomed', 'stretched', 'tiled', 'centered')

class ImageOpacityOption(Option, ImageTarget):
	# use PrefImageOpacityOption to save in preferences

	default = (None, 1, ZOOMED, 1)

	def _addOption(self, noneOkay=False, **kw):
		if self.default[0] is None:
			self._image = None
		else:
			self._image = self.default[0]

		self._option = Tk.Frame(self._master)

		self._well = ImageWell(self._option, image=self._image,
				callback=self._updateImage, noneOkay=noneOkay)
		self._well.grid(rowspan=2)

		self.scale = FloatOption(self._option, 0, 'scale', self.default[1],
					self._set, startCol=2, min=0)
		self.opacity = FloatOption(self._option, 1, 'opacity', self.default[3],
					self._set, startCol=2, min=0, max=1)

		self.tiling = TilingOption(self._option, 0, '', self.default[2],
					self._set, startCol=4)
		self.tiling._option.grid(rowspan=2)
		self.scale.disable()

	def _updateImage(self, image):
		self._image = image
		self._set()

	def _set(self, e=None):
		tiling = self.tiling.get()
		if tiling in (ZOOMED, STRETCHED):
			self.scale.disable()
		else:
			self.scale.enable()
		Option._set(self)

	def get(self):
		return self._image, self.scale.get(), self.tiling.get(), self.opacity.get()

	def set(self, value):
		if value == None:
			self._image = None
			self.opacity.set(1)
			return
		self._image, scale, tiling, opacity = value
		self._well.showImage(self._image)
		self.opacity.set(opacity)
		if self.tiling.get() in (ZOOMED, STRETCHED):
			self.scale.enable()
		self.tiling.set(tiling)
		self.scale.set(scale)
		if tiling in (ZOOMED, STRETCHED):
			self.scale.disable()

	def enable(self):
		if self._label:
			self._label.config(state=Tk.NORMAL)
		self._well.enable()
		self.opacity.enable()
		self.tiling.enable()

	def disable(self):
		if self._label:
			self._label.config(state=Tk.DISABLED)
		self._well.disable()
		self.opacity.disable()
		self.tiling.disable()

from chimera import preferences

class PrefImageOpacityOption(preferences.Option):

	def __init__(self, cat, defValue, callback, closure, UIkw={}, imageFilename=None):
		if not imageFilename:
			raise ValueError("missing imageFilename")
		self._imageFilename = imageFilename
		preferences.Option.__init__(self, cat, defValue, callback,
							closure, UIkw=UIkw)
		assert((self.valToPref, self.prefToVal) == (None, None))

	def savedValue(self, forPrefSave=False):
		sv = preferences.Option.savedValue(self, forPrefSave=forPrefSave)
		if forPrefSave:
			import os
			filename = self._imageFilename
			pf = os.path.split(preferences.preferences.filename())
			path = os.path.join(*(pf[0:-1] + (filename,)))
			if sv[0] is None:
				filename = None
			else:
				try:
					sv[0].save(path)
				except SyntaxError:
					# recover from mysterious #13449
					filename = None
					from chimera import replyobj
					replyobj.warning("Unable to save background image")
			if filename is None:
				try:
					os.remove(path)
				except OSError:
					pass
			sv = (filename,) + sv[1:]
		return sv

	def set(self, value, fromTkoption=False, asSaved=False, fromPref=False):
		if fromPref and isinstance(value[0], basestring):
			import os
			filename = value[0]
			pf = os.path.split(preferences.preferences.filename())
			path = os.path.join(*(pf[0:-1] + (filename,)))
			try:
				from PIL import Image
				image = Image.open(path)
			except IOError:
				image = None
			value = (image,) + value[1:]
		preferences.Option.set(self, value, fromTkoption=fromTkoption,
				asSaved=asSaved, fromPref=fromPref)
