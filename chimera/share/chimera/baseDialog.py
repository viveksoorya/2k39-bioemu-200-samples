# Copyright (c) 2000 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: baseDialog.py 42335 2021-10-22 15:54:14Z pett $

"""
baseDialog -- provide dialog framework for chimera dialogs

The ModalDialog and ModelessDialog classes share several charactistics:

* each are configured via instance variables
* the names of the buttons correspond to methods
* one button may be highlighted as the default button
* the dialogs are designed to be created once and reused

"""
import string
import Tkinter
Tk = Tkinter
import Ttk
#import sys
from triggerSet import TriggerSet
triggers = TriggerSet()
TOOL_DISPLAY_CHANGE = "tool display change"
triggers.addTrigger(TOOL_DISPLAY_CHANGE)

# some possible button names
Apply = 'Apply'
Cancel = 'Cancel'
Close = 'Close'
OK = 'OK'

# manufacture a string useable in string.translate to map button
# names to identifiers
identChars = string.letters + string.digits + '_'
transTable = string.maketrans(' ', ' ')
delChars = ""
for c in transTable:
	if c not in identChars:
		delChars = delChars + c
del identChars, c

_lastPositionTime = None
def buttonFuncName(buttonName):
	return string.translate(buttonName, transTable, delChars)

class BaseDialog(object):
	"""Base class for chimera dialogs.

	Configuration variables:
	* name -- unique name of dialog for chimera dialog control
	* title -- title of dialog, defaults to name
	* buttons -- set of buttons to place at bottom of dialog
	* default -- which button to use as default

	If the class attribute / constructor keyword argument 'oneshot'
	is provided and True, the dialog will be destroyed on
	Cancel/Close/OK.  Otherwise, the dialog is only withdrawn.

	The class attribute / constructor keyword argument 'keepShown'
	is designed to allow a particular button to be treated as if
	it were Apply or OK.  The value is either None (no button gets
	the treatment) or a string value of the button name.  In the
	latter case, a checkbutton will be positioned above the bottom
	row of buttons to control if the named button acts like 'OK'
	(dialog closes) or Apply (dialog stays up).  In fact, the button
	will call Apply/OK as appropriate.

	The buttons should correspond to method names in the class.
	Some methods are already provided (see rest of BaseDialog
	documentation and ModalDialog and ModelessDialog).

	The <Return> key is bound to the default button.  If your
	dialog has a text entry field that needs to bind to <Return>,
	use the preventDefault method on the entry widget to prevent
	the <Return> from invoking the default button.
	
	The button methods should be declared in one of following
	two forms:

		def button-name(self, event=None)
		def button-name(self):

	The first form is needed for Cancel/Close buttons and the
	default button.  It allows the button method to be called
	with or without an event argument.

	From the Motif 1.1 Style Guide, common button combinations are
	(some are better for modeless, some for modal dialogs):

		Cancel
		Close
		OK				Modal
		OK Cancel
		OK Apply Cancel
		OK Apply Reset Cancel
		Yes No				Modal
		Yes No Cancel			Modal
		Retry Cancel			Modal

	Instance variables (to avoid):

	* _toplevel -- dialog's Toplevel widget

	Button names are assumed to correspond to dialog methods
	of the same name.  There should always be a Cancel or Close
	button.
	"""

	name = None
	title = None
	buttons = (Close,)
	default = None
	help = None		# urlAndPackage (see help.register())
	oneshot = False
	overMaster = False
	keepShown = None

	__doOnce = True

	def __init__(self, master=None, title=None, buttons=None, default=None,
			help=None, oneshot=None, highlight=None, keepShown=None,
			resizable=True, initiateAutoPositioning=True, *args, **kw):
		if master == None:
			from tkgui import app
			master = app
		else:
			self.overMaster = True
		self._master = master
		self._toplevel = Tk.Toplevel(master, *args, **kw)
		self._toplevel.wm_group(master)
		if initiateAutoPositioning:
			self.initialPosition()

		if title:
			self.title = title
		if not self.title:
			self.title = self.name
		if self.title:
			self._toplevel.title(self.title)
		if buttons:
			self.buttons = buttons
		if highlight and not default:
			default = highlight
		if default:
			self.default = default
		if not help is None:
			self.help = help
		if oneshot:
			self.oneshot = oneshot
		if keepShown:
			self.keepShown = keepShown
		if not resizable:
			self._toplevel.wm_resizable(0, 0)
		# 'OK' needs to be able to delay 'oneshot' destruction
		# until after the user-callback returns...
		self.delayOneshot = False
		#sys.__stderr__.write('Create dialog: %s %s\n' %
		#	(self.title, str(self._toplevel)))
		#self._toplevel.bind("<Destroy>", self.Destroy)
		self._toplevel.protocol('WM_DELETE_WINDOW', self.Cancel)
		if isinstance(self.buttons, basestring):
			# compensate for common error of buttons
			# not being a sequence.
			self.buttons = (self.buttons,)
		if Cancel in self.buttons:
			self._toplevel.bind("<Escape>",
						lambda e=None, c=self.Cancel: c())
		elif Close in self.buttons:
			self._toplevel.bind("<Escape>",
						lambda e=None, c=self.Close: c())

		bot = Tk.Frame(self._toplevel)
		bot.pack(side=Tk.BOTTOM, fill=Tk.X)
		hr = Tk.Frame(self._toplevel, relief=Tk.GROOVE,
						borderwidth=1, height=2)
		hr.pack(side=Tk.BOTTOM, fill=Tk.X)

		if self.keepShown:
			self.__ksVar = Tkinter.IntVar(bot)
			self.__ksVar.set(False)
			ckbut = Tkinter.Checkbutton(bot, variable=self.__ksVar,
				text="Keep dialog up after %s" % self.keepShown,
				command=self.__keepShownCB)
			from tkFont import Font
			font = Font(font=ckbut.cget('font'))
			font.config(size=int(0.75*float(font.cget('size'))+0.5),
						weight='normal')
			ckbut.config(font=font)
			ckbut.pack(side=Tk.TOP, anchor=Tk.SE)
			self.__keepShownCB() # set up initial button assignment

		for statusPrefix, statusSuffix, packKw in [
					('status', 'Status', {'fill': Tk.BOTH, 'expand': Tk.YES}),
					('secondaryStatus', 'SecondaryStatus', {'padx': 2})]:
			if hasattr(self, 'provide'+statusSuffix) and getattr(
			self, 'provide'+statusSuffix):
				slkw = { 'anchor': 'w', 'justify': 'left' }
				statusWidth = getattr(self, statusPrefix+'Width')
				if statusWidth:
					slkw['width'] = statusWidth
				statusPosition = getattr(self, statusPrefix+'Position')
				if statusPosition == "above":
					slMaster = self._toplevel
				else:
					slMaster = bot
				statusLine = Tk.Label(slMaster, **slkw)
				setattr(self, statusPrefix+'Line', statusLine)
				setattr(self, '_'+statusPrefix+'BlankHandle', None)
				statusResizing = getattr(self, statusPrefix+'Resizing')
				if not statusResizing:
					statusLine.bind('<Map>', lambda e=None, sl=statusLine:
									self._statusMapCB(sl))
				if statusPosition == "above":
					statusLine.pack(side=Tk.BOTTOM, fill=Tk.X,
						expand=Tk.NO)
				else:
					statusLine.pack(side=Tk.LEFT, **packKw)
		if self.help:
			import help
			help.register(self._toplevel, self.help)

		self.buttonWidgets = {}
		if resizable:
			sg = Ttk.Sizegrip(bot)
			sg.pack(anchor=Tk.SE, side=Tk.RIGHT)
		self.addSpecialButtons(bot)

		buttons = list(self.buttons[:])	# don't destroy original buttons
		# if Cancel or Close is present, it should be next to Help
		if Cancel in buttons:
			buttons.remove(Cancel)
			self.buttonWidgets[Cancel] = self.__addButton(bot,
						Cancel, self.default is Cancel)
		if Close in buttons:
			buttons.remove(Close)
			self.buttonWidgets[Close] = self.__addButton(bot,
						Close, self.default is Close)
		buttons.reverse()
		for b in buttons:
			self.buttonWidgets[b] = self.__addButton(bot, b,
							self.default == b)
		if self.name:
			import dialogs
			dialogs.reregister(self.name, self)

		# pack last, so that resizing dialog will not occlude
		# action buttons
		self.__top = Tk.Frame(self._toplevel)
		self.__top.pack(side=Tk.TOP, anchor=Tk.W, expand=1,
								fill=Tk.BOTH)
		# do this after pack so that fillInUI can show progress if
		# necessary
		self.fillInUI(self.__top)

	def initialPosition(self):
		if not self.overMaster:
			self._idleWaits = 0
			self._lastReqSize = None
			# tiling screws up if multiple dialogs are placed at
			# almost exactly the same time (since their sizes
			# aren't well-established), so spread them out...
			global _lastPositionTime
			from time import time
			delta = 0.1
			t = time()
			if _lastPositionTime is None or t > _lastPositionTime+delta:
				_lastPositionTime = t
				self._toplevel.after_idle(self._initialPositionCheck)
			else:
				def wait(s=self,
						t=int(1000.0 * (_lastPositionTime+delta - t)), *args):
					s._toplevel.after(t, s._initialPositionCheck)
				self._toplevel.after_idle(wait)
				_lastPositionTime += delta

	def _initialPositionCheck(self, *args):
		from tkgui import preferences, GENERAL, DIALOG_PLACEMENT
		if not preferences.get(GENERAL, DIALOG_PLACEMENT):
			return
		master = self._master
		if master is None:
			# dialog has no master to be positioned next to
			return
		tl = self._toplevel
		if tl.wm_transient():
			return
		if hasattr(tl, 'autoposition') and not tl.autoposition:
			return
		self._initialPosition()

	def _initialPosition(self, *args):
		tl = self._toplevel
		reqSize = (tl.winfo_reqwidth(), tl.winfo_reqheight())
		if not self._lastReqSize or reqSize[0] == 1:
			self._lastReqSize = reqSize
			tl.after_idle(self._initialPosition)
			return
		if reqSize != self._lastReqSize:
			self._idleWaits = 0
			self._lastReqSize = reqSize
			tl.after_idle(self._initialPosition)
			return
		self._idleWaits += 1
		if self._idleWaits < 5:
			tl.after_idle(self._initialPosition)
			return
		geom = self._fitPosition()
		if geom is None:
			geom = self._sidePosition()
		self._toplevel.geometry("%+d%+d" % geom)

	def _fitPosition(self):
		tl = self._toplevel
		w, h = tl.winfo_reqwidth(), tl.winfo_reqheight()
		sw, sh = tl.winfo_screenwidth(), tl.winfo_screenheight()
		outlines = []
		from tkgui import app
		for win in tuple(app.winfo_children()) + (app.winfo_toplevel(),):
			if not isinstance(win, (Tkinter.Toplevel, Tkinter.Tk)):
				continue
			if win == tl:
				continue
			if win.wm_state() == 'icon':
				continue
			if win.winfo_ismapped():
				wx, wy = win.winfo_rootx(), win.winfo_rooty()
				ww, wh = win.winfo_width(), win.winfo_height()
				outlines.append((wx, wx+ww-1, wy, wy+wh-1))

		if not outlines:
			return None

		leastOverlap = leastSep = bestPos = None
		for outline in outlines:
			# go around outlines in right, bottom, left, top order
			oMinX, oMaxX, oMinY, oMaxY = outline
			positions = []
			# right top
			if oMaxX + w <= sw and oMinY + (h-1) <= sh:
				positions.append((oMaxX+1, oMaxX+w, oMinY, oMinY+(h-1)))
			# right bottom
			if oMaxX + w <= sw and oMaxY - (h-1) >= 0:
				positions.append((oMaxX+1, oMaxX+w, oMaxY-(h-1), oMaxY))
			# bottom left
			if oMinX + (w-1) <= sw and oMaxY + h <= sh:
				positions.append((oMinX, oMinX+(w-1), oMaxY+1, oMaxY+h))
			# bottom right
			if oMaxX - (w-1) >= 0 and oMaxY + h <= sh:
				positions.append((oMaxX-(w-1), oMaxX, oMaxY+1, oMaxY+h))
			# left top
			if oMinX - w >= 0 and oMinY + (h-1) <= sh:
				positions.append((oMinX-w, oMinX-1, oMinY, oMinY+(h-1)))
			# left bottom
			if oMinX - w >= 0 and oMaxY - (h-1) >= 0:
				positions.append((oMinX-w, oMinX-1, oMaxY-(h-1), oMaxY))
			# top left
			if oMinX + (w-1) <= sw and oMinY - h >= 0:
				positions.append((oMinX, oMinX+(w-1), oMinY-h, oMinY-1))
			# top right
			if oMaxX - (w-1) >= 0 and oMinY - h >= 0:
				positions.append((oMaxX-(w-1), oMaxX, oMinY-h, oMinY-1))
			for pos in positions:
				overlap, sep = _evalPos(pos, outlines, leastOverlap, leastSep)
				if overlap is not None:
					leastOverlap, leastSep, bestPos = overlap, sep, pos
		if bestPos is not None:
			return (bestPos[0], bestPos[2])
		return None

	def _sidePosition(self):
		tl = self._toplevel
		w, h = tl.winfo_reqwidth(), tl.winfo_reqheight()
		sw, sh = tl.winfo_screenwidth(), tl.winfo_screenheight()
		master = self._master
		mw, mh, mx, my = (master.winfo_width(), master.winfo_height(),
				master.winfo_rootx(), master.winfo_rooty())
		# try right, then left, then bottom, then top
		room = sw - (mx + mw)
		gy = my + (mh - h)/2
		if gy < 0: gy = 0
		bottom = -1
		from tkgui import windowSystem
		if windowSystem == 'aqua':
			# X/Tk seemingly doesn't know Mac menubar exists...
			mbHeight = self._toplevel.winfo_pixels("0.25i")
			if gy < mbHeight: gy = mbHeight
			# nor does it handle negative y correctly...
			bottom = mbHeight
		if room >= w:
			bestOverlap = 0
			geom = (mx + mw, gy)
		else:
			bestOverlap = (w-room) * h
			if windowSystem == 'aqua':
				# cocoa Tk doesn't implement negative geometry correctly
				geom = (sw-w, gy)
			else:
				geom = (-1, gy)

		# now left...
		if bestOverlap > 0:
			room = mx
			if room >= w:
				bestOverlap = 0
				geom = (mx - w, gy)
			else:
				overlap = (w-room) * h
				if overlap < bestOverlap:
					bestOverlap = overlap
					geom = (0, gy)

		# bottom...
		if bestOverlap > 0:
			room = sh - my - mh
			gx = mx + (mw - w)/2
			if gx < 0: gx = 0
			if room >= h:
				bestOverlap = 0
				geom = (gx, my + mh)
			else:
				overlap = (h-room) * w
				if overlap < bestOverlap:
					bestOverlap = overlap
					geom = (gx, bottom)

		# top...
		if bestOverlap > 0:
			room = my
			if windowSystem == 'aqua':
				room -= mbHeight
			if room >= h:
				bestOverlap = 0
				geom = (gx, my - h)
			else:
				overlap = (h-room) * w
				if overlap < bestOverlap:
					bestOverlap = overlap
					if windowSystem == 'aqua':
						geom = (gx, mbHeight)
					else:
						geom = (gx, 0)
		return geom

	def __addButton(self, master, text, default=False):
		def command(s=self, txt=text):
			if s.buttonWidgets[txt].cget('state') != 'disabled':
				getattr(s, buttonFuncName(txt))()
		if default:
			# need to eat event, because buttons command don't get one.
			master.winfo_toplevel().bind("<Return>",
						lambda e=None, c=command: c())
		b = Tk.Button(master, text=text, command=command)
		b.pack(anchor=Tk.E, side=Tk.RIGHT, padx='1p', pady='1p')
		if default:
			b.configure(default='active')
		if default:
			master.focus_set()
		return b

	def __keepShownCB(self):
		keepName = buttonFuncName(self.keepShown)
		if hasattr(self, keepName) and getattr(self, keepName) not in [
		self.Apply, self.OK]:
			# if the button has an explicit function, 
			# keep using that
			return
		# make the "keep shown" button function as Apply or OK
		# as appropriate
		exec('self.%s = self.%s' % (keepName, self.keepEquiv()))

	def setKeepShown(self, val):
		self.__ksVar.set(val)
		self.__keepShownCB()

	def keepEquiv(self):
		if self.keepShown and self.__ksVar.get():
			return 'Apply'
		return 'OK'

	def placeOverMaster(self, master=None):
		# If our toplevel is not mapped, make sure it is
		# withdrawn so that "update_windows()" does not
		# make it pop up and jump around on the screen.
		if not self._toplevel.winfo_ismapped():
			self._toplevel.withdraw()
		if master is None:
			master = self._master.winfo_toplevel()
		import tkgui
		tkgui.update_windows()
		if master.winfo_ismapped():
			x = master.winfo_rootx() \
				+ master.winfo_width() / 2 \
				- self._toplevel.winfo_reqwidth() / 2
			y = master.winfo_rooty() \
				+ master.winfo_height() / 2 \
				- self._toplevel.winfo_reqheight() / 2
			# ensure that the window is on-screen
			if x < 0:
				x = 0
			if y < 0:
				y = 0
		else:
			x = master.winfo_screenwidth() / 2 \
				- self._toplevel.winfo_reqwidth() / 2
			y = master.winfo_screenheight() / 2 \
				- self._toplevel.winfo_reqheight() / 2
		self._toplevel.geometry('+%d+%d' % (x, y))

	def enter(self):
		"""Bring dialog to the foreground."""
		if self.overMaster:
			self.placeOverMaster()
		self.raiseWindow()

	def raiseWindow(self):
		self._toplevel.deiconify()
		import CGLtk
		CGLtk.raiseWindow(self._toplevel)

	def destroy(self):
		"""destroy this dialog"""
		if self.name:
			import dialogs
			dialogs.reregister(self.name, self.__class__)
		self._toplevel.destroy()
		self.buttonWidgets= []
		if isinstance(self, ModelessDialog) and self.title:
			triggers.activateTrigger(TOOL_DISPLAY_CHANGE, (self, False))

	def Cancel(self):
		"""Cancel any changes and dismiss dialog.
		
		This method (or 'destroy') may need to be overridden
		in the subclass.
		"""
		self.Close()

	def Close(self):
		"""Close dialog.

		The Cancel method should be overridden instead.
		"""
		self._toplevel.withdraw()
		# clear focus within dialog
		self._toplevel.focus()
		# Explicitly take the focus back, so we don't accidently
		# lose it to another application (e.g., on Windows).
		siblings = self._toplevel.master.winfo_children()
		siblings.reverse()
		for sib in siblings:
			if isinstance(sib, Tk.Toplevel) \
			and sib.winfo_ismapped():
				sib.focus()
				break
		else:
			self._toplevel.master.focus()
		if self.oneshot and not self.delayOneshot:
			self.destroy()

	#def Destroy(self, e=None):
	#	if e and e.widget == str(self._toplevel):
	#		sys.__stderr__.write('Destroy dialog: %s %s\n' %
	#					(self.title, e.widget))

	def uiMaster(self):
		"""Return the master widget that the UI should be placed in."""
		return self.__top

	def fillInUI(self, master):
		"""Fill in UI contents of dialog.
		
		master -- the master widget to put the dialog contents in

		This method should be replaced.
		"""
		pass

	def addSpecialButtons(self, master):
		if self.help == False:
			# help inappropriate; don't add Help button
			return
		b = self.__addButton(master, 'Help')
		self.buttonWidgets['Help'] = b
		if not hasattr(self, 'Help'):
			def helpPress(top=self._toplevel):
				import help
				help.display(top)
			self.Help = helpPress
			if not self.help:
				b.config(state=Tk.DISABLED)

	def preventDefault(self, widget):
		"""prevent Return in widget from automatically invoking default button"""
		# We add an additional bind tag to the widget that is
		# invoked before the widget's toplevel widget tag.  Then
		# we bind <Return> to that tag, so we can break out of
		# the return processing.
		breakTag = 'ReturnBreak'
		if BaseDialog.__doOnce:
			# TODO: presumably this would need be done once
			# per Tcl interpreter
			widget.bind_class(breakTag, '<Return>',
							lambda e: 'break')
			BaseDialog.__doOnce = False
		tags = list(widget.bindtags())
		top = tags.index(str(widget.winfo_toplevel()))
		tags.insert(top, breakTag)
		widget.bindtags(tuple(tags))

