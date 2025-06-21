# Copyright (c) 2000 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: base.py 42412 2022-12-21 00:32:12Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import help, openModels, Molecule
from Group import Group, GroupAttr
import Tix, Pmw
import Tkinter
import CGLtk
import os

_buttonInfo = {}
_mp = None

def addButton(name, callback, minModels=1, maxModels=None,
			moleculesOnly=True, balloon=None, defaultFrequent=True,
			defaultFavorite=None, groupsOkay=False):
	"""Add a button to the 'Model Actions' button list.

	   'name' is the button name (duh).  'callback' is the
	   function to call when the button is pressed.  The arg to
	   'callback' will be a list of models.  'min/maxModels'
	   indicate how many models have to be selected in the
	   browser for the button to be active ('None' indicates no
	   limit).  if 'moleculesOnly' is True, then those models have
	   to be Molecules.

	   This is a module function so that it can be called even if
	   the model panel has not yet been created.
	"""

	if defaultFavorite is None:
		defaultFavorite = defaultFrequent
	if _buttonInfo.has_key(name):
		raise KeyError, \
			"Button named '%s' already exists" % name
	_buttonInfo[name] = (callback, minModels, maxModels,
					moleculesOnly, balloon, defaultFavorite, groupsOkay)

	if _mp:
		_mp._confDialog.newButton(name, balloon=balloon,
					defaultFavorite=defaultFavorite)
		_mp._showButton(name)

_columnNames = []
_valueTypes = []
_valueFuncs = []
_defaultShows = []
def addColumns(columnInfo, defaultShown=1):
	"""Add columns to the model table.

	   'columnInfo' is a list of 3-tuples, one for each column
	   to add.  The tuple consists of (column name, value type,
	   value-fetch function).  The value type should be 'text',
	   'image', 'imagetext', or 'toggle'.  The value-fetch function
	   takes one argument (a model) and (for 'image' and 'text')
	   should return the value to display in the table cell.  For
	   'imagetext' the return value should be an (image, text)
	   tuple.  'toggle' shows a toggle button and the return value
	   should be a (boolean, callback) tuple.  If the boolean is
	   true, a check will be shown on the toggle button; otherwise
	   the button is blank.  The callback is invoked when the
	   toggle is pressed, with the model and the new boolean as
	   arguments.  The value of an image is the name of the image
	   (the Tix name, e.g. 'tick' for tickmark).  A value of None
	   for image or text will leave a blank cell.

	   'defaultShown' controls whether the column is shown in
	   the model table or not as long as the user has not yet
	   expressed a preference in the Configuration panel about it.
	"""

	noneShown = 1
	for name,type,func in columnInfo:
		if name in _columnNames:
			raise ValueError, "Duplicate model panel"\
						"column name: %s" % name
		_columnNames.append(name)
		_valueTypes.append(type)
		_valueFuncs.append(func)
		_defaultShows.append(defaultShown)
		if _mp:
			try:
				shown = _mp._confDialog.prefs[
							'shownColumns'][name]
			except KeyError:
				shown = defaultShown
			_mp.shownColumns.append(shown)
			if shown:
				noneShown = 0
			_mp._confDialog.newColumn(name, shown)

	if not noneShown:
		_mp._buildTable()

def readableName(model):
	if model.name:
		for char in model.name:
			if ord(char) < 32:
				break
		else:
			return model.name
	if isinstance(model, chimera.Molecule):
		return "unknown Molecule"
	if isinstance(model, chimera.MSMSModel):
		return "unknown MSMS surface"
	if isinstance(model, chimera.VRMLModel):
		return "unknown VRML object"
	return "unknown"

def inputPath(model):
	if not hasattr(model, 'openedAs') or '\n' in model.openedAs[0]:
		return readableName(model)
	path = model.openedAs[0]
	curdir = os.getcwd() + os.sep
	if path.startswith(curdir):
		return path[len(curdir):]
	return path

def getPhysicalChains(model):
	# return chains of physically connected residues as list of lists;
	# single-residue "chains" collated into first list
	from operator import add
	physical = [[]]
	seen = {}

	for root in model.roots(1):
		resAtoms = root.atom.residue.atoms
		numRootAtoms = root.size.numAtoms

		if numRootAtoms < len(resAtoms):
			# disconnected residue; continue only if this is
			# the largest fragment of the residue
			largestFrag = 1
			for atom in resAtoms:
				if atom.rootAtom == root.atom:
					continue
				if atom.molecule.rootForAtom(atom, 1).size\
						.numAtoms > numRootAtoms:
					largestFrag = 0
					break
			if not largestFrag:
				continue

		if numRootAtoms <= len(resAtoms):
			curPhysical = physical[0]
		else:
			curPhysical = []
			physical.append(curPhysical)
		for atom in model.traverseAtoms(root):
			res = atom.residue
			if seen.has_key(res):
				continue
			seen[res] = 1

			curPhysical.append(res)
	
	return physical

def nameColumn(m):
	if _mp and _mp._confDialog.showColorVar.get():
		bcolor = isinstance(m, chimera.Molecule) and m.color or None
		return readableName(m), bcolor
	return readableName(m)
	
def _oslIdent(item):
	if isinstance(item, Group):
		models = item.models
		osls = [m.oslIdent() for m in models]
		from chimera.misc import oslModelCmp
		osls.sort(oslModelCmp)
		return u"%s\N{HORIZONTAL ELLIPSIS}%s" % (osls[0][1:], osls[-1][1:])
	return item.oslIdent()[1:]

from _surface import SurfaceModel
addColumns([
	('ID', 'text', _oslIdent),
	('', 'well', lambda m: (hasattr(m, 'color') and (not isinstance(m, SurfaceModel)) and m.color, True, True, lambda m, c: setattr(m, 'color', c))),
	('Active', 'toggle', lambda m: (m.openState.active, lambda m, b: setattr(m.openState, 'active', b))),
	('Shown', 'toggle', lambda m: (m.display, lambda m, b: setattr(m, 'display', b))),
	('Name', 'text', nameColumn)
])
addColumns([
	('Skip', 'toggle', lambda m: (getattr(m, '_mp_skip', False), lambda m, b: setattr(m, '_mp_skip', b) or _mp._requestUpdate())),
	('Note', 'text', lambda m: (hasattr(m, 'note') and m.note or '')),
	('Input file', 'text', inputPath)
], defaultShown=False)

