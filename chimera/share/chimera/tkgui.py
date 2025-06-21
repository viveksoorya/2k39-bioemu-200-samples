# Copyright (c) 2000-2017 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: tkgui.py 42418 2023-01-03 21:56:53Z pett $

"""
Chimera Graphical User Interface using Tk
"""
import sys, os
import Tkinter
Tk = Tkinter

# install fixed version of nametowidget so that cloned menu widgets work
def fixedNametowidget(self, name):
	w = self
	if not isinstance(name, str):
		name = str(name)
	if name[0] == '.':
		w = w._root()
		name = name[1:]
	while name:
		i = name.find('.')
		if i >= 0:
			name, tail = name[:i], name[i+1:]
		else:
			tail = ''
		try:
			w = w.children[name]
		except KeyError:
			if name[0] == '#':
				# looks like clone widget...
				if not tail:
					tail = name
				lastDot = tail.rfind('.')
				if lastDot >= 0:
					tail = tail[lastDot+1:]
				clone = tail.replace('#', '.')
				return self.nametowidget(clone)
			elif name.startswith("tixsw:"):
				return w
			raise
		name = tail
	return w

Tkinter.Misc.originalNametowidget = Tkinter.Misc.nametowidget
Tkinter.Misc.fixedNametowidget = fixedNametowidget
Tkinter.Misc.nametowidget = fixedNametowidget
Tkinter.Misc._nametowidget = fixedNametowidget

# Workaround for threaded python event processing delays
# that improves our chances of hitting our frame rate targets.
if hasattr(Tkinter._tkinter, "setbusywaitinterval"):
	Tkinter._tkinter.setbusywaitinterval(1)

# workaround for Imaging/PIL and some TIFF files
from PIL import TiffImagePlugin
tiffInfoDict = { (2, 1, (8, 8, 8, 8), (1,)): ("RGBA", "RGBA") }
for k, v in tiffInfoDict.items():
	if not TiffImagePlugin.OPEN_INFO.has_key(k):
		TiffImagePlugin.OPEN_INFO[k] = v
del k, v, tiffInfoDict

# workaround for widget.update and _tkinter.dooneevent doing frame updates
# when we don't want them
def update_windows():
	# Like widget.update() but only does window-related events --
	# that is, no timer or file events.
	import _tkinter
	while _tkinter.dooneevent(_tkinter.DONT_WAIT|_tkinter.WINDOW_EVENTS|_tkinter.IDLE_EVENTS):
		pass

import Pmw
import Togl

import chimera
from chimera import splash
from chimera import dialogs, help, preferences, selection, replyobj
from chimera.misc import chimeraLabel
from chimera import tkoptions

from chimera import toolbar
from CGLtk.color import ColorWell
from CGLtk.MenuBalloon import MenuBalloon
from chimera.baseDialog import ModelessDialog, ModalDialog
from chimera.selection.manager import selMgr
from chimera.selection.seq import SeqSelDialog
from chimera import exportDialog
from chimera import publishDialog
from chimera import printer

app = None	# top-level Tk widget for application

windowSystem = None		# 'x11', 'aqua', 'win32'

# mouse button and modifier codes
B1 = intern("1")
B2 = intern("2")
B3 = intern("3")
CTRL = intern("Ctrl")
SHFT = intern("Shift")
ALT = intern("Alt")	# Alt = Mod1

# preference categories and names
from initprefs import GENERAL
CONFIRM_EXIT = "Confirm quit"
FULLSCREEN_GRAPHICS = "Fullscreen graphics"
COMPACT_OPENSAVE = "Use short open/save browser"
CONFIRM_OVERWRITE = "File browser confirms overwrite"
STARTUP_DIRECTORY = "Open dialog starts in directory \nfrom last session"
PATH_STYLE = "File lists path style"
PATH_NEXT = "file - leading path"
PATH_NORMAL = "full path"
MOUSE = "Mouse"
AQUA_MENUS = 'Menus in windows on Mac'
DEBUG_OPENGL = 'Debug OpenGL on startup'
UPDATE_CHECK_INTERVAL = 'Update check interval'
INITIAL_WINDOW_SIZE = "Initial window size"
FIXED_SIZE = "Fixed size"
DIALOG_PLACEMENT = "Try to avoid placing dialogs\nover main window"

class PathStyleOption(tkoptions.EnumOption):
	"""Specialization of EnumOption class for path style"""
	values = (PATH_NEXT, PATH_NORMAL)
	balloon = \
		'In lists of files, show each file as the file name\n'\
		'followed by the directory path to the file or as\n'\
		'a directory path with the file name at the end\n'\
		'\nChange takes effect at next Chimera session'

class UpdateIntervalOption(tkoptions.SymbolicEnumOption):
	"""possible update intervals, the values are in days"""
	labels = ('never', 'daily', 'weekly', 'biweekly', 'monthly', 'quarterly')
	values = (0, 1, 7, 15, 30, 90)

class InitialWindowSizeOption(tkoptions.SymbolicEnumOption):
	labels = ('remember last', 'fixed')
	values = (0, 1)

class ConfirmQuitOption(tkoptions.SymbolicEnumOption):
	labels = ('always', 'conditional', 'never')
	values = ('always', 'conditional', 'never')
	balloon = \
		'Whether to show a confimation dialog when Chimera\n' \
		'exits.  If "conditional", then confirmation will only\n' \
		'occur if a tool feels that substantial unsaved work\n' \
		'will be lost by exiting.  This option also controls\n' \
		'confirmation during "close session", though in that\n' \
		'case "always" is downgraded to "conditional".'

class WindowSizeOption(tkoptions.Option):
	"""like an Int2TupleOption, if it existed"""

	min = None
	max = None
	cbmode = tkoptions.Option.RETURN

	def _addOption(self, min=None, max=None, **kw):
		if min != None:
			self.min = min
		if max != None:
			self.max = max
		entry_opts = {
			'validatecommand': self._val_register(self._validate),
			'relief': Tk.SUNKEN,
			'borderwidth': 2,
			'width': 4,
			'validate': 'all',
		}
		entry_opts.update(kw)
		self._option = Tk.Frame(self._master)
		self.entries = []
		e = Tk.Entry(self._option, **entry_opts)
		e.pack(side=Tk.LEFT)
		self.entries.append(e)
		self.X = Tk.Label(self._option, text='x')
		self.X.pack(side=Tk.LEFT)
		e = Tk.Entry(self._option, **entry_opts)
		e.pack(side=Tk.LEFT)
		self.entries.append(e)
		self.bgcolor = self.entries[0].cget('bg')
		self._value = [ None, None ]
		if 'state' in entry_opts and entry_opts['state'] == Tk.DISABLED:
			self.disable()
		return self._option

	def enable(self):
		for e in self.entries:
			e.config(state=Tk.NORMAL)
		self.X.config(state=Tk.NORMAL)
		if self._label:
			self._label.config(state=Tk.NORMAL)

	def disable(self):
		for e in self.entries:
			e.config(state=Tk.DISABLED)
		self.X.config(state=Tk.DISABLED)
		if self._label:
			self._label.config(state=Tk.DISABLED)

	def _set(self, args):
		action = args['action']
		entry = args['widget']
		index = self.entries.index(entry)
		try:
			value = int(args['new'])
		except ValueError, info:
			if action != -1:
				entry.configure(bg=self.errorColor)
			else:
				# enter/leave, reset to valid value
				entry.configure(bg=self.bgcolor)
				if self._value[0] is not None and self._value[1]is not None:
					self.set(self._value)
			return Tk.TRUE
		entry.configure(bg=self.bgcolor)
		if action == -1:
			if self.min is not None and value < self.min:
				altered = self._value[index] != self.min
				self._update_value(self.min, index)
				if altered:
					tkoptions.Option._set(self)
			elif self.max is not None and value > self.max:
				altered = self._value[index] != self.max
				self._update_value(self.max, index)
				if altered:
					tkoptions.Option._set(self)
			else:
				if self._value != value:
					self._value[index] = value
					tkoptions.Option._set(self)
			return Tk.TRUE
		if (self.min is not None and value < self.min) \
		or (self.max is not None and value > self.max):
			entry.configure(bg=self.errorColor)
			return Tk.TRUE
		if self.cbmode == tkoptions.Option.CONTINUOUS:
			self._value[index] = value
			tkoptions.Option._set(self)
		return Tk.TRUE

	def _bindReturn(self):
		# override as appropriate
		for e in self.entries:
			e.bind('<Return>', self._return)

	def _return(self, e=None):
		widget = e.widget
		args = {
			'action': -1,
			'new': widget.get(),
			'widget': widget
		}
		self._set(args)
		if self.cbmode == tkoptions.Option.RETURN_TAB \
		or (self.cbmode == tkoptions.Option.RETURN and widget != self.entries[1]):
			w = widget.tk_focusNext()
			if w:
				w.focus()
		return 'break'
	
	def _update_index(self, value, index):
		self._value[index] = value
		entry = self.entries[index]
		validate = entry.cget('validate')
		if validate != Tk.NONE:
			entry.configure(validate=Tk.NONE)
		state = entry.cget('state')
		if state == Tk.DISABLED:
			entry.configure(state=Tk.NORMAL)
		entry.delete(0, Tk.END)
		strvalue = '%d' % value
		entry.insert(Tk.END, strvalue)
		if state == Tk.DISABLED:
			entry.configure(state=Tk.DISABLED)
		if validate != Tk.NONE:
			entry.configure(validate=validate)

	def set(self, value):
		assert(len(value) == 2)
		value = [int(value[0]), int(value[1])]
		for index in range(2):
			self._update_index(value[index], index)

	def get(self):
		return self._value

	def setMultiple(self):
		raise RuntimeError, "%s does not implement setMultiple()" % (
							self.__class__.__name__)


exitOnQuit = True
def _confirmExit(neverAsk=False):
	"""Double check if the user wanted to exit"""
	global app
	import tkMessageBox
	from chimera import triggers, APPQUIT, CONFIRM_APPQUIT, ChimeraSystemExit
	if not neverAsk and preferences.get(GENERAL, CONFIRM_EXIT) != "never":
		msgs = []
		triggers.activateTrigger(CONFIRM_APPQUIT, msgs)
		if not msgs and preferences.get(GENERAL, CONFIRM_EXIT) == "always":
			msgs.append("")
		for msg in msgs:
			if not msg:
				message = "Really Quit?"
			else:
				message = msg + "\nReally Quit?"
			if not tkMessageBox.askokcancel(master=app, title="Quit Confirmation",
					message=message):
				return
	triggers.activateTrigger(APPQUIT, None)
	global exitOnQuit
	if not exitOnQuit or sys.platform == 'win32':
		# need to shutdown GUI before exiting to avoid crash on Windows
		replyobj.clearReplyStack()
		app.winfo_toplevel().destroy()
		app = None
	if exitOnQuit:
		raise ChimeraSystemExit, 0

from OpenSave import OpenModeless
class _ImportDialog(OpenModeless):
	title = "Open File in Chimera"
	def fillInUI(self, parent):
		# Allow dialog creation without showing the dialog.
		parent.winfo_toplevel().withdraw()
		OpenModeless.fillInUI(self, parent)
	def Apply(self):
		pt = self.getPathsAndTypes()
		for path, ftype in pt:
			if not chimera.fileInfo.batch(ftype):
				openPath(path, ftype)
		# Process file types where paths are batched to open one model.
		bpaths = {}
		for path, ftype in pt:
			if chimera.fileInfo.batch(ftype):
				if ftype in bpaths:
					bpaths[ftype].append(path)
				else:
					bpaths[ftype] = [path]
		for ftype, paths in bpaths.items():
			openPath(paths, ftype)

def openPath(path, ftype, ignore_cache=False):
	from os.path import basename
	if isinstance(path, (list,tuple)):
		descrip = '%s ... (%d files)' % (basename(path[0]), len(path))
	else:
		descrip = basename(path)
	descrip = descrip.decode('utf8')
	replyobj.status("Opening %s" % descrip)
	try:
		mols = chimera.openModels.open(path, type=ftype, ignore_cache=ignore_cache)
	except SyntaxError, value:
		replyobj.error(descrip + ": " + str(value) + "\n")
	except IOError, value:
		replyobj.error(str(value) + "\n")
	except SystemExit:
		raise
	except:
		replyobj.reportException("Error reading " + descrip)
	replyobj.status("Done opening %s" % descrip)

def _importModel():
	importDialog().enter()

_importDialog = None
def importDialog():
	global _importDialog
	if not _importDialog:
		types = chimera.fileInfo.types(sourceIsFile=1)
		types.sort(lambda a, b: cmp(a.lower(), b.lower()))
		filters = []
		def mkFilter(fileType):
			globs = []
			for ext in chimera.fileInfo.extensions(fileType):
				globs.append('*' + ext)
			return (fileType, globs)
		for t in types:
			filters.append(mkFilter(t))
		_importDialog = _ImportDialog(filters=filters,
				historyID="main chimera import dialog",
				defaultFilter="all (guess type)")
		# new file types add filters...
		def newFileTypeCB(trigName, myData, typeName,
					_id=_importDialog, mf=mkFilter):
			types = chimera.fileInfo.types(sourceIsFile=1)
			if typeName not in types:
				# may not be a "file-based" type (PDB ID, etc.)
				return
			types.sort(lambda a, b: cmp(a.lower(), b.lower()))
			_id.addFilter(mf(typeName), index=types.index(typeName))
		chimera.fileInfo.triggers.addHandler(
			chimera.fileInfo.NEWFILETYPE, newFileTypeCB, None)
	return _importDialog

# must import coloreditor at main scope so it can replace functionality
from chimera import coloreditor
ColorWell.setDefaultColorPanel(coloreditor.Editor)
def _colorEditor():
	d = ColorWell.colorPanel()
	d.enter()
	return d

class _OnVersionDialog(ModelessDialog):
	"""show chimera version"""

	name = 'About ' + chimera.title
	buttons = ('Chimera Home', 'Chimera License',
					'Embedded Licenses', 'Close')
	default = 'Close'
	help = False

	def fillInUI(self, master):
		from chimera import chimage
		icon = chimage.get('chimera48.png', master)
		l = Tk.Label(master, image=icon, borderwidth=10)
		l.__image = icon
		l.pack(side=Tk.LEFT)
		import platform
		bits = "64" if sys.maxsize > 2 ** 32 else ""
		plat = '%s%s' % (platform.system(), bits)
		from chimera import version
		text = ("UCSF Chimera, %s\n"
			"Platform: %s.  "
			"Windowing system: %s.\n"
			"\n"
			"Copyright (c) 2000-2023 by the Regents of the University of California.\n"
			"All rights reserved.  Use the Chimera License button below for license details.\n"
			"\n"
			"Portions of this software have other copyrights.  Use the Embedded Licenses\n"
			"button below for license details about embedded software.\n"
			"\n"
			"To check for the availability of newer versions, use the Check for Updates\n"
			"menu item." % (version.version, plat, windowSystem)
			)
		l = Tk.Label(master, borderwidth=10, justify=Tk.LEFT, text=text)
		l.pack(side=Tk.RIGHT)

	def ChimeraLicense(self):
		from chimera import help
		help.display("licensing.html")

	def EmbeddedLicenses(self):
		from chimera import help
		help.display("embedded.html")

	def ChimeraHome(self):
		home = "http://www.cgl.ucsf.edu/chimera/"
		help.display(home)


class _InspectDialog(ModelessDialog):
	"""Selection Inspector"""

	name = 'Inspect Selection'
	help = 'UsersGuide/inspection.html'
	buttons = ('Write List...', 'Write PDB...', 'Close')
	# no default button
	trigger = "selection changed"
	handler = None

	from chimera.tkoptions import inspectionInfo
	inspectionInfo.register(chimera.Atom)
	inspectionInfo.register(chimera.Bond)
	inspectionInfo.register(chimera.Residue)
	inspectionInfo.register(chimera.Molecule, displayAs="Molecule model")
	inspectionInfo.register(chimera.PseudoBond, displayAs="Pseudobond")
	inspectionInfo.register(chimera.PseudoBondGroup,
						displayAs="Pseudobond group")
	inspectionInfo.register(chimera.MSMSModel, displayAs="MSMS surface")

	def fillInUI(self, master):
		from chimera import Inspector
		self.totalsVar = Tk.StringVar(master)
		self.totalsLabel = Tk.Label(master, textvariable=self.totalsVar,
				justify="left", anchor="nw", width=25, height=5)
		self.totalsLabel.pack(side=Tk.TOP, fill="both", expand=1)
		self.inspector = Inspector.Inspector(master)

		self.otherClasses = {}
		for insp in self.inspectionInfo.inspectables:
			self._addInspectable(insp)
		self.inspectionInfo.registerCB(self._addInspectable)

	def unmap(self, e=None):
		if self.handler:
			chimera.triggers.deleteHandler(self.trigger,
								self.handler)
			self.handler = None
			for mc, handler in self.mainClassHandlers.items():
				chimera.triggers.deleteHandler(mc.__name__,
								handler)
			self.mainClassHandlers = {}

			for oc, handler in self.otherClassHandlers.items():
				chimera.triggers.deleteHandler(oc.__name__,
								handler)
			self.otherClassHandlers = {}

	def map(self, e=None):
		if not self.handler:
			graphs = selection.currentGraphs()
			subgraphs = selection.currentSubgraphs()
			vertices, edges = selection.currentContents()
			self.updateItems(graphs, subgraphs, vertices, edges)
			self.handler = chimera.triggers.addHandler(self.trigger,
							self.__changed, None)
			self.mainClassHandlers = {}
			for insp in self.inspectionInfo.inspectables:
				self.mainClassHandlers[insp] = \
					chimera.triggers.addHandler(
						insp.__name__,
						self.__monitorItems, None)
			self.otherClassHandlers = {}
			for oc, info in self.otherClasses.items():
				self.otherClassHandlers[oc] = \
					chimera.triggers.addHandler(
					oc.__name__, self.__monitorItems, info)

	def _addInspectable(self, insp):
		from chimera import Inspector
		if insp in self.inspectionInfo.displayAs:
			Inspector.displayClass[insp] = \
					self.inspectionInfo.displayAs[insp]
		options = tkoptions.getOptionsForClass(insp)
		for option in options:
			self.inspector.register(insp, option.attribute,
				option, displayAttr=option.name)
			if not hasattr(option, 'triggerClass'):
				continue
			otherClass = option.triggerClass
			if otherClass in self.inspectionInfo.inspectables:
				continue
			try:
				reason = option.reason
			except AttributeError:
				reason = None
			if not reason:
				self.otherClasses[otherClass] = (None, insp)
				continue
			try:
				prevReasons = self.otherClasses[otherClass][0]
			except KeyError:
				self.otherClasses[otherClass] = ([reason], insp)
				continue
			if not prevReasons:
				continue
			prevReasons.append(reason)

	def __changed(self, trigger, closure, selection):
		# selection is instance of Selection
		graphs = selection.graphs()
		subgraphs = selection.subgraphs()
		vertices, edges = selection.contents()
		self.updateItems(graphs, subgraphs, vertices, edges)

	def __monitorItems(self, trigger, closure, items):
		# deleted items should be removed from selection
		# and cause the __changed trigger to be invoked
		modified = items.modified
		if not modified:
			return
		if closure is not None:
			reasons, mainClass = closure
			if reasons:
				for reason in reasons:
					if reason in items.reasons:
						break
				else:
					return
			if self.inspector.currentClass == mainClass:
				self.inspector.updateCurrentClass()
			return
		for item in modified: break	# get one item to examine
		cclass = self.inspector.currentClass
		if cclass is None or not isinstance(item, cclass):
			return
		sel = set(self.inspector.itemInfo[cclass])
		if sel.intersection(modified) and not sel.intersection(items.deleted):
			# don't call if deletions since that will throw C++
			# error, instead allow __changed to fix things up later
			self.inspector.updateCurrentClass()

	def updateItems(self, graphs, subgraphs, vertices, edges):
		self.inspector.updateItems(
					graphs + subgraphs + vertices + edges)
		labelTxt = "Selected:"
		lines = 1
		altText = {
			selection.SelGraph: ('model', 'models'),
			selection.SelSubgraph: ('subgraph', 'subgraphs'),
			selection.SelVertex: ('vertex', 'vertices'),
			selection.SelEdge: ('edge', 'edges')
		}

		items = {
			selection.SelGraph: graphs,
			selection.SelSubgraph: subgraphs,
			selection.SelVertex: vertices,
			selection.SelEdge: edges
		}
		selLevels = items.keys()
		selLevels.sort()
		for sl in selLevels:
			levelItems = items[sl]
			if not levelItems:
				continue
			total = 0
			for insp in self.inspectionInfo.inspectables:
				if insp.selLevel != sl:
					continue
				num = len(filter(lambda x:
					isinstance(x, insp), levelItems))
				if num == 0:
					continue
				if insp in self.inspectionInfo.displayAs:
					displayName = \
					self.inspectionInfo.displayAs[insp]
				else:
					displayName = insp.__name__
				displayName = displayName.lower()
				if num > 1:
					displayName += "s"
				labelTxt = labelTxt + "\n  %d %s" % (num,
								displayName)
				lines = lines + 1
				total += num
				if total == len(levelItems):
					break

			if total == len(levelItems):
				continue

			remainder = len(levelItems) - total
			if remainder == 1:
				gtxt = altText[sl][0]
			else:
				gtxt = altText[sl][1]
			labelTxt = labelTxt + " [%d other %s]" % (remainder,
									gtxt)
		if lines == 1:
			labelTxt = labelTxt + "\n  Nothing"
			lines = lines + 1
		self.totalsLabel.config(height=lines)
		self.totalsVar.set(labelTxt)

	def WriteList(self):
		from chimera.WriteSelDialog import WriteSelDialog
		from chimera.dialogs import display
		d = display(WriteSelDialog.name)
		d.configure(klass=self.inspector.currentClass, selected=True)

	def WritePDB(self):
		from ModelPanel.writePDBdialog import WritePDBdialog
		from chimera.dialogs import display
		display(WritePDBdialog.name).configure(selOnly=True)

