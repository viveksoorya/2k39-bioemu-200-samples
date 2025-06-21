# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: midas_ui.py 42378 2022-05-09 23:07:16Z pett $

import chimera
import Tkinter
import Pmw
import os
from chimera import help
from chimera.baseDialog import ModelessDialog
from OpenSave import SaveModeless
from chimera import preferences, tkoptions, selection
import Midas
import time
import midas_text
from chimera.oslParser import OSLSyntaxError

ui = None
uiActive = 0

def showActiveButtons(option):
	global ui
	if ui:
		if option.get():
			ui.createActiveButtons()
		else:
			ui.removeActiveButtons()

def showDisplayedButtons(option):
	global ui
	if ui:
		if option.get():
			ui.createDisplayButtons()
		else:
			ui.removeDisplayButtons()

def showSkipButtons(option):
	global ui
	if ui:
		if option.get():
			ui.createSkipButtons()
		else:
			ui.removeSkipButtons()

def differentAmountButtons(options):
	global ui
	if ui:
		if preferences.get(MIDAS_CATEGORY, ACTIVE_BUTTONS):
			ui.removeActiveButtons()
			ui.createActiveButtons()
		if preferences.get(MIDAS_CATEGORY, DISPLAYED_BUTTONS):
			ui.removeDisplayButtons()
			ui.createDisplayButtons()
		if preferences.get(MIDAS_CATEGORY, SKIP_BUTTONS):
			ui.removeSkipButtons()
			ui.createSkipButtons()

STARTUP_FILES = "Files to read at startup"
SES_MEMORY = "Number of commands to\nremember between sessions"
SKIP_BUTTONS = 'Show skip buttons'
DISPLAYED_BUTTONS = 'Show display buttons'
ACTIVE_BUTTONS = 'Show activation buttons'
NUM_BUTTONS = 'Number of display/activation buttons'
MIDAS_CATEGORY = "Command Line"
_midasPreferencesOrder = [
	STARTUP_FILES, SES_MEMORY, DISPLAYED_BUTTONS, ACTIVE_BUTTONS, SKIP_BUTTONS, NUM_BUTTONS,
]
preferences.register(MIDAS_CATEGORY, {
	STARTUP_FILES: (tkoptions.OrderedFileListOption,
		["~/.chimera/midasrc", ".chmidasrc"], None, {'height': 4}),
	SES_MEMORY: (tkoptions.IntOption, 60, None, {'min': 0}),
	SKIP_BUTTONS: (tkoptions.BooleanOption, False, showSkipButtons),
	DISPLAYED_BUTTONS: (tkoptions.BooleanOption, False, showDisplayedButtons),
	ACTIVE_BUTTONS: (tkoptions.BooleanOption, True, showActiveButtons),
	NUM_BUTTONS: (tkoptions.IntOption, 10, differentAmountButtons),
}, aliases=["Midas"])
preferences.setOrder(MIDAS_CATEGORY, _midasPreferencesOrder)

PREV_COMMANDS = "remembered commands"
prefs = preferences.addCategory("command line gui", preferences.HiddenCategory,
					optDict={PREV_COMMANDS: []})

triggerName = "typed Midas command"
chimera.triggers.addTrigger(triggerName)