class ModelPanel(ModelessDialog):
	title="Model Panel"
	buttons=('Close','Configure...')
	name="model panel"
	help="UsersGuide/modelpanel.html"

	itemTableHelp = "click to select models;"\
			"\nright-hand action buttons work on selected models;"\
			"\ndouble-click to perform default action on model"\
			"\n(see 'Configure...' for default action info)"
	def fillInUI(self, parent):
		global _mp
		_mp = self

		self.parent = parent

		# model table
		self._getConfig()

		# action buttons
		atf = self.allTitleFrame = Tkinter.Frame(self.parent)
		atf.grid(row=5, column=20, sticky='w')
		atf.grid_remove()
		self.commandLabel = Tkinter.Label(atf, text="Command")
		self.commandLabel.grid(row=0, column=1)
		Tkinter.Label(atf, text="Fav").grid(row=0, column=3, sticky='w')

		self.buttonScroll = Pmw.ScrolledFrame(self.parent,
							hscrollmode='none')
		self.buttonScroll.grid(row=10, column=20, sticky='nsew')
		self.favActionButtons = FavButtonBox(
			self.buttonScroll.interior(), orient='vertical', pady=0)
		self._shownActions = None
		self.allActionButtons = AllButtonBox(
			self.buttonScroll.interior(), self)
		self._favToggle = Pmw.RadioSelect(self.parent,
				command=self._favToggleCB,
				orient="horizontal", buttontype="radiobutton")
		self._favToggle.add("favorites")
		self._favToggle.add("all")
		self._favToggle.grid(row=20, column=20)
		self.favButtonsCreated = []
		self.allButtonsCreated = []

		self._addColumns()
		# add buttons from other extensions...
		self._addButtons()

		# add standard buttons
		addButton("add/edit note...", noteCmd, balloon="add notation"
			" that will be displayed in model table", moleculesOnly=False)
		addButton("activate", lambda m, f='active', v=1,
			smf=setModelField: smf(m, f, v, openState=1),
			moleculesOnly=False,
			balloon="make selected models active"
			"\n(responsive to mouse motions)")
		addButton("activate all", lambda m, f=activateAllCmd: f(),
			minModels = 0, moleculesOnly=False,
			balloon="activate all models;\n"
			"restore previous active states with this same button")
		addButton("activate next", lambda m, f=activateNextCmd: f(),
			minModels = 0, moleculesOnly=False, defaultFavorite=False,
			balloon="activate next model in sequence")
		addButton("activate only", lambda m, f='active',
			smfo=setModelFieldOnly: smfo(m, f, openState=1),
			moleculesOnly=False,
			balloon="make selected models active"
			"\n(responsive to mouse motions);\ndeactivate others")
		addButton("activate previous", lambda m, f=activatePreviousCmd: f(),
			minModels = 0, moleculesOnly=False, defaultFavorite=False,
			balloon="activate previous model in sequence")
		addButton("attributes...", attributesCmd,
			moleculesOnly=False,
			balloon="inspect/modify model attributes")
		def runClipping(models):
			import ModelClip.gui
			cd = chimera.dialogs.display(ModelClip.gui.ClipDialog.name)
			cd.setModel(models[0])
		addButton("clipping...", runClipping, moleculesOnly=False,
			balloon="adjust per-model clipping plane")
		addButton("close", openModels.close, moleculesOnly=False,
			balloon="close models")
		addButton("deactivate", lambda m, f='active', v=0,
			smf=setModelField: smf(m, f, v, openState=1),
			moleculesOnly=False,
			balloon="make selected models inactive"
			"\n(insensitive to mouse motions)")
		addButton("focus", focusCmd, moleculesOnly=False,
			defaultFavorite=False,
			balloon="bring selected models fully into view"
			"\nin main graphics window")
		addButton("group/ungroup", groupCmd, moleculesOnly=False,
			balloon= "group selected items into a single line"
			" or, if just one group selected, ungroup them",
			groupsOkay=True)
		addButton("hide", lambda m, f='display', v=0,
			smf=setModelField: smf(m, f, v),
			moleculesOnly=False,
			balloon="hide selected models; undo with 'show'")
		def showRainbowDialog(models):
			from chimera import dialogs
			from rainbow import RainbowDialog
			if len(models) > 1:
				target = "models"
			else:
				target = "residues"
			dialogs.display(RainbowDialog.name).configure(
						models=models, target=target)
		addButton("rainbow...", showRainbowDialog, defaultFavorite=False,
			balloon="rainbow-color residues or chains")
		addButton("rename...", renameCmd, moleculesOnly=False, groupsOkay=True)
		addButton("select", selectCmd, moleculesOnly=False,
			balloon="incorporate models into graphics window"
			"\nselection using current selection mode"
			"\n(see graphics window Selection menu)")
		from chainPicker import ChainPicker
		addButton("select chain(s)...", lambda m,
			cp=ChainPicker: cp(m).enter(),
			balloon="select some/all chains\n"
			"(using current selection\n"
			"mode from Selection menu)")
		addButton("sequence...", seqCmd, defaultFavorite=False,
			balloon="inspect molecule sequence")
		addButton("show", lambda m, f='display', v=1,
			smf=setModelField: smf(m, f, v),
			moleculesOnly=False, balloon="unhide selected models")
		addButton("show all atoms", showAllAtomsCmd,
			balloon="show all atoms"
			" (but use 'show' to undo 'hide')")
		addButton("show next", lambda m, f=displayNextCmd: f(),
			minModels = 0, moleculesOnly=False, defaultFavorite=False,
			balloon="display next model in sequence")
		addButton("show only", lambda m, f='display',
			smfo=setModelFieldOnly: smfo(m, f), moleculesOnly=False,
			balloon="show selected models and hide all others")
		addButton("show previous", lambda m, f=displayPreviousCmd: f(),
			minModels = 0, moleculesOnly=False, defaultFavorite=False,
			balloon="display previous model in sequence")
		addButton("surface main", lambda m, c="main", sc=surfCmd:
			sc(m, c), defaultFavorite=False,
			balloon="surface non-ligand portion of models")
		def showTileDialog(models):
			from chimera import dialogs
			from EnsembleMatch.choose import TileStructuresCB
			dialogs.display(TileStructuresCB.name).configure(
								models=models)
		addButton("tile...", showTileDialog, minModels=2,
			moleculesOnly=False, defaultFavorite=False,
			balloon="arrange selected models into a"
			"\nrectangular grid and focus on them")
		addButton("toggle active", lambda m, f='active',
			tmf=toggleModelField: tmf(m, f, openState=1),
			moleculesOnly=False,
			balloon="invert active states of selected models")
		addButton("trace backbones", lambda m, bc=backboneCmd:
			bc(m, resTrace=0), defaultFavorite=False,
			balloon="show backbone atom trace for protein"
			"\nor nucleic acid; undo with 'show all atoms'")
		addButton("trace chains", backboneCmd, defaultFavorite=False,
			balloon="show residue connectivity trace for protein"
			"\nor nucleic acid; undo with 'show all atoms'")
		from transformDialog import TransformDialog
		addButton("transform as...", TransformDialog,
			moleculesOnly=False,
			balloon="rotate/translate models same as another model")
		from writePDBdialog import WritePDBdialog
		addButton("write PDB", lambda mols: chimera.dialogs.display(
			WritePDBdialog.name).configure(mols, selOnly=False),
			balloon="write molecule as PDB file")
		from ksdsspDialog import KsdsspDialog
		addButton("compute SS", KsdsspDialog,
			balloon="compute secondary structure elements"
			"\nusing Kabsch and Sander algorithm")
		
		self._favToggle.invoke("favorites")

		# add these last, since if they somehow fire before the
		# constructor is complete then an exception will occur
		self._updateHandler = None
		chimera.triggers.addHandler('Model', self._requestUpdate, None)
		chimera.triggers.addHandler('OpenState', self._fillTable, None)

	def Configure(self):
		"""configure action buttons"""
		self._confDialog.enter()

	def see(self, buttonName):
		pass # I don't think anything calls this

	def selected(self, moleculesOnly=False, groupsOkay=False):
		"""Return a list of the selected models"""

		selected = []
		for ii in self.itemTable.hlist.info_selection():
			item = self.items[int(ii)]
			if groupsOkay:
				selected.append(item)
				continue
			models = _getModels(item)
			if moleculesOnly:
				models = [m for m in models if isinstance(m, Molecule)]
			selected.extend(models)
		return selected

	def selectionChange(self, models, extend=False, priorSelection=None):
		"""set (or extend) the selection to contain the given models
		
		   'models' can be Models or oslIdents"""

		# may have to ungroup groups if they are partially selected
		newSelected = []
		breakGroups = []
		if models:
			testSet = set()
			for m in models:
				testSet.update(_getModels(m))
			if isinstance(models[0], basestring):
				# OSL ident
				for i, item in enumerate(self.items):
					val = item.oslIdent()
					if isinstance(val, set):
						if testSet & val:
							breakGroups.append(item)
					elif val in testSet:
						newSelected.append(i)
			else:
				for i, item in enumerate(self.items):
					val = set(_getModels(item))
					if val & testSet:
						if val & testSet < val:
							breakGroups.append(item)
						else:
							newSelected.append(i)
		if breakGroups:
			if priorSelection is None:
				priorSelection = self.selected(groupsOkay=True)
			for group in breakGroups:
				self.items.remove(group)
				self.items.extend(group.components)
				if group in priorSelection:
					priorSelection.remove(group)
					priorSelection.extend(group.components)
			self.selectionChange(models, extend=extend,
					priorSelection=priorSelection)
			return
		if priorSelection is not None:
			self._fillTable(fromScratch=True, selected=priorSelection)
		if not extend:
			self.itemTable.hlist.selection_clear()

		for i in newSelected:
			self.itemTable.hlist.selection_set(i)
		self._selChangeCB()

	def _addButtons(self):
		"""Add buttons to interface that were requested before
		   panel was created.
		"""

		for name, info in _buttonInfo.items():
			balloon, defaultFavorite = info[-3:-1]
			self._confDialog.newButton(name, balloon=balloon,
						defaultFavorite=defaultFavorite)
			self._showButton(name)

	def _addColumns(self):
		"""Process column information"""
		self.shownColumns = []

		for i in range(len(_columnNames)):
			name = _columnNames[i]
			if name == "Note":
				shown = False
				for m in openModels.list():
					if hasattr(m, 'note') and m.note:
						shown = True
						break
			else:
				try:
					shown = self._confDialog.prefs[
							'shownColumns'][name]
				except KeyError:
					shown = _defaultShows[i]
			self.shownColumns.append(shown)
			self._confDialog.newColumn(name, shown)
		self._buildTable()

	def _buttonParams(self, name):
		callback, minModels, maxModels, moleculesOnly, balloon, \
					defaultFavorite, groupsOkay = _buttonInfo[name]
		kw = {}
		state = 'normal'
		if self._shouldDisable(minModels, maxModels, moleculesOnly):
			state = 'disabled'
		kw['state'] = state
		kw['pady'] = 0
		# if you click a button fast enough, you can get around it's
		# upcoming disabling...
		def cmd(cb=callback, s=self, mo=moleculesOnly, minm=minModels,
				maxm=maxModels, go=groupsOkay):
			if not s._shouldDisable(minm, maxm, mo):
				cb(s.selected(moleculesOnly=mo, groupsOkay=go))
		kw['command'] = cmd
		return kw, balloon, defaultFavorite

	def _buildTable(self):
		if hasattr(self, 'itemTable'):
			# can't dynamically add columns to Tix widget;
			# destroy and recreate
			selected = self.selected()
			self.itemTable.grid_forget()
			self.itemTable.destroy()
		else:
			selected = None

		w, h = self._confDialog.prefs['table w/h']
		inch = self.parent.winfo_fpixels("1i")
		self.itemTable = Tix.ScrolledHList(self.parent,
			width="%d" % int(w * inch + 0.5),
			height="%d" % int(h * inch + 0.5),
			options="""hlist.columns %d
			hlist.header 1
			hlist.selectMode extended
			hlist.indicator 0"""
			% len(filter(lambda s: s == 1, self.shownColumns)))
		help.register(self.itemTable, balloon=self.itemTableHelp)
		self.itemTable.hlist.config(browsecmd=self._selChange,
							command=self._dblClick)
		self.textStyle = Tix.DisplayStyle("text",
				refwindow=self.itemTable)
		# get a style for checkbutton columns...
		self.checkButtonStyle = Tix.DisplayStyle("window",
				refwindow=self.itemTable, anchor="center")
		self.colorWellStyle = Tix.DisplayStyle("window",
				refwindow=self.itemTable, anchor="center")
		colNum = 0
		self.columnMap = []
		showFullTitles = False
		last = self._confDialog.prefs["lastUse"]
		from time import time
		now = self._confDialog.prefs["lastUse"] = time()
		if last is None or now - last > 777700: # about 3 months
			showFullTitles = True
		used_abbrs = set()
		for index in range(len(_columnNames)):
			if not self.shownColumns[index]:
				continue
			self.columnMap.append(index)
			text = _columnNames[index]
			if _valueTypes[index] == 'toggle' \
			and not showFullTitles:
				for i in range(1, len(text)):
					abbr = text[:i]
					if abbr not in used_abbrs:
						used_abbrs.add(abbr)
						break
				text = abbr
			self.itemTable.hlist.header_create(colNum,
						itemtype='text', text=text)
			colNum = colNum + 1
			
		self.parent.columnconfigure(10, weight=1)
		self.parent.rowconfigure(10, weight=1)
		self.itemTable.grid(row=5, column=10, sticky='nsew',
								rowspan=16)
		self._fillTable(selected=selected, fromScratch=1)
		self.itemTable.bind("<Configure>", self._rememberSize, add=True)

	def _dblClick(self, item):
		"""user has double-clicked on model table entry"""

		# if the state of the action buttons is due to change,
		# execute that change before calling the double-click routine
		if hasattr(self, '_selChangeIdle') and self._selChangeIdle:
			self.parent.after_cancel(self._selChangeIdle)
			self._selChangeCB()

		self._confDialog.dblClick()

	def _doUpdate(self):
		self._updateHandler = None
		self._fillTable(*self._triggerArgs)
		self._triggerArgs = None

	def _favButton(self, name, fav):
		names = self.favButtonsCreated
		actionButtons = self.favActionButtons
		if fav:
			names.append(name)
			names.sort(lambda a, b: cmp(a.lower(), b.lower()))
			kw, balloon, defaultFavorite = self._buttonParams(name)
			index = names.index(name)
			if index == len(names)-1:
				addFunc = actionButtons.add
			else:
				addFunc = actionButtons.insert
				kw['beforeComponent'] = names[index+1]

			but = addFunc(name, **kw)
			but.config(default='disabled')
			if balloon:
				help.register(but, balloon=balloon)
		else:
			names.remove(name)
			actionButtons.delete(name)

	def _favToggleCB(self, label):
		if label == "favorites":
			self._showActions(self.favActionButtons)
		else:
			self._showActions(self.allActionButtons)

	def _fillTable(self, *triggerArgs, **kw):
		if len(triggerArgs) > 0:
			if triggerArgs[0] == 'OpenState':
				if 'active change' not in triggerArgs[-1].reasons:
					return
			elif triggerArgs[0] == 'Model':
				global _groupNameCache
				_groupNameCache.clear()
		hlist = self.itemTable.hlist
		defaultable = False
		if kw.get('selected', None) != None:
			selected = kw['selected']
		else:
			selected = self.selected(groupsOkay=True)
			defaultable = True
		rebuild = False
		curModels = set(openModels.list())
		if not hasattr(self, 'items'):
			global _groups
			self.items = _groups[:]
			_groups[:] = []
			rebuild = True
		elif kw.get('fromScratch', False):
			rebuild = True
		else:
			prevModels = set()
			for item in self.items:
				prevModels.update(_getModels(item))
			if curModels != prevModels:
				rebuild = True

		if rebuild:
			newItems = []
			for item in self.items:
				if not isinstance(item, Group):
					continue
				item.update()
				if len(item.models) > 1:
					newItems.append(item)
					curModels.difference_update(item.models)
			self.items = newItems + list(curModels)
			self.items.sort(self._itemSort)
			self._prevValues = {}
			hlist.delete_all()
			vf = _valueFuncs[self.columnMap[0]]
			for i, item in enumerate(self.items):
				hlist.add(i, **self._hlistKw(item, 0))
				self._prevValues[(i, 0)] = vf(item)
			for ci in range(1, len(self.columnMap)):
				vf = _valueFuncs[self.columnMap[ci]]
				for i, item in enumerate(self.items):
					hlist.item_create(i, ci, **self._hlistKw(item, ci))
					self._prevValues[(i, ci)] = vf(item)
		else:
			for ci in range(len(self.columnMap)):
				vf = _valueFuncs[self.columnMap[ci]]
				for i, item in enumerate(self.items):
					curVal = vf(item)
					prevVal = self._prevValues[(i, ci)]
					if isinstance(curVal, tuple):
						for vi in range(len(curVal)):
							valItem = curVal[vi]
							if callable(valItem) and not isinstance(valItem,
									GroupAttr):
								continue
							pv = prevVal[vi]
							if type(valItem) != type(pv) or valItem != pv:
								break
						else:
							# equal
							continue
					elif curVal == prevVal:
						continue
					self._prevValues[(i, ci)] = curVal
					hlist.item_configure(i, ci, **self._hlistKw(item, ci))
		# if only one item, select it
		if defaultable and len(self.items) == 1:
			selected = self.items
		for item in selected:
			if item not in self.items:
				continue
			hlist.selection_set(self.items.index(item))
		self._selChange(None)

	def _getConfig(self):
		"""retrieve configuration preferences"""

		# set up configuration dialog
		from confDialog import ConfDialog
		self._confDialog = ConfDialog(self)
		self._confDialog.Close()

	def _hlistKw(self, item, colNum):
		vt = _valueTypes[self.columnMap[colNum]]
		vf = _valueFuncs[self.columnMap[colNum]]
		kw = {'itemtype': vt}
		txt = None
		img = None
		val = vf(item)
		if isinstance(val, set) and vt not in ['toggle', 'well']:
			return {}
		from Group import GroupAttr
		if vt == 'text':
			txt = val
			if isinstance(txt, GroupAttr):
				testable = list(txt.vals)[0]
			else:
				testable = txt
			if not isinstance(testable, basestring):
				txt, bcolor = txt
				if bcolor is not None:
					if not isinstance(bcolor, basestring):
						if hasattr(bcolor, 'rgba'):
							rgba = bcolor.rgba()
						else:
							rgba = bcolor
						from CGLtk.color import rgba2tk
						bcolor = rgba2tk(rgba)
						fcolor = CGLtk.textForeground(
							bcolor, self.itemTable)
					kw['style'] = Tix.DisplayStyle("text",
						refwindow=self.itemTable,
						background=bcolor,
						foreground=fcolor,
						selectforeground=bcolor)
			else:
				kw['style'] = self.textStyle
		elif vt == 'image':
			img = val
		elif vt == 'imagetext':
			img, txt = val
		elif vt == 'toggle':
			kw['itemtype'] = 'window'
			truth, cb = val
			togKw = {'command':
				# avoid holding references to model
				lambda cb=cb, i=self.items.index(item),
					nt=isinstance(truth, GroupAttr) or not truth:
					cb(self.items[i], nt),
				'indicatoron': 0,
				'borderwidth': 0}
			if isinstance(truth, GroupAttr):
				togKw['image'] = self.itemTable.tk.call(
					'tix', 'getimage', 'ck_onoff_37')
			elif truth:
				togKw['image'] = self.itemTable.tk.call(
					'tix', 'getimage', 'ck_on')
			else:
				togKw['image'] = self.itemTable.tk.call(
					'tix', 'getimage', 'ck_off')
			toggle = Tkinter.Checkbutton(
						self.itemTable.hlist, **togKw)
			kw['window'] = toggle
			kw['style'] = self.checkButtonStyle
		elif vt == 'well':
			color, noneOkay, alphaOkay, cb = val
			if color is False:
				kw['itemtype'] = 'text'
				txt = ""
			else:
				kw['itemtype'] = 'window'
				if isinstance(color, chimera.MaterialColor):
					color = color.rgba()
				from weakref import proxy
				def wellCB(clr, cb=cb, mdl=proxy(item)):
					if clr is not None:
						clr = chimera.MaterialColor(
									*clr)
					cb(mdl, clr)
				from CGLtk.color.ColorWell import ColorWell
				kw['window'] = ColorWell(self.itemTable.hlist,
					color, callback=wellCB,
					multiple=isinstance(color, GroupAttr),
					width=18, height=18,
					noneOkay=noneOkay, wantAlpha=alphaOkay)
				kw['style'] = self.colorWellStyle
		else:
			raise ValueError("Unknown column type: '%s'" % vt)
		
		if txt != None:
			kw['text'] = unicode(txt)
		if img != None:
			kw['image'] = self.itemTable.tk.call(
							'tix', 'getimage', img)
		return kw
	
	def _itemSort(self, i1, i2):
		def getVal(vals):
			if isinstance(vals, set):
				return min(vals)
			return vals
		id1 = getVal(i1.id)
		id2 = getVal(i2.id)
		if id1 < id2:
			return -1
		if id1 > id2:
			return 1
		subid1 = getVal(i1.subid)
		subid2 = getVal(i2.subid)
		if subid1 < subid2:
			return -1
		if subid1 > subid2:
			return 1
		return 0

	def _rememberSize(self, event):
		w, h = event.width, event.height
		if min(w,h) < 20:
			return
		inch = self.parent.winfo_fpixels("1i")
		self._confDialog.prefs["table w/h"] = (w/inch, h/inch)

	def _requestUpdate(self, *triggerArgs):
		# Rebuilding the table can be slow if there are many open models.
		# Consequently, if a script is opening/closing/changing models in
		# such a scenario the script can be slowed down a lot.
		# So we slow down the rebuild to try to allow all such triggers to
		# fire first.  Conversely, slowing down the rebuild also slows down
		# interactive response (the active/shown button are three-state and
		# therefore don't update until the table is rebuillt), so slow it down
		# proportional to the number of open models.

		if self._updateHandler:
			self.parent.after_cancel(self._updateHandler)
		self._triggerArgs = triggerArgs
		# after_idle() doesn't seem to suppress any updates
		delay = min(max(1, len(self.items)), 500)
		self._updateHandler = self.parent.after(delay, self._doUpdate)

	def _selChange(self, item):
		# slow browse callback interferes with double-click detection,
		# so delay callback enough to allow most double-clicks to work
		if hasattr(self, '_selChangeIdle') and self._selChangeIdle:
			self.parent.after_cancel(self._selChangeIdle)
		self._selChangeIdle = self.parent.after(300, self._selChangeCB)

	def _selChangeCB(self):
		numSel = len(self.itemTable.hlist.info_selection())
		allButtons = _buttonInfo.keys()
		favs = self._confDialog.prefs["favorites"]
		for buttons, actionButtons in [
				([b for b in allButtons if favs[b]], self.favActionButtons),
				(allButtons, self.allActionButtons)]:
			for b in buttons:
				state = 'normal'
				callback, minModels, maxModels, moleculesOnly, \
					balloon, defaultFavorite, groupsOkay \
							= _buttonInfo[b]
				if self._shouldDisable(minModels, maxModels,
								moleculesOnly):
					state = 'disabled'
				actionButtons.button(b).config(state=state)
		self._selChangeIdle = None

	def _shouldDisable(self, minModels, maxModels, moleculesOnly):
		if moleculesOnly:
			numSel = len(self.selected(moleculesOnly=True))
		else:
			numSel = len(self.itemTable.hlist.info_selection())
		if minModels != None and numSel < minModels \
		or maxModels != None and numSel > maxModels:
			return 1
		return 0

	def _showActions(self, actionButtons):
		if actionButtons == self._shownActions:
			return
		if self._shownActions:
			if actionButtons == self.favActionButtons:
				self.allActionButtons.grid_remove()
				self.allTitleFrame.grid_remove()
			else:
				self.favActionButtons.grid_remove()
				self.allTitleFrame.grid()
				bw = actionButtons.buttonWidth()
				lw = self.commandLabel.winfo_reqwidth()
				pad = (bw-lw) /2.0
				self.allTitleFrame.columnconfigure(0, minsize=pad)
				self.allTitleFrame.columnconfigure(2, minsize=pad)
		actionButtons.grid()
		self.buttonScroll.component('clipper').configure(
						width=actionButtons.clipWidth()+2, height='2i')
		if chimera.tkgui.windowSystem == 'aqua':
			# work around bug where Aqua would behave as if the
			# scroller was to the right of its actual position
			# once the clipper was narrowed
			def later(tl = self.allTitleFrame.winfo_toplevel()):
				tl.wm_geometry(tl.wm_geometry())
			self.allTitleFrame.after(100, later)
		self.buttonScroll.yview(mode='moveto', value=0.0)
		self._shownActions = actionButtons

	def _showButton(self, name):
		kw, balloon, defaultFavorite = self._buttonParams(name)
		favPrefs = self._confDialog.prefs['favorites']
		names = self.allButtonsCreated
		actionButtons = self.allActionButtons
		names.append(name)
		names.sort(lambda a, b: cmp(a.lower(), b.lower()))
		index = names.index(name)
		if index == len(names)-1:
			addFunc = actionButtons.add
		else:
			addFunc = actionButtons.insert
			kw['beforeComponent'] = names[index+1]

		but = addFunc(name, **kw)
		but.config(default='disabled')
		if balloon:
			help.register(but, balloon=balloon)
		if favPrefs.get(name, defaultFavorite):
			self._favButton(name, True)