from OpenSave import SaveModeless
class _ReplyDialog(ModelessDialog):
	"""Dialog a log of the info/warning/error messages.

	This dialog is special, it is not displayed the first time,
	so that it can be created early on to catch all error messages.
	"""

	name = 'reply'
	title = 'Reply Log'
	help = 'UsersGuide/reply.html'
	buttons = ('Save', 'Close')

	def __init__(self, master=None, *args, **kw):
		ModelessDialog.__init__(self, master, *args, **kw)
		ModelessDialog.Close(self)	# see comment above

	def fillInUI(self, master):
		f = Tk.Frame(master)
		f.pack(expand=Tk.NO, fill=Tk.X, side=Tk.BOTTOM)
		b = Tk.Button(f, text="Clear", command=self.Clear)
		b.pack(side=Tk.LEFT)
		b = Tk.Button(f, text="Copy", command=self.Copy)
		b.pack(side=Tk.LEFT)
		l = Tk.Label(f, text="  Search:")
		l.pack(side=Tk.LEFT)
		self.copyButton = b
		b = Tk.Button(f, text="Back", command=self.SearchBack,
				state="disabled")
		self.searchBackButton = b
		b.pack(side=Tk.RIGHT)
		b = Tk.Button(f, text="Forward", command=self.SearchForward,
				state="disabled")
		self.searchForwardButton = b
		b.pack(side=Tk.RIGHT)
		e = Tk.Entry(f, width=20)
		e.pack(fill=Tk.X, expand=Tkinter.YES, side=Tk.RIGHT)
		e.bind("<KeyRelease>", self._searchChanged)
		self.searchEntry = e
		self.countVar = Tk.IntVar(master)

		from CGLtk import ScrolledText
		t = ScrolledText.ScrolledText(master, width=40, heigh=8)
		self.text = t
		t.pack(expand=Tk.YES, fill=Tk.BOTH)
		if windowSystem == 'aqua':
			# Can't select text for copying unless text widget has
			# focus.  Aqua doesn't give focus on mouse click to a
			# disabled (not-editable) text widget.  Fix that.
			t.bind('<ButtonPress>', lambda e,t=t: t.focus(),
			       add = True)
		t.bind("<<Selection>>", self._selectionChanged)
		# Force an update to "Copy" button state
		self._selectionChanged(None)

		replyobj.pushReply(replyobj.Reply(self.text))

	def Clear(self):
		self.text.config(state=Tk.NORMAL)
		self.text.delete(1.0, Tk.END)
		self.text.config(state=Tk.DISABLED)

	def _selectionChanged(self, event):
		if self.text.tag_ranges("sel"):
			state = "normal"
		else:
			state = "disabled"
		self.copyButton.config(state=state)

	def _searchChanged(self, event):
		pattern = self.searchEntry.get()
		if pattern:
			self.searchBackButton.config(state="normal")
			self.searchForwardButton.config(state="normal")
		else:
			self.searchBackButton.config(state="disabled")
			self.searchForwardButton.config(state="disabled")

	def Copy(self):
		self.text.tk.call("tk_textCopy", self.text)

	def SearchForward(self):
		tr = self.text.tag_ranges("sel")
		if not tr:
			index = "1.0"
		else:
			index = str(tr[-1])
		pattern = self.searchEntry.get()
		try:
			where = self.text.search(pattern, index, forwards=True,
							count=self.countVar,
							regexp=True, nocase=True)
		except Tk.TclError, e:
			replyobj.error("Search error: %s\n"
					"Probably an error in regular expression.\n"
					% str(e))
		else:
			self._showSearchResults(pattern, where)

	def SearchBack(self):
		tr = self.text.tag_ranges("sel")
		if not tr:
			index = "end"
		else:
			index = str(tr[0])
		pattern = self.searchEntry.get()
		try:
			where = self.text.search(pattern, index, backwards=True,
							count=self.countVar,
							regexp=True, nocase=True)
		except Tk.TclError, e:
			replyobj.error("Search error: %s\n"
					"Probably an error in regular expression.\n"
					% str(e))
		else:
			self._showSearchResults(pattern, where)

	def _showSearchResults(self, pattern, where):
		if not where:
			from chimera.baseDialog import NotifyDialog
			d = NotifyDialog("Search pattern \"%s\" not found"
						% pattern,
						title="Search Error")
			d.run(self.uiMaster())
			return
		self.text.focus_set()
		self.text.tag_remove("sel", "1.0", "end")
		index = str(where)
		count = self.countVar.get()
		self.text.tag_add("sel", index,
					"%s + %d chars" % (index, count))
		self.text.see(index)

	def Save(self):
		SaveModeless(title="Save Reply Messages", command=self.saveFile)

	def saveFile(self, okay, d):
		if not okay:
			return
		fileList = d.getPaths()
		if len(fileList) == 0:
			return
		saveReplyLog(fileList[0])

def saveReplyLog(path):
	"""Save reply log contents to a file"""
	from chimera import dialogs
	r = dialogs.find(_ReplyDialog.name)
	if r:
		text = r.text.get('1.0', 'end')
	else:
		text = ''
	import os.path
	path = os.path.expanduser(path)
	try:
		try:
			text.encode('ascii')
		except UnicodeError:
			import codecs
			f = codecs.open(path, "w", "utf-16")
		else:
			f = open(path, 'w')
		f.write(text)
		f.close()
	except IOError, v:
		from chimera import NonChimeraError
		raise NonChimeraError("Error while saving log file to %s: %s"
							% (path, str(v)))

def clearReplyLog():
	"""Clear reply log"""
	from chimera import dialogs
	r = dialogs.find(_ReplyDialog.name)
	if r:
		r.Clear()

class _SelAtomSpecDialog(ModelessDialog):
	"""Get atom spec to select from user"""

	name = 'Select atom spec'
	title = 'Select Atom Specifier'
	help = 'UsersGuide/midas/atom_spec.html'
	buttons = ('OK', 'Apply', 'Cancel')
	default = 'OK'

	def fillInUI(self, parent):
		self.label = Tk.Label(parent, text="Atom specifier to select:")
		self.label.grid(row=0)
		self.entry = Tk.Entry(parent)
		self.entry.grid(row=1, sticky='ew')
		self.includeBondsVar = Tk.IntVar(parent)
		self.bondsCheckbox = Tk.Checkbutton(parent,
			text="Include bonds", variable=self.includeBondsVar)
		self.includeBondsVar.set(1)
		self.bondsCheckbox.grid(row=2, sticky="w")

	def Apply(self):
		from specifier import evalSpec

		sel = selection.ItemizedSelection()
		try:
			sel.merge(selection.REPLACE, evalSpec(self.entry.get()))
		except SyntaxError:
			self.enter()
			replyobj.warning("Not a valid Chimera atom specifier.\n"
				"Use the previous dialog's Help button for"
				" more info.\n")
		if self.includeBondsVar.get():
			sel.addImplied(vertices=0)
		selectionOperation(sel)

#def LensInspectCB():
#	from chimera import LensInspector
#	global lensInspector
#	lensInspector = LensInspector.LensInspector(app,
#						app.viewer.backgroundLens)
#	dialogs.reregister("Lens Inspector", lambda d=lensInspector: d.show())
#	# now register know lens types
#	from chimera import HighlightLens
#	HighlightLens.register(lensInspector)
#	return lensInspector

class _SelNamePromptDialog(ModelessDialog):
	"""Get selection name to save as from user"""

	name = 'Selection save name'
	title = 'Name Selection'
	help = 'UsersGuide/selection.html#savesel'
	buttons = ('OK', 'Cancel')
	default = 'OK'

	def fillInUI(self, parent):
		label = Tk.Label(parent, text="Name current selection as:")
		label.grid(row=0)
		self.entry = Tk.Entry(parent)
		self.entry.grid(row=1, sticky='ew')
		label = Tk.Label(parent, text="""
(Named selections can be used as command-line
atom specifiers or can be reselected using the
the Rapid Access panel or the Select menu's
"Named Selections" submenu)""")
		label.grid(row=2)

	def enter(self):
		self.entry.focus()
		ModelessDialog.enter(self)

	def Apply(self):
		name = self.entry.get().strip()
		if name:
			selection.saveSel(name)
		else:
			self.enter()
			from chimera import UserError
			raise UserError("No selection name specified")

class _SelSave:
	"""maintains a menu of named selections"""
	def __init__(self, parentMenu, title="Named Selections"):
		self.title = title
		self.parentMenu = parentMenu
		self.menu = Tk.Menu(parentMenu, title=title)
		parentMenu.add_cascade(label=title, menu=self.menu)
		parentMenu.entryconfig(title, state="disabled")
		chimera.triggers.addHandler(selection.SEL_NAMED, self._saveCB, None)
		chimera.triggers.addHandler(selection.DEL_NAMED_SELS, self._saveCB, None)

	def _saveCB(self, trigName, _2, selInfo):
		if trigName == selection.DEL_NAMED_SELS:
			for selName in selInfo:
				# avoid matching 'end' etc. and escape special characters
				menuName = '\\' + "".join(["\\" + c if c in "*?[\\" else c for c in selName])
				self.menu.delete(menuName)
			return
		selName, update = selInfo
		self.parentMenu.entryconfig(self.title, state="normal")
		if not update:
			numSels = len(selection.savedSels)
			newColumn = numSels > 0 and numSels % 20 == 0
			cmd = lambda sn=selName: selectionOperation(
						selection.savedSels[sn])
			self.menu.add_command(label=selName, command=cmd,
									columnbreak=newColumn)

class SoftwareUpdatesDialog(ModelessDialog):
	title = "Check for Updates"
	buttons = ("Download Page", "Close")
	help = False # suppress Help button

	def __init__(self, message):
		self.message = message
		ModelessDialog.__init__(self, oneshot=1)

	def fillInUI(self, parent):
		from chimera import HtmlText
		lines = self.message.count('\n') + 1
		text = HtmlText.HtmlText(parent, relief=Tkinter.FLAT,
				height=lines, highlightthickness=0)
		text.insert(0.0, self.message)
		text.configure(state='disabled')
		text.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(0, weight=1)
		return

	def DownloadPage(self):
		# use help module to centralize error recovery
		dl = "http://www.cgl.ucsf.edu/chimera/download.html"
		help.display(dl)

INITIAL_SIZE = "initial size"
WINDOW_SIZE = "Window size"
inital_size_options = {
	WINDOW_SIZE: [512, 384]		# initial window size
}
preferences.addCategory(INITIAL_SIZE, preferences.HiddenCategory,
						optDict=inital_size_options)
del inital_size_options

UPDATE_CHECK = "update check"
LAST_TIME = "last time"  
update_options = {
	LAST_TIME: 0
}
preferences.addCategory(UPDATE_CHECK, preferences.HiddenCategory,
							optDict=update_options)
del update_options

def periodicCheckForNewerChimera():
	import datetime as DT
	lastTime = preferences.get(UPDATE_CHECK, LAST_TIME)
	utc = DT.datetime.today()
	if lastTime == 0:
		# first time
		daysAgo = interval = 1
	else:
		lastTime = DT.datetime(*lastTime)  # convert back to datetime
		daysAgo = (utc - lastTime).days
		interval = preferences.get(GENERAL, UPDATE_CHECK_INTERVAL)
	if interval and daysAgo >= interval:
		# convert utc to tuple so preferences can read it back in
		lt = (utc.year, utc.month, utc.day, utc.hour, utc.minute,
					utc.second, utc.microsecond, utc.tzinfo)
		preferences.set(UPDATE_CHECK, LAST_TIME, lt)
		try:
			latestVersion(showDialog=False)
		except (SystemExit, chimera.ChimeraSystemExit):
			raise
		except chimera.NotABug:
			from chimera.replyobj import reportException
			reportException()
		except:
			from chimera.replyobj import reportException
			reportException('Error doing periodicCheck')

class PasswordPrompt(ModalDialog):
	title = "Authentication Required"
	buttons = ('OK', 'Cancel')
	default = 'OK'
	text_width = 60

	def __init__(self, realm, uri, master=None, *args, **kw):
		self.realm = realm
		self.uri = uri
		ModalDialog.__init__(self, master, resizable=True, *args, **kw)

	def fillInUI(self, parent):
		text = ( "A user name and password are being "
				"requested by %s.  The site says: '%s'"
				% (self.uri, self.realm) )
		label = Tk.Label(parent, text=text, justify='left', height=3)
		import tkFont
		font = tkFont.Font(root=parent, font=label.cget('font'))
		label.config(wraplength=(self.text_width * font.measure('n')))
		label.grid(row=0, columnspan=2, sticky=Tk.W, padx=2, pady=5)
		self.__label = label
		from chimera.tkoptions import StringOption
		self.__user = StringOption(parent, 1, 'User name', '', None,
							width=16)
		self.__password = StringOption(parent, 2, 'Password', '', None,
							width=16, show='*')

	def Cancel(self):
		ModalDialog.Cancel(self, value=(None, None))

	def OK(self):
		ModalDialog.Cancel(self, value=(self.__user.get(),
						self.__password.get()))

import urllib2
class PasswordManager(urllib2.HTTPPasswordMgrWithDefaultRealm):

	def find_user_password(self, realm, authuri):
		user, passwd = urllib2.HTTPPasswordMgrWithDefaultRealm.find_user_password(self, realm, authuri)
		if user is None and passwd is None:
			user, passwd = PasswordPrompt(realm, authuri).run(app)
			if user or passwd:
				self.add_password(realm, authuri, user, passwd)
		return user, passwd
passwordManager = PasswordManager()

# Add password handlers for urllib2
httpBasicAuthHandler = urllib2.HTTPBasicAuthHandler(passwordManager)
proxyBasicAuthHandler = urllib2.ProxyBasicAuthHandler(passwordManager)
opener = urllib2.build_opener(httpBasicAuthHandler, proxyBasicAuthHandler)
urllib2.install_opener(opener)

# monkey patch urllib.FancyURLopener to fix authentication
# check and to use GUI to get username and password
import urllib
class ChimeraFancyURLopener(urllib.FancyURLopener):
	def http_error_401(self, url, fp, errcode, errmsg, headers, data=None):
		# The standard handler gets confused when there are
		# multiple www-authenticate headers
		import re
		pat = re.compile('[ \t]*([^ \t]+)[ \t]+realm="([^"]*)"')
		for stuff in headers.getheaders('www-authenticate'):
			match = pat.match(stuff)
			if not match:
				continue
			scheme, realm = match.groups()
			if scheme.lower() == 'basic':
				break
		else:
			urllib.URLopener.http_error_default(self, url, fp,
						 errcode, errmsg, headers)
		name = 'retry_' + self.type + '_basic_auth'
		if data is None:
			return getattr(self,name)(url, realm)
		else:
			return getattr(self,name)(url, realm, data)
	def prompt_user_passwd(self, host, realm):
		# The standard handler uses raw_input()
		return passwordManager.find_user_password(realm, host)
urllib._FancyURLopener = urllib.FancyURLopener
urllib.FancyURLopener = ChimeraFancyURLopener

# is this chimera up to date?
def latestVersion(showDialog=True):
	from chimera import tasks
	from chimera import version
	import urllib

	cancelled = []
	def cancel_cb():
		cancelled.append(True)
	task = tasks.Task("Check for newer version of chimera", cancel_cb, modal=True)
	def reportCB(barrived, bsize, fsize):
		if cancelled:
			raise IOError("cancelled at user request")
		if fsize > 0:
			percent = (100.0*barrived*bsize)/fsize
			prog = '%.0f%% of %d bytes' % (percent, fsize)
		else:
			prog = '%.0f Kbytes received' % ((barrived*bsize)/1024,)
		task.updateStatus(prog)
	# duplicate mk/os.make OSARCH logic except for Mac OS X
	# where we ship universal binaries
	import platform
	osarch = platform.system()
	if sys.maxsize > 2 ** 32:
		osarch += "64"
	try:
		url = ("http://www.cgl.ucsf.edu/cgi-bin/chimeraVersion.py"
			"?%s+%s+%s" % (osarch, chimera.opengl_platform(),
							version.release))
		tempFilename, headers = urllib.urlretrieve(url,
							reporthook=reportCB)
	except IOError, v:
		from chimera import NonChimeraError
		raise NonChimeraError("Unable to contact UCSF Computer Graphics"
			" Lab to check for new version."
			" Either the network connection is down"
			" somewhere in between or an HTTP proxy needs"
			" to be configured with the Web Access preference.")
	finally:
		task.finished()
		task = None	# no more task

	if headers.gettype() != 'text/html':
		from chimera import NonChimeraError
		raise NonChimeraError("Invalid response when contacting"
			" UCSF Computer Graphics Lab to check for new version."
			" (Got %s response.)" % headers.gettype())

	info = u"You are currently running chimera %s.\n<p>\n" % version.version
	# look for:
	#  <release-type> <release> "build" <build> <fetch url> [<notes url>]
	hasBuildInfo = False
	production = False
	candidate = False
	snapshot = False
	errorFound = False
	charset = headers.getparam('charset')
	if charset is None:
		charset = 'iso-8859-1'	# HTTP 1.1 default
	import codecs
	tmp = codecs.open(tempFilename, encoding=charset, errors='replace')
	for line in tmp.readlines():
		words = line.split()
		if len(words) > 3 and words[2] == "build":
			if not hasBuildInfo:
				hasBuildInfo = True
				info += "There is a newer version of Chimera available:\n<p>\n"
			if words[0] == 'production':
				production = True
			elif words[0] == 'candidate':
				candidate = True
			elif words[0] == 'snapshot':
				snapshot = True
			info += ("&bull; chimera %s version %s (%s %s)"
							% tuple(words[0:4]))
			if len(words) > 4:
				info += "  <a href='%s'>Download</a>" % words[4]
			if len(words) > 5:
				info += "  <a href='%s'>Release notes</a>" % words[5]
			info += '<br>\n'
		elif not hasBuildInfo:
			errorFound = True
			info += line
	tmp.close()
	try:
		os.remove(tempFilename)
	except OSError:
		pass
	if not hasBuildInfo:
		if not errorFound:
			info += "No newer versions of chimera found.\n"
	else:
		if candidate or snapshot:
			info += ("<p>\nCandidate and snapshot versions receive"
				" less testing than a production version.\n")
	if showDialog or (showDialog == None and hasBuildInfo):
		SoftwareUpdatesDialog(info)
	return production, candidate, snapshot

