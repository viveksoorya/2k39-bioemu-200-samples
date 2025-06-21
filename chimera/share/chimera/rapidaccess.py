# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

def initialRapidAccess():
	def _later(trigName, atStartup, trigData):
		from tkgui import app
		from chimera import openModels
		ra = app.rapidAccess
		if not openModels.list() and (ra._toolLookup or ra.dataHistory.history):
			if not prefs[EVER_SHOWN]:
				ra.showHelp()
			ra.shown = True
			if atStartup:
				# work around Tk bug
				app.toolbar._gridHistory.discard(app.graphics)
		from triggerSet import ONESHOT
		return ONESHOT
	from chimera import triggers, CLOSE_SESSION
	triggers.addHandler('new frame', _later, True)
	def _afterCloseSession(*args):
		# allow models to actually be closed...
		triggers.addHandler('new frame', _later, False)
	triggers.addHandler(CLOSE_SESSION, _afterCloseSession, None)
	from tkgui import app
	ra = app.rapidAccess
	from Animate.Scenes import scenes
	for trigName in ('scene_append', 'scene_remove', 'scene_update'):
		scenes.triggerset.addHandler(trigName, ra.drawScenes, None)
	from Midas import ADD_POSITIONS, REMOVE_POSITIONS
	triggers.addHandler(ADD_POSITIONS, ra._positionsChanged, None)
	triggers.addHandler(REMOVE_POSITIONS, ra._positionsChanged, None)

from chimera import registerPostGraphicsFunc
registerPostGraphicsFunc(initialRapidAccess)