class ModelessDialog(BaseDialog):
	"""Base class for modeless chimera dialogs.

	The Help button depends on the class 'help' variable or 'help'
	constructor arg (latter overrides).  If specified (see below),
	a Help button will be automatically added that will open the
	given URL.  If 'None' (the default), a disabled Help button is
	added (indicating that help for the dialog will/may be added in
	the future).  If help is explicitly False, that indicates that
	the dialog is simple enough to be self-explanatory and no help
	will ever be provided, and a Help button is omitted.

	A status line is provided if the 'provideStatus' attribute is True.
	The 'status' method is used to post status messages.
	The status line defaults to above the action buttons and their
	horizontal divider.  If the 'statusPosition' attribute is "left",
	then the status area is to the left of the action buttons.  The
	status area will not resize the top level to show long messages
	unless the 'statusResizing' attribute is True.  The minimum with
	of the status line (in characters) can be specified with the
	'statusWidth' attribute. A secondary status area, designed for
	use with a 'left'-style status line, is provided if 'provide
	SecondaryStatus' is True. It is positioned to the right of the
	status line and flush against the buttons.  It is controlled much
	the same way as the status line, but with variables named
	provideSecondaryStatus, secondaryStatusPosition, and secondaryStatusWidth.
	It is used by calling the 'secondaryStatus' method.

	Additional Configuration Variables:
	* help -- URL or (URL, package).  The URL is relative to the package.
	* provideStatus -- boolean.  Described above.

	Two hooks for lazy updating of the UI are supported.  The
	map and unmap methods may be replaced with ones that turn
	on and off updating.
	"""

	buttons = (OK, Apply, Close)

	provideStatus = False
	statusWidth = None
	statusPosition = "above"
	statusResizing = False
	provideSecondaryStatus = False
	secondaryStatusWidth = None
	secondaryStatusPosition = "left"
	secondaryStatusResizing = False

	def __init__(self, master=None, *args, **kw):
		"""Initialize modeless dialog.

		master -- application widget
		"""
		from tkgui import windowSystem
		if windowSystem == 'aqua':
			self._kludgeNeeded = True
		BaseDialog.__init__(self, master, *args, **kw)
		self.uiMaster().bind("<Map>", self._map)
		self.uiMaster().bind("<Unmap>", self._unmap)
		if windowSystem == 'aqua':
			if self._kludgeNeeded:
				self._kludgeHandler = self.uiMaster().after(1000, self._macKludge)
			else:
				self._kludgeHandler = False
		if self.uiMaster().winfo_ismapped():
			# need to manually fire the 'map' function
			self._map()

	def _macKludge(self):
		self.uiMaster().winfo_toplevel().geometry("")
		self._kludgeHandler = None

	def Close(self):
		BaseDialog.Close(self)
		from tkgui import windowSystem
		if windowSystem == 'aqua':
			self._kludgeNeeded = False
			if getattr(self, '_kludgeHandler', False):
				self.uiMaster().after_cancel(self._kludgeHandler)
				self._kludgeHandler = None

	def OK(self):
		"""Apply and dismiss dialog.
		
		The Apply method should be overridden instead of this one."""
		self.delayOneshot = True
		# Close before Apply so that Apply functions that take a
		# long time nonetheless give immediate feedback (window
		# disappears).  Also, avoids having users hitting OK multiple
		# times and thereby executing the slow Apply function 
		# multiple times!
		self.Close()
		self.Apply()
		if self.oneshot:
			self.destroy()
	
	def Apply(self):
		"""Apply any changes made in dialog.
		
		This method may be replaced.
		"""
		pass

	def isVisible(self):
		return self._toplevel.state() == Tk.NORMAL

	def _map(self, e=None):
		try:
			self.map()
		finally:
			#if self.name or hasattr(self, 'emQuit'):
			if self.title:
				triggers.activateTrigger(TOOL_DISPLAY_CHANGE, (self, True))
			from tkgui import windowSystem
			if windowSystem == 'aqua':
				if self._kludgeHandler:
					self.uiMaster().after_cancel(self._kludgeHandler)
					self._kludgeHandler = None

	def map(self):
		"""Things to do when dialog is mapped.
		
		This method may be replaced."""
		pass

	def status(self, msg, blankAfter=None, echoToMain=False, log=False,
			followWith="", followTime=20, followLog=None,
			color='black', secondary=False):
		"""Display a status message

		   'blankAfter' controls how long (in seconds) before the
		   status area is automatically cleared.  Use zero to disable
		   auto-clearing this message.  'None' uses the user preference.

		   'echoToMain' and 'log' control sending an identical message
		   to the main window status line and the reply log,
		   respectively.

		   'followWith' is a message to follow the first one with.
		   'followTime' is how long until the followup message is
		   cleared (ala blankAfter).  'followLog' is whether to log
		   the follow message (defaults to the same as 'log').

		   Show the text in 'color' color.

		   If 'secondary' is True, send the message to the secondary
		   status area (the class attr provideSecondary must be True
		   for this work, analogously to the provideStatus attr).
		"""
		if secondary:
			statusLine = self.secondaryStatusLine
			provideStatus = self.provideSecondaryStatus
			blankHandleName = '_secondaryStatusBlankHandle'
		else:
			statusLine = self.statusLine
			provideStatus = self.provideStatus
			blankHandleName = '_statusBlankHandle'
		from chimera import replyobj
		if not provideStatus:
			raise ValueError("no status support in dialog")
		if getattr(self, blankHandleName):
			self.statusLine.after_cancel(getattr(self, blankHandleName))
			setattr(self, blankHandleName, None)

		if followLog is None:
			followLog = log

		if echoToMain:
			replyobj.status(msg, blankAfter=blankAfter, color=color)
		if log:
			replyobj.info(msg)
			if followWith:
				if not msg.endswith("\n"):
					msg += "\n"
				msg += "[above message copied to Reply Log]"
		statusLine.configure(text=msg.strip(), fg=color)
		statusLine.update_idletasks()

		blankTime = blankAfter
		if blankAfter is None:
			import preferences
			from replyobj import REPLY_PREFERENCES, STATUS_CLEARING
			blankTime = preferences.get(REPLY_PREFERENCES,
							STATUS_CLEARING)
		if blankTime != 0:
			if followWith:
				nextMsg = followWith
				nextTime = followTime
			elif log:
				nextMsg = "Previous message also written" \
						" to reply log"
				nextTime = 20
				followLog = False
			else:
				nextMsg = ""
				nextTime = 0
				followLog = False
			setattr(self, blankHandleName, self.statusLine.after(
				1000 * blankTime, lambda nm=nextMsg, nt=nextTime, s2=secondary,
				e2m=echoToMain, log=followLog, clr=color:
				self.status(nm, blankAfter=nt, secondary=s2, echoToMain=e2m,
					log=log, color=clr)))

	def _unmap(self, e=None):
		try:
			self.unmap()
		finally:
			#if self.name or hasattr(self, 'emQuit'):
			if self.title:
				triggers.activateTrigger(TOOL_DISPLAY_CHANGE, (self, False))

	def unmap(self):
		"""Things to do when dialog is unmapped.
		
		This method may be replaced."""
		pass

	def _statusMapCB(self, sl):
		"""Callback from status line Map event"""

		# Done in 'Map' callback so that height is correct

		# this isn't even called if resizing is allowed, so disallow
		sl.pack_propagate(False)