class LabelWarningDialog(ModelessDialog):
	"""asks for confirmation when many 3D text labels are requested"""

	oneshot = True
	buttons = ('OK', 'Cancel')
	default = 'OK'
	def __init__(self, numLabels, cb, *args, **kw):
		# args are number of labels requested, and callback
		# if the request is okayed
		self.cb = cb
		self.numLabels = numLabels
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		Tkinter.Label(parent, text="You have requested %d labels.\n"
			"Are you sure?" % self.numLabels).grid(row=0, column=0)

	def Apply(self):
		self.cb()

class SurfaceWarningDialog(ModelessDialog):
	"""asks for confirmation when many molecular surfaces are requested"""

	oneshot = True
	buttons = ('OK', 'Cancel')
	default = 'OK'
	def __init__(self, numSurfaces, cb, *args, **kw):
		# args are number of surfaces requested, and callback
		# if the request is okayed
		self.cb = cb
		self.numSurfaces = numSurfaces
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		Tkinter.Label(parent, text="You have requested %d "
			"molecular surfaces.\nAre you sure?"
			% self.numSurfaces).grid(row=0, column=0)

	def Apply(self):
		self.cb()

def _setLastSession(session):
	top = app.winfo_toplevel()
	if session is None:
		fileMenu.entryconfig("Save Session", state='disabled')
		top.title(chimera.title)
		# clear entry field in Save Session dialog to make
		# accidental overwrite less likely
		from SimpleSession.gui import SaveSessionDialog
		dlg = dialogs.find(SaveSessionDialog.name)
		if dlg:
			paths = dlg.getPaths()
			if paths:
				try:
					dlg.setPath(os.path.dirname(paths[0]))
				except IOError:
					# network drive may be gone
					# see ticket #13202
					pass
			dlg.millerBrowser.fileFaves.component(
							'entryfield').clear()
	else:
		fileMenu.entryconfig("Save Session", state='normal')
		try:
			u_session = unicode(session)
		except UnicodeDecodeError:
			u_session = str(session).decode('utf-8', 'replace')
		top.title(u"%s\u2014%s" % (chimera.title,
			os.path.splitext(os.path.basename(u_session))[0]))

def saveSession(fromMenu=False):
	from chimera import UserError
	if fromMenu and chimera.lastSession is None:
		cmdKey = "Command" if windowSystem == "aqua" else "Control"
		raise UserError("No previous session;"
			" use 'Save As' (%s-Shift-S) to save a new session" % cmdKey)
	from SimpleSession.save import saveSession
	from tempfile import mkstemp
	saveDir = os.path.dirname(chimera.lastSession)
	if not os.path.exists(saveDir):
		chimera.setLastSession(None)
		raise UserError("Session directory (%s) no longer exists.\n"
			"Use 'Save Session As' menu item instead." % saveDir)
	saveSession(chimera.lastSession, **chimera.getLastSessionDescriptKw())

def closeSessionCB(*args):
	chimera.setLastSession(None)
	chimera.setLastSessionDescriptKw(None)
	setSelMode('replace')
	cad = dialogs.find(ColorActionDialog.name, create=False)
	if cad:
		cad.Close() # will reset color target
chimera.triggers.addHandler(chimera.CLOSE_SESSION, closeSessionCB, None)

class _TransparencyDialog(ModelessDialog):
	"""Get a typed-in surface transparency from the user"""

	oneshot = True
	title = 'Transparency Percentage'
	buttons = ('OK', 'Apply', 'Cancel')
	default = 'OK'
	help = "UsersGuide/menu.html#othertrans"

	def fillInUI(self, parent):
		self.option = tkoptions.FloatOption(parent, 0,
					"Transparency percentage", 0.0, None,
					min=0.0, max=100.0)
	def Apply(self):
		val = self.option.get()
		from chimera import actions
		actions.transpSurf(val/100.0)

def openDocument(*pathnames):
	from chimera import openModels
	for name in pathnames:
		openModels.open(name)

# _createMenus:
#	Create the menu widget hierarchy so we can use the same hierarchy
# for both the menu bar and the popup menu on the main window.

MENU_TOOLS = "Tools"
MENU_FAVORITES = "Favorites"
_additionalMenus = [
	{'label': MENU_TOOLS, 'underline': 0},
	{'label': MENU_FAVORITES, 'underline': 2}
]
def addMenu(menu=None, **kw):
	insertIndex = app.menubar.index(_additionalMenus[-1]['label']) + 1
	_additionalMenus.append(kw)
	if not menu:
		menu = Tk.Menu(app.menubar, title=kw.pop('title', kw.get('label')))
	app.menubar.insert_cascade(insertIndex, menu=menu, **kw)
	updateAquaMenuBar(app.menubar)
	return menu

def deleteMenu(label):
	global _additionalMenus
	app.menubar.delete(app.menubar.index(label))
	_additionalMenus = [kw for kw in _additionalMenus if kw['label'] != label]
	updateAquaMenuBar(app.menubar)