if not chimera.nogui:
	class FavButtonBox(Pmw.ButtonBox):
		def __init__(self, *args, **kw):
			Pmw.ButtonBox.__init__(self, *args, **kw)

		def clipWidth(self):
			maxWidth = 0
			for i in range(self.numbuttons()):
				w = self.button(i).winfo_reqwidth()
				if w > maxWidth:
					maxWidth = w
			return maxWidth

		buttonWidth = clipWidth

	class AllButtonBox(Tkinter.Frame):
		def __init__(self, master, modelPanel):
			Tkinter.Frame.__init__(self, master)
			self.__rowInfo = {}
			self.__modelPanel = modelPanel
			self.__maxButtonWidth = 0

		def add(self, name, **buttonKw):
			return self.__addButton(name, len(self.__rowInfo), **buttonKw)

		def button(self, name):
			return self.__rowInfo[name][2]

		def clipWidth(self):
			if self.__rowInfo:
				return self.__maxButtonWidth + self.__checkWidth
			return 0

		def buttonWidth(self):
			return self.__maxButtonWidth

		def insert(self, name, beforeComponent=None, **buttonKw):
			at = self.__rowInfo[beforeComponent][0]
			for bname, info in self.__rowInfo.items():
				row, frame, button, check = info
				if row >= at:
					frame.grid_forget()
					frame.grid(row=row+1, column=0)
					self.__rowInfo[bname][0] += 1
			return self.__addButton(name, at, **buttonKw)

		def __addButton(self, name, row, **buttonKw):
			f = Tkinter.Frame(self)
			f.grid(row=row, column=0)
			b = Tkinter.Button(f, text=name, **buttonKw)
			b.grid(row=0, column=0, sticky="ew")
			bw = b.winfo_reqwidth()
			if bw > self.__maxButtonWidth:
				for info in self.__rowInfo.values():
					info[1].columnconfigure(0, minsize=bw)
				self.__maxButtonWidth = bw
			else:
				f.columnconfigure(0, minsize=self.__maxButtonWidth)
			chkKw = {'command': lambda nm=name, s=self: s.__changeFav(nm),
				'indicatoron': 0, 'pady': 0,
				'borderwidth': 0}
			isFav = self.__modelPanel._confDialog.prefs['favorites'][name]
			if isFav:
				chkKw['image'] = f.tk.call('tix', 'getimage', 'ck_on')
			else:
				chkKw['image'] = f.tk.call('tix', 'getimage', 'ck_off')
			if chimera.tkgui.windowSystem == 'aqua':
				chkKw['relief'] = 'flat'
				chkKw['bd'] = 0
			check = Tkinter.Checkbutton(f, **chkKw)
			self.__checkWidth = check.winfo_reqwidth()
			check.grid(row=0, column=1)
			self.__rowInfo[name] = [row, f, b, check]
			return b

		def __changeFav(self, name):
			favs = self.__modelPanel._confDialog.prefs['favorites']
			fav = favs[name]
			self.__modelPanel._favButton(name, not fav)
			favsCopy = favs.copy()
			favsCopy[name] = not fav
			self.__modelPanel._confDialog.prefs['favorites'] = favsCopy
			chk = self.__rowInfo[name][-1]
			if fav:
				chk.configure(image=chk.tk.call('tix', 'getimage', 'ck_off'))
			else:
				chk.configure(image=chk.tk.call('tix', 'getimage', 'ck_on'))