class ModalDialog(BaseDialog):
	"""Base class for modal chimera dialogs.
	"""
	# Code shamelessly stolen from conrad's ModalWindow which was
	# stolen from SimpleDialog.

	buttons = (Cancel,)

	def __init__(self, master=None, *args, **kw):
		BaseDialog.__init__(self, master, *args, **kw)
		self._toplevel.withdraw()
		self.inDialog = False

	def run(self, master):
		self._toplevel.wm_transient(master)
		if master.tk.call('tk', 'windowingsystem') in ('win32', 'aqua'):
			self.placeOverMaster(master)
		self.returnValue = None
		self.enter()
		self._toplevel.mainloop()
		return self.returnValue

	def enter(self):
		BaseDialog.enter(self)
		if not self.inDialog:
			# grab
			import Pmw
			Pmw.pushgrab(self._toplevel, False, lambda: None)
			self.inDialog = True

	def Cancel(self, value=None):
		BaseDialog.Cancel(self)
		import tkgui
		# workaround (ATI?) bug with releasing grab
		tkgui.update_windows()
		if self.inDialog:
			import Pmw
			Pmw.popgrab(self._toplevel)	# grab release
			self.inDialog = False
		self.returnValue = value
		self._toplevel.quit()

def _bitmap_image(widget, name):
	# try to use an image instead of a bitmap for
	# error, warning, info, or question
	bitmap = None
	image_names = widget.image_names()
	if isinstance(image_names, basestring):
		image_names = image_names.split()
	image = '::tk::icons::' + name
	if name == 'info':
		image += 'rmation'
	if image not in image_names:
		image = None
		bitmap = name
	return bitmap, image