def _createMenus(parent):
	# TODO: setup ballon help information for all menu buttons
	menu = Tk.Menu(parent, type="menubar", tearoff=False)
	help.register(menu, "UsersGuide/chimerawindow.html")

	if windowSystem == 'aqua':
		parent.tk.createcommand('::tk::mac::ShowPreferences',
					showPreferences)

	global fileMenu
	fileMenu = Tk.Menu(menu, title="File")
	#TODO: fileMenu.winfo_toplevel().config(visual="pseudocolor 4")
	menu.add_cascade(label="File", underline=0, menu=fileMenu)
	#help.register(fileMenu, "UsersGuide/menu.html#menusession")

	global selectMenu
	selectMenu = makeSelectorsMenu(menu, "Select")
	menu.add_cascade(label="Select", underline=0, menu=selectMenu)
	#help.register(selectMenu, "UsersGuide/menu.html#menuselect")

	actionsMenu = Tk.Menu(menu, title="Actions")
	menu.add_cascade(label="Actions", underline=0, menu=actionsMenu)

	presetsMenu = Tk.Menu(menu, title="Presets")
	menu.add_cascade(label="Presets", underline=0, menu=presetsMenu)
	from chimera import preset
	preset.init(presetsMenu)

	#
	# Extension menu contents added by Extension Manager
	#
	for addMenuKw in _additionalMenus:
		menu.add_cascade(**addMenuKw)

	helpMenuName = "Help"
	if windowSystem == 'aqua':
		# Hack so that Aqua Tk 8.5.3 does not add a broken
		# Help/Search menu entry field for SpotLight on Mac OS 10.5.
		helpMenuName = "Help "
	helpMenu = Tk.Menu(menu, title=helpMenuName, name=helpMenuName.lower())
	if windowSystem == 'aqua':
		# tearoff doesn't work
		helpMenu.config(tearoff=False)
	menu.add_cascade(label=helpMenuName, underline=0, menu=helpMenu)
	help.register(helpMenu, "UsersGuide/menu.html#menuhelp")

	# now fill in File menu
	def accKey(menu, cmd, key):
		if windowSystem == 'aqua':
			cmdMod = "Command-"
			if key.isupper():
				bindTo = "Shift-" + key.lower()
				menuSym = "Shift-" + key
			else:
				bindTo = key
				menuSym = key.upper()
		else:
			cmdMod = "Control-"
			bindTo = key
			menuSym = key
		menu.winfo_toplevel().bind_all("<" + cmdMod + bindTo + ">", lambda e, c=cmd: c())
		return cmdMod + menuSym
	cmd = _importModel
	fileMenu.add_command(label="Open...", underline=0,
		command=cmd, accelerator=accKey(fileMenu, cmd, 'o'))
	from chimera import fetch
	fileMenu.add_command(label="Fetch by ID...", underline=0,
		command=fetch.showFetchDialog)
	fileMenu.add_separator()
	def showOpenSessionDialog():
		from SimpleSession.gui import OpenSessionDialog
		dialogs.display(OpenSessionDialog.name)
	fileMenu.add_command(label="Restore Session...", underline=0,
		command=showOpenSessionDialog)
	cmd = lambda: saveSession(fromMenu=True)
	sAcc = accKey(fileMenu, cmd, 's')
	if windowSystem == 'aqua':
		# kludge needed to make menu entry initially grayed out...
		fileMenu.add_command(label="Save Session", underline=0,
			command=cmd, accelerator=sAcc)
		fileMenu.after(100, lambda fm=fileMenu:
			fm.entryconfig("Save Session", state='disabled'))
	else:
		fileMenu.add_command(label="Save Session", underline=0,
			command=cmd, state='disabled', accelerator=sAcc)
	def showSaveSessionDialog():
		from SimpleSession.gui import SaveSessionDialog
		dialogs.display(SaveSessionDialog.name)
	cmd = showSaveSessionDialog
	fileMenu.add_command(label="Save Session As...", underline=13,
		command=cmd, accelerator=accKey(fileMenu, cmd, "S"))
	fileMenu.add_separator()
	fileMenu.add_command(label="Save Image...", underline=5, command=lambda\
			f=dialogs.display, n=printer.ImageSaveDialog.name: f(n))
	def showWritePdbDialog():
		import ModelPanel
		from ModelPanel.writePDBdialog import WritePDBdialog
		dialogs.display(WritePDBdialog.name).configure(
			chimera.openModels.list(modelTypes=[chimera.Molecule]),
			selOnly=False)
	fileMenu.add_command(label="Save PDB...", underline=5,
		command=showWritePdbDialog)
	def showWriteMol2Dialog():
		import WriteMol2
		from WriteMol2.gui import WriteMol2Dialog
		dialogs.display(WriteMol2Dialog.name)
	fileMenu.add_command(label="Save Mol2...", underline=5,
		command=showWriteMol2Dialog)
	fileMenu.add_command(label="Export Scene...", underline=0,
			command=lambda: dialogs.display(exportDialog.name))
	fileMenu.add_command(label="Publish...", underline=0,
			command=lambda: dialogs.display(publishDialog.name))
	fileMenu.add_separator()
	fileMenu.add_command(label="Close Session", underline=0,
		command=chimera.closeSession)
	cmd = showConfirmExitDialog
	if windowSystem == 'aqua':
		# don't add command-q on Aqua since it's redundant and
		# will produce two "confirm quit" dialogs (if you're
		# cancelling them)
		kw = {}
	else:
		kw = {'accelerator': accKey(fileMenu, cmd, 'q')}
	fileMenu.add_command(label="Quit", underline=0, command=cmd, **kw)

	# now fill in Select menu (selectors already present)
	selectMenu.add_separator()
	selectMenu.add_command(label="Sequence...", underline=2,
		command=lambda f=dialogs.display, n=SeqSelDialog.name: f(n))
	selectMenu.add_command(label="Atom Specifier...", underline=0,
		command=lambda f=dialogs.display,
		n=_SelAtomSpecDialog.name: f(n))
	def showAttrDialog():
		import ShowAttr
		dialogs.display(ShowAttr.ShowAttrDialog.name).configure(
								mode="Select")
	selectMenu.add_command(label="By Attribute Value...", underline=13,
		command=showAttrDialog)
	selectMenu.add_command(label="Zone...", underline=0, command=startZone)
	selectMenu.add_separator()
	def _clearSelFunc():
		selection.setCurrent([])
	selectMenu.add_command(label="Clear Selection", underline=0,
		command=_clearSelFunc)
	selectMenu.add_command(label="Invert (all models)", underline=0,
		command=lambda: selection.invertCurrent(allModels=True))
	if tkFlavor == 'cocoa':
		# Arrow key shortcut conflicts with cursor motion.
		selectMenu.add_command(label=u"Invert (selected models) \N{RIGHTWARDS ARROW}",
				       underline=5,
		    command=lambda: selection.invertCurrent(allModels=False))
	else:
		selectMenu.add_command(label="Invert (selected models)",
				       underline=5,
				       accelerator=u'\N{RIGHTWARDS ARROW}',
		    command=lambda: selection.invertCurrent(allModels=False))
	selectMenu.add_command(label="Select All", underline=8, command=lambda
			s=selection: s.setCurrent(chimera.openModels.list(all=True)))
	global selmodesMenu
	selmodesMenu = Tk.Menu(selectMenu, title="Selection Mode")
	for mode in ("append", "intersect", "replace", "subtract"):
		selmodesMenu.add_command(label=mode, underline=0,
				command=lambda m=mode, ssm=setSelMode: ssm(m))
	selmodesMenu.add_separator()
	selmodesMenu.add_command(label="Show mode icon", command=setSelModeIconDisplay)
	global _selModePrefs, _SM_SHOW_ICON
	def initSelModeIcon(prefs=_selModePrefs, key=_SM_SHOW_ICON):
		if prefs[key]:
			from chimera import tkgui
			tkgui.setSelModeIconDisplay(True)
	chimera.registerPostGraphicsFunc(initSelModeIcon)
	selectMenu.add_cascade(label="Selection Mode", underline=0,
							menu=selmodesMenu)
	setSelMode('replace')
	from chimera.selection.upDown import selUp, selDown
	if tkFlavor == 'cocoa':
		# Arrow key shortcut conflicts with cursor motion.
		selectMenu.add_command(label=u"Broaden\t\N{UPWARDS ARROW}",
				       underline=0,
				       command=selUp)
		selectMenu.add_command(label=u"Narrow\t\N{DOWNWARDS ARROW}",
				       underline=0,
				       command=selDown)
	else:
		selectMenu.add_command(label="Broaden", underline=0,
				       accelerator=u'\N{UPWARDS ARROW}',
				       command=selUp)
		selectMenu.add_command(label="Narrow", underline=0,
				       accelerator=u'\N{DOWNWARDS ARROW}',
				       command=selDown)
	global selCache
	selCache = [selection.copyCurrent(), []]
	if tkFlavor == 'cocoa':
		# Arrow key shortcut conflicts with cursor motion.
		undoLabel = u"Undo\t\N{LEFTWARDS ARROW}"
		selectMenu.add_command(label=undoLabel, underline=0,
				       state="disabled",
		  command=lambda s=selection, sc=selCache: s.setCurrent(sc[1]))
	else:
		undoLabel = "Undo"
		selectMenu.add_command(label=undoLabel, underline=0,
				       state="disabled",
				       accelerator=u'\N{LEFTWARDS ARROW}',
		  command=lambda s=selection, sc=selCache: s.setCurrent(sc[1]))

	selectMenu.add_separator()
	selectMenu.add_command(label="Name Selection...", underline=0,
		command=lambda f=dialogs.display, n=_SelNamePromptDialog.name: f(n))
	global _undoHandler
	_undoHandler = None
	def _selChangeCB(trigName, myData, curSel):
		global _undoHandler
		if _undoHandler is not None:
			chimera.triggers.deleteHandler('post-frame',
								_undoHandler)
		selectMenu, selCache = myData
		# need to collate programmatic selection changes...
		def _delaySelChangeCB(tn, md, td, selectMenu=selectMenu,
							selCache=selCache):
			global _undoHandler
			_undoHandler = None
			selectMenu, selCache = md
			selectMenu.entryconfig(undoLabel, state="normal")
			selCache[1] = selCache[0]
			selCache[0] = selection.copyCurrent()
			from chimera.triggerSet import ONESHOT
			return ONESHOT
		_undoHandler = chimera.triggers.addHandler('post-frame',
				_delaySelChangeCB, (selectMenu, selCache))
	chimera.triggers.addHandler('selection changed', _selChangeCB,
							(selectMenu, selCache))
	_SelSave(selectMenu)
	selMgr.addCallback(lambda msm=makeSelectorsMenu, m=menu, s=selectMenu,
		t="Select": msm(m, t, menu=s))

	# now fill in Actions menu
	from chimera import actions
	# display action
	displayMenu = Tk.Menu(actionsMenu, title="Atoms/Bonds")
	displayMenu.add_command(label="show", underline=0,
				command=lambda sd=actions.setDisplay: sd(1))
	displayMenu.add_command(label="show only", underline=5,
				command=actions.showOnly)
	displayMenu.add_command(label="hide", underline=0,
				command=lambda sd=actions.setDisplay: sd(0))
	drp = actions.displayResPart
	backboneMenu = Tk.Menu(displayMenu, title="Backbone Only")
	backboneMenu.add_command(label="chain trace", underline=0,
			command=lambda drp=drp: drp(trace=True))
	backboneMenu.add_command(label="full", underline=0,
			command=lambda drp=drp: drp(backbone=True, other=True))
	backboneMenu.add_command(label="minimal", underline=0,
			command=lambda drp=drp: drp(backbone=True))
	displayMenu.add_cascade(label="backbone only", underline=1,
							menu=backboneMenu)
	sideChainMenu = Tk.Menu(displayMenu, title="Side Chain/Base")
	sideChainMenu.add_command(label="show", underline=0,
			command=lambda drp=drp: drp(side=True, add=True))
	sideChainMenu.add_command(label="show only", underline=6,
			command=lambda drp=drp: drp(side=True))
	displayMenu.add_cascade(label="side chain/base", underline=1,
							menu=sideChainMenu)
	displayMenu.add_separator()
	sabd = actions.setAtomBondDraw
	displayMenu.add_command(label="stick", underline=1, command=lambda
		am=chimera.Atom.EndCap, bm=chimera.Bond.Stick: sabd(am, bm))
	displayMenu.add_command(label="ball & stick", underline=0,
		command=lambda am=chimera.Atom.Ball, bm=chimera.Bond.Stick:
		sabd(am, bm))
	displayMenu.add_command(label="sphere", underline=1, command=lambda
		am=chimera.Atom.Sphere, bm=chimera.Bond.Wire: sabd(am, bm))
	displayMenu.add_command(label="wire", underline=0, command=lambda
		am=chimera.Atom.Dot, bm=chimera.Bond.Wire: sabd(am, bm))
	linewidthMenu = Tk.Menu(displayMenu, title="Wire Width")
	for lw in [1, 1.5, 2, 2.5, 3, 4, 5]:
		linewidthMenu.add_command(label=str(lw),
				command=lambda lw=lw, slw=actions.setLineWidth: slw(lw))
	displayMenu.add_cascade(label="wire width", underline=1,
							menu=linewidthMenu)
	ringMenu = Tk.Menu(displayMenu, title="Rings")
	srf = actions.setRingFill
	ringMenu.add_command(label="fill thick", command=lambda f="thick": srf(f))
	ringMenu.add_command(label="fill thin", command=lambda f="thin": srf(f))
	ringMenu.add_command(label="fill off", command=lambda f=None: srf(f))
	sra = actions.setRingAromatic
	ringMenu.add_command(label="aromatic disk", command=lambda f="disk": sra(f))
	ringMenu.add_command(label="aromatic circle",
							command=lambda f="circle": sra(f))
	ringMenu.add_command(label="aromatic off", command=lambda f=None: sra(f))
	displayMenu.add_cascade(label="rings", underline=0, menu=ringMenu)
	nucleicMenu = Tk.Menu(displayMenu, title="Nucleotide Objects")
	nucleicMenu.add_command(label="off", command=actions.nucleicOff)
	def showNucTool():
		from NucleicAcids.gui import gui
		gui()
	nucleicMenu.add_command(label="settings...", command=showNucTool)
	displayMenu.add_cascade(label="nucleotide objects", underline=0,
							menu=nucleicMenu)
	displayMenu.add_separator()
	displayMenu.add_command(label="delete", command=actions.delAtomsBonds)
	actionsMenu.add_cascade(label="Atoms/Bonds", underline=0, menu=displayMenu)
	# ribbon action
	ribbonMenu = Tk.Menu(actionsMenu, title="Ribbon")
	ribbonMenu.add_command(label="show", underline=0,
			command=lambda sd=actions.setResidueDisplay: sd(1))
	ribbonMenu.add_command(label="hide", underline=0,
			command=lambda sd=actions.setResidueDisplay: sd(0))
	ribbonMenu.add_separator()
	srd = actions.setRibbonDraw
	ribbonMenu.add_command(label='flat', underline=0, command=lambda
				rm=chimera.Residue.Ribbon_2D: srd(rm))
	ribbonMenu.add_command(label='edged', underline=0, command=lambda
				rm=chimera.Residue.Ribbon_Edged: srd(rm))
	ribbonMenu.add_command(label='rounded', underline=0, command=lambda
				rm=chimera.Residue.Ribbon_Round: srd(rm))
	ribbonMenu.add_separator()
	actionsMenu.add_cascade(label="Ribbon", underline=0, menu=ribbonMenu)
	# surface action
	surfaceMenu = Tk.Menu(actionsMenu, title="Surface")
	surfaceMenu.add_command(label="show", underline=0,
				command=actions.showSurface)
	surfaceMenu.add_command(label="hide", underline=0,
				command=actions.hideSurface)
	surfaceMenu.add_separator()
	ssr = actions.setSurfaceRepr
	surfaceMenu.add_command(label="solid", underline=1,
			command=lambda m=chimera.MSMSModel.Filled: ssr(m))
	surfaceMenu.add_command(label="mesh", underline=0,
			command=lambda m=chimera.MSMSModel.Mesh: ssr(m))
	surfaceMenu.add_command(label="dot", underline=0,
			command=lambda m=chimera.MSMSModel.Dot: ssr(m))
	surfaceMenu.add_separator()
	transpMenu = Tk.Menu(surfaceMenu, title="Surface Transparency")
	for t in range(11):
		transpMenu.add_command(label="%d%%" % (10 * t), underline=0,
				command=lambda t=t*0.1: actions.transpSurf(t))
	transpMenu.add_command(label="other...", underline=0,
						command=_TransparencyDialog)
	transpMenu.add_command(label="base color", underline=0,
				command=lambda: actions.transpSurf(-1))
	surfaceMenu.add_cascade(label="transparency", underline=0,
							menu=transpMenu)
	actionsMenu.add_cascade(label="Surface", underline=0, menu=surfaceMenu)

	# color action
	colorsMenu = Tk.Menu(actionsMenu, title="Colors")
	addColorMenuEntries(colorsMenu, standardColors)
	actionsMenu.add_cascade(label="Color", underline=0, menu=colorsMenu)
	colorsMenu.add_separator()
	# color by heteroatom...
	colorsMenu.add_command(label="by heteroatom", underline=3,
				command=lambda: actions.colorByElement(hetero=True))
	# color by element...
	colorsMenu.add_command(label="by element", underline=3, command=lambda:
			actions.colorByElement())
	# color panel...
	fw = FakeWell()
	colorsMenu.add_command(label="from editor", underline=6,
				command=lambda: fw.activate())

	# erase color (color = None)...
	global appliesToVar
	appliesToVar = Tkinter.StringVar(parent)
	appliesToVar.set("all")
	colorsMenu.add_command(label="none", underline=0,
				command=lambda: setColor(None))
	colorsMenu.add_separator()
	# all options...
	colorsMenu.add_command(label="all options...", underline=0,
		command=lambda dn=ColorActionDialog.name: dialogs.display(dn))

	# label action
	labelMenu = Tk.Menu(actionsMenu, title="Label")
	labelMenu.add_command(label="off", underline=0,
					command=lambda sl=actions.setLabel: sl(None))
	# Name
	labelMenu.add_command(label="name", underline=0, command=lambda
		sl=actions.setLabel: sl(lambda a: isinstance(a, chimera.Atom)
		and a.oslIdent(chimera.SelAtom)[1:] or ""))
	# Element
	labelMenu.add_command(label="element", underline=0,
				command=lambda sl=actions.setLabel: sl("element.name"))
	# IDATM type
	labelMenu.add_command(label="IDATM type", underline=0,
				command=lambda sl=actions.setLabel: sl("idatmType"))
	# Custom...
	class otherLabelDialog(ModelessDialog):
		title = "Label 'Other'"
		buttons = ('Cancel', 'OK')
		default = 'OK'
		help = "UsersGuide/menu.html#actlabother"
		oneshot = True

		def __init__(self):

			ModelessDialog.__init__(self)

		def fillInUI(self, parent):
			flab = Tk.Label(parent, text="Label with fixed string:")
			flab.grid(row=0, column=0, sticky="e")
			self._entry = Tk.Entry(parent)
			self._entry.grid(row=0, column=1, sticky='ew')
			parent.columnconfigure(1, weight=1)

			seenAttrs = {
				'name':1, 'idatmType':1, 'idatmIsExplicit':1,
				'display':1, 'drawMode':1, 'hide':1, 'label':1,
				'surfaceDisplay':1, 'vdw':1, 'coordIndex': 1,
				'selLevel': 1, 'surfaceOpacity': 1,
			}
			useableAttrs = []
			useableTypes = (basestring, float, int)
			from types import ClassType
			from chimera import actions
			for a in actions.selAtoms():
				for attrName in dir(a):
					if seenAttrs.has_key(attrName):
						continue
					seenAttrs[attrName] = 1
					if attrName[0] == '_' \
					or attrName[0].isupper(): # e.g. 'Ball'
						continue
					attr = getattr(a, attrName)
					if isinstance(attr, useableTypes) \
					or (isinstance(attr, ClassType)
					and hasattr(attr, '__str__')):
						useableAttrs.append(attrName)
			useableAttrs.sort(lambda a, b:
						cmp(a.lower(), b.lower()))
			if len(useableAttrs) == 0:
				return
			flab = Tk.Label(parent, text="Label with attribute:")
			flab.grid(row=1, column=0, sticky="e")

			self._attrVar = Tk.StringVar(parent)
			self._attrVar.set(useableAttrs[0])
			mb = Tk.Menubutton(parent, textvariable=self._attrVar,
								relief='raised')
			mb.grid(row=1, column=1, sticky='w')
			menu = Tk.Menu(mb, tearoff=False)
			mb["menu"] = menu
			for attr in useableAttrs:
				menu.add_command(label=attr, command=lambda
					a=attr, v=self._attrVar: v.set(a))

		def Apply(self):
			from chimera.actions import setLabel
			if self._entry.get():
				setLabel(self._entry.get(), fixed=1)
			elif hasattr(self, '_attrVar'):
				setLabel(self._attrVar.get())

	labelMenu.add_command(label="other...", underline=1,
			      command=otherLabelDialog)
	# Residues ->
	residueMenu = Tk.Menu(labelMenu, title="Residue Label")
	# class to minimize attribute access of labeled residue...
	residueMenu.add_command(label="off", underline=0,
		command=lambda: actions.setResLabel(""))
	residueMenu.add_command(label="name", underline=2,
		command=lambda: actions.setResLabel("%(name)s"))
	residueMenu.add_command(label="1-letter code", underline=0,
		command=lambda: actions.setResLabel("%(1-letter code)s"))
	residueMenu.add_command(label="specifier", underline=3,
		command=lambda: actions.setResLabel("%(specifier)s"))
	residueMenu.add_command(label="name + specifier", underline=0,
		command=lambda: actions.setResLabel("%(name)s %(specifier)s"))
	residueMenu.add_command(label="1-letter code + specifier", underline=2,
		command=lambda: actions.setResLabel("%(1-letter code)s %(specifier)s"))
	# custom...
	class CustomResLabel(ModelessDialog):
		title = "Custom Residue Label"
		buttons = ('OK', 'Apply', 'Close')
		default = 'OK'
		help = "UsersGuide/customlabel.html"
		oneshot = True

		def fillInUI(self, parent):
			self.prefLastLab = "last"
			self.prefs = preferences.addCategory("custom res label",
				preferences.HiddenCategory, optDict=
				{ self.prefLastLab: "%(name)s %(number)s" })
			self.entry = Pmw.EntryField(parent, labelpos='w',
				label_text="Residue label", value=
				self.prefs[self.prefLastLab])
			self.entry.grid(row=0, column=0, sticky='ew',
								columnspan=2)
			self.entry.component('entry').focus_set()
			self.entry.selection_range(0, 'end')
			self.entry.icursor(0)
			parent.columnconfigure(0, weight=1)
			buttons = ["name", "1-letter code", "specifier",
					"number", "insertion code", "chain"]
			Tkinter.Label(parent, text="Insert substitution\n"
				"code for:").grid(row=1, column=0, sticky='e',
				rowspan=len(buttons))
			for i, subst in enumerate(buttons):
				Tkinter.Button(parent, text=subst, command=
					lambda subcode="%%(%s)s" % subst:
					self.buttonInsert(subcode)).grid(
					row=i+1, column=1, sticky='ew')

		def buttonInsert(self, text):
			if self.entry.selection_present():
				self.entry.delete("sel.first", "sel.last")
			self.entry.insert("insert", text)
			self.entry.component('entry').focus_set()

		def Apply(self):
			self.entry.invoke()
			labelFmt = self.entry.get()
			self.prefs[self.prefLastLab] = labelFmt
			actions.setResLabel(labelFmt)

	residueMenu.add_command(label="custom...", underline=0,
						command=CustomResLabel)

	labelMenu.add_cascade(label="residue", underline=0, menu=residueMenu)
	labelMenu.add_separator()
	labelMenu.add_command(label="options...", underline=0,
						command=showLabelPrefs)
	actionsMenu.add_cascade(label="Label", underline=0, menu=labelMenu)
	# focus action
	actionsMenu.add_command(label="Focus", underline=0,
				command=actions.focus)
	# set-pivot action
	actionsMenu.add_command(label="Set Pivot", underline=6,
						command=actions.setPivot)

	# selection inspector...
	actionsMenu.add_separator()
	actionsMenu.add_command(label="Inspect", underline=0,
		command=lambda f=dialogs.display, n=_InspectDialog.name: f(n))

	# write selection...
	def showWriteSelDialog():
		from chimera.WriteSelDialog import WriteSelDialog
		d = dialogs.display(WriteSelDialog.name)
		d.configure(klass=chimera.Atom, selected=True)
	actionsMenu.add_command(label="Write List...", underline=0,
						command=showWriteSelDialog)

	# write PDB...
	def showWritePDBdialog():
		from ModelPanel.writePDBdialog import WritePDBdialog
		dialogs.display(WritePDBdialog.name).configure(selOnly=True)
	actionsMenu.add_command(label="Write PDB...", underline=6,
						command=showWritePDBdialog)

	# now fill in Help menu
	def showSearchDialog():
		from chimera import SearchDocs
		chimera.dialogs.display(SearchDocs.SearchDialog.name)
	helpMenu.add_command(label="Search Documentation...",
		command = showSearchDialog, underline=0)
	helpMenu.add_command(label="User's Guide", underline=7,
		command=lambda f=help.display: f("UsersGuide/index.html"))
	helpMenu.add_command(label="Commands Index", underline=9,
		command=lambda f=help.display: f("UsersGuide/framecommand.html"))
	helpMenu.add_command(label="Tutorials", underline=0,
		command=lambda f=help.display: f("UsersGuide/frametut.html"))
	if sys.platform != 'darwin':
		helpMenu.add_command(label="Context Help", underline=0,
				     command=lambda a=parent: help.contextCB(a))
	helpMenu.add_separator()
	helpMenu.add_command(label="Check for Updates", underline=10,
		command=latestVersion)
	helpMenu.add_command(label="Contact Us", underline=2,
		command=lambda f=help.display: f("feedback.html"))

	def showBugReportDialog():
		import BugReport
		brd = BugReport.displayDialog()
		if brd:
			brd.setBugReport(BugReport.BugReport())

	helpMenu.add_command(label="Report a Bug...", underline=0,
			     command=showBugReportDialog)
	helpMenu.add_command(label="Citation Info", underline=9,
		command=lambda f=help.display: f("credits.html"))
	def showRegDialog():
		from chimera import register
		dialogs.display(register.RegDialog.name)
	helpMenu.add_command(label="Registration...", underline=0,
						command=showRegDialog)
	helpMenu.add_command(label="About " + chimera.title, underline=0,
			     command=showAboutDialog)

	# TODO: add cursor mode buttons to menu bar
	return menu

def setColor(color):
	global appliesToVar
	from chimera import actions
	actions.setColor(color, appliesToVar=appliesToVar)

def contrasting(rgb):
	if tkFlavor == 'cocoa':
		return "black"
	if 2 *rgb[0] + 3 * rgb[1] + rgb[2] < 638:
		return "white"
	return "black"

class FakeWell:
	def __init__(self):
		self._active = False
		self._selTriggerID = None
		self.noneOkay = True
	def activate(self, exclusive=True, notifyPanel=True):
		if not self._active:
			from CGLtk.color.ColorWell import colorPanel
			if notifyPanel:
				# need to have an "rgba" attribute
				# equal to what is currently in the
				# editor, else the editor will set
				# itself to black...
				self.rgba = colorPanel().rgba
				colorPanel().register(self,
						exclusive=exclusive)
				delattr(self, "rgba")
			colorPanel().show()
			self._active = True
			self.showColor(color=colorPanel().rgba,
						notifyPanel=False)
	def deactivate(self, notifyPanel=True):
		if self._active:
			from CGLtk.color.ColorWell import colorPanel
			if notifyPanel:
				colorPanel().deregister(self,
						notifyWell=False)
			self._active = False
	def showColor(self, color=None, multiple=False,
			notifyPanel=True, doCallback=True):
		if multiple or not doCallback:
			return
		if color == None:
			setColor(None)
		else:
			setColor(chimera.MaterialColor(*color))

standardColors = ["red", "orange red", "orange", "yellow",
	"green", "forest green", "cyan", "light sea green", "blue",
	"cornflower blue", "medium blue", "purple", "hot pink",
	"magenta", "white", "light gray", "gray", "dark gray",
	"dim gray", "black"]

class ColorActionDialog(ModelessDialog):
	title = "Color Actions"
	name = "color action dialog"
	buttons = ('Close',)
	help = 'UsersGuide/coloractions.html'

	def fillInUI(self, parent):
		from colorTable import colors
		top = parent.winfo_toplevel()
		menuBar = Tkinter.Menu(top, type="menubar", tearoff=False)
		top.config(menu=menuBar)
		toolsMenu = Tkinter.Menu(menuBar)
		for toolName in ['Rainbow', 'Color Secondary Structure',
				'Render by Attribute', "Coulombic Surface Coloring",
				"Surface Color", "Color Zone"]:
			from chimera import runCommand
			toolsMenu.add_command(label=toolName, command=lambda tn=toolName:
				runCommand("start %s" % tn))
		menuBar.add_cascade(label="Tools", menu=toolsMenu)
		aquaMenuBar(menuBar, parent, row=0, columnspan=3)

		scFrame = Tkinter.Frame(parent)
		scFrame.grid(row=1, column=0, rowspan=3)
		if windowSystem == 'aqua':
			baseKw = {}
		else:
			baseKw = { 'padx': 0, 'pady': 0 }
		self._layoutColors(scFrame, standardColors, len(standardColors), baseKw)

		radioFrame = Tkinter.Frame(parent)
		radioFrame.grid(row=1, column=1)
		subFrames = {"background": None, "depth cue": None}
		Tkinter.Label(radioFrame, text="Coloring\napplies to:").grid(row=0)
		for i, butInfo in enumerate([ ("atoms/bonds", "atoms/bonds"),
				("ribbons", "ribbons"), ("surfaces", "surfaces"),
				("atom labels", "atom labels"), ("bond labels", "bond labels"),
				("residue labels", "residue labels"),
				("all of the above", "all"),
				("ribbon helix interior", "ribbon inside"),
				("background", "bg"), ("depth cue", "dc") ]):
			butLabel, butVal = butInfo
			gridArgs = {"row": i+1, "sticky": 'w'}
			if butInfo[0] in subFrames:
				master = Tkinter.Frame(radioFrame)
				master.grid(**gridArgs)
				gridArgs = {"row": 0, "column": 0}
				subFrames[butInfo[0]] = master
			else:
				master = radioFrame
			Tkinter.Radiobutton(master, variable=appliesToVar, pady=0,
				text=butLabel, value=butVal).grid(**gridArgs)
		Tkinter.Button(subFrames["background"], text="more...",
			command=showBGPrefs).grid(row=0, column=1)

		def showEffectsTab():
			from extension.StdTools import raiseViewingTab
			raiseViewingTab("Effects")
		Tkinter.Button(subFrames["depth cue"], text="more...",
			command=showEffectsTab).grid(row=0, column=1)

		ocFrame = Tkinter.Frame(parent)
		ocFrame.grid(row=2, column=1)
		Tkinter.Label(ocFrame, text="Other colorings:").grid(row=0, column=0)
		kw = {'bd': 1}
		kw.update(baseKw)
		from chimera.actions import colorByElement
		Tkinter.Button(ocFrame, relief="solid", text="by heteroatom",
			command=lambda: colorByElement(appliesToVar=appliesToVar,
			hetero=True), **kw).grid(row=1, column=0, sticky='ew')
		Tkinter.Button(ocFrame, relief="solid", text="by element",
			command=lambda: colorByElement(appliesToVar=appliesToVar),
			**kw).grid(row=2, column=0, sticky='ew')
		fw = FakeWell()
		Tkinter.Button(ocFrame, relief="solid", text="from editor",
			command=lambda: fw.activate(), **kw).grid(
			row=3, column=0, sticky='ew')
		Tkinter.Button(ocFrame, relief="solid", text="none",
			command=lambda: setColor(None), **kw
			).grid(row=4, column=0, sticky='ew')

		self.allColorsFrame = Tkinter.Frame(parent)
		colorNames = [c for c in colors.keys() if "grey" not in c]
		colorNames.sort()
		self._layoutColors(self.allColorsFrame, colorNames, len(standardColors),
							baseKw)
		kw = baseKw
		self.showAllVar = Tkinter.IntVar(parent)
		self.showAllVar.set(False)
		Tkinter.Checkbutton(parent, variable=self.showAllVar,
			text=u"Show all colors\u2192", command=self._showAllCB, **kw
			).grid(row=3, column=1, sticky='se')

	def Close(self):
		if appliesToVar.get() != "all":
			replyobj.status("Reverting coloring menu target to 'all the above'")
			appliesToVar.set("all")
		ModelessDialog.Close(self)

	def _layoutColors(self, frame, layoutColors, columnLength, baseKw):
		from chimera.colorTable import colors, getColorByName
		frame.keep_images = images = [] # prevent images from being destroyed
		for i, colorName in enumerate(layoutColors):
			rgb = colors[colorName]
			tkColor = "#%02x%02x%02x" % rgb
			if colorName == "red":
				textColor="black"
			else:
				textColor = contrasting(rgb)
			#if False:
			if windowSystem == 'aqua':
				p = Tk.PhotoImage(width = 16, height = 16)
				p.put(tkColor, to=(0,0,15,15))
				kw = {'image': p, 'compound': 'left', 'anchor': 'w',
						'padx': 0, 'pady': 0}
				kw.update(baseKw)
				images.append(p)
			else:
				kw = baseKw
			b = Tkinter.Button(frame, bg=tkColor, fg=textColor, relief="flat",
				activebackground=tkColor, activeforeground=textColor,
				command=lambda cn=colorName: setColor(getColorByName(cn)),
				text=colorName, **kw)
			row = i % columnLength
			col = int(i / columnLength)
			b.grid(row=row, column=col, sticky='ew')

	def _showAllCB(self):
		if self.showAllVar.get():
			self.allColorsFrame.grid(row=1, column=2, rowspan=3)
		else:
			self.allColorsFrame.grid_forget()