from chimera import dialogs
dialogs.register(ModelPanel.name, ModelPanel)

def _setAttr(m, field, value, openState=0):
	if openState:
		setattr(m.openState, field, value)
	else:
		setattr(m, field, value)

# functions used in model panel button; could be called directly also
def setModelField(models, field, value, openState=0):
	for m in models:
		_setAttr(m, field, value, openState)

def setModelFieldOnly(models, field, onVal=1, offVal=0, openState=0):
	# turn off first, then on, so that models not in the models list
	# that nonetheless have shared openStates get the 'on' value
	for m in openModels.list():
		_setAttr(m, field, offVal, openState)
	for m in models:
		_setAttr(m, field, onVal, openState)

def toggleModelField(models, field, onVal=1, offVal=0, openState=0):
	openStates = {}
	for m in models:
		if openState:
			openStates[m.openState] = 1
			continue
		if curval == onVal:
			_setAttr(m, field, offVal, openState)
		else:
			_setAttr(m, field, onVal, openState)
	for os in openStates.keys():
		if getattr(os, field) == onVal:
			setattr(os, field, offVal)
		else:
			setattr(os, field, onVal)

_prevActivities = None
def activateAllCmd():
	"""Activate all models.  Restore previous activities if called again."""

	global _prevActivities
	if _prevActivities:
		for m in openModels.list():

			if _prevActivities.has_key(m.openState):
				m.openState.active = _prevActivities[
								m.openState]
		_prevActivities = None
		if _mp:
			butText = 'activate all'
	else:
		_prevActivities = {}
		for m in openModels.list():
			if _prevActivities.has_key(m.openState):
				continue
			_prevActivities[m.openState] = m.openState.active
			m.openState.active = 1
		if _mp:
			butText = 'restore activities'
	if _mp:
		favPrefs = _mp._confDialog.prefs['favorites']
		if favPrefs['activate all']:
			_mp.favActionButtons.component('activate all').config(text=butText)
		_mp.allActionButtons.button('activate all').config(text=butText)