class MidasUI:
	"Class for presenting a Midas command line"

	recordLabel = "Command History..."
	hideLabel = "Hide Command Line"
	compactLabel = "Remove duplicate consecutive commands"

	def __init__(self):
		from chimera import tkgui
		self.frame = Tkinter.Frame(tkgui.app)
		self.frame.columnconfigure(1, weight=1)
		help.register(self.frame,
				"UsersGuide/chimerawindow.html#emulator")

		sep = Tkinter.Frame(self.frame, relief='sunken', bd=2)
		sep.grid(row=0, column=0, columnspan=3, sticky='ew')

		self.histDialog = HistoryDialog(self)
		listbox = self.histDialog.listbox.component('listbox')
		import tkFont
		font = tkFont.Font(font=listbox.cget('font'))
		pixels = font.metrics('linespace')
		self.cmd = Pmw.ComboBox(self.frame, fliparrow=True,
			history=False, labelpos='w', label_text="Command:",
			listheight=10*(pixels+4), entry_exportselection=False,
			selectioncommand=self._selCmdCB,
			entryfield_validate=self.histDialog._entryModified,
			scrolledlist_items=[self.recordLabel, self.hideLabel, self.compactLabel])
		self.cmd.grid(row=1, column=0, columnspan=3, sticky='ew')
		self.histDialog.populate()

		chimera.tkgui.addKeyboardFunc(self.graphicsKeyboardCB)

		entry = self.cmd.component('entry')
		entry.bind('<Up>', self.histDialog.up)
		entry.bind('<Shift-Up>', self.histDialog.up)
		entry.bind('<Control-p>', self.histDialog.up)
		entry.bind('<Control-P>', self.histDialog.up)
		entry.bind('<Down>', self.histDialog.down)
		entry.bind('<Shift-Down>', self.histDialog.down)
		entry.bind('<Control-n>', self.histDialog.down)
		entry.bind('<Control-N>', self.histDialog.down)
		entry.bind('<Map>', self.monitorSel)
		entry.bind('<Unmap>', self.unmonitorSel)
		entry.bind('<Control-u>', self.cmdClear)
		entry.bind('<Return>', self.processCommand)

		self.activeButtonsFrame = None
		if preferences.get(MIDAS_CATEGORY, ACTIVE_BUTTONS):
			self.createActiveButtons()
		self.displayButtonsFrame = None
		if preferences.get(MIDAS_CATEGORY, DISPLAYED_BUTTONS):
			self.createDisplayButtons()
		self.skipButtonsFrame = None
		if preferences.get(MIDAS_CATEGORY, SKIP_BUTTONS):
			self.createSkipButtons()

		self.show()

		# read startup files
		global ui
		ui = self
		for sf in preferences.get(MIDAS_CATEGORY, STARTUP_FILES):
			from OpenSave import tildeExpand
			sf = tildeExpand(sf)
			if os.path.exists(sf):
				midas_text.message(
				   "Processing Midas start-up file %s" % sf)
				midas_text.processCommandFile(sf)

	def graphicsKeyboardCB(self, event):
		cmd = self.cmd.component('entry')
		index = cmd.index
		char = event.char
		if not char:
			sym = event.keysym
			if sym == "Up":
				self.histDialog.up(event)
			elif sym == "Down":
				self.histDialog.down(event)
			elif sym == "Left":
				cmd.icursor(index("insert")-1)
			elif sym == "Right":
				cmd.icursor(index("insert")+1)
			else:
				return
		elif char == '\r':
			self.processCommand(None)
		elif char == '\b':
			if cmd.selection_present():
				cmd.delete(index("sel.first"),
							index("sel.last"))
			else:
				cmd.delete(index("insert")-1)
			self.histDialog._entryModified()
		elif char == '\016': # control-n
			self.histDialog.down(event)
		elif char == '\020': # control-p
			self.histDialog.up(event)
		else:
			if cmd.selection_present():
				cmd.delete(index("sel.first"),
							index("sel.last"))
			cmd.insert("insert", char)
			self.histDialog._entryModified()
		cmd.focus()

	def createSkipButtons(self):

		if self.skipButtonsFrame:
			return

		self.skipVars = []
		self.skipButtons = []
		self.skipButtonsFrame = buttonFrame = Tkinter.Frame(self.frame)
		buttonFrame.grid(row=2, column=0, columnspan=3, sticky='ew')
		Tkinter.Label(buttonFrame, text="Skip in previous/next: ").pack(
			side='left')
		for id in range(preferences.get(MIDAS_CATEGORY, NUM_BUTTONS)):
			state = 'disabled'
			models = chimera.openModels.list(id)
			models = [m for m in models if not isinstance(m, chimera.PseudoBondGroup)]
			if models:
				state = 'normal'

			var = Tkinter.IntVar(self.frame)
			self.skipVars.append(var)
			var.set(False)
			skipButton = Tkinter.Checkbutton(buttonFrame,
							 variable=var, state=state, text="%d" % id)
			skipButton.pack(side='left')
			self.skipButtons.append(skipButton)
		self.skipOpenModelsHandler = chimera.triggers.addHandler('OpenModels', self.skipHandler, None)

	def removeSkipButtons(self):
		f = self.skipButtonsFrame 
		if f is None:
			return
		f.destroy()
		self.skipButtonsFrame = None
		self.skipVars = []
		self.skipButtons = []
		chimera.triggers.deleteHandler('OpenModels', self.skipOpenModelsHandler)

	def createDisplayButtons(self):

		if self.displayButtonsFrame:
			return

		self.displayVars = []
		self.displayButtons = []
		self.displayButtonsFrame = buttonFrame = Tkinter.Frame(self.frame)
		buttonFrame.grid(row=3, column=0, columnspan=3, sticky='ew')
		Tkinter.Label(buttonFrame, text="Displayed models: ").pack(
			side='left')
		for id in range(preferences.get(MIDAS_CATEGORY, NUM_BUTTONS)):
			state = 'disabled'
			display = 0
			models = chimera.openModels.list(id)
			models = [m for m in models if not isinstance(m, chimera.PseudoBondGroup)]
			if models:
				state = 'normal'
				if models[0].display:
					display = 1

			var = Tkinter.IntVar(self.frame)
			self.displayVars.append(var)
			var.set(display)
			dispButton = Tkinter.Checkbutton(buttonFrame,
							 variable=var, state=state, text="%d" % id,
							 command=lambda x=id, s=self: s.displayButtonPush(x))
			dispButton.pack(side='left')
			self.displayButtons.append(dispButton)
		self.allDisplayVar = Tkinter.IntVar(self.frame)
		self.allDisplayVar.set(0)
		allButton = Tkinter.Checkbutton(buttonFrame, text="All",
							variable=self.allDisplayVar,
							command=self.allDisplayedButtonPush)
		allButton.pack(side='left')
		Tkinter.Button(buttonFrame, text="Next", command=self.nextDisplayedButtonPush).pack(side='left')
		Tkinter.Button(buttonFrame, text="Previous", command=self.prevDisplayedButtonPush).pack(side='left')
			
		self.displayModelHandler = chimera.triggers.addHandler('Model', self.displayedHandler, None)
		self.displayOpenModelsHandler = chimera.triggers.addHandler('OpenModels', self.displayedHandler, None)

	def removeDisplayButtons(self):
		f = self.displayButtonsFrame 
		if f is None:
			return
		f.destroy()
		self.displayButtonsFrame = None
		self.displayVars = []
		self.displayButtons = []
		chimera.triggers.deleteHandler('Model', self.displayModelHandler)
		chimera.triggers.deleteHandler('OpenModels', self.displayOpenModelsHandler)

	def skipHandler(self, triggerName, myData, trigData):
		if 'model list change' not in trigData.reasons:
			return
		model_limit = preferences.get(MIDAS_CATEGORY, NUM_BUTTONS)
		models = chimera.openModels.list()
		visited = {}
		for model in models:
			if visited.has_key(model.id) \
			or model.id not in range(model_limit) \
			or isinstance(model, chimera.PseudoBondGroup):
				continue
			visited[model.id] = ()
			self.skipButtons[model.id]['state'] = 'normal'
		for id in range(model_limit):
			if visited.has_key(id):
				continue
			self.skipVars[id].set(False)
			self.skipButtons[id]['state'] = 'disabled'

	def displayedHandler(self, triggerName, myData, trigData):
		if 'display changed' not in trigData.reasons \
		and 'model list change' not in trigData.reasons:
			return
		model_limit = preferences.get(MIDAS_CATEGORY, NUM_BUTTONS)
		models = chimera.openModels.list()
		visited = {}
		for model in models:
			if visited.has_key(model.id) \
			or model.id not in range(model_limit) \
			or isinstance(model, chimera.PseudoBondGroup):
				continue
			visited[model.id] = ()
			self.displayButtons[model.id]['state'] = 'normal'
			self.displayVars[model.id].set(model.display)
		for id in range(model_limit):
			if visited.has_key(id):
				continue
			self.displayVars[id].set(0)
			self.displayButtons[id]['state'] = 'disabled'

	def allDisplayedButtonPush(self):
		models = chimera.openModels.list()
		disp = self.allDisplayVar.get()
		for m in models:
			m.display = disp
				
	def displayButtonPush(self, model_id):
		for m in chimera.openModels.list(model_id):
			m.display = not m.display

	def createActiveButtons(self):

		if self.activeButtonsFrame:
			return

		self.activeVars = []
		self.activeButtons = []
		self.activeButtonsFrame = buttonFrame = Tkinter.Frame(self.frame)
		buttonFrame.grid(row=4, column=0, columnspan=3, sticky='ew')
		Tkinter.Label(buttonFrame, text="Active models: ").pack(
			side='left')
		for id in range(preferences.get(MIDAS_CATEGORY, NUM_BUTTONS)):
			state = 'disabled'
			active = 0
			models = chimera.openModels.list(id)
			models = filter(lambda m: not isinstance(m,
								 chimera.PseudoBondGroup), models)
			if models:
				state = 'normal'
				if models[0].openState.active:
					active = 1

			var = Tkinter.IntVar(self.frame)
			self.activeVars.append(var)
			var.set(active)
			actButton = Tkinter.Checkbutton(buttonFrame,
							variable=var, state=state, text="%d" % id,
							command=lambda x=id, s=self: s.activeButtonPush(x))
			actButton.pack(side='left')
			self.activeButtons.append(actButton)
		self.allActiveVar = Tkinter.IntVar(self.frame)
		self.allActiveVar.set(0)
		allButton = Tkinter.Checkbutton(buttonFrame, text="All",
							     variable=self.allActiveVar,
							     command=self.allActiveButtonPush)
		allButton.pack(side='left')
		Tkinter.Button(buttonFrame, text="Next", command=self.nextActiveButtonPush).pack(side='left')
		Tkinter.Button(buttonFrame, text="Previous", command=self.prevActiveButtonPush).pack(side='left')
			
		self.activeOpenStateHandler = chimera.triggers.addHandler('OpenState', self.activeHandler, None)
		self.activeOpenModelsHandler = chimera.triggers.addHandler('OpenModels', self.activeHandler, None)

	def removeActiveButtons(self):
		f = self.activeButtonsFrame 
		if f is None:
			return
		f.destroy()
		self.activeButtonsFrame = None
		self.activeVars = []
		self.activeButtons = []
		chimera.triggers.deleteHandler('OpenState', self.activeOpenStateHandler)
		chimera.triggers.deleteHandler('OpenModels', self.activeOpenModelsHandler)
		
	def activeHandler(self, triggerName, myData, trigData):
		if 'active change' not in trigData.reasons \
		and 'model list change' not in trigData.reasons:
			return
		model_limit = preferences.get(MIDAS_CATEGORY, NUM_BUTTONS)
		models = chimera.openModels.list()
		visited = {}
		for model in models:
			if visited.has_key(model.id) \
			or model.id not in range(model_limit) \
			or isinstance(model, chimera.PseudoBondGroup):
				continue
			visited[model.id] = ()
			self.activeButtons[model.id]['state'] = 'normal'
			self.activeVars[model.id].set(model.openState.active)
		for id in range(model_limit):
			if visited.has_key(id):
				continue
			self.activeVars[id].set(0)
			self.activeButtons[id]['state'] = 'disabled'

	def allActiveButtonPush(self):
		from midas_text import allModelSelect
		if self.allActiveVar.get():
			allModelSelect(True)
		else:
			allModelSelect(False)
				
	def activeButtonPush(self, which):
		# used to just emulate 'select' command, but select won't
		# operate on non-molecule models, so changed it.
		from midas_text import allModelSelect
		allModelSelect(self.activeVars[which].get() == 1, id=which)

	def _activateLowest(self, models):
		minID = min([m.id for m in models])
		for m in self.filterSkipped(chimera.openModels.list()):
			m.openState.active = m.id == minID
			if m.openState.active:
				from chimera import replyobj
				replyobj.status(m.name, secondary=True)

	def _activateHighest(self, models):
		maxID = max([m.id for m in models])
		for m in self.filterSkipped(chimera.openModels.list()):
			m.openState.active = m.id == maxID
			if m.openState.active:
				from chimera import replyobj
				replyobj.status(m.name, secondary=True)

	def _displayLowest(self, models):
		minID = min([m.id for m in models])
		for m in self.filterSkipped(chimera.openModels.list()):
			m.display = m.id == minID
			if m.display:
				from chimera import replyobj
				replyobj.status(m.name, secondary=True)

	def _displayHighest(self, models):
		maxID = max([m.id for m in models])
		for m in self.filterSkipped(chimera.openModels.list()):
			m.display = m.id == maxID
			if m.display:
				from chimera import replyobj
				replyobj.status(m.name, secondary=True)

	def filterSkipped(self, models):
		if not self.skipButtonsFrame:
			return models
		numButtons =  preferences.get(MIDAS_CATEGORY, NUM_BUTTONS)
		return [m for m in models if m.id < numButtons and not self.skipVars[m.id].get()]

	def nextActiveButtonPush(self):
		models = self.filterSkipped(chimera.openModels.list())
		if not models:
			return
		allIDs = set([m.id for m in models])
		if len(allIDs) == 1:
			for m in models:
				m.openState.active = True
			return
		# if multiple active, make only lowest active
		activeIDs = set([m.id for m in models if m.openState.active])
		if len(activeIDs) != 1:
			self._activateLowest(models)
			return
		activeID = list(activeIDs)[0]
		higherModels = [m for m in models if m.id > activeID]
		if not higherModels:
			self._activateLowest(models)
			return
		self._activateLowest(higherModels)

	def prevActiveButtonPush(self):
		models = self.filterSkipped(chimera.openModels.list())
		if not models:
			return
		allIDs = set([m.id for m in models])
		if len(allIDs) == 1:
			for m in models:
				m.openState.active = True
			return
		# if multiple active, make only lowest active
		activeIDs = set([m.id for m in models if m.openState.active])
		if len(activeIDs) != 1:
			self._activateLowest(models)
			return
		activeID = list(activeIDs)[0]
		lowerModels = [m for m in models if m.id < activeID]
		if not lowerModels:
			self._activateHighest(models)
			return
		self._activateHighest(lowerModels)

	def nextDisplayedButtonPush(self):
		models = self.filterSkipped(chimera.openModels.list())
		if not models:
			return
		allIDs = set([m.id for m in models])
		if len(allIDs) == 1:
			for m in models:
				m.display = True
			return
		# if multiple displayed, make only lowest displayed
		displayedIDs = set([m.id for m in models if m.display])
		if len(displayedIDs) != 1:
			self._displayLowest(models)
			return
		displayedID = list(displayedIDs)[0]
		higherModels = [m for m in models if m.id > displayedID]
		if not higherModels:
			self._displayLowest(models)
			return
		self._displayLowest(higherModels)

	def prevDisplayedButtonPush(self):
		models = self.filterSkipped(chimera.openModels.list())
		if not models:
			return
		allIDs = set([m.id for m in models])
		if len(allIDs) == 1:
			for m in models:
				m.display = True
			return
		# if multiple displayed, make only lowest displayed
		displayedIDs = set([m.id for m in models if m.display])
		if len(displayedIDs) != 1:
			self._displayLowest(models)
			return
		displayedID = list(displayedIDs)[0]
		lowerModels = [m for m in models if m.id < displayedID]
		if not lowerModels:
			self._displayHighest(models)
			return
		self._displayHighest(lowerModels)

	def hide(self):
		global uiActive
		if not uiActive:
			return
		uiActive = 0
		from chimera import tkgui
		tkgui.app.allowResize = False
		self.frame.pack_forget()
		self.frame.after(500,
			lambda app=tkgui.app, *args: setattr(app, 'allowResize', True))

	def show(self):
		global uiActive
		if uiActive:
			return
		uiActive = 1
		from chimera import tkgui
		tkgui.app.allowResize = False
		self.frame.pack(expand=False, side='bottom', fill='x',
						before=tkgui.app.toolPane)
		self.cmd.component('entry').focus()
		self.frame.after(500,
			lambda app=tkgui.app, *args: setattr(app, 'allowResize', True))

	def monitorSel(self, event):
		self._msHandler = chimera.triggers.addHandler(
				"selection changed", self._selChanged, None)

	def unmonitorSel(self, event):
		chimera.triggers.deleteHandler("selection changed",
							self._msHandler)

	def _selChanged(self, trigName, myData, trigData):
		ats = selection.currentAtoms()
		if len(ats) != 1:
			return
		entry = self.cmd.component('entry')
		text = entry.get()
		pre = True
		for i in range(len(text)):
			c = text[i]
			if c == '+' and pre and (i == len(text)-1
							or text[i+1].isspace()):
				break
			pre = c.isspace()
		else:
			return
		entry.delete(i)
		entry.insert(i, ats[0].oslIdent())

	def _selCmdCB(self, sel):
		if sel == self.recordLabel:
			self.histDialog.enter()
			self.cmd.setentry("")
		elif sel == self.hideLabel:
			self.hide()
			self.cmd.setentry("")
		elif sel == self.compactLabel:
			self.cmd.setentry("")
			oldCmds = prefs[PREV_COMMANDS]
			prev = None
			newCmds = []
			for oc in oldCmds:
				if oc == prev:
					continue
				newCmds.append(oc)
				prev = oc
			prefs[PREV_COMMANDS] = newCmds
			self.histDialog.populate()

	def processCommand(self, event):
		self.cmd.selection_range('0', 'end')
		text = self.cmd.get()
		midas_text.clearError()

		for cmdText in text.split("\n"):
			if not cmdText:
				continue
			self.histDialog.add(cmdText)
			try:
				midas_text.makeCommand(cmdText)
				chimera.triggers.activateTrigger(triggerName, cmdText)
			except (Midas.MidasError, OSLSyntaxError), v:
				from chimera import triggers, COMMAND_ERROR
				triggers.activateTrigger(COMMAND_ERROR, (cmdText, v))
				from chimera.replyobj import convertToPrintable
				midas_text.error(convertToPrintable(v))
				break

	def cmdClear(self, event=None):
		self.cmd.component('entry').delete('0', 'end')

	def cmdReplace(self, cmd):
		entry = self.cmd.component('entry')
		entry.delete('0', 'end')
		entry.insert('0', cmd)