def addColorMenuEntries(menu, colorNames, rows=None):
	images = []
	from chimera.colorTable import colors, getColorByName
	for i, colorName in enumerate(colorNames):
		rgb = colors[colorName]
		tkColor = "#%02x%02x%02x" % rgb
		if colorName == "red":
			textColor="black"
		else:
			textColor = contrasting(rgb)
		if tkFlavor == 'cocoa':
			p = Tk.PhotoImage(width = 16, height = 16)
			p.put(tkColor, to=(0,0,15,15))
			images.append(p)
			kw = {'image':p, 'compound': 'left'}
		else:
			kw = {}
		if rows:
			kw['columnbreak'] = ((i % rows) == rows-1)
		menu.add_command(label=colorName,
			activebackground=tkColor, background=tkColor,
			activeforeground=textColor, foreground=textColor,
			command=lambda cn=colorName: setColor(getColorByName(cn)), **kw)
	menu.keep_images = images	# Prevent images from being destroyed

def aquaMenuBar(menubar, parent, row = None, columnspan = 1, pack = None):
	if windowSystem == 'aqua':
		aboutMenuEntry(menubar)
		from CGLtk.AquaTkFixes import WindowMenuBar
		m = WindowMenuBar(menubar, parent, row, columnspan, pack)
		menubar.aqua_menu = m
		try:
			show = preferences.get(GENERAL, AQUA_MENUS)
		except:
			show = True
		if not show:
			m.show(False)
		if row is not None:
			return row+1
	if row is not None:
		return row

def aquaMenuBars():
	from Tkinter import Toplevel
	tl = [t for t in app.winfo_children() if isinstance(t, Toplevel)]
	ml = [t.cget('menu') for t in tl]
	ml = [app.nametowidget(m) for m in ml if m]
	aml = [m.aqua_menu for m in ml if hasattr(m, 'aqua_menu')]
	aml.append(app.menubar.aqua_menu)
	return aml

def showAquaMenus(show):
	if not app:
		return
	for m in aquaMenuBars():
		m.show(show)

def updateAquaMenuBar(menubar):
	if hasattr(menubar, 'aqua_menu'):
		menubar.aqua_menu.update_menus()

def aboutMenuEntry(menu):
	chimeraMenu = Tk.Menu(menu, name='apple', tearoff=False)
	menu.insert_cascade(0, label='Chimera', menu=chimeraMenu)
	chimeraMenu.add_command(label='About %s...' % chimera.title,
				command=showAboutDialog)

def showAboutDialog():
	dialogs.display(_OnVersionDialog.name)

def showPreferences():
	dialogs.display("preferences")

def showBGPrefs():
	import dialogs
	d = dialogs.display("preferences")
	from bgprefs import BACKGROUND
	d.setCategoryMenu(BACKGROUND)

def showLabelPrefs():
	import dialogs
	d = dialogs.display("preferences")
	from initprefs import PREF_LABEL
	d.setCategoryMenu(PREF_LABEL)

def showConfirmExitDialog():
	dialogs.display("Confirm Exit")

def startZone():
	from chimera import ZoneDialog
	d = dialogs.display(ZoneDialog.ZoneDialog.name)
	d.callback = finishZone

def finishZone(zd):
	from chimera.specifier import zone, ATOM, RESIDUE
	resOrAtom =  zd.doResidues.get() and RESIDUE or ATOM
	if zd.doFurther.get():
		further = float(zd.furtherEntry.get())
	else:
		further = None
	if zd.doCloser.get():
		closer = float(zd.closerEntry.get())
	else:
		closer = None
	if selMode in ["intersect", "subtract"]:
		models = selection.currentMolecules()
	else:
		models = chimera.openModels.list()
	sel = zone(selection.copyCurrent(), resOrAtom,
					further, closer, models)
	sel.addImplied(vertices=0)
	selectionOperation(sel)

def setSelMode(mode):
	global selMode
	selMode = mode

	selectMenu.entryconfig("Selection Mode*",
					label="Selection Mode (%s)" % mode)
	if _sm_icon:
		_sm_icon.configure(image=_sm_images[mode])

def selectionOperation(sel):
	# change currect selection according to selection mode
	if selMode == 'replace':
		selection.setCurrent(sel)
		return
	if not isinstance(sel, selection.Selection):
		isel = selection.ItemizedSelection()
		isel.add(sel)
		isel.addImplied()
		sel = isel
	if selMode == 'append':
		selection.mergeCurrent(selection.EXTEND, sel)
	elif selMode == 'intersect':
		selection.mergeCurrent(selection.INTERSECT, sel)
	elif selMode == 'subtract':
		selection.mergeCurrent(selection.REMOVE, sel)

_SM_SHOW_ICON = "show icon"
_selModePrefs = preferences.addCategory("sel modes",
	preferences.HiddenCategory, optDict={ _SM_SHOW_ICON: False })
_sm_images = {}
_sm_icon = None
def setSelModeIconDisplay(display="toggle"):
	global _sm_icon, _sm_images
	if display == "toggle":
		display = not _selModePrefs[_SM_SHOW_ICON]
	_selModePrefs[_SM_SHOW_ICON] = display
	if _selModePrefs[_SM_SHOW_ICON]:
		selmodesMenu.entryconfig("* icon", label="Hide mode icon")
		if _sm_icon:
			_sm_icon.grid()
		else:
			from statusline import status_line, button_opts, grid_opts
			sl = status_line(create=True)
			from extension.TextIcon import TextIcon
			for mode in ("append", "intersect", "replace", "subtract"):
				_sm_images[mode] = TextIcon(sl.frame, mode[0].upper(),
					imageSize=(16, 16), bg=(107, 142, 35))
			_sm_icon = Tkinter.Button(sl.frame, image=_sm_images[selMode],
				command=_nextSelMode, **button_opts)
			_sm_icon.grid(row=0, column=sl.SELMODE_COLUMN, **grid_opts)
	else:
		selmodesMenu.entryconfig("* icon", label="Show mode icon")
		_sm_icon.grid_remove()

def _nextSelMode():
	selModes = ["append", "intersect", "replace", "subtract"]
	nextModeIndex = selModes.index(selMode) + 1
	if nextModeIndex >= len(selModes):
		nextModeIndex = 0
	setSelMode(selModes[nextModeIndex])

_prevSelectors = {}
def makeSelectorsMenu(parent, title,
				selectors=None, prevSelectors=None, menu=None):
	# create a menu hierarchy for choosing available selectors

	if selectors is None:
		if not menu:
			# first time menu hierarchy's created
			menu = Tkinter.Menu(parent, title=title)
			menu.menuBalloon = MenuBalloon(menu)
			registerMenuBalloon(menu.menuBalloon)
		else:
			menu.menuBalloon.clear()
		selectors = selMgr.selectorDict()

	if prevSelectors == None:
		global _prevSelectors
		prevSelectors = _prevSelectors
		_prevSelectors = selectors

	if not menu:
		menu = Tkinter.Menu(parent, title=title)

	# We have two competing constraints here.  We want to avoid deleting
	# menus if possible since corresponding tearoffs will disappear.
	# On the other hand, clearing and rebuilding menus results in
	# a memory leak since Tkinter won't dispose of callbacks until
	# a menu is destroyed.
	#
	# Our strategy therefore is to remember the previous set of selectors
	# that we built from and make as few changes as possible to the
	# menus.  Nonetheless, we will delete empty menus to reclaim memory
	# despite the tearoff issue.

	# Tk seems to use a slightly-differently-named clone widget for
	# menus that are moved in and out of the menubar hierarchy, so
	# avoid deleting menus and reattaching them; instead delete
	# non-submenu entries and non-retained submenus
	def _sortFunc(a, b):
		aname, aval = a
		bname, bval = b
		if isinstance(aval[1], tuple):
			agrouping = aval[1][1]
		else:
			agrouping = 0
		if isinstance(bval[1], tuple):
			bgrouping = bval[1][1]
		else:
			bgrouping = 0
		return cmp(agrouping, bgrouping) or cmp(
						aname.lower(), bname.lower())
	sortedItems = selectors.items()
	sortedItems.sort(_sortFunc)
	sortedKeys = [(i[0], isinstance(i[1][1], tuple) and i[1][1][1] or 0)
							for i in sortedItems]
	prevItems = prevSelectors.items()
	prevItems.sort(_sortFunc)
	prevKeys = [(i[0], isinstance(i[1][1], tuple) and i[1][1][1] or 0)
							for i in prevItems]
	if menu.cget('tearoff'):
		menuPos = 1 # tearoff
	else:
		menuPos = 0 # no tearoff
	spos = ppos = 0
	sgrouping = pgrouping = None
	while spos < len(sortedKeys) or ppos < len(prevKeys):
		# start at 1 because of tearoff
		actions = []
		try:
			skey, sgroup = sortedKeys[spos]
			sregistrant, sval = selectors[skey]
		except IndexError:
			sgroup = sgrouping
			actions = ["delete"]
		try:
			pkey, pgroup = prevKeys[ppos]
			pregistrant, pval = prevSelectors[pkey]
		except IndexError:
			pgroup = pgrouping
			actions = ["insert"]

		if not actions:
			keyCmp = cmp(pkey.lower(), skey.lower())
			if keyCmp < 0:
				actions = ["delete"]
			elif keyCmp == 0:
				if type(sval) == type(pval):
					if isinstance(sval, dict):
						if pval and not sval:
							# delete newly empty
							# menus
							actions = ["delete",
								"insert"]
						else:
							subMenu = menu.\
								nametowidget(
								menu.entrycget(
								menuPos,'menu'))
							makeSelectorsMenu(menu,
								skey,
								selectors=sval,
								prevSelectors=
								pval,
								menu=subMenu)
					elif sval != pval:
						actions = ["delete", "insert"]
					# otherwise, leave alone
				else:
					actions = ["delete", "insert"]
			else:
				actions = ["insert"]

		if pgrouping != None and pgroup != pgrouping:
			# delete separator
			menu.delete(menuPos)
		if sgrouping != None and sgroup != sgrouping:
			# add separator
			menu.insert_separator(menuPos)
			menuPos += 1
		for action in actions:
			if action == "delete":
				subMenu = None
				if isinstance(pval, dict):
					# submenu
					subMenu = menu.nametowidget(
						menu.entrycget(menuPos, 'menu'))
				menu.delete(menuPos)
				if subMenu:
					subMenu.destroy()
				ppos += 1
			else:
				# insert
				if isinstance(sval, dict):
					menu.insert_cascade(menuPos, label=skey,
						menu=makeSelectorsMenu(menu,
						skey, selectors=sval,
						prevSelectors={}))
				else:
					menu.insert_command(menuPos, label=skey,
						command=lambda
						f1=selectionOperation,
						f2=selMgr.selectionFromText,
						t=sval[0]: f1(f2(t)))
				spos += 1
				menuPos += 1
		if not actions:
			spos += 1
			ppos += 1
			menuPos += 1
		sgrouping = sgroup
		pgrouping = pgroup
	if hasattr(menu, 'menuBalloon'):
		selMgr.registerSelectorBalloons(menu.menuBalloon)
	return menu

_menuBalloons = []
def registerMenuBalloon(balloon):
	if app and not app.showBalloons:
		balloon.configure(state='none')
	_menuBalloons.append(balloon)

def releaseMenuBalloon(balloon):
	_menuBalloons.remove(balloon)

_outlineLayouts = []
def registerOutlineLayout(ol):
	if app and not app.showBalloons:
		ol.setAllowBalloons(0)
	_outlineLayouts.append(ol)

def releaseOutlineLayout(ol):
	_outlineLayouts.remove(ol)

_screenMMWidth = 0

def getScreenMMWidth():
	return float(_screenMMWidth)

def setScreenMMWidth(mmwidth):
	global _screenMMWidth
	if mmwidth == 0 and app:
		mmwidth = app.winfo_screenmmwidth()
		if mmwidth == 0:
			mmwidth = app.winfo_screenmmwidth()
			if mmwidth == 0:
				mmwidth = float(app.winfo_screenwidth()) / 86 * 25.4
	if _screenMMWidth == mmwidth:
		return
	_screenMMWidth = mmwidth
	if app:
		event = Tk.Event()
		event.widget = app.graphics
		event.width = app.winfo_width()
		event.height = app.winfo_height()
		app._trackGraphicsWindowSize(event)

def usingDefaultScreenWidth():
	if app is None:
		return True
	dwidth = app.winfo_screenmmwidth()
	if dwidth == 0:
		dwidth = float(app.winfo_screenwidth()) / 86 * 25.4
	global _screenMMWidth
	return (_screenMMWidth == dwidth)