def _filterSkipped():
	return [m for m in chimera.openModels.list() if not getattr(m, '_mp_skip', False)]

def _activateLowest(models):
	minID = min([m.id for m in models])
	for m in _filterSkipped():
		m.openState.active = m.id == minID
		if m.openState.active:
			from chimera import replyobj
			replyobj.status(m.name, secondary=True)

def _activateHighest(models):
	maxID = max([m.id for m in models])
	for m in _filterSkipped():
		m.openState.active = m.id == maxID
		if m.openState.active:
			from chimera import replyobj
			replyobj.status(m.name, secondary=True)

def activateNextCmd():
	"""Activate next model, deactivating others."""
	models = _filterSkipped()
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
		_activateLowest(models)
		return
	activeID = list(activeIDs)[0]
	higherModels = [m for m in models if m.id > activeID]
	if not higherModels:
		_activateLowest(models)
		return
	_activateLowest(higherModels)

def activatePreviousCmd():
	"""Activate previous model, deactivating others."""
	models = _filterSkipped()
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
		_activateLowest(models)
		return
	activeID = list(activeIDs)[0]
	lowerModels = [m for m in models if m.id < activeID]
	if not lowerModels:
		_activateHighest(models)
		return
	_activateHighest(lowerModels)

def _displayLowest(models):
	minID = min([m.id for m in models])
	for m in _filterSkipped():
		m.display = m.id == minID
		if m.display:
			from chimera import replyobj
			replyobj.status(m.name, secondary=True)