class AskYesNoDialog(ModalDialog):
	"""Class for asking a yes/no question (modally)"""

	buttons = ('Yes', 'No')
	oneshot = True
	icon = 'question'

	def __init__(self, text, justify='left', icon=None, **kw):
		"""'text' should be the question being asked"""
		self.text = text
		self.justify = justify
		if icon is not None:
			self.icon = icon
		ModalDialog.__init__(self, **kw)

	def fillInUI(self, parent):
		import Tkinter as Tk
		if self.icon:
			b, i = _bitmap_image(parent, self.icon)
			self.image = Tk.Label(parent, bitmap=b, image=i)
			self.image.pack(side=Tk.LEFT, padx=4, pady=4)
		self.message = Tk.Label(parent, text=self.text,
				wraplength=400, justify=self.justify)
		self.message.pack(fill=Tk.BOTH, expand=Tk.TRUE, padx=4, pady=4)
		self.message.bind("<Configure>", self.msgConfig)
		self.reconfig = True

	def msgConfig(self, event):
		if not self.reconfig:
			# only reconfigure once to avoid configure loops
			return
		self.message.config(wraplength=event.width)
		self.reconfig = False
		
	def Yes(self):
		ModalDialog.Cancel(self, value='yes')

	def No(self):
		ModalDialog.Cancel(self, value='no')