class Application(Tk.Frame):

	_infoTimer = None
	_saveSize = ()

	def __init__(self, master=None, embed=False, **kw):
		self.embedded = embed
		Tk.Frame.__init__(self, master, **kw)
		global _screenMMWidth
		_screenMMWidth = master.winfo_screenmmwidth()
		if _screenMMWidth == 0:
			_screenMMWidth = master.winfo_screenwidth() / 86 * 25.4
		# let caller pack/grid/place as it wishes
		from replyobj import REPLY_PREFERENCES, BALLOON_HELP
		replyobj.registerPreferences()
		self.showBalloons = preferences.get(REPLY_PREFERENCES, BALLOON_HELP)
		from initprefs import PREF_LABEL, ATOMSPEC_BALLOON
		self.atomspecBalloon = preferences.get(PREF_LABEL, ATOMSPEC_BALLOON)
		self.balloon = help.makeBalloonWidget(master)
		replyobj.status('creating menus')
		self.menubar = _createMenus(self)
		aquaMenuBar(self.menubar, self, pack = True)
		replyobj.status('creating toolbar')
		self.toolPane = Tk.Frame(self)
		self.toolPane.pack(expand=Tk.YES, fill=Tk.BOTH)
		help.register(self.toolPane, "UsersGuide/chimerawindow.html")
		self.toolbar = toolbar.Toolbar(self.toolPane)
		self.toolbar.pack(anchor=Tk.NW, side=Tk.TOP, expand=Tk.YES, fill=Tk.BOTH)
		replyobj.status('creating viewer')
		self.viewer = chimera.LensViewer()
		chimera.openModels.viewer = self.viewer
		replyobj.status('initializing OpenGL')
		# graphics gets attached to viewer by C/C++ init function
		self.atomspecBalloon = False
		self._fullscreen = None		# fullscreen Toplevel widget
		self.graphics = None
		self.fullscreen_graphics = False
		self.rapidAccess = None
		try:
			self.makeGraphicsWindow()
		except RuntimeError, what:
			raise chimera.ChimeraExit, what

		self.bind('<KeyPress>', self._keypress)
		if windowSystem == 'aqua':
			# Make Command-` and Command-~ circulate the window
			# focus forwards and backwards.
			self.bind('<Command-KeyPress-`>', lambda e: 0)
			self.bind('<Command-KeyPress-~>', lambda e: 0)
			self.bind_all('<Command-KeyPress-`>',
				      lambda e: _circulateFocus())
			self.bind_all('<Command-KeyPress-~>',
				      lambda e: _circulateFocus(backward=True))
		self.bind('<MouseWheel>', self._mousewheel)
		# mouse bindings are done later
		self.labelBalloon = None
		self.viewer.inhibitLabelBalloon = False

		if windowSystem == 'aqua':
			self.tk.createcommand('::tk::mac::Quit',
					      showConfirmExitDialog)

	def _trackGraphicsWindowSize(self, event):
		if chimera.fullscreen:
			return
		w = app.toolbar.work	# graphics or rapid access
		if not w:
			return
		width = w.winfo_width()
		height = w.winfo_height()
		if width == 1 and height == 1:
			return
		res = getScreenMMWidth() / w.winfo_screenwidth()
		mmwidth = res * width
		mmheight = res * height
		ps = self.viewer.pixelScale
		chimera.triggers.activateTrigger('graphics window size',
				(ps * width, ps * height, mmwidth, mmheight))
		v = self.viewer
		v.camera.windowWidth = mmwidth
		if not preferences.get(GENERAL, INITIAL_WINDOW_SIZE):
			preferences.set(INITIAL_SIZE, WINDOW_SIZE,
					(width, height))
		# now check to see graphics is resizeable
		info = w.grid_info()
		if info.get('sticky', True) or not self.allowResize:
			return
		self.updateBackground(True)
		w.grid_configure(sticky='news')

	def updateBackground(self, sameAsGraphics):
		# make empty space when resizing appear to
		# be the graphics background color
		if not sameAsGraphics:
			tkColor = self.option_get('background', 'Frame')
		else:
			color = chimera.viewer.background
			if color is None:
				tkColor = '#000000'
			else:
				from CGLtk.color import rgba2tk
				tkColor = rgba2tk(color.rgba())
		w = self.toolbar
		if w["background"] == tkColor:
			return
		while w:
			w["background"] = tkColor
			parent = w.winfo_parent()
			if not parent:
				break
			if isinstance(parent, str):
				parent = w._nametowidget(parent)
			w = parent

	def makeGraphicsWindow(self):
		# Graphics gets attached to viewer by C/C++ init function.
		# Raises RuntimeError if unable to change pixel formats.
		import libgfxinfo
		if chimera.fullscreen:
			if windowSystem not in ('win32', 'x11'):
				chimera.fullscreen = False
				replyobj.warning('fullscreen is currently only supported on Microsoft Windows and X Windows')
		kw = {
			"double": True, "rgba": True, "depth": True,
			"stencil": True,
			"multisample": chimera.multisample,
			"alpha": chimera.bgopacity,
			"stereo": chimera.stereo.endswith('sequential stereo'),
			"createcommand": self.viewer.createCB,
			"displaycommand": self.viewer.updateCB,
			"reshapecommand": self.viewer.reshapeCB,
			"destroycommand": self.viewer.destroyCB,
		}

		if self.graphics:
			kw["sharelist"] = "main"
		if (chimera.stereo.endswith('sequential stereo')
		and not libgfxinfo.has(libgfxinfo.StereoMultisample)):
			kw["multisample"] = False
		parent = self.toolbar
		raWidth = raHeight = None	# rapid access width/height
		if chimera.fullscreen:
			# when using fullscreen graphics, rapid access
			# window stays normal size
			if self._fullscreen is None:
				self._fullscreen = Tk.Toplevel(self)
				self.pack()  # needed if starting in fullscreen
				self._fullscreen.wm_attributes('-fullscreen', 1)
				self._fullscreen.withdraw()
			parent = self._fullscreen
			kw["width"] = parent.winfo_screenwidth()
			kw["height"] = parent.winfo_screenheight()
			if not self.graphics:
				# replicate first time code to handle
				# --fullscreen on command line
				how = preferences.get(GENERAL, INITIAL_WINDOW_SIZE)
				if how == 1:
					w, h = preferences.get(GENERAL, FIXED_SIZE)
				else:
					w, h = preferences.get(INITIAL_SIZE, WINDOW_SIZE)
				raWidth = w
				raHeight = h
		elif self.fullscreen_graphics:
			if self._saveSize:
				kw["width"], kw["height"] = self._saveSize
				raWidth, raHeight = self._saveSize
		elif self.graphics:
			if not self.toolbar.work or self.toolbar.work == self.graphics:
				kw["width"] = self.graphics.cget("width")
				kw["height"] = self.graphics.cget("height")
			else:
				xywh = self.toolbar.work.grid_bbox()
				kw["width"] = xywh[2]
				kw["height"] = xywh[3]
			raWidth = kw["width"]
			raHeight = kw["height"]
		else:
			# initial size
			how = preferences.get(GENERAL, INITIAL_WINDOW_SIZE)
			if how == 1:
				w, h = preferences.get(GENERAL, FIXED_SIZE)
			else:
				w, h = preferences.get(INITIAL_SIZE, WINDOW_SIZE)
			raWidth = kw["width"] = w
			raHeight = kw["height"] = h
		from mousemodes import multitouch
		if multitouch and windowSystem == 'aqua':
			kw['touchescommand'] = self.trackPadTouchesCB

		while 1:
			try:
				chimera.tweak_graphics("save background alpha",
							chimera.bgopacity)
				graphics = Togl.Togl(parent, **kw)
			except Tk.TclError, what:
				if kw["multisample"]:
					# failed getting a multisample window
					# so don't bother trying ever again
					chimera.multisample = False
					kw["multisample"] = False
					continue
				e = str(what)
				if e.startswith("unable to share display lists"):
					e = "Graphics hardware supports request, but "\
					"can not switch while maintaining display data."
				elif chimera.stereo.endswith('sequential stereo'):
					e = "Unable to find hardware stereo support\n(%s)" % e
				elif chimera.bgopacity:
					e = "Unable to find hardware background transparency support\n(%s)" % e
					chimera.tweak_graphics("save background alpha", False)
				elif e.startswith("couldn't choose pixel format") \
				or e.startswith("could not create rendering context"):
					e = ("Display misconfiguration "
					"detected.  "
					"Please double check that the "
					"display's color quality is 24-bit "
					"color or greater.  "
					"You also might need to update or "
					"reinstall your graphics driver, "
					"and/or upgrade your graphics card.  "
					"Or you might need to switch to the "
					"64-bit version of chimera if your "
					"operating system is 64-bit.  "
					"Also see the chimera installation "
					"instructions for additional help.")
				raise RuntimeError, e
			break
		if self.graphics:
			if self.toolbar.work == self.graphics:
				self.toolbar.work = None
			self.graphics.destroy()
			# remap mouse bindings
			for sequence, button, modifiers, index in _mouseBindings:
				graphics.bind(sequence, lambda e, b=button, m=modifiers,
						i=index: _processMouse(b, m, i, app.viewer, e))
		graphics.configure(ident="main")
		if self.atomspecBalloon:
			self.cancelLabelBalloon()
		self.graphics = graphics
		self.fullscreen_graphics = chimera.fullscreen
		if self.rapidAccess:
			self.rapidAccess.configure(width=raWidth, height=raHeight)
		else:
			from rapidaccess import RapidAccess
			self.rapidAccess = RapidAccess(self.toolbar,
					width=raWidth, height=raHeight)
			self.rapidAccess.bind('<KeyPress>', self._keypress)
		# geometry management by toolbar
		help.register(self.graphics, "UsersGuide/chimerawindow.html")
		if chimera.fullscreen:
			self.toolbar.work = None
			graphics.pack(expand=1, fill=Tk.BOTH)
			graphics.focus()
		else:
			if self.toolbar.work == None:
				self.toolbar.work = self.graphics
			if self._fullscreen:
				self._fullscreen.destroy()
				self._fullscreen = None
				app.graphics.focus()
		if self.atomspecBalloon:
			self.bindAtomSpecBalloon()
		graphics.bind('<KeyPress>', self._keypress)
		if windowSystem == 'aqua':
			graphics.bind('<Command-KeyPress-`>', lambda e: 0)
			graphics.bind('<Command-KeyPress-~>', lambda e: 0)
		graphics.bind('<MouseWheel>', self._mousewheel)
		self.allowResize = False
		self.update_idletasks()
		def startAllowResize(*args):
			self.allowResize = True
			from chimera.triggerSet import ONESHOT
			return ONESHOT
		chimera.triggers.addHandler('new frame', startAllowResize, None)
		def freezeAllowResize(*args):
			self.allowResize = False
		def thawAllowResize(*args):
			self.after(500, startAllowResize)
		from SimpleSession import BEGIN_RESTORE_SESSION, END_RESTORE_SESSION
		chimera.triggers.addHandler(BEGIN_RESTORE_SESSION,
						freezeAllowResize, None)
		chimera.triggers.addHandler(END_RESTORE_SESSION,
						thawAllowResize, None)
		graphics.bind('<Key-F2>', self.bringToFront)
		graphics.bind('<Key-F8>', self.popupMenu)
		graphics.bind('<Key-F11>', self.toggleFullscreen)
		if chimera.fullscreen:
			self._fullscreen.bind('<Map>', self._fixFullscreenSize)
			if not self.rapidAccess.shown:
				self._fullscreen.deiconify()
		try:
			graphics.bind('<Key-App>', self.popupMenu)
		except Tk.TclError:
			pass
		try:
			graphics.bind('<Key-Menu>', self.popupMenu)
		except Tk.TclError:
			pass
		if self.viewer.camera.mode().startswith("row stereo"):
			graphics.configure(stereo="row interleaved")

	def _fixFullscreenSize(self, event=None):
		# In multiscreen setups, winfo_screenwidth/height gives total
		# width/height, but the fullscreen window only covers one
		# screen, so reset the width and height to the actual values.
		self.graphics.configure(
			width=self._fullscreen.winfo_width(),
			height=self._fullscreen.winfo_height())

	def bringToFront(self, event=None):
		top = self.winfo_toplevel()
		top.deiconify()
		import CGLtk
		CGLtk.raiseWindow(top)

	def popupMenu(self, event):
		if hasattr(event, 'keycode'):
			x = event.x_root
			y = event.y_root
		else:
			x = event.x
			y = event.y
		mb = self.menubar
		# TODO: use Tk's clone naming convention?
		name = mb._w + '.clone'
		exists = mb.tk.call('info', 'commands', name)
		if exists:
			# don't create menu if it exists
			mb.tk.call(name, 'post', x, y)
			return
		tmp = mb.tk.call(mb._w, 'clone', name, 'normal')
		mb.tk.call(name, 'post', x, y)

	def toggleFullscreen(self, event):
		self._setFullscreen(not chimera.fullscreen)

	def displayMenus(self):
		if not self.embedded:
			self.winfo_toplevel().config(menu=self.menubar)

	def _mousewheel(self, event):
		from mousemodes import multitouch
		if windowSystem == 'aqua' and multitouch:
                        # Ignore scroll events generated by the Mac trackpad (2-finger drag).
                        # There seems to be no reliable way to tell if a scroll came from the trackpad.
                        # Scrolls from the Apple Magic Mouse look like a trackpad scroll.
                        # Only way to tell true trackpad events seems to be to look at trackpad touches.
                        if getattr(self, 'last_trackpad_touch_count', 0) >= 2:
                                return  # Ignore trackpad generated scroll
                        if hasattr(self, 'last_trackpad_touch_time'):
                                import time
                                if time.time() < self.last_trackpad_touch_time + 1.0:
                                        # Suppress momentum scrolling for 1 second after trackpad scrolling ends.
                                        return
		self.cancelLabelBalloon()
		from chimera.mousemodes import mousewheel
		if not mousewheel or (event.state & (0xff << 8)):
			# a button is pressed, so ignore wheel
			return
		self.viewer.recordPosition(event.time, event.x, event.y, None)
		d = event.delta
		if windowSystem == 'aqua':
			sign = -1 if macNaturalScrolling() else 1
			d *= 30*sign
		event.x -= d
		_zoom(self.viewer, event)

	def zoomByFactor(self, f):
		import Midas
		Midas.updateZoomDepth(self.viewer)
		try:
			self.viewer.scaleFactor *= f
		except ValueError:
			import chimera
			raise chimera.LimitationError("refocus to continue scaling")

	def trackPadTouchesCB(self, widget, *touches):
		min_pinch = 0.1
		n = len(touches)/3
                import time
                self.last_trackpad_touch_time = time.time()
                self.last_trackpad_touch_count = n
		id_xy = [tuple(float(p) for p in touches[3*i:3*i+3]) for i in range(n)]
		lt = getattr(self, 'lastTouches', {})
		moves = [(id,x-lt[id][0],y-lt[id][1]) for id,x,y in id_xy if id in lt]
		self.lastTouches = dict((id,(x,y)) for id,x,y in id_xy)
		if len(moves) == n:
                        if n > 1:
                                self.cancelLabelBalloon()
			if n == 2:
				(dx0,dy0),(dx1,dy1) = moves[0][1:], moves[1][1:]
				from math import sqrt, exp, atan2, pi
				l0,l1 = sqrt(dx0*dx0 + dy0*dy0),sqrt(dx1*dx1 + dy1*dy1)
				d12 = dx0*dx1+dy0*dy1
				if l0 >= min_pinch and l1 >= min_pinch and d12 < -0.7*l0*l1:
					# pinch or twist
					(x0,y0),(x1,y1) = id_xy[0][1:], id_xy[1][1:]
					sx,sy = x1-x0,y1-y0
					sn = sqrt(sx*sx + sy*sy)
					sd0,sd1 = sx*dx0 + sy*dy0, sx*dx1 + sy*dy1
					if abs(sd0) > 0.5*sn*l0 and abs(sd1) > 0.5*sn*l1:
						# pinch
						s = 1 if sd1 > 0 else -1
						self.zoomByFactor(exp(0.02*s*(l0+l1)))
						return
					else:
						# twist
						from chimera import Xform, openModels as om
						a = (atan2(-sy*dx1+sx*dy1,sn*sn) +
						     atan2(sy*dx0-sx*dy0,sn*sn))*180/pi
						xf = Xform.rotation(0,0,1,3*float(a))
						om.applyXform(xf)	# Handles center of rotation shift
				dx = sum(x for id,x,y in moves)
				dy = sum(y for id,x,y in moves)
				# rotation
				from chimera import Vector, Xform, openModels as om
				axis = Vector(-dy, dx, 0)
				angle = axis.length
				if angle != 0:
					axis.normalize()
					xf = Xform.rotation(axis,angle)
					om.applyXform(xf)  # Handles center of rotation shift
			elif n == 3:
				dx = sum(x for id,x,y in moves)
				dy = sum(y for id,x,y in moves)
				# translation
				from chimera import Vector, Xform, openModels as om
				step = Vector(dx, dy, 0)
				if step.length != 0:
					step *= 0.005 * self.viewer.camera.extent
					xf = Xform.translation(step)
					om.applyXform(xf)  # Handles center of rotation shift
				
				
	def _keypress(self, event):
		# KeyPress event callback
		if event.keysym in ("Up", "Down", "Right", "Left"):
			if self.toolbar.work != self.graphics:
				return
			from chimera.selection.upDown import selUp, selDown
			if event.keysym == "Up":
				selUp()
			elif event.keysym == "Down":
				selDown()
			elif event.keysym == "Right":
				from chimera.selection import invertCurrent
				if event.state % 2 == 1: # shift key down
					invertCurrent(allModels=True)
				else:
					invertCurrent(allModels=False)
			elif event.keysym == "Left":
				if event.state % 2 == 1: # shift key down
					selection.clearCurrent()
				else:
					selection.setCurrent(selCache[1])
		elif _keybdFuncs:
			for keybdf in reversed(_keybdFuncs):
				if keybdf(event) != "continue":
					break

	def _setBalloon(self, option):
		self.showBalloons = option.get()
		if self.showBalloons:
			self.balloon.configure(state="balloon")
			for mb in _menuBalloons:
				mb.configure(state="balloon")
			for ol in _outlineLayouts:
				ol.setAllowBalloons(1)
		else:
			self.balloon.configure(state="none")
			for mb in _menuBalloons:
				mb.configure(state="none")
			for ol in _outlineLayouts:
				ol.setAllowBalloons(0)

	def bindAtomSpecBalloon(self):
		self.atomspecBalloon = True
		self._atomspecBalloonUpdate = self.graphics.bind('<Any-Motion>',
			lambda e, s=self: s.updateLabelBalloon(e), add=1)
		self._atomspecBalloonCancel = self.graphics.bind('<Any-Leave>',
			lambda e, s=self: s.cancelLabelBalloon(), add=1)

	def unbindAtomSpecBalloon(self):
		self.atomspecBalloon = False
		self.graphics.unbind('<Any-Motion>',
						self._atomspecBalloonUpdate)
		self.graphics.unbind('<Any-Leave>',
						self._atomspecBalloonCancel)
		self.cancelLabelBalloon()

	def _setAtomspecBalloon(self, option):
		if option.get():
			if self.atomspecBalloon:
				return
			self.bindAtomSpecBalloon()
		else:
			if not self.atomspecBalloon:
				return
			self.unbindAtomSpecBalloon()

	def _setFullscreen(self, fullscreen):
		if fullscreen == chimera.fullscreen:
			return
		prev_fullscreen = chimera.fullscreen
		chimera.fullscreen = fullscreen
		if not prev_fullscreen:
			self._saveSize = (self.graphics.cget("width"),
						self.graphics.cget("height"))
		self.makeGraphicsWindow()
		if chimera.openModels.list():
			app.rapidAccess.shown = chimera.fullscreen

	def cancelLabelBalloon(self):
		if self._infoTimer:
			self.after_cancel(self._infoTimer)
			self._infoTimer = None
		if self.labelBalloon:
			# deregister balloon
			self.labelBalloon.destroy()
			self.labelBalloon = None
			replyobj.status("")

	def updateLabelBalloon(self, event):
		if self.viewer.inhibitLabelBalloon:
			return
		self.cancelLabelBalloon()
		if event.type in [4, 5]:
			# 4 == ButtonPress, 5 == ButtonRelease
			return
		self._infoTimer = self.after(200,
				 lambda s=self, e=event: s.showLabelBalloon(e))

	def showLabelBalloon(self, event):
		self._infoTimer = None
		self.viewer.recordPosition(event.time, event.x, event.y, None)
		objs = self.viewer.pick(event.x, event.y)
		if not objs:
			return
		o = objs[0]
		balloonText = chimeraLabel(o)
		b = Tk.Toplevel(self.graphics, takefocus=0)
		self.labelBalloon = b
		if windowSystem == 'aqua':
			import CGLtk
			CGLtk.balloonDontTakeFocus(b)
		b.wm_overrideredirect(1)	# Window manager manage window.
		b.wm_geometry('+%d+%d' % (event.x_root + 10, event.y_root + 1))
		b.wm_resizable(0, 0)
		if isinstance(o, chimera.Bond) \
		or isinstance(o, chimera.PseudoBond):
			from StructMeasure.DistMonitor import precision
			# \u00C5 is the Angstrom symbol
			balloonText += u" %.*f\u00C5" % (precision(),
					chimera.distance(*tuple([a.xformCoord()
					for a in o.atoms])))

		label = Tk.Label(b, text=balloonText)
		label.pack()
		b.lift()

		seq = res = None
		if isinstance(o, chimera.Atom):
			res = o.residue
		elif isinstance(o, chimera.Bond):
			res = o.atoms[0].residue
		elif isinstance(o, chimera.Residue):
			res = o
		if res:
			mol = res.molecule
			if not hasattr(mol, '_hetnamDescriptions'):
				hnd = mol._hetnamDescriptions = {}
				if hasattr(mol, 'pdbHeaders'):
					recs = mol.pdbHeaders.get('HETNAM', []) \
						+ mol.pdbHeaders.get('HETSYN', [])
					alternatives = {}
					for rec in recs:
						if rec[8:10].strip():
							# continuation
							hnd[het] = hnd[het] + rec[15:].strip()
						else:
							het = rec[11:14].strip()
							if het in hnd:
								alternatives[het] = hnd[het]
							hnd[het] = rec[15:].strip()
					# use "punchier" description :-)
					for het, alt in alternatives.items():
						if len(alt) < len(hnd[het]):
							hnd[het] = alt
				from chimera.misc import processPdbChemName
				for k, v in hnd.items():
					hnd[k] = processPdbChemName(v)
			if res.type in mol._hetnamDescriptions:
				replyobj.status(mol._hetnamDescriptions[res.type],
					blankAfter=0)
			else:
				chainID = res.id.chainId
				try:
					seq = res.molecule.sequence(chainID)
				except (KeyError, AssertionError):
					pass
				else:
					if res not in seq.residues:
						seq = None
				if seq and seq.descriptiveName:
					try:
						replyobj.status("chain %s: %s" % (seq.chainID,
							seq.descriptiveName), blankAfter=0)
					except ValueError:
						pass

_pickType = None
def _processPick(viewer, event):
	objs = viewer.pick(event.x, event.y)
	# objs may have duplicates, so remove the extras so shift/pick will work
	dict = {}
	for o in objs:
		dict[o] = ()
	objs = dict.keys()	# objs is now a unique list
	if event.state % 2 == 1:
		selection.toggleInCurrent(objs)		# Shift-key down
	else:
		selection.setCurrent(objs)
	global _pickType
	if len(objs) == 1 and selection.containedInCurrent(objs[0]):
		_pickType = type(objs[0])
	else:
		_pickType = None
	viewer.setCursor(None)