def _displayHighest(models):
	maxID = max([m.id for m in models])
	for m in _filterSkipped():
		m.display = m.id == maxID
		if m.display:
			from chimera import replyobj
			replyobj.status(m.name, secondary=True)

def displayNextCmd():
	"""Activate next model, deactivating others."""
	models = _filterSkipped()
	if not models:
		return
	allIDs = set([m.id for m in models])
	if len(allIDs) == 1:
		for m in models:
			m.display = True
		return
	# if multiple shown, show only lowest
	shownIDs = set([m.id for m in models if m.display])
	if len(shownIDs) != 1:
		_displayLowest(models)
		return
	shownID = list(shownIDs)[0]
	higherModels = [m for m in models if m.id > shownID]
	if not higherModels:
		_displayLowest(models)
		return
	_displayLowest(higherModels)

def displayPreviousCmd():
	"""Activate previous model, deactivating others."""
	models = _filterSkipped()
	if not models:
		return
	allIDs = set([m.id for m in models])
	if len(allIDs) == 1:
		for m in models:
			m.display = True
		return
	# if multiple shown, show only lowest
	shownIDs = set([m.id for m in models if m.display])
	if len(shownIDs) != 1:
		_displayLowest(models)
		return
	shownID = list(shownIDs)[0]
	lowerModels = [m for m in models if m.id < shownID]
	if not lowerModels:
		_displayHighest(models)
		return
	_displayHighest(lowerModels)