import Tkinter
class RapidAccess(Tkinter.Frame, object):

	backgroundColor = 'steel blue'
	helpBackgroundColor = 'sky blue'
	textColor = 'light gray'
	largeTextFactor = 1.5
	sceneWeight = 4
	selWeight = 1

	def __init__(self, *args, **kw):
		self._shown = False
		self._keepShown = False

		if 'bg' not in kw and 'background' not in kw:
			kw['bg'] = self.backgroundColor
		Tkinter.Frame.__init__(self, *args, **kw)
		self.grid_propagate(0)
		self.rowconfigure(0, weight=1)
		self.toolArea = Tkinter.Frame(self, bg=self.backgroundColor, bd=1,
			relief='solid')
		self.toolArea.grid(row=0, column=0, sticky="nsw")
		trow = 0
		self.toolArea.rowconfigure(trow, weight=1)
		self.toolIconArea = Tkinter.Frame(self.toolArea,
			bg=self.backgroundColor)
		self.toolIconArea.grid(row=trow, column=0, sticky='nsew')
		self.toolIconRow = trow
		trow += 1
		self.toolIconArea.columnconfigure(0, weight=1)
		self.toolIconArea.columnconfigure(1, weight=1)
		self.toolIconCol1 = Tkinter.Frame(self.toolIconArea,
						bg=self.backgroundColor)
		self.toolIconCol1.grid(row=0, column=0, sticky='n')
		self.toolIconCol2 = Tkinter.Frame(self.toolIconArea,
						bg=self.backgroundColor)
		self.toolIconCol2.grid(row=0, column=1, sticky='n')
		self._toolLookup = {}
		self.toolIconArea.rowconfigure(0, weight=1)
		self.noToolIconsLabel = Tkinter.Label(self.toolIconArea,
			text="Tool Icons", bg=self.backgroundColor, fg=self.textColor)
		from CGLtk.Font import shrinkFont
		shrinkFont(self.noToolIconsLabel, fraction=self.largeTextFactor)
		self.noToolIconsLabel.grid(row=0, column=0, columnspan=2, sticky='nsew')
		self.iconDivider = Tkinter.Frame(self.toolArea, bg="black",
			height="1p")
		self.iconDivider.grid(row=trow, column=0, sticky="ew")
		trow += 1
		from chimera import dialogs
		Tkinter.Button(self.toolArea, command=lambda dialogs=dialogs:
			dialogs.display("preferences").setCategoryMenu("Tools"),
			text="Add Tool Icon...", highlightbackground=self.backgroundColor
			).grid(row=trow, column=0)
		trow += 1
		self.activeToolsFrame = Tkinter.LabelFrame(self.toolArea,
			text="Active Dialogs", bg=self.backgroundColor)
		shrinkFont(self.activeToolsFrame)
		self.activeToolsFrame.columnconfigure(0, weight=1)
		self.activeToolsFrame.grid(row=trow, column=0, sticky="nsew")
		self.activeToolsRow = trow
		trow += 1
		self.noActiveToolsLabel = Tkinter.Label(self.activeToolsFrame,
			text="None", bg=self.backgroundColor, fg=self.textColor)
		self.noActiveToolsLabel.grid(sticky="nsew")
		self._dialogInfo = {}
		from baseDialog import triggers, TOOL_DISPLAY_CHANGE
		triggers.addHandler(TOOL_DISPLAY_CHANGE, self._dialogChange, None)
		from dialogs import activeDialogs
		from extension import manager
		currentDialogs = set(activeDialogs())
		currentDialogs.update(manager.instances)
		for cd in currentDialogs:
			self._dialogChange(dialogInfo=(cd, True))
		self.helpButton = Tkinter.Button(self.toolArea, command=self.showHelp,
			text="Show Help", highlightbackground=self.backgroundColor)
		self.helpButton.grid(row=trow, column=0)

		self.columnconfigure(1, weight=1)
		self.sceneSelHelpArea = Tkinter.Frame(self)
		self.sceneSelHelpArea.grid(row=0, column=1, sticky="nsew")
		srow = 0
		Tkinter.Frame(self.sceneSelHelpArea, bg="black",
			height="1p").grid(row=srow, column=0, sticky="ew")
		srow += 1
		self.sceneSelHelpArea.columnconfigure(0, weight=1)
		self.sceneArea = Tkinter.Frame(self.sceneSelHelpArea)
		self.sceneArea.columnconfigure(0, weight=1)
		self.sceneArea.rowconfigure(0, weight=1)
		self.sceneRow = srow
		self.sceneArea.grid(row=self.sceneRow, column=0, sticky="nsew")
		srow += 1
		self.sceneSelHelpArea.rowconfigure(self.sceneRow,
						weight=self.sceneWeight)

		self.sceneSelDivider = Tkinter.Frame(self.sceneSelHelpArea, bg="black",
			height="1p")
		self.helpRow = srow
		self.sceneSelDivider.grid(row=self.helpRow, column=0, sticky="ew")
		srow += 1

		# positions; only shown when some exist
		self.positionArea = Tkinter.Frame(self.sceneSelHelpArea,
				bg=self.backgroundColor)
		self.positionArea.grid(row=srow, column=0, sticky="ew")
		self.positionArea.grid_remove()
		self.positionArea.columnconfigure(0, weight=1)
		self.positionArea.columnconfigure(1, weight=1)
		self.positionArea.columnconfigure(2, weight=1)
		srow += 1

		self.scenePosDivider = Tkinter.Frame(self.sceneSelHelpArea, bg="black",
			height="1p")
		self.scenePosDivider.grid(row=srow, column=0, sticky="ew")
		self.scenePosDivider.grid_remove()
		srow += 1

		self.selArea = Tkinter.Frame(self.sceneSelHelpArea,
			bg=self.backgroundColor)
		self.selRow = srow
		self.selArea.grid(row=self.selRow, column=0, sticky="nsew")
		srow += 1
		self.sceneSelHelpArea.rowconfigure(self.selRow, weight=self.selWeight)
		self.selArea.columnconfigure(0, weight=1)
		self.selArea.columnconfigure(1, weight=1)
		self.selArea.columnconfigure(2, weight=1)
		from dialogs import display
		from tkgui import _SelNamePromptDialog as snpd
		Tkinter.Button(self.selArea, text="Name current selection...", command=
			lambda f=display, n=snpd.name, s=self: setattr(s, 'shown', False)
			or f(n), pady=0, highlightbackground=self.backgroundColor).grid(
			row=1000, column=1)
		self.selArea.rowconfigure(999, weight=1)
		from CGLtk.Font import shrinkFont
		self.noSelsLabel = Tkinter.Label(self.selArea, text="Named Selections",
			bg=self.backgroundColor, fg=self.textColor)
		shrinkFont(self.noSelsLabel, fraction=self.largeTextFactor)
		self.noSelsLabel.grid(row=999, column=0, columnspan=3)
		from chimera import openModels, triggers, \
				BEGIN_RESTORE_SESSION, END_RESTORE_SESSION
		from selection import SEL_NAMED, DEL_NAMED_SELS
		triggers.addHandler(SEL_NAMED, self._namedSelCB, None)
		triggers.addHandler(DEL_NAMED_SELS, self._namedSelCB, None)
		Tkinter.Frame(self.sceneSelHelpArea, bg="black",
			height="1p").grid(row=srow, column=0, sticky="ew")

		self.dataArea = Tkinter.Frame(self, bd=1, relief='solid')
		self.dataArea.grid(row=0, column=2, sticky="nse")
		self.dataArea.rowconfigure(0, weight=1)
		drow = 0
		import Pmw
		self.dataButtonScroll = sf = Pmw.ScrolledFrame(self.dataArea,
				frame_bg=self.backgroundColor, clipper_bg=self.backgroundColor,
				horizflex='expand', hscrollmode='none', vscrollmode='static')
		sf.grid(row=drow, column=0, columnspan=3, sticky="nsew")
		self.dataButtonScroll.grid_remove()
		self.dataButtonArea = sf.interior()
		self.dataButtonArea.rowconfigure(0, weight=1)
		self.dataButtonArea.columnconfigure(0, weight=1)
		self.noDataLabel = Tkinter.Label(self.dataArea,
			text="Recent\nData\nSources", bg=self.backgroundColor,
			fg=self.textColor)
		shrinkFont(self.noDataLabel, fraction=self.largeTextFactor)
		self.noDataLabel.grid(row=drow, column=0, columnspan=3, sticky='nsew')
		drow += 1
		Tkinter.Frame(self.dataArea, bg="black",
			height="1p").grid(row=drow, column=0, columnspan=3, sticky="ew")
		drow += 1
		from tkgui import importDialog
		b1 = Tkinter.Button(self.dataArea, highlightbackground=self.backgroundColor,
			command=lambda imp=importDialog: imp().enter(), text="Browse...")
		b1.grid(row=drow, column=0, sticky='ew')
		import fetch
		b2 = Tkinter.Button(self.dataArea, command=fetch.showFetchDialog,
			text="Fetch...", highlightbackground=self.backgroundColor)
		b2.grid(row=drow, column=1, sticky='ew')
		self.editVar = Tkinter.IntVar(self.dataArea)
		self.editVar.set(False)
		b3 = Tkinter.Checkbutton(self.dataArea, command=self.rebuildDataHistory,
			text="Edit", variable=self.editVar, bg=self.backgroundColor,
			fg=self.textColor, highlightbackground=self.backgroundColor)
		b3.grid(row=drow, column=2, sticky="nsew")
		self.dataArea.columnconfigure(0, weight=1)
		self.dataArea.columnconfigure(1, weight=1)
		self.dataArea.columnconfigure(2, weight=0)
		self._dataWidth = 1.15 * (b1.winfo_reqwidth() + b2.winfo_reqwidth()
			+ b3.winfo_reqwidth())
		self.dataButtonScroll.component('clipper').config(width=self._dataWidth)
		self.dataHistory = DataHistory(self)
		self.rebuildDataHistory()

		openModels.addAddHandler(self._modelOpenedCB, None)
		self._inSession = False
		triggers.addHandler(BEGIN_RESTORE_SESSION, self._sesTrigCB, True)
		triggers.addHandler(END_RESTORE_SESSION, self._sesTrigCB, False)

		self.sceneFrame = Tkinter.Frame(self.sceneArea, bg=self.backgroundColor)
		self.sceneFrame.grid(row=0, column=0, sticky="nsew")
		self.sceneFrame.rowconfigure(0, weight=1)
		self.sceneFrame.columnconfigure(0, weight=1)
		self.noScenesLabel = Tkinter.Label(self.sceneFrame,
			text="Scenes", bg=self.backgroundColor, fg=self.textColor)
		self.noScenesLabel.grid(row=0, column=0)
		from CGLtk.Font import shrinkFont
		shrinkFont(self.noScenesLabel, fraction=self.largeTextFactor)
		self.scenesFrame = Tkinter.Frame(self.sceneFrame,
			bg=self.backgroundColor)
		self.scenesFrame.grid(row=0, column=0)
		def showSceneGUI(s=self):
			from Animate.GUI import GUI
			from dialogs import display
			display(GUI.name)
			s.shown = False
		f = Tkinter.Frame(self.sceneFrame, bg=self.backgroundColor)
		f.grid(row=1, column=0)
		from CGLtk.WrappingLabel import WrappingLabel
		disclaimer = WrappingLabel(f, text="Scenes are under development"
			" and may not be fully functional",
			bg=self.backgroundColor, fg=self.textColor)
		shrinkFont(disclaimer)
		disclaimer.grid(row=0, column=0, sticky="ew")
		Tkinter.Button(f, text="Save scene...",
			command=showSceneGUI, highlightbackground=self.backgroundColor
			).grid(row=1, column=0)

		# put icon in status line area
		self.iconClosed, self.iconOpen, self.iconAnimDark, self.iconAnimLight \
			 = self._initIcon()
		from statusline import status_line, button_opts, grid_opts
		sl = status_line(create=True)
		self.masterButton = Tkinter.Button(sl.frame, image=self.iconClosed,
			command=self._toggleShown, **button_opts)
		self.masterButton.grid(row=0, column=sl.ACCESS_COLUMN, **grid_opts)

		hf = self.helpFrame = Tkinter.Frame(self.sceneSelHelpArea,
			bg=self.backgroundColor)
		hf.columnconfigure(0, weight=1)
		hrow = 0
		Tkinter.Frame(hf, bg="black", height="1p").grid(
			row=hrow, column=0, sticky="ew")
		hrow += 1
		pady = "0.035i"
		from CGLtk.WrappingLabel import WrappingLabel
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			text='This is the "Rapid Access" interface,'
			' for quick access to items you frequently use.'
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text='It can be hidden/shown at any time by clicking the lightning-'
			'bolt icon near the bottom right of the Chimera window,'
			' or hidden automatically by opening 3D data.'
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text="On the right are recently used data sources, and"
			" buttons to browse for local files and to fetch data"
			" from the web."
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text="On the left is a toolbar for icons to start your favorite"
			' tools.  The "Add Tool Icon" button brings up a dialog to specify'
			" which tools' icons should be shown, and where to put the toolbar."
			' Click Save to make your changes apply to future uses of Chimera.'
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text="At the bottom left are buttons to raise any currently active"
			" Chimera dialogs."
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text="The middle section can have up to three parts: saved"
			" scenes at the top, named selections at the bottom, and any"
			" saved positions in between. Clicking a scene thumbnail"
			' restores that scene, and clicking "Save scene" brings up'
			" a dialog for saving the current scene."
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text="Clicking the name of a previously saved position or selection"
			' restores that position or selection, respectively.  The "Name'
			' current selection" button allows saving the current selection.'
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text="Clicking on most items in Rapid Access will hide the"
			" interface and reveal the Chimera graphics window.  To open"
			" recent data without dismissing Rapid Access, press the Shift key"
			" while clicking the data-source button."
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		WrappingLabel(hf, bg=self.helpBackgroundColor, pady=pady, justify="left",
			anchor='w',
			text="This help can be hidden/shown using the button"
			" at the bottom left of the Rapid Access interface."
			).grid(row=hrow, column=0, sticky='ew')
		hrow += 1
		Tkinter.Frame(hf, bg="black", height="1p").grid(
			row=hrow, column=0, sticky="ew")
		hrow += 1
		self.helpFrame.grid(row=self.helpRow, column=0, sticky="ew")
		self.helpFrame.grid_remove()

	def addTool(self, tbButton, image, buttonKw, balloon, helpURL):
		from chimera.tkgui import app
		from toolbar import TOOLBAR_RA
		if not self._toolLookup and app.toolbar.side != TOOLBAR_RA:
			self._showToolIconArea(False)
		self.toolIconArea.rowconfigure(0, weight=0)
		self.noToolIconsLabel.grid_remove()
		# req_height for a frame is 1 until it's managed, so...
		col1height = col2height = 0
		for child in self.toolIconCol1.winfo_children():
			col1height += child.winfo_reqheight()
		for child in self.toolIconCol2.winfo_children():
			col2height += child.winfo_reqheight()
		if col1height > col2height:
			toolParent = self.toolIconCol2
		else:
			toolParent = self.toolIconCol1
		if 'command' in buttonKw:
			oldCmd = buttonKw['command']
			buttonKw['command'] = lambda app = app, oc = oldCmd, *args: setattr(
				self, 'shown', False) or oc(*args)
		else:
			buttonKw['command'] = lambda app = app, *args: setattr(
				self, 'shown', False)
		button = Tkinter.Button(toolParent, **buttonKw)
		import help
		help.register(button, helpURL, balloon)

		import chimage
		imtk = chimage.get(image, button, allowRelativePath=True)
		button.config(image=imtk)
		# need to stash ref to Tk image or else it's immediately destroyed!
		button._image = imtk
		button.grid(column=0, sticky='n')
		self._toolLookup[tbButton] = button

	def drawScenes(self, *args):
		from Animate.Scenes import scenes
		if scenes.names():
			for child in self.scenesFrame.winfo_children():
				child.grid_forget()
				child.destroy()
			self._manufactureScenes()
			self.scenesFrame.grid()
			self.noScenesLabel.grid_remove()
		else:
			self.scenesFrame.grid_remove()
			self.noScenesLabel.grid()

	def hideHelp(self):
		self.sceneSelHelpArea.rowconfigure(self.sceneRow,
						weight=self.sceneWeight)
		self.sceneSelHelpArea.rowconfigure(self.selRow, weight=self.selWeight)
		self.helpFrame.grid_remove()
		self.sceneSelDivider.grid()
		self.helpButton.configure(text="Show Help", command=self.showHelp)

	def rebuildDataHistory(self):
		for child in self.dataButtonArea.winfo_children():
			child.grid_remove()
			child.destroy()
		if self.editVar.get():
			targetWidth = self._dataWidth - 18
		else:
			targetWidth = self._dataWidth
		if self.dataHistory.history:
			self.noDataLabel.grid_remove()
			self.dataButtonScroll.grid()
			self.dataButtonArea.rowconfigure(0, weight=0)
			seen = set()
			iconNames = set()
			for i, dataInfo in enumerate(self.dataHistory.history):
				if dataInfo in seen:
					continue
				seen.add(dataInfo)
				try:
					dataName, webType, fileType = dataInfo
				except ValueError:
					dataName, fileType = dataInfo
					if fileType.endswith('ID'):
						webType = fileType[:-2].strip()
					elif fileType == "ModBase":
						webType = fileType
					else:
						webType = None
				if dataName.startswith("#VRML"):
					base = "<<VRML string>>"
				else:
					from os.path import basename
					base = basename(dataName)
					if len(base) > 50:
						base = base[:24] + "..." + base[-24:]
				if webType:
					from chimera import fileInfo
					try:
						wtText = fileInfo.webType(webType)
					except:
						wtText = webType
					label = "%s [%s]" % (base, wtText)
				else:
					label = base
				showBalloon = base != dataName and not dataName.startswith("#VRML")
				b = Tkinter.Button(self.dataButtonArea, text=label,
					pady=0, highlightbackground=self.backgroundColor)
				if b.winfo_reqwidth() > targetWidth:
					showLets = (len(label)) / 2
					while showLets > 1 and b.winfo_reqwidth() > targetWidth:
						showLets -= 1
						b.configure(
							text=label[:showLets] + "..." + label[0 - showLets:])
					showBalloon = True
				b.bind("<ButtonRelease-1>", lambda e=None, dn=dataName, ft=fileType,
					wt=webType: self._openData(False, dn, ft, wt))
				b.bind("<Shift-ButtonRelease-1>", lambda e=None, dn=dataName,
					ft=fileType, wt=webType: self._openData(True, dn, ft, wt))
				b.grid(row=i, column=0, sticky="ew")
				if showBalloon:
					import help
					if webType:
						help.register(b, balloon=label)
					else:
						if len(dataName) > 120:
							btext = dataName[:60] + "..." + dataName[-60:]
						else:
							btext = dataName
						help.register(b, balloon=btext)
				if self.editVar.get():
					from CGLtk.Hybrid import bitmap
					x = Tkinter.Button(self.dataButtonArea, image=bitmap('x'),
						command=lambda di=dataInfo, s=self: s.dataHistory.removeData(di))
					x.grid(row=i, column=1)
		else:
			self.dataButtonScroll.grid_remove()
			self.noDataLabel.grid()
			self.dataButtonArea.rowconfigure(0, weight=1)

	def removeTool(self, tbButton):
		button = self._toolLookup.pop(tbButton)
		button.grid_forget()
		button.destroy()
		if not self._toolLookup:
			self.noToolIconsLabel.grid()
			from tkgui import app
			from toolbar import TOOLBAR_RA
			if app.toolbar.side != TOOLBAR_RA:
				self._showToolIconArea(True)

	def showHelp(self):
		self.sceneSelHelpArea.rowconfigure(self.sceneRow, weight=1)
		self.sceneSelHelpArea.rowconfigure(self.selRow, weight=1)
		self.sceneSelDivider.grid_remove()
		self.helpFrame.grid()
		self.helpButton.configure(text="Hide Help", command=self.hideHelp)
		prefs[EVER_SHOWN] = True

	def showToolArea(self, show):
		if show:
			self._showToolIconArea(True)
		else:
			if self._toolLookup:
				self._showToolIconArea(False)

	def _getShown(self):
		return self._shown

	def _setShown(self, shown):
		if shown != self._shown:
			self._toggleShown()

	shown = property(_getShown, _setShown)

	def _animate(self, interval, icons, targetShown):
		if self._shown != targetShown:
			# this animation no longer relevant
			return
		self.masterButton.config(image=icons.pop(0))
		if icons:
			self.masterButton.after(interval, lambda s=self: s._animate(
				interval, icons, targetShown))

	def _dialogChange(self, triggerName=None, _=None, dialogInfo=None):
		dialog, shown = dialogInfo
		if shown:
			if dialog in self._dialogInfo or not hasattr(dialog, 'title'):
				return
			self.noActiveToolsLabel.grid_remove()
			from tkgui import app
			if hasattr(dialog, 'raTitle'):
				title = dialog.raTitle
			else:
				title = dialog.title
			b = self._dialogInfo[dialog] = Tkinter.Button(self.activeToolsFrame,
				text=title, command=lambda d=dialog, app=app:
				setattr(self, 'shown', False) or d.enter(),
				pady=0, highlightbackground=self.backgroundColor)
			fw = self.activeToolsFrame.winfo_width()
			btext = title
			showBalloon = False
			while fw > 1 and b.winfo_reqwidth() >= fw and btext:
				btext = btext[:-1]
				b.configure(text=btext + "...")
				showBalloon = True
			b.grid(column=0, sticky="ew")
			if showBalloon:
				import help
				help.register(b, balloon=title)
		else:
			if dialog not in self._dialogInfo:
				return
			b = self._dialogInfo.pop(dialog)
			try:
				b.grid_forget()
				if not self._dialogInfo:
					self.noActiveToolsLabel.grid()
			except Tkinter.TclError:
				# We may be called when program is exiting
				pass

	def _evalSceneFit(self, scenes, rows, cols, targetWidth, targetHeight):
		height = 0
		columnWidths = [0] * cols
		si = 0
		for row in range(rows):
			rowHeight = 0
			for col in range(cols):
				scene = scenes[si]
				w = h = 0
				for child in scene.winfo_children():
					w = max(w, child.winfo_reqwidth())
					h += child.winfo_reqheight()
				rowHeight = max(rowHeight, h)
				columnWidths[col] = max(columnWidths[col], w)
				si += 1
				if si >= len(scenes):
					break
			height += rowHeight
		width = sum(columnWidths)
		if height == 0 or width == 0 or targetWidth == 0 or targetHeight == 0:
			return 1.0
		ratio = width / float(height)
		tratio = targetWidth / float(targetHeight)
		if ratio > tratio:
			return tratio / float(ratio)
		return ratio / float(tratio)

	def _initIcon(self):
		import chimera, os.path
		iconName = "style_bolt.png"
		fileName = chimera.pathFinder().firstExistingFile("chimera",
			os.path.join("images", iconName), False, False)
		if not fileName:
			import errno, os
			raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), iconName)

		from PIL import Image
		image = Image.open(fileName)

		from chimera.colorTable import colors
		from statusline import tint
		closedImage = tint(image, colors["navy blue"], self.toolArea)
		openImage = tint(image, colors["deep sky blue"], self.toolArea)
		animDark = closedImage
		animLight = tint(image, colors["white"], self.toolArea)
		return closedImage, openImage, animDark, animLight

	def _manufactureScenes(self):
		from Animate.Scenes import scenes as animateScenes
		scenes = []
		for name in animateScenes.names():
			scene = animateScenes.getScene_by_name(name)
			f = Tkinter.Frame(self.scenesFrame, bd=4, relief="raised")
			from PIL import ImageTk
			img = ImageTk.PhotoImage(scene.img, master=f)
			l = Tkinter.Label(f, image=img)
			l.__img = img
			l.grid(row=0, column=0)
			from CGLtk.WrappingLabel import WrappingLabel
			WrappingLabel(f, text=scene.dispname, preserveWords=True).grid(
				row=1, column=0, sticky="ew")
			def showScene(e, nm=name):
				self.shown = False
				from Animate import Scenes
				Scenes.scenes.show(nm)
			for child in f.winfo_children():
				child.bind("<ButtonRelease-1>", showScene)
				if scene.description:
					import help
					help.register(child, balloon=scene.description)
			scenes.append(f)
		bestFit = None
		targetWidth, targetHeight = (self.sceneFrame.winfo_width(),
								self.sceneFrame.winfo_height())
		for cols in range(1, len(scenes) + 1):
			import math
			rows = int(math.ceil(len(scenes) / float(cols)))
			fit = self._evalSceneFit(scenes, rows, cols,
				targetWidth, targetHeight)
			if bestFit == None or fit > bestFit:
				bestFit = fit
				bestRows, bestCols = rows, cols
			else:
				break
		for row in range(bestRows):
			for col in range(bestCols):
				if scenes:
					scenes.pop(0).grid(row=row, column=col)

	def _modelOpenedCB(self, _1, _2, models):
		# if any non-hidden model opened, hide
		if not self._keepShown and [m for m in models if m.id >= 0]:
			# don't change shown due to metal complex creation
			# or nucleotides depiction creation
			for m in models:
				from chimera import PseudoBondGroup, VRMLModel
				if not ((isinstance(m, PseudoBondGroup)
				and m.category.startswith("coordination complexes"))
				or (isinstance(m, VRMLModel)
				and m.name.endswith("Nucleotides"))):
					self.shown = False
					break
		if self._inSession:
			self._nextKeepShown = False
		else:
			self._keepShown = False

	def _namedSelCB(self, trigName, _2, selInfo):
		from chimera.selection import DEL_NAMED_SELS
		class SelButton(Tkinter.Button):
			pass # needed to distinguish from other button widgets
		from selection import savedSels
		if trigName == DEL_NAMED_SELS:
			for child in self.selArea.winfo_children():
				if child.__class__.__name__ == "SelButton":
					child.grid_forget()
					child.destroy()
			for i, selName in enumerate(sorted(savedSels.keys())):
				self._namedSelCB(i+1, None, selName)
			return
		elif isinstance(trigName, int):
			numSels = trigName
			selName = selInfo
		else:
			selName, update = selInfo
			if update:
				return
			from selection import savedSels
			numSels = len(savedSels)
		if numSels == 1:
			row = 1000
			col = 0
			self.noSelsLabel.grid_remove()
		else:
			row = 1000 - (numSels / 3)
			col = numSels % 3
		self.selArea.rowconfigure(row, weight=0)
		self.selArea.rowconfigure(row - 1, weight=1)
		from tkgui import selectionOperation, app
		def cb(sn=selName, sop=selectionOperation, ssels=savedSels, app=app):
			sop(ssels[sn])
			self.shown = False
		SelButton(self.selArea, text=selName, command=cb, pady=0,
			highlightbackground=self.backgroundColor).grid(
			row=row, column=col, sticky="ew")

	def _openData(self, keepShown, dataName, dataType, webType):
		self._keepShown = keepShown
		import chimera
		chimera.raFetchedType = webType
		from chimera import openModels, fileInfo
		if fileInfo.category(dataType) == fileInfo.SCRIPT and not keepShown:
			# scripts may change existing models or add 2D Labels...
			self.shown = False
		try:
			openModels.open(dataName, dataType)
		except IOError, e:
			import os.path
			if webType is None and not os.path.exists(dataName):
				NonExistentDataDialog(self, dataName, dataType)
			else:
				import replyobj
				replyobj.warning(unicode(e))
		finally:
			chimera.raFetchedType = None

	def _positionsChanged(self, _1, _2, positionNames):
		for child in self.positionArea.winfo_children():
			child.grid_remove()
			child.destroy()
		import Midas
		if not Midas.positions:
			self.positionArea.grid_remove()
			self.scenePosDivider.grid_remove()
			return
		posNames = Midas.positions.keys()
		posNames.sort()
		for i, pn in enumerate(posNames):
			if len(pn) > 25:
				pn = pn[:11] + "..." + pn[-11:]
			b = Tkinter.Button(self.positionArea, text=pn, command=lambda pn=pn:
				(Midas.reset(pn) or True) and setattr(self, 'shown', False),
				pady=0, highlightbackground=self.backgroundColor)
			b.grid(row=i/3, column=i%3)
		self.positionArea.grid()
		self.scenePosDivider.grid()

	def _sesTrigCB(self, _1, beginning, _2):
		self._inSession = beginning
		if beginning:
			self._nextKeepShown = None
		else:
			# old sessions may not fire begin-session triggers...
			if getattr(self, '_nextKeepShown', None) is not None:
				self._keepShown = self._nextKeepShown

	def _showToolIconArea(self, show):
		if show:
			self.toolIconArea.grid()
			self.toolArea.rowconfigure(self.toolIconRow, weight=1)
			self.iconDivider.grid()
			self.toolArea.rowconfigure(self.activeToolsRow, weight=0)
		else:
			self.toolIconArea.grid_remove()
			self.toolArea.rowconfigure(self.toolIconRow, weight=0)
			self.iconDivider.grid_remove()
			self.toolArea.rowconfigure(self.activeToolsRow, weight=1)

	def _toggleShown(self):
		from chimera import fullscreen
		from chimera.tkgui import app
		# In fullscreen mode, keep both rapid access and graphics
		# windows visible.
		if self._shown:
			if fullscreen:
				app._fullscreen.deiconify()
			else:
				self.graphicsTakesTrackPadEvents()
				app.toolbar.work = app.graphics
				self.hideHelp()
			animSeq = [self.iconAnimDark, self.iconAnimLight, self.iconAnimDark,
				self.iconAnimLight, self.iconClosed]
		else:
			app.toolbar.work = app.rapidAccess
			animSeq = [self.iconAnimLight, self.iconAnimDark,
				self.iconAnimLight, self.iconAnimDark, self.iconOpen]
		if fullscreen:
			self._shown = True
		else:
			self._shown = not self._shown
		self.masterButton.after(50, lambda s=self: s._animate(50,
			animSeq, self._shown))

	def graphicsTakesTrackPadEvents(self):
		# This hack makes the graphics widget receive trackpad events on the Mac.
		# Without it, if the mouse is over a hidden rapid access button then that button
		# gets the trackpad events.  This problem arises because Mac Tk was not designed
		# to handle trackpad events.
		from chimera.tkgui import app, windowSystem
		if windowSystem == 'aqua':
			g = app.graphics
			if g:
				g.tk.call(g._w, 'maketopfortrackpadevents')