def _doublePick(viewer, event):
	"""generate menu appropriate for current selection

	(could use a modal dialog instead)
	"""
	menu = Tk.Menu(app, tearoff=False)
	haveItems = False
	if _pickType == chimera.Bond:
		b = selection.currentBonds()
		if len(b) == 1:
			b = b[0]
			menu.add_command(label=chimeraLabel(b),
							state=Tk.DISABLED)
			from BuildStructure import gui as bsgui
			menu.add_command(label="Rotate Bond",
				command=lambda: bsgui.addRotation(b))
			menu.add_command(label="Adjust Bond",
				command=lambda: dialogs.display(
				bsgui.BuildStructureDialog.name)
				.setCategory(bsgui.ADJUST_BONDS))
			haveItems = True
	if _pickType in [chimera.Bond, chimera.PseudoBond]:
		e = selection.currentEdges()
		if e:
			if not haveItems and len(e) == 1:
				menu.add_command(label=chimeraLabel(e[0]),
							state=Tk.DISABLED)
			def selBonded(edges):
				sel = selection.ItemizedSelection()
				atoms = []
				for edge in edges:
					atoms.extend(edge.atoms)
				sel.add(atoms)
				selectionOperation(sel)
			menu.add_command(label="Select Bonded",
						command=lambda: selBonded(e))
			haveItems = True
	if _pickType == chimera.Atom:
		a = selection.currentAtoms(ordered=True)
		if len(a) == 1:
			from chimera.elements import metals
			if a[0].element in metals:
				from MetalGeom.gui import MetalsDialog
				menu.add_command(label="Coordination Geometry",
					command=lambda a=a[0]: dialogs.display(
					MetalsDialog.name).metalsMenu.setvalue(a))
			if _distAtom() == a[0]:
				menu.add_command(label="Hide Distances to Nearby Residues",
					command=lambda a=a[0]: _nearbyDistances(a))
			else:
				menu.add_command(label="Show Distances to Nearby Residues",
					command=lambda a=a[0]: _nearbyDistances(a))
			from BuildStructure import gui as bsgui
			menu.add_command(label="Modify Atom",
				command=lambda: dialogs.display(
				bsgui.BuildStructureDialog.name)
				.setCategory(bsgui.CHANGE_ATOM))
			from chimera import actions
			menu.add_command(label="Set Pivot",
						command=actions.setPivot)
			haveItems = True
		elif len(a) == 2:
			from StructMeasure.gui import addDistance
			menu.add_command(label="Show Distance", command=
				lambda f=addDistance, a=a: f(*a))
			haveItems = True
		elif len(a) in [3, 4]:
			from StructMeasure.gui import addAngle
			if len(a) == 3:
				label = "Measure Angle"
			else:
				label = "Measure Torsion"
			menu.add_command(label=label,
				command=lambda a=a: addAngle(a))
			haveItems = True
	if haveItems:
		menu.add_command(label="Inspect",
			command=lambda pt=_pickType: dialogs.display(_InspectDialog.name,
			wait=True).inspector.inspect(pt))
		menu.tk_popup(event.x_root, event.y_root, entry=1)

import weakref
_distAtom = weakref.ref(_doublePick)
_distPartners = weakref.WeakSet()
_distRelabeledResidues = weakref.WeakSet()
def _nearbyDistances(atom):
	global _distAtom, _distPartners, _distRelabeledResidues
	from StructMeasure.DistMonitor import addDistance, removeDistance, _findDistance
	da = _distAtom()
	if da != _doublePick and not da.__destroyed__:
		while _distPartners:
			partner = _distPartners.pop()
			if partner.__destroyed__:
				continue
			if _findDistance(da, partner):
				removeDistance(da, partner)
	while _distRelabeledResidues:
		res = _distRelabeledResidues.pop()
		if not res.__destroyed__:
			res.label = ""
	if atom == da:
		_distAtom = weakref.ref(_doublePick)
		return
	_distAtom = weakref.ref(atom)
	from numpy import array
	from _multiscale import get_atom_coordinates as gac
	from _closepoints import find_close_points, BOXES_METHOD
	from chimera import openModels, Molecule
	atoms = array([a for m in openModels.list(modelTypes=[Molecule])
		for a in m.atoms])
	ignore, nearbyIndices = find_close_points(BOXES_METHOD,
		gac(array([atom])), gac(atoms), 3.6)
	exclude = set([atom])
	for nb in atom.neighbors:
		exclude.add(nb)
		for gnb in nb.neighbors:
			exclude.add(gnb)
	if not atom.residue.label:
		atom.residue.label = str(atom.residue)
		_distRelabeledResidues.add(atom.residue)
	for partner in atoms[nearbyIndices]:
		if partner.residue == atom.residue or partner in exclude:
			continue
		if partner not in atom.neighbors and not _findDistance(atom, partner):
			addDistance(atom, partner)
			_distPartners.add(partner)
			if not partner.display:
				for a in partner.residue.atoms:
					a.display = True
			if not partner.residue.label:
				partner.residue.label = str(partner.residue)
				_distRelabeledResidues.add(partner.residue)

_labelObj = None
def _pickLabel(viewer, event):
	global _labelObj
	_labelObj = viewer.pickLabel(event.x, event.y)
	adjustZ = event.state % 2 == 1		# is Shift-key down?
	if adjustZ:
		viewer.setCursor("translate z")
	else:
		viewer.setCursor("translate x/y")

def _dragLabel(viewer, event):
	if not _labelObj:
		return
	coord = _labelObj.labelCoord()
	offset = _labelObj.currentLabelOffset()
	coord += offset
	adjustZ = event.state % 2 == 1		# is Shift-key down?
	newCoord = viewer.moveLabel(event.x, event.y, adjustZ, coord)
	delta = newCoord - coord
	_labelObj.labelOffset = offset + delta

def _releaseLabel(viewer, event):
	global _labelObj
	_labelObj = None
	viewer.setCursor(None)

def _centerPick(viewer, event):
	viewer.recordPosition(event.time, event.x, event.y, None)
	objs = viewer.pick(event.x, event.y)
	from chimera import openModels as om
	if len(objs) == 0:
		om.cofrMethod = om.FrontCenter
		return

        from _surface import SurfacePiece
        if len(objs) == 1 and isinstance(objs[0], SurfacePiece):
                # Center on clicked point on surface.
                p = objs[0]	# SurfacePiece
                from VolumeViewer import slice
                xyz_in, xyz_out = slice.clip_plane_points(event.x, event.y)
                from Matrix import apply_inverse_matrix
                sxyz1, sxyz2 = apply_inverse_matrix(p.model.openState.xform, xyz_in, xyz_out)
                if sxyz1 is not None:
                        import PickBlobs
                        t, f = PickBlobs.closest_piece_intercept(p, sxyz1, sxyz2)
                        if f is not None:
                                xyz = tuple(a + f*(b-a) for a,b in zip(xyz_in, xyz_out))
                                chimera.viewer.camera.center = xyz
		                om.cofrMethod = om.Fixed
		                om.cofr = chimera.Point(*xyz)
                return

	sel = selection.ItemizedSelection(objs)
	sel.addImplied(vertices = True, edges = False)	# Allow center on bond.
	import Midas
	try:
		c = Midas.center(sel, frames=5)
	except Midas.MidasError:
		c = None	# Nothing that can be centered on.
	if c:
		om.cofrMethod = om.Fixed
		om.cofr = c

_autospinHandler = None

def _doAutospin(trigger, xform, frameNumber):
	chimera.openModels.applyXform(xform)

def _startAutoSpin(viewer, event, func, xform):
	from chimera.mousemodes import autospin
	if autospin and xform and not xform.isIdentity() \
	and viewer.startAutoSpin(event.time, event.x, event.y):
		viewer.inhibitLabelBalloon = True
		global _autospinHandler
		_autospinHandler = chimera.triggers.addHandler('new frame',
							func, xform)
	viewer.setCursor(None)

def stopSpinning():
	global _autospinHandler
	if _autospinHandler:
		chimera.triggers.deleteHandler('new frame', _autospinHandler)
	_autospinHandler = None

_saveVsphereXform = None

def _vsphere(viewer, event):
	global _saveVsphereXform
	xf = viewer.vsphere(event.time, event.x, event.y, event.state % 2 == 1)
	_saveVsphereXform = xf
	if xf.isIdentity():
		return
	chimera.openModels.applyXform(xf)

_clipModel = None

def initClip(model):
	valid, bbox = model.bbox()
	if not valid:
		raise ValueError, "No bounding box for model"
	p = model.clipPlane
	if p.normal == chimera.Vector():
		# Plane has never been initialized.
		# Default to plane through the center of model
		# with front half clipped (if unrotated).
		model.clipPlane = chimera.Plane(bbox.center(),
						chimera.Vector(0, 0, -1))
		normalizeClipFacing(model, changePivot=False)
		# Set optional clipThickness to a 1/10 of the shortest side
		# of the bounding box (1/2 might not be visibily clipped).
		model.clipThickness = min(bbox.urb - bbox.llf) / 10
	model.useClipPlane = True

def normalizeClipFacing(model, changePivot=True):
	"""clip perpendicular to line of sight with pivot in center of view"""

	xf = model.openState.xform
	xf.invert()
	p = model.clipPlane
	p.normal = xf.apply(chimera.Vector(0.0, 0.0, -1.0))
	if changePivot:
		cam = app.viewer.camera
		n, f = cam.nearFar
		x, y, z = cam.center
		p.origin = xf.apply(chimera.Point(x, y, 0.5*(n+f)))
	model.clipPlane = p

def setClipModel(model):
	# can raise ValueError (via initClip)
	global _clipModel
	if not model:
		_clipModel = None
		return
	initClip(model)
	from weakref import ref
	_clipModel = ref(model)

def getClipModel():
	global _clipModel
	if _clipModel is None:
		return None
	model = _clipModel()
	if model:
		if model.__destroyed__:
			model = None
	if model is None:
		_clipModel = None
	return model

from chimera import mousemodes

# types of mouse events
DOWN = 0	# Press
MOVE = 1	# Motion
UP = 2		# Release
DOUBLE_DOWN = 3	# Double-Press
DOUBLE_UP = 4	# Double-Release

_mouseFuncOrder = [
	"rotate", "translate x,y", "translate z", "scale",
	"pick", "menu", "drag label", "center"
]

def _zoomStart(v, e):
	import Midas
	Midas.updateZoomDepth(v)
	v.recordPosition(e.time, e.x, e.y, "zoom"),
	
def _zoom(v, e):
	try:
		v.zoom(e.x, e.y, e.state %2 == 1)
	except ValueError:
		raise chimera.LimitationError("refocus to continue scaling")

def _translateZStart(v, e):
	import Midas
	Midas.updateZoomDepth(v)
	v.recordPosition(e.time, e.x, e.y, "translate z"),

_mouseFuncs = {
	# tuple of mouse events: (DOWN, MOVE, UP [, DOUBLE_DOWN, DOUBLE_UP])
	"rotate": (
		lambda v, e: v.recordPosition(e.time, e.x, e.y, "rotate"),
		_vsphere,
		lambda v, e: _startAutoSpin(v, e, _doAutospin, _saveVsphereXform)
	),
	"translate x,y": (
		lambda v, e: v.recordPosition(e.time, e.x, e.y, "translate x/y"),
		lambda v, e: v.translateXY(e.x, e.y, e.state % 2 == 1),
		lambda v, e: v.setCursor(None)
	),
	"translate z": (
		_translateZStart,
		lambda v, e: v.translateZ(e.x, e.y, e.state % 2 == 1),
		lambda v, e: v.setCursor(None)
	),
	"pick": (
		lambda v, e: v.recordPosition(e.time, e.x, e.y, "pick"),
		lambda v, e: v.dragPick(e.x, e.y),
		_processPick,
		None,
		_doublePick
	),
	#"lens": (
	#	lambda v, e: v.selectLens(e.x, e.y),
	#	lambda v, e: v.moveLens(e.x, e.y),
	#	lambda v, e: v.setCursor(None)
	#),
	"scale": (
		_zoomStart,
		_zoom,
		lambda v, e: v.setCursor(None)
	),
	"menu": (
		lambda v, e: app.popupMenu(e), None, None
	),
	"drag label": (
		_pickLabel,
		_dragLabel,
		_releaseLabel
	),
	"center": (
		_centerPick,
		None,
		None,
	),
}

for fname in _mouseFuncOrder:
	mousemodes.addFunction(fname, _mouseFuncs[fname])
mousemodes.setButtonFunction(B1, (), "rotate", isDefault=True)
mousemodes.setButtonFunction(B2, (), "translate x,y", isDefault=True)
mousemodes.setButtonFunction(B1, (CTRL,), "pick", isDefault=True)
mousemodes.setButtonFunction(B2, (CTRL,), "translate z", isDefault=True)
mousemodes.setButtonFunction(B3, (), "scale", isDefault=True)
mousemodes.setButtonFunction(B3, (CTRL,), "center", isDefault=True)

_keybdFuncs = []
def addKeyboardFunc(func):
	_keybdFuncs.append(func)

def deleteKeyboardFunc(func):
	_keybdFuncs.reverse()
	_keybdFuncs.remove(func)
	_keybdFuncs.reverse()

def _showChildren(app, event):
	if not hasattr(app, 'hiddenChildren'):
		return
	for w in app.hiddenChildren:
		try:
			w.deiconify()
		except Tk.TclError:
			continue	# window gone? don't care
		w.tkraise()
	chimera.triggers.activateTrigger('mapped', None)

def _hideChildren(app, event):
	hidden = []
	for w in app.winfo_children():
		if not isinstance(w, Tkinter.Toplevel):
			continue
		if w.wm_state() == 'icon':
			continue
		if w.winfo_ismapped():
			hidden.append(w)
			w.wm_positionfrom('user')  # remember window position

			# on Darwin, where X11 is just another app, bad things
			# happen if X11 itself is asked to hide and we try to
			# hide the child windows before the X server does, so
			# delay the hide and check mapped status...
			w.after_idle(lambda w=w:
					w.winfo_ismapped() and w.withdraw())
	app.hiddenChildren = hidden
	chimera.triggers.activateTrigger('unmapped', None)

def _circulateFocus(backward = False):
	try:
		f = app.focus_get()
	except KeyError:
		# can happen for tear-off menus
		return
	if f is None:
		return
	ft = f.winfo_toplevel()
	a = app.winfo_toplevel()
	from Tkinter import Toplevel
	t = [a] + [w for w in app.winfo_children()
		   if w == ft or (isinstance(w, Toplevel) and
				  w.winfo_ismapped() and
				  w.wm_state() != 'icon')]
	if ft in t:
		i = t.index(ft)
		if backward: i -= 1
		else: i += 1
		t[i % len(t)].tkraise()

_mouseBindings = (
	('<ButtonPress-1>', B1, (), DOWN),
	('<Button1-Motion>', B1, (), MOVE),
	('<ButtonRelease-1>', B1, (), UP),
	('<Double-ButtonPress-1>', B1, (), DOUBLE_DOWN),
	('<Double-ButtonRelease-1>', B1, (), DOUBLE_UP),
	('<Control-ButtonPress-1>', B1, (CTRL,), DOWN),
	('<Control-Button1-Motion>', B1, (CTRL,), MOVE),
	('<Control-ButtonRelease-1>', B1, (CTRL,), UP),
	('<Double-Control-ButtonPress-1>', B1, (CTRL,), DOUBLE_DOWN),
	('<Double-Control-ButtonRelease-1>', B1, (CTRL,), DOUBLE_UP),
	('<ButtonPress-2>', B2, (), DOWN),
	('<Button2-Motion>', B2, (), MOVE),
	('<ButtonRelease-2>', B2, (), UP),
	('<Double-ButtonPress-2>', B2, (), DOUBLE_DOWN),
	('<Double-ButtonRelease-2>', B2, (), DOUBLE_UP),
	('<Control-ButtonPress-2>', B2, (CTRL,), DOWN),
	('<Control-Button2-Motion>', B2, (CTRL,), MOVE),
	('<Control-ButtonRelease-2>', B2, (CTRL,), UP),
	('<Double-Control-ButtonPress-2>', B2, (CTRL,), DOUBLE_DOWN),
	('<Double-Control-ButtonRelease-2>', B2, (CTRL,), DOUBLE_UP),
	('<ButtonPress-3>', B3, (), DOWN),
	('<Button3-Motion>', B3, (), MOVE),
	('<ButtonRelease-3>', B3, (), UP),
	('<Double-ButtonPress-3>', B3, (), DOUBLE_DOWN),
	('<Double-ButtonRelease-3>', B3, (), DOUBLE_UP),
	('<Control-ButtonPress-3>', B3, (CTRL,), DOWN),
	('<Control-Button3-Motion>', B3, (CTRL,), MOVE),
	('<Control-ButtonRelease-3>', B3, (CTRL,), UP),
	('<Double-Control-ButtonPress-3>', B3, (CTRL,), DOUBLE_DOWN),
	('<Double-Control-ButtonRelease-3>', B3, (CTRL,), DOUBLE_UP),
)

_lastModifiers = ()
def _processMouse(button, modifiers, which, viewer, event):
	global _lastModifiers
	app.cancelLabelBalloon()
	# modifiers are sticky until another button is pressed
	if which == DOWN:
		_lastModifiers = modifiers
	elif _lastModifiers != modifiers:
		modifiers = _lastModifiers
	calls = mousemodes.getCallables(button, modifiers)
	if not calls:
		return
	if which in (DOWN, DOUBLE_DOWN):
		# button press and double-press
		stopSpinning()
		app.graphics.focus()
		viewer.inhibitLabelBalloon = False
	if len(calls) == 3 and which >= DOUBLE_DOWN:
		# ignore double click actions
		return
	func = calls[which]
	if not func:
		return
	func(viewer, event)

def createApp(embed):
	replyobj.status("create application")
	# reuse Tcl interpreter from splash screen
	master = splash.root

	if not chimera.visual and master.winfo_screenvisual() == 'pseudocolor':
		if (master.winfo_screendepth() < 12):
			# try for a deeper depth for more colorful interfaces
			chimera.visual = "pseudocolor 12"
	if chimera.visual:
		master.option_add('*visual', chimera.visual)

	replyobj.status("loading Pmw")
	import Pmw
	Pmw.initialise(master)
	# make Pmw errors use the same reporting mechanism as all other errors
	class _pmwHoax:
		def write(self, errText):
			from chimera.replyobj import reportException
			reportException(fullDescription=errText)
	Pmw.reporterrorstofile(_pmwHoax())

	replyobj.status("creating main window")
	app = Application(master, embed=embed)
	app.bind('<Map>', lambda event, w=app: _showChildren(w, event))
	app.bind('<Unmap>', lambda event, w=app: _hideChildren(w, event))
	if windowSystem == 'x11':
		# Support for mousewheels on Linux/Unix commonly comes through
		# mapping the wheel to the extended buttons.
		def mousewheel(e, delta):
			try:
				w = e.widget.focus_displayof()
			except (AttributeError, KeyError):
				# e.widget might be string
				# if not created by Tkinter (eg., menu tearoff)
				# Also, tearoffs generate KeyError in
				# nametowidget lookup
				return
			if w: w.event_generate('<MouseWheel>', delta=delta,
				state=e.state, rootx=e.x_root, rooty=e.y_root,
				x=e.x, y=e.y, time=e.time)
		app.bind_all('<Button-4>', lambda e, mw=mousewheel: mw(e, 120))
		app.bind_all('<Button-5>', lambda e, mw=mousewheel: mw(e, -120))

		from chimera import chimage
		icon = chimage.get('chimera48.png', app)
		iconwin = Tk.Toplevel(master=app, background=None)
		iconimage = Tk.Label(iconwin, image=icon)
		iconimage.__image = icon
		iconimage.pack()
		app.winfo_toplevel().wm_iconwindow(iconwin)
	elif windowSystem == 'win32':
		filename = chimera.pathFinder().firstExistingFile("chimera",
					os.path.join("Icons", "chimera32.ico"),
					False, False)
		if filename:
			# this requires Tcl/Tk 8.3.3 (or newer)
			top = app.winfo_toplevel()
			# top.wm_iconbitmap(filename) with -default
			top.tk.call('wm', 'iconbitmap', top._w, '-default',
								filename)
	app.master.protocol("WM_DELETE_WINDOW", showConfirmExitDialog)

	if windowSystem == 'aqua':
		# Button 2 and 3 reversed due to Aqua Tk bug (8.5.2).
		bmap = {B1:B1, B2:B3, B3:B2}
		global _mouseBindings
		mb = [(s,bmap[b],m,i) for s,b,m,i in _mouseBindings]
		_mouseBindings = tuple(mb)
		# Add Option key and Command key modifiers to emulate
		# buttons 3 and 2 for users with a 1-button mouse.
		b2b = [('<Command-'+s.replace('2','1')[1:],b,m,i)
		       for s,b,m,i in _mouseBindings if '2' in s]
		b3b = [('<Option-'+s.replace('3','1')[1:],b,m,i)
		       for s,b,m,i in _mouseBindings if '3' in s]
		_mouseBindings += tuple(b2b) + tuple(b3b)
	for sequence, button, modifiers, index in _mouseBindings:
		app.graphics.bind(sequence, lambda e, b=button, m=modifiers,
				i=index: _processMouse(b, m, i, app.viewer, e))
	return app