_attrInspectors = {}
_headers = {}
_seqInspectors = {}
_inspectors = [_attrInspectors, _headers] # _seqInspectors is per chain

def _checkTrigger():
	global _modelTrigger
	for inspDict in _inspectors:
		if len(inspDict) > 0:
			break
	else:
		# should be no trigger active; start one
		_modelTrigger = chimera.triggers.addHandler(
						'Model', _modelTriggerCB, None)

def attributesCmd(models):
	global _attrInspectors
	_checkTrigger()
	for model in models:
		if not _attrInspectors.has_key(model):
			from modelInspector import ModelInspector
			_attrInspectors[model] = ModelInspector(model)
		_attrInspectors[model].enter()

def seqCmd(items):
	global _seqInspectors
	todo = []
	for item in items[:]:
		if not _seqInspectors.has_key(item):
			from chimera.Sequence import StructureSequence
			if isinstance(item, StructureSequence):
				copySeq = StructureSequence.__copy__(item)
				copySeq.name = item.fullName()
				_addSeqInspector(item, mavSeq=copySeq)
			else:
				seqs = item.sequences()
				if seqs:
					todo.extend(seqs)
				else:
					items.remove(item)
				continue
		_seqInspectors[item].enter()
	if todo:
		if len(todo) > 1:
			from seqPanel import SeqPickerDialog
			from chimera import dialogs
			d = dialogs.display(SeqPickerDialog.name)
			d.molListBox.setvalue(todo)
		else:
			seqCmd(todo)
	else:
		# if handed only sequences...
		return [_seqInspectors[item] for item in items]

def _addSeqInspector(item, mavSeq=None, mav=None):
	global _seqInspectors, _saveSessionTrigger
	if not _seqInspectors:
		from SimpleSession import SAVE_SESSION
		_saveSessionTrigger = chimera.triggers.addHandler(
				SAVE_SESSION, _saveSessionCB, None)
	trigMav = []
	hid = item.triggers.addHandler(item.TRIG_DELETE,
			lambda tn, md, td: md[0].Quit(), trigMav)
	def quitCB(mav, i=item, h=hid):
		del _seqInspectors[i]
		i.triggers.deleteHandler(i.TRIG_DELETE, h)
		if not _seqInspectors:
			from SimpleSession import SAVE_SESSION
			chimera.triggers.deleteHandler(SAVE_SESSION, _saveSessionTrigger)
	if mav:
		mav.quitCB = quitCB
	else:
		from MultAlignViewer.MAViewer import MAViewer
		if mavSeq.descriptiveName:
			title = "chain %s: %s" % (mavSeq.chainID, mavSeq.descriptiveName)
		else:
			title = mavSeq.name
		mav = MAViewer([mavSeq], title=title, quitCB=quitCB,
						autoAssociate=None, sessionSave=False)
	_seqInspectors[item] = mav
	trigMav.append(mav)

def _modelTriggerCB(trigName, myArg, modelsChanges):
	for model in modelsChanges.deleted:
		for inspDict in _inspectors:
			if inspDict.has_key(model):
				_deleteInspector(model, inspDict)

def _saveSessionCB(trigName, myArg, session):
	from SimpleSession import sessionID, sesRepr
	info = []
	for seq, mav in _seqInspectors.items():
		info.append((seq.name, sessionID(seq.molecule),
			[seq.saveInfo() for seq in mav.seqs], mav.saveInfo()))
	print>>session, """
try:
	from ModelPanel import restoreSeqInspectors
	restoreSeqInspectors(%s)
except:
	reportRestoreError("Error restoring sequence viewers")
""" % sesRepr(info)

def restoreSeqInspectors(info):
	global _seqInspectors
	from SimpleSession import idLookup
	for seqName, molID, seqsInfo, mavInfo in info:
		mol = idLookup(molID)
		for seq in mol.sequences():
			if seq.name == seqName:
				break
		else:
			continue
		if seq in _seqInspectors:
			continue

		from MultAlignViewer.MAViewer import restoreMAV
		from chimera.Sequence import restoreSequence
		mav = restoreMAV([restoreSequence(seqInfo)
						for seqInfo in seqsInfo], mavInfo)
		_addSeqInspector(seq, mav=mav)

def _deleteInspector(model, dict):
	inspector = dict[model]
	del dict[model]
	for inspDict in _inspectors:
		if len(inspDict) > 0:
			break
	else:
		# no inspectors; drop triggers
		chimera.triggers.deleteHandler('Model', _modelTrigger)
	if hasattr(inspector, 'destroy'):
		inspector.destroy()
	else:
		inspector._toplevel.destroy()

def backboneCmd(models, resTrace=1):
	from chimera.misc import displayResPart
	for m in models:
		if not hasattr(m, 'residues'):
			continue
		if resTrace:
			displayResPart(m.residues, trace=1)
		else:
			displayResPart(m.residues, backbone=1)

def focusCmd(models):
	from chimera import openModels, viewer, update
	shown = {}
	for m in openModels.list():
		shown[m] = m.display
		if m in models:
			m.display = 1
		else:
			m.display = 0
	update.checkForChanges()
	viewer.viewAll()
	if chimera.openModels.cofrMethod != chimera.OpenModels.Independent:
		openModels.cofrMethod = openModels.CenterOfView
		viewer.clipping = True

	for m,disp in shown.items():
		m.display = disp
	update.checkForChanges()