class NotifyDialog(ModalDialog):
	"""Class for notifying user of an event (modally)"""

	buttons = ('OK')
	default = 'OK'
	oneshot = True
	help = False

	def __init__(self, text, justify='left', icon='info', **kw):
		"""'text' should be notification message"""
		self.text = text
		self.justify = justify
		self.icon = icon
		ModalDialog.__init__(self, **kw)

	def fillInUI(self, parent):
		import Tkinter as Tk
		if self.icon:
			b, i = _bitmap_image(parent, self.icon)
			self.image = Tk.Label(parent, bitmap=b, image=i)
			self.image.pack(side=Tk.LEFT, padx=4, pady=4)
		self.message = Tk.Label(parent, text=self.text,
					wraplength=400, justify=self.justify)
		self.message.pack(fill=Tk.BOTH, expand=Tk.TRUE, padx=4, pady=4)
		self.message.bind("<Configure>", self.msgConfig)
		self.reconfig = True

	def msgConfig(self, event):
		if not self.reconfig:
			# only reconfigure once to avoid configure loops
			return
		self.message.config(wraplength=event.width)
		self.reconfig = False
		
	def OK(self):
		ModalDialog.Cancel(self)

def _evalPos(pos, outlines, leastOverlap, leastSep):
	pMinX, pMaxX, pMinY, pMaxY = pos
	overlap = 0
	for oMinX, oMaxX, oMinY, oMaxY in outlines:
		if pMinX > oMaxX or pMaxX < oMinX or pMinY > oMaxY or pMaxY < oMinY:
			continue
		overlap += (max(oMaxX-pMinX, 0) + max(pMaxX-oMinX, 0)) * (
			max(oMaxY-pMinY, 0) + max(pMaxY-oMinY, 0))
		if leastOverlap is not None and overlap >= leastOverlap:
			return None, None
	if overlap > 0:
		return overlap, None

	sep = 0
	for oMinX, oMaxX, oMinY, oMaxY in outlines:
		if oMinX > pMaxX:
			sepX = oMinX - pMaxX
		elif pMinX > oMaxX:
			sepX = pMinX - oMaxX
		else:
			sepX = 0
		if oMinY > pMaxY:
			sepY = oMinY - pMaxY
		elif pMinY > oMaxY:
			sepY = pMinY - oMaxY
		else:
			sepY = 0
		sep += max(sepX, sepY)
		if leastSep is not None and sep >= leastSep:
			return None, None
	return overlap, sep

if __name__ == '__main__':
	master = Tk.Tk()
	class TestDialog(ModelessDialog):
		title = 'Print'
		#buttons = ['Print', 'Test', 'Cancel']
		#default = 'Print'
		buttons = ('Cancel',)
		default = 'Cancel'

		def __init__(self, master):
			ModelessDialog.__init__(self, master)

		def Print(self, event=None):
			print 'print'

	e = TestDialog(master)
	master.mainloop()