def initializeGUI(exitonquit, debug_opengl, embed):
	master = splash.root
	global windowSystem, tkFlavor
	windowSystem = master.tk.call('tk', 'windowingsystem')
	if windowSystem == 'aqua':
		if 'AppKit' in master.winfo_server():
			tkFlavor = 'cocoa'
		else:
			tkFlavor = 'carbon'
	else:
		tkFlavor = ''

	global app
	replyobj.status('initializing general preferences')
	_initializeGeneralPreferences()

	# load Tix package
	replyobj.status("loading Tix")
	import Tix
	try:
		try:
			tixlib = os.path.basename(os.environ['TIX_LIBRARY'])
			import re
			tmp = re.search('[0-9][0-9.]*', tixlib)
			if tmp:
				tixver = tixlib[tmp.start() : tmp.end()]
				if float(tixver) <= 8.1:
					tixver = tixver + '.' \
					+ master.tk.call('set', 'tcl_version')
			else:
				tixver = None
		except KeyError:
			tixver = None
		if tixver:
			master.tk.call('package', 'require', '-exact', 'Tix', tixver)
		else:
			master.tk.call('package', 'require', 'Tix')
	except Tk.TclError:
		master.tk.call('load', '', 'Tix')
	master.tk.call('tix', 'initstyle')

	replyobj.status('initializing graphics')
	try:
		import OpenGLDebug
		if preferences.get(GENERAL, DEBUG_OPENGL):
			debug_opengl = True
		OpenGLDebug.checkConfig(master, debug_opengl)

		chimera.triggers.addTrigger('unmapped')
		chimera.triggers.addTrigger('mapped')
		chimera.triggers.addTrigger('status line')
		chimera.triggers.addTrigger('graphics window size')

		#splash.create()
		how = preferences.get(GENERAL, INITIAL_WINDOW_SIZE)
		if how == 1:
			w, h = preferences.get(GENERAL, FIXED_SIZE)
		else:
			w, h = preferences.get(INITIAL_SIZE, WINDOW_SIZE)
		app = createApp(embed)
		app.bind('<Configure>', app._trackGraphicsWindowSize)
		if chimera.fullscreen:
			app.rapidAccess.shown = True
		# save initial size, so we can use the original values
		# even if the geometry management picks something different
		app._initialSize = (w, h)
	except chimera.ChimeraExit, e:
		if splash.root:
			from tkMessageBox import showerror
			showerror(chimera.appName + ' startup error', e)
		else:
			print >> sys.stderr, "Error starting %s: %s" % \
								(chimera.appName, e)
		raise SystemExit, 2
	except:
		# Make sure the output is going to terminal since we're
		# about to go away
		replyobj.reportException("Error starting " + chimera.appName)
		raise SystemExit, 2

	replyobj.status('initializing preferences')

	#preferences.addCategory(printer.PAGE_SETUP, printer.PageSetupCategory)
	#preferences.addCategory(printer.IMAGE_SETUP, printer.ImageSetupCategory)
	preferences.register(printer.POVRAY_SETUP, printer.povrayPreferences)
	preferences.setOrder(printer.POVRAY_SETUP, printer.povrayPreferencesOrder)
	printer.initializeCreditPreferences()


	replyobj.status('initializing dialogs')
	_initializeDialogs()

	replyobj.status('initializing COM')
	_initializeCOM()

	# Specify whether Chimera should raise SystemExit when user quits.
	global exitOnQuit
	exitOnQuit = exitonquit

def _firstStatus(lastVersion):
	from chimera import statusline
	statusline.show_status_line(True)

	from chimera import version
	if lastVersion and lastVersion != version.release:
		curVer = version.buildVersion(version.releaseNum)
		lastVer = version.buildVersion(
					version.expandVersion(lastVersion))
		def firstStatus(v=curVer, lv=lastVer):
			replyobj.status("You are now running Chimera version %s"
				"; see Reply Log for more info\n" % v,
				color='blue')
			replyobj.info(
"""You are now running Chimera version %s.
Your previous version was %s.
Check the release notes for new features and other info.
(To access the release notes, use the Help menu to bring up the User's Guide.
Then click the 'Documentation index' link and you will then see a link
for the release notes.)
""" % (v, lv))
	else:
		def firstStatus():
			if mousemodes.getFuncName(B1, (CTRL,)) == "pick":
				replyobj.status("Control click/drag to select"
				" on structures\n", followWith=
				"Control dbl-click atoms/bonds for"
				" context menu\n")
	chimera.registerPostGraphicsFunc(firstStatus)

def _checkForUnicodeUserName():
	try:
		user = os.environ['USERNAME']
	except KeyError:
		return
	if user.encode('mbcs').decode('mbcs') == user:
		return
	import libgfxinfo
	windows = libgfxinfo.getOS()
	# ignoring Windows server editions
	if 'Windows XP' in windows or 'Windows NT' in windows:
		tool = "Regional and Language Options"
		language = "default input language"
	elif 'Windows Vista' in windows:
		tool = "Regional and Language Options"
		language = "system locale"
	else:
		# assume Windows 7
		tool = "Region and Language"
		language = "system locale"
	replyobj.warning(u"Your user name, %s, has a character in it that"
			u" cannot be encoded for non-Unicode Windows"
			u" programs (like some of the programs bundled with"
			u" Chimera).  You might be able to fix it by"
			u" changing the %s in the %s tool in the Windows"
			u" Control Panel.  If not, create a new account"
			u" with a non-Unicode name, and login to that"
			u" account to use Chimera to its fullest."
			% (user, language, tool))

def finalizeGUI():
	# wait for graphics to be initialized so we have a graphics context
	extraArgs = splash.destroy()
	if chimera.geometry:
		top = app.winfo_toplevel()
		top.geometry(chimera.geometry)
	app.pack(expand=Tk.YES, fill=Tk.BOTH)
	app.displayMenus()

	if not app.graphics.winfo_viewable():
		app.graphics.wait_visibility()

	if windowSystem == 'aqua':
		app.tk.createcommand('::tk::mac::OpenDocument', openDocument)

	if tkFlavor == 'cocoa':
		# Work around Cocoa Tk 8.6 bug where up/down arrow key presses
		# put invisible entries in Entry fields causing parse errors.
		app.tk.call('bind', 'Entry', '<Up>', '{break}')
		app.tk.call('bind', 'Entry', '<Down>', '{break}')

	# We want to create the reply dialog to capture Python stdout,
	# even if the user doesn't want to see it upon startup.
	# We have to wait to register the reply dialog until after app exists
	# so it will be in the same Tk interpreter.
	dialogs.register(_ReplyDialog.name, _ReplyDialog)
	dialogs.find(_ReplyDialog.name, create=True)	# create but don't display

	versionPrefs = preferences.addCategory("version tracking",
		preferences.HiddenCategory, optDict={"last version": None})
	lastVersion = versionPrefs['last version']
	from chimera import version
	versionPrefs['last version'] = version.release
	if preferences.get(replyobj.REPLY_PREFERENCES,
			   replyobj.SHOW_STATUS_LINE):
		_firstStatus(lastVersion)

	# now safe to create colors
	chimera.initializeGraphics()

	# initialize mouse preferences now, so saved autoSpin will be used
	if windowSystem == "aqua":
		from mousemodes import MULTITOUCH_GESTURES
		kw = {'inherit': [(MULTITOUCH_GESTURES, GENERAL,
			MULTITOUCH_GESTURES, None)]}
	else:
		kw = {}
	preferences.addCategory(MOUSE, mousemodes.MouseCategory, **kw)

	# add custom ribbon cross sections to "Ribbon" menu
	from RibbonStyleEditor import xsection
	xsection.redisplayMenu()

	# load custom presets
	import preset
	preset.get().reloadCustomPresets()

	for func in chimera._postGraphicsFuncs:
		try:
			func()
		except:
			replyobj.reportException(
			  "Error executing post-graphics callback function")
	chimera._postGraphicsFuncs = []
	chimera._postGraphics = True

	# Apply viewing preferences
	from chimera import viewing
	viewing.applyPreferences(app.viewer)

	app.update_idletasks()

	from initprefs import PREF_LABEL, ATOMSPEC_BALLOON
	if preferences.get(PREF_LABEL, ATOMSPEC_BALLOON):
		app.bindAtomSpecBalloon()

	if windowSystem == 'aqua':
		# Make key input work on aqua at start-up without requiring
		# a mouse click in the main window.
		app.focus()
	if windowSystem == 'win32':
		_checkForUnicodeUserName()

        if chimera.opengl_renderer() == 'GDI Generic' and chimera.opengl_version() == '1.1.0':
		msg = ('Graphics driver does not support all Chimera capabilities.\n\n'
                       'Chimera displays popup balloons when hovering over atoms.\n'
                       'These will not appear and selection with the mouse ctrl-click\n'
                       'will not work because your computer has an inadequate OpenGL\n'
                       'graphics driver: Microsoft GDI Generic 1.1.0.\n'
                       'Other Chimera capabilities will work.\n'
                       'You need to install a graphics driver\n'
                       'to make mouse selection and balloons work.')
	        from initprefs import GRAPHICS_CHECK, GRAPHICS_GDI_CHECKED
	        if preferences.get(GRAPHICS_CHECK, GRAPHICS_GDI_CHECKED):
                        # Show message in reply log only.
                        replyobj.info(msg)
                else:
                        # Popup warning dialog only one time.
                        replyobj.warning(msg)
                        preferences.set(GRAPHICS_CHECK, GRAPHICS_GDI_CHECKED, True)

	return extraArgs

_macNaturalScrolling = None
def macNaturalScrolling():
	global _macNaturalScrolling
	if _macNaturalScrolling is None:
		# Assume natural scrolling direction on Mac 10.7 and later.
		# User could change this in system preferences but don't know how to detect that.
		import platform
		_macNaturalScrolling = (platform.system() == 'Darwin' and OSVersion() >= 11)
	return _macNaturalScrolling

def OSVersion():
	import platform
	fields = platform.release().split('.')
	v = None
	if fields:
		try:
			v = int(fields[0])
		except ValueError:
			pass
	return v
				       
def setInitialWindowSize():
	s = app.viewer.pixelScale
	import Midas
	Midas.windowsize([w*s for w in app._initialSize])
	del app._initialSize

# General preferences callback functions
from initprefs import _setAtomspecBalloon
def _setToolbarSide(o):
	if app:
		app._setToolbarSide(o)
def _setFullscreen(o):
	fullscreen = o.get()
	if app:
		app._setFullscreen(fullscreen)
	else:
		chimera.fullscreen = fullscreen

def _setInitialWindowSize(o):
	ws = preferences.getOption(GENERAL, FIXED_SIZE)
	ui = ws.ui()
	if not ui:
		return
	width = app.graphics.winfo_width()
	height = app.graphics.winfo_height()
	if o.get():
		ui.enable()
		preferences.set(GENERAL, FIXED_SIZE, (width, height))
	else:
		ui.disable()
		preferences.set(INITIAL_SIZE, WINDOW_SIZE, (width, height))

def _initializeGeneralPreferences():
	# open dialog starts in startup directory except on Windows/Mac
	if sys.platform in ['win32', 'darwin']:
		startup_dir_default = Tk.YES
	else:
		startup_dir_default = Tk.NO
	# all callbacks can not refer to app directly
	generalPreferences = {
		COMPACT_OPENSAVE:
			(tkoptions.BooleanOption, Tk.NO, None, { "balloon":
			'Show only last two filesystem browsers columns\n'
			'at a time, or show all'
			}),
		CONFIRM_OVERWRITE:
			(tkoptions.BooleanOption, Tk.YES, None, { "balloon":
			'Confirm saving to an existing file chosen\n'
			'from a file browser'
			}),
		CONFIRM_EXIT:
			(ConfirmQuitOption, "conditional", None),
		PATH_STYLE:
			(PathStyleOption, PATH_NEXT, None),
		STARTUP_DIRECTORY:
			(tkoptions.BooleanOption, startup_dir_default, None),
		FULLSCREEN_GRAPHICS:
			(tkoptions.BooleanOption, chimera.fullscreen,
				_setFullscreen, { "balloon":
				"Make graphics window cover the whole screen"}),
		DEBUG_OPENGL:
			(tkoptions.BooleanOption, False, None),
		UPDATE_CHECK_INTERVAL:
			(UpdateIntervalOption, 15, None),
		INITIAL_WINDOW_SIZE: 
			(InitialWindowSizeOption, 0, _setInitialWindowSize),
		FIXED_SIZE: 
			(WindowSizeOption, [512, 384], None, { "min": 1 }),
		DIALOG_PLACEMENT:
			(tkoptions.BooleanOption, True, None),
	}
	if Tk.TkVersion <= 8.4:
		kw = generalPreferences[FULLSCREEN_GRAPHICS][3]
		kw["balloon"] += "\n(Microsoft Windows only)"
		if windowSystem != 'win32':
			kw["state"] = Tk.DISABLED
	generalPreferencesOrder = [
		CONFIRM_EXIT, PATH_STYLE,
		FULLSCREEN_GRAPHICS, DIALOG_PLACEMENT,
		CONFIRM_OVERWRITE, COMPACT_OPENSAVE, STARTUP_DIRECTORY,
		DEBUG_OPENGL, UPDATE_CHECK_INTERVAL,
		INITIAL_WINDOW_SIZE, FIXED_SIZE,
	]
	if windowSystem == 'aqua':
		sam = lambda opt: showAquaMenus(opt.get())
		generalPreferences[AQUA_MENUS] = (tkoptions.BooleanOption,
						  Tk.YES, sam)
		generalPreferencesOrder.append(AQUA_MENUS)
	preferences.register(GENERAL, generalPreferences)
	preferences.setOrder(GENERAL, generalPreferencesOrder)
	if preferences.get(GENERAL, INITIAL_WINDOW_SIZE) == 0:
		kw = generalPreferences[FIXED_SIZE][3]
		kw["state"] = Tk.DISABLED

def _initializeDialogs():
	# we want to create preferences dialog so that the preferences
	# variables exist
	dialogs.register("preferences", preferences.showPreferencesPanel)

	dialogs.register(_InspectDialog.name, _InspectDialog)
	dialogs.register(_OnVersionDialog.name, _OnVersionDialog)
	dialogs.register(_SelAtomSpecDialog.name, _SelAtomSpecDialog)
	dialogs.register(_SelNamePromptDialog.name, _SelNamePromptDialog)
	dialogs.register(SeqSelDialog.name, SeqSelDialog)
	dialogs.register(exportDialog.name, exportDialog.ExportDialog)
	dialogs.register(publishDialog.name, publishDialog.PublishDialog)
	dialogs.register(ColorActionDialog.name, ColorActionDialog)

	dialogs.register("Confirm Exit", _confirmExit)
	dialogs.register("color editor", _colorEditor)
	#dialogs.register("Lens Inspector", LensInspectCB)

from chimera.threadq import runThread

#
# Next few functions are for handling COM servers in Chimera.
# There seems to be a problem between COM and Tkinter where
# COM dispatched messages are executed in a context (thread?) where
# accessing Tk objects causes the Python process to hang.
# We can't quite use the thread code above since we don't start
# a new thread, but the code is similar.
#
_COMFactories = []
_COMHandler = None
_COMCallbacks = []

def _initializeCOM():
	try:
		import pythoncom
	except ImportError:
		return
	pythoncom.CoInitialize()
	chimera.triggers.addHandler(chimera.APPQUIT, _finishCOM, None)

def _finishCOM(trigger, closure, ignore):
	import pythoncom
	from win32com.server.factory import RevokeClassFactories
	global _COMFactories, _COMHandler
	if _COMHandler:
		chimera.triggers.deleteHandler("check for changes", _COMHandler)
		_COMHandler = None
	for factories in _COMFactories:
		RevokeClassFactories(factories)
	_COMFactories = []
	pythoncom.CoUninitialize()

def registerCOMServer(clsidList):
	import pythoncom
	from win32com.server.factory import RegisterClassFactories
	global _COMFactories, _COMHandler
	factories = RegisterClassFactories(clsidList)
	if factories:
		_COMFactories.append(factories)
	if len(_COMFactories) > 0 and _COMHandler is None:
		pythoncom.CoResumeClassObjects()
		_COMHandler = chimera.triggers.addHandler("check for changes",
								_COMPump, None)
	return factories

def deregisterCOMServer(factories):
	import pythoncom
	global _COMFactories, _COMHandler
	_COMFactories.remove(factories)
	if len(_COMFactories) == 0 and _COMHandler is not None:
		chimera.triggers.deleteHandler("check for changes", _COMHandler)
		_COMHandler = None

def addCOMCallback(cb):
	global _COMCallbacks
	_COMCallbacks.append(cb)

def _COMPump(trigger, closure, ignore):
	import pythoncom
	global _COMCallbacks
	for cb in _COMCallbacks:
		try:
			cb()
		except:
			replyobj.reportException("COM callback error")
	_COMCallbacks = []
	try:
		pythoncom.PumpWaitingMessages()
	except:
		#replyobj.reportException("COM PumpWaitingMessage")
		pass

#
# End of COM functions
#

def eventLoop():
	if sys.platform == 'darwin':
		import appleevents
		appleevents.register_apple_event_handler()
	from chimera import update
	update.startFrameUpdate(app)	# start monitoring for data changes
	app.mainloop()

def _restoreSessionCheck(*args):
	from chimera import openModels
	if not openModels.list():
		return
	from chimera.baseDialog import AskYesNoDialog
	dlg = AskYesNoDialog("There are models open."
		"  Close them before restoring the session?", default="Yes")
	if dlg.run(app) == "yes":
		openModels.close(openModels.list())

from SimpleSession import BEGIN_RESTORE_SESSION
chimera.triggers.addHandler(BEGIN_RESTORE_SESSION, _restoreSessionCheck, None)