class HistoryDialog(ModelessDialog):
	title = "Command History"
	buttons = ("Record...", "Execute", "Delete", "Copy", "Close")
	help = "UsersGuide/history.html"

	def __init__(self, controller):
		# make dialog hidden initially
		self.controller = controller
		ModelessDialog.__init__(self)
		self.Close()
		self._searchCache = None
		self._ignoreNextModified = False

	def fillInUI(self, parent):
		self.listbox = Pmw.ScrolledListBox(parent,
				dblclickcommand= self.execute,
				selectioncommand=self.select,
				listbox_exportselection=0,
				listbox_selectmode='extended')
		self.listbox.pack(expand='yes', fill='both')
		self.listbox.select_set('end')
		self.recordDialog = None

	def _focusCB(self, event=None):
		self.controller.cmd.focus()
		self._toplevel.tkraise()

	def add(self, item):
		self.listbox.insert('end', item)
		self.listbox.see('end')
		self.listbox.select_clear(0, 'end')
		self.listbox.select_set('end')
		commands = list(self.listbox.get())
		last8 = commands[-8:]
		last8.reverse()
		c = self.controller
		c.cmd.setlist(last8+[c.recordLabel, c.hideLabel, c.compactLabel])
		numRemember = preferences.get(MIDAS_CATEGORY, SES_MEMORY)
		if numRemember:
			prefs[PREV_COMMANDS] = commands[-numRemember:]
		else:
			prefs[PREV_COMMANDS] = []

	def populate(self):
		# not done during __init__ to avoid callback to ComboBox
		# which hasn't been initialized yet (uses our font metrics!)
		prevCommands = prefs[PREV_COMMANDS]
		self.listbox.setlist(prevCommands)
		self.listbox.select_set('end')
		self.select()
		self.controller.cmd.selection_range('0', 'end')
		last8 = prevCommands[-8:]
		last8.reverse()
		c = self.controller
		c.cmd.setlist(last8+[c.recordLabel, c.hideLabel, c.compactLabel])
		cursel = self.listbox.curselection()
		if cursel:
			self.listbox.see(cursel)

	def select(self):
		sels = self.listbox.getcurselection()
		if len(sels) != 1:
			return
		self.controller.cmdReplace(sels[0])

	def copy(self):
		text = "\n".join(self.listbox.getcurselection()) + '\n'
		w = self.uiMaster()
		w.clipboard_clear()
		w.clipboard_append(text)

	Copy = copy

	def delete(self):
		sel = set([int(i) for i in self.listbox.curselection()])
		prevCommands = prefs[PREV_COMMANDS]
		prefs[PREV_COMMANDS] = [prevCommands[i]
			for i in range(len(prevCommands)) if i not in sel]
		self.populate()

	Delete = delete

	def execute(self):
		for cmd in self.listbox.getcurselection():
			self.controller.cmdReplace(cmd)
			self.controller.processCommand(None)

	Execute = execute

	def record(self):
		if not self.recordDialog:
			self.recordDialog = RecordDialog(self)
		self.recordDialog.enter()

	Record = record

	def up(self, event=None):
		sels = self.listbox.curselection()
		if len(sels) != 1:
			return
		sel = sels[0]
		if isinstance(sel, basestring):
			sel = int(sel)
		curText = self.controller.cmd.get()
		matchAgainst = None
		self._ignoreNextModified = False
		if event and event.state & 0x0001:
			# shift key
			if self._searchCache is None:
				words = curText.strip().split()
				if words:
					matchAgainst = words[0]
					self._searchCache = matchAgainst
			else:
				matchAgainst = self._searchCache
			self._ignoreNextModified = True
		if matchAgainst:
			while sel > 0:
				if self.listbox.get(sel-1).startswith(matchAgainst):
					break
				sel -= 1
		if sel == 0:
			return

		self.listbox.select_clear(0, 'end')
		self.listbox.select_set(sel - 1)
		newText = self.listbox.get(sel - 1)
		self.controller.cmdReplace(newText)
		if curText == newText:
			self.up(event)
		if not self._ignoreNextModified:
			self._searchCache = None

	def down(self, event=None):
		sels = self.listbox.curselection()
		if len(sels) != 1:
			return
		sel = sels[0]
		if isinstance(sel, basestring):
			sel = int(sel)
		curText = self.controller.cmd.get()
		matchAgainst = None
		self._ignoreNextModified = False
		if event and event.state & 0x0001:
			# shift key
			if self._searchCache is None:
				words = curText.strip().split()
				if words:
					matchAgainst = words[0]
					self._searchCache = matchAgainst
			else:
				matchAgainst = self._searchCache
			self._ignoreNextModified = True
		if matchAgainst:
			last = self.listbox.index('end') - 1
			while sel < last:
				if self.listbox.get(sel+1).startswith(matchAgainst):
					break
				sel += 1
		if sel == self.listbox.index('end') - 1:
			return
		self.listbox.select_clear(0, 'end')
		self.listbox.select_set(sel + 1)
		newText = self.listbox.get(sel + 1)
		self.controller.cmdReplace(self.listbox.get(sel + 1))
		if curText == newText:
			self.down(event)
		if not self._ignoreNextModified:
			self._searchCache = None

	def _entryModified(self, *args):
		if self._ignoreNextModified:
			self._ignoreNextModified = False
		else:
			if self._searchCache is not None:
				self._searchCache = None
				self.listbox.select_clear(0, 'end')
				self.listbox.select_set(self.listbox.index('end') - 1)
		return Pmw.OK