_groups = []
_groupNameCache = {}
def groupCmd(items, name=None):
	from Group import Group
	removeGroups = []
	addItems = []
	newGroup = None
	if len(items) == 1:
		item = items[0]
		if isinstance(item, Group):
			removeGroups.append(item)
			addItems.extend(item.components)
			sel = item.components
		else:
			from chimera import UserError
			raise UserError("Cannot group a single model.")
	else:
		models = []
		for item in items:
			if isinstance(item, Group):
				removeGroups.append(item)
				models.extend(item.models)
			else:
				models.append(item)
		global _groupNameCache
		models.sort()
		key = tuple([id(m) for m in models])
		if name is None:
			if key in _groupNameCache:
				name = _groupNameCache[key]
			else:
				name = getGroupName(items)
		_groupNameCache[key] = name
		newGroup = Group(items, name)
		addItems.append(newGroup)
		sel = addItems
	if _mp:
		selected = _mp.selected()
		for rg in removeGroups:
			_mp.items.remove(rg)
		_mp.items.extend(addItems)
		_mp._fillTable(fromScratch=True, selected=selected)
		_mp.selectionChange(sel)
	else:
		if addItems:
			addGroups = [ai for ai in addItems if isinstance(ai, Group)]
			_groups.extend(addGroups)
			if _groups and _groups == addGroups:
				# track Model deletions
				def checkGroups(tname, myData, tdata):
					if tdata.deleted:
						newGroups = []
						for group in _groups:
							group.update()
							if group.models:
								newGroups.append(group)
						_groups[:] = newGroups
						if not _groups:
							from chimera.triggerSet import ONESHOT
							return ONESHOT
				chimera.triggers.addHandler('Model', checkGroups, None)
		if removeGroups:
			for rg in removeGroups:
				_groups.remove(rg)
	return newGroup

def getGroupOf(model):
	if not _mp:
		raise RuntimeError("Model Panel not yet created")
	from Group import Group
	for item in _mp.items:
		if isinstance(item, Group):
			if model in item.models:
				return item
		elif item == model:
			return None
	raise ValueError("Model not in model panel at all")

def _saveGroups(trigName, myData, sessionFile):
	from Group import Group
	if not chimera.nogui and _mp:
		# if model panel is waiting to update, cancel that and
		# immediately update
		if _mp._updateHandler:
			_mp.parent.after_cancel(_mp._updateHandler)
			_mp._doUpdate()
		groups = [g for g in _mp.items if isinstance(g, Group)]
	else:
		groups = _groups
	if not groups:
		return
	from SimpleSession import sessionID
	def _repr(grp):
		strings = []
		from ModelPanel.Group import Group
		for c in grp.components:
			if isinstance(c, Group):
				strings.append("groupCmd(%s)" % _repr(c))
			else:
				try:
					minfo = sessionID(c)
				except:
					minfo = (c.id, c.subid, c.__class__.__name__)
				strings.append("_mpGetModel(%s)" % repr(minfo))
		return "[%s], name=%s" % (", ".join(strings), repr(grp.name))
	print>>sessionFile, """
try:
	def _mpAfterModels():
		def _mpGetModel(info):
			from SimpleSession import modelMap, idLookup
			if isinstance(info, tuple) and len(info) == 3:
				id, subid, className = info
				return [m for m in modelMap[(id, subid)]
					if m.__class__.__name__ == className][0]
			return idLookup(info)
		from ModelPanel import groupCmd
"""
	for grp in groups:
		print>>sessionFile, "\t\tgroupCmd(%s)" % _repr(grp)
	print>> sessionFile, """
	registerAfterModelsCB(_mpAfterModels)
	del _mpAfterModels
except:
	reportRestoreError("Error restoring model panel groups")
"""
from SimpleSession import SAVE_SESSION
chimera.triggers.addHandler(SAVE_SESSION, _saveGroups, None)

from chimera.baseDialog import ModalDialog
class GroupNameDialog(ModalDialog):
	buttons = ("OK",)
	default = "OK"
	help = "UsersGuide/modelpanel.html#group"

	def __init__(self, defName):
		self.defName = defName
		ModalDialog.__init__(self)

	def fillInUI(self, parent):
		import Pmw
		self.nameEntry = Pmw.EntryField(parent, labelpos='w', label_text=
			"Group name:")
		self.nameEntry.setentry(self.defName)
		self.nameEntry.component('entry').select_range(0, 'end')
		self.nameEntry.component('entry').focus()
		self.nameEntry.grid(sticky="ew")

	def OK(self):
		self.Cancel(self.nameEntry.getvalue())

def getGroupName(items):
	defName = defaultGroupName(items)
	if chimera.nogui:
		return defName
	master = _mp and _mp.uiMaster().winfo_toplevel() or chimera.tkgui.app
	return GroupNameDialog(defName).run(master)

groupCounter = 0
def defaultGroupName(items):
	global groupCounter
	groupCounter += 1
	name = "Group %d" % groupCounter
	names = set([item.name for item in items])
	if len(names) == 1:
		name = names.pop()
		if not (len(name) == 4 and name[0].isdigit()
				and name[1:].isalnum()):
			# not PDB ID
			name = plural(name)
	else:
		import os.path
		prefix = os.path.commonprefix(names)
		if len(prefix) > 2:
			for n in names:
				if len(n) > len(prefix) and n[len(prefix)].isalpha():
					break
			else:
				name = plural(prefix)
	return name

def plural(text):
	if not text:
		return text
	if text[-1] == 's':
		if text[-2:] == "ss":
			return text + "es"
		else:
			return text
	if text[-1] == 'h':
		if text[-2:-1] in "cs":
			return text + "es"
		else:
			return text + "s"
	if text[-1] in "oxz":
		return text + "es"
	return text + "s"

def noteCmd(models):
	from noteDialog import NoteDialog
	NoteDialog(models)

def renameCmd(items):
	from renameDialog import RenameDialog
	RenameDialog(items)

def selectCmd(models):
	sel = chimera.selection.ItemizedSelection()
	sel.add(models)
	chimera.tkgui.selectionOperation(sel)
	
def showAllAtomsCmd(models):
	for m in models:
		if not hasattr(m, 'atoms') or not hasattr(m, 'bonds'):
			continue
		m.display = 1
		for a in m.atoms:
			a.display = 1

def surfCmd(models, category):
	import Midas
	mols = filter(lambda m: isinstance(m, chimera.Molecule), models)
	Midas.surfaceNew(category, models=mols)
	for m in mols:
		for a in m.atoms:
			if a.surfaceCategory == category:
				a.surfaceDisplay = 1

def _getModels(item):
	# VolumeModel has a 'models' attr(!), so...
	if isinstance(item, Group):
		return item.models
	return [item]