DATA_HISTORY = "data history"
HISTORY_LENGTH = "history length"
EVER_SHOWN = "has interface ever been shown to this user"
from preferences import addCategory, HiddenCategory
prefs = addCategory("Rapid Access", HiddenCategory,
	inherit=[(DATA_HISTORY, "OpenRecent", 'history', None)],
	optDict={ DATA_HISTORY: [], HISTORY_LENGTH: 100, EVER_SHOWN: False })

class DataHistory(object):
	def __init__(self, ra):
		self.rapidAccess = ra

		self.history = prefs[DATA_HISTORY]
		self._historyLength = prefs[HISTORY_LENGTH]

		from chimera import triggers, APPQUIT
		triggers.addHandler('file open', self._dataIO, True)
		triggers.addHandler('file save', self._dataIO, False)

		# only save data history when Chimera quits
		triggers.addHandler(APPQUIT, self._saveHistory, None)

	def _getHistoryLength(self):
		return self._historyLength

	def _setHistoryLength(self, hl):
		self._historyLength = prefs[HISTORY_LENGTH] = hl
		self.rapidAccess.rebuildDataHistory()

	historyLength = property(_getHistoryLength, _setHistoryLength)

	def _dataIO(self, trigName, opened, dataInfo):
		if opened:
			dataName, webType, dataType = dataInfo
		else:
			dataName, dataType = dataInfo
			webType = None
		from chimera import fileInfo
		if opened or fileInfo.openCallback(dataType):
			self.rememberData(dataName, webType, dataType)

	def rememberData(self, dataName, webType, dataType):
		if dataType.lower() == 'vrml' and dataName.startswith('#VRML'):
			return
		import os.path
		if webType == None and os.path.exists(dataName) \
		and not os.path.isabs(dataName):
			# remember absolute path
			dataName = os.path.abspath(dataName)
		for i in range(self.history.count((dataName, dataType))):
			self.history.remove((dataName, dataType))
		for i in range(self.history.count((dataName, webType, dataType))):
			self.history.remove((dataName, webType, dataType))
		# avoid modifying original history so that preference
		# saving doesn't get confused
		self.history = [(dataName, webType, dataType)] \
			+ self.history[:self.historyLength - 1]
		self.rapidAccess.rebuildDataHistory()

	def removeData(self, dataInfo):
		# dataInfo == None means remove all non-existent
		history = self.history[:]
		modified = False
		if dataInfo:
			for i in range(history.count(dataInfo)):
				history.remove(dataInfo)
				modified = True
		else:
			import os.path
			for entry in history[:]:
				try:
					dataName, webType, dataType = entry
				except ValueError:
					dataName, dataType = entry
					webType = "not known"
				if (webType is None or webType == "not known" and os.path.isabs(dataName)) \
				and not os.path.exists(dataName):
					history.remove(entry)
					modified = True
		if modified:
			self.history = history
			self.rapidAccess.rebuildDataHistory()

	def _saveHistory(self, *args):
		prefs[DATA_HISTORY] = self.history

from baseDialog import ModelessDialog
class NonExistentDataDialog(ModelessDialog):
	oneshot = True
	buttons = ('OK',)

	def __init__(self, rapidAccess, dataName, dataType, **kw):
		self.rapidAccess = rapidAccess
		self.dataName = dataName
		self.dataType = dataType
		self.title = dataName + " not found"
		ModelessDialog.__init__(self, **kw)

	def fillInUI(self, parent):
		Tkinter.Label(parent, text="%s no longer exists\n"
			"What would you like to do?" % self.dataName).grid(row=0, column=0)
		import Pmw
		self.choices = Pmw.RadioSelect(parent, orient='vertical', pady=0,
			buttontype='radiobutton')
		self.choices.grid(row=1, column=0)
		self.choices.add("Ignore")
		self.choices.add("Remove", text="Remove its entry from data list")
		self.choices.add("Remove all",
				text="Remove all non-existent files from data list")
		self.choices.invoke("Remove")

	def Apply(self):
		choice = self.choices.getvalue()
		if choice == "Ignore":
			return
		if choice == "Remove":
			self.rapidAccess.dataHistory.removeData(
					(self.dataName, None, self.dataType))
		else:
			self.rapidAccess.dataHistory.removeData(None)