class RecordDialog(SaveModeless):
	title = "Command Recording"
	buttons = ("OK", "Cancel")

	def __init__(self, histDialog):
		# make dialog hidden initially
		self.histDialog = histDialog
		SaveModeless.__init__(self, clientPos='s', clientSticky="ew",
						initialfile="chimera.cmd")

	def fillInUI(self, parent):
		SaveModeless.fillInUI(self, parent)
		self.clientArea.columnconfigure(0, weight=1)
		self.clientArea.columnconfigure(1, weight=1)
		self.amount = Pmw.RadioSelect(self.clientArea,
			orient='vertical', buttontype='radiobutton',
			labelpos='w', pady=0, label_text="Record")
		self.amount.add("selected commands")
		self.amount.add("all commands")
		self.amount.invoke(1)
		self.amount.grid(row=0, column=0)
		self.commandStyle = Pmw.RadioSelect(self.clientArea,
			orient='vertical', command=self._adjustFileName,
			buttontype='radiobutton', labelpos='w', pady=0,
			label_text="Record as")
		self.commandStyle.add("Chimera commands")
		self.commandStyle.add("Python commands")
		self.commandStyle.invoke(0)
		self.commandStyle.grid(row=1, column=0)
		self.appending = Tkinter.IntVar(parent)
		self.appending.set(0)
		Tkinter.Checkbutton(self.clientArea, variable=self.appending,
			text="Append to file").grid(row=0, column=1, rowspan=2)

	def Apply(self, event=None):
		paths = self.getPaths()
		if not paths:
			raise ValueError, "No filename given for recording"
		fname = paths[0]
		if self.appending.get():
			mode = "a"
		else:
			mode = "w"
		from OpenSave import osOpen
		file = osOpen(fname, mode)
		writePython = self.commandStyle.getvalue()[:6]=="Python"
		if writePython:
			file.write("from chimera import runCommand\n")
		if self.amount.getvalue()[:3] == "all":
			cmds = self.histDialog.listbox.get()
		else:
			cmds = self.histDialog.listbox.getvalue()
		for cmd in cmds:
			if writePython:
				file.write("runCommand(" + repr(cmd) + ")\n")
			else:
				file.write(cmd + "\n")
		file.close()

	def _adjustFileName(self, butName):
		if butName == "Chimera commands":
			want = ".cmd"
			alt = ".py"
		else:
			want = ".py"
			alt = ".cmd"
		entered = self.millerBrowser.fileFaves.get().strip()
		if entered.endswith(alt):
			new = entered[:0-len(alt)] + want
			self.millerBrowser.fileFaves.component(
						'entryfield').setentry(new)

def createUI():
	global ui
	if ui:
		ui.show()
	else:
		MidasUI()

def hideUI():
	if ui:
		ui.hide()
