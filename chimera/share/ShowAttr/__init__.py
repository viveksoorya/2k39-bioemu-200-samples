# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42364 2022-01-26 21:27:48Z pett $

import chimera
from chimera import selection, Molecule
from chimera.baseDialog import ModelessDialog
from SimpleSession import isRegisteredAttribute
import Tkinter, Pmw
from prefs import prefs, TARGET, \
	ATTRS_ATOMS, ATTRS_RESIDUES, ATTRS_MOLECULES, ATTRS_SEGREGIONS, \
	COLORS, COLOR_ATOMS, COLOR_RIBBONS, COLOR_SURFACES, SCALING,\
	ATOM_STYLE, ATOM_RADII, NOVAL_RADIUS, WORM_RADII, NOVAL_WORM, \
	WORM_STYLE, RESTRICT
from CGLtk.optCascade import CascadeOptionMenu

class AtomAttrs:
	menuName = 'atoms'
	prefName = ATTRS_ATOMS
	colorAtoms = True
	colorRibbons = False
	modelType = Molecule
	def __init__(self):
		self.screenedAttrs = {
			'name': False, 'idatmIsExplicit': False,
			'idatmType': str,
			'drawMode': False, 'hide': False, 'label': False,
			'numBonds': False, 'minimumLabelRadius': False,
			'surfaceDisplay': False, 'vdw': False,
			'selLevel': False, 'surfaceOpacity': False,
			'serialNumber': False, 'defaultRadius': False,
			'radius': False, 'coordIndex': False
			}
		self.screenedSubAttrs = set()
		self.ctype = None
	def selectedObjects(self):
		return selection.currentAtoms()
	def objectId(self, o, level):
		return o.oslIdent(level)
	def modelObjects(self, models):
		items = []
		for model in models:
			items.extend(model.atoms)
		return items
	def objectsInModels(self, objects, models):
		mSet = set(models)
		items = [a for a in objects if a.molecule in mSet]
		return items
	def sortObjects(self, objList):
		from chimera.misc import oslCmp
		objList.sort(lambda a1, a2:
			     oslCmp(a1.oslIdent(), a2.oslIdent()))
	def childObjects(self):
		return []
	def childType(self):
		return self.ctype
	def colorItem(self, item, c, oc, **kw):
		if kw['colorAtoms']:
			if kw['opaqueAtoms']:
				item.color = oc
			else:
				item.color = c
		if kw['colorSurfaces']:
			item.surfaceColor = c
			item.surfaceOpacity = -1
			item.vdwColor = c
	def setRadius(self, item, rad, style, restrict = None):
		if not restrict or item in restrict:
			item.radius = rad
			item.drawMode = style
atomAttrs = AtomAttrs()
	
class ResidueAttrs:
	menuName = 'residues'
	prefName = ATTRS_RESIDUES
	colorAtoms = True
	colorRibbons = True
	modelType = Molecule
	def __init__(self, childType = None):
		self.screenedAttrs = {
			'name': False, 'ribbonDisplay': False, 'isSheet': False,
			'ribbonDrawMode': False, 'selLevel': False,
			'ringMode': False, 'numAtoms': False,
			'ssId': False, 'fillMode': False, 'fillDisplay': False,
			'uniprotIndex': False, 'heavyAtomCount': False,
			}
		self.screenedSubAttrs = set()
		self.ctype = childType
	def selectedObjects(self):
		return selection.currentResidues()
	def objectId(self, o, level):
		return o.oslIdent(level)
	def modelObjects(self, models):
		items = []
		for model in models:
			items.extend(model.residues)
		return items
	def objectsInModels(self, objects, models):
		mset = set(models)
		items = [r for r in objects if r.molecule in mset]
		return items
	def sortObjects(self, objList):
		from chimera.misc import oslCmp
		objList.sort(lambda r1, r2:
			     oslCmp(r1.oslIdent(), r2.oslIdent()))
	def childObjects(self, object):
		return object.oslChildren()
	def childType(self):
		return self.ctype
	def colorItem(self, item, c, oc, **kw):
		if kw['colorRibbons']:
			if kw['opaqueRibbons']:
				item.ribbonColor = oc
			else:
				item.ribbonColor = c
		if kw['colorAtoms'] or kw['colorSurfaces']:
			for a in item.atoms:
				if kw['colorAtoms']:
					if kw['opaqueAtoms']:
						a.color=oc
					else:
						a.color=c
				if kw['colorSurfaces']:
					a.surfaceColor=c
					a.surfaceOpacity = -1
					a.vdwColor=c
	def setRadius(self, item, rad, style, restrict = None):
		for a in item.atoms:
			if not restrict or a in restrict:
				a.radius = rad
				a.drawMode = style
	def setWormRadius(self, item, rad, style, restrict = None):
		if not restrict or item in restrict:
			item.ribbonDrawMode = chimera.Residue.Ribbon_Round
			item.ribbonDisplay = True
			item.ribbonStyle = style
residueAttrs = ResidueAttrs(atomAttrs)

class MoleculeAttrs:
	menuName = 'molecules'
	prefName = ATTRS_MOLECULES
	colorAtoms = True
	colorRibbons = True
	modelType = Molecule
	def __init__(self, childType = None):
		self.screenedAttrs = {
			'autochain': False, 'ballScale': False,
			'lineType': False,
			'lineWidth': False, 'id': False, 'subid': False,
			'pointSize': False, 'ribbonHidesMainchain': False,
			'selLevel': False, 'showStubBonds': False,
			'stickScale': False, 'structureAssigned': False,
			'surfaceOpacity': False, 'vdwDensity': False,
			'clipThickness': False, 'aromaticLines': False,
			'aromaticLineType': False, 'idatmValid': False,
			'lowerCaseChains': False, 'useClipPlane': False,
			'useClipThickness': False, 'aromaticMode': False,
			'aromaticDisplay': False, 'residueLabelPos': False,
			'numBonds': False, 'pdbVersion': False,
			'ribbonSmoothing': False, 'ribbonStiffness': False,
			'ribbonType': False, 'numAtoms': False,
			'numResidues': False
			}
		self.screenedSubAttrs = set(['phi', 'psi', 'chi1', 'chi2',
			'chi3', 'chi4', 'kdHydrophobicity'])
		self.ctype = childType
	def selectedObjects(self):
		return selection.currentMolecules(asDict=True)
	def objectId(self, o, level):
		return o.oslIdent(level)
	def modelObjects(self, models):
		return models
	def objectsInModels(self, objects, models):
		mset = set(models)
		items = [m for m in objects if m in mset]
		return items
	def sortObjects(self, objList):
		from chimera.misc import oslCmp
		objList.sort(lambda m1, m2:
			     oslCmp(m1.oslIdent(), m2.oslIdent()))
	def childObjects(self, object):
		return object.residues
	def childType(self):
		return self.ctype
	def colorItem(self, item, c, oc, **kw):
		if kw['colorRibbons']:
			for r in item.residues:
				if kw['opaqueRibbons']:
					r.ribbonColor = oc
				else:
					r.ribbonColor = c
		if kw['colorAtoms'] or kw['colorSurfaces']:
			for a in item.atoms:
				if kw['colorAtoms']:
					if kw['opaqueAtoms']:
						a.color = oc
					else:
						a.color = c
				if kw['colorSurfaces']:
					a.surfaceColor = c
					a.surfaceOpacity = -1
					a.vdwColor = c
	def setRadius(self, item, rad, style, restrict = None):
		for a in item.atoms:
			if not restrict or a in restrict:
				a.radius = rad
				a.drawMode = style
	def setWormRadius(self, item, rad, style, restrict = None):
		for r in item.residues:
			if not restrict or r in restrict:
				r.ribbonDrawMode = chimera.Residue.Ribbon_Round
				r.ribbonDisplay = True
				r.ribbonStyle = style
moleculeAttrs = MoleculeAttrs(residueAttrs)

from Segger.regions import Segmentation
class SegRegionAttrs:
	menuName = 'segmentation regions'
	prefName = ATTRS_SEGREGIONS
	colorAtoms = False
	colorRibbons = False
	modelType = Segmentation
	def __init__(self):
		self.screenedAttrs = {
			'mask_id':False, 'rid':False, 'smoothing_level':False,
			}
		self.screenedSubAttrs = set()
		self.ctype = None
	def selectedObjects(self):
		import Segger
		return Segger.SelectedRegions()
	def selectables(self, items):
		return [r.surface() for r in items if r.has_surface()]
	def objectId(self, r, level):
		id = ':%d' % r.rid
		if level == selection.SelGraph:
			id = r.segmentation.oslIdent(level) + id
		return id
	def modelObjects(self, models):
		items = []
		for model in models:
			items.extend(model.regions)
		return items
	def objectsInModels(self, objects, models):
		mset = set(models)
		items = [a for a in objects if a.segmentation in mset]
		return items
	def sortObjects(self, objList):
		objList.sort(lambda r1, r2: cmp(r1.rid, r2.rid))
	def childObjects(self):
		return []
	def childType(self):
		return self.ctype
	def colorItem(self, item, c, oc, **kw):
		item.set_color(c.rgba())
segRegionAttrs = SegRegionAttrs()
	
objectTypes = (atomAttrs, residueAttrs, moleculeAttrs, segRegionAttrs)

intTypes = [int, long]
floatTypes = [float]
from numpy import dtype
for bits in ["16", "32", "64", "128"]:
	for base in ["int", "uint"]:
		try:
			intTypes.append(dtype(base + bits))
		except TypeError:
			pass
	try:
		floatTypes.append(dtype("float" + bits))
	except TypeError:
		pass
numericTypes = intTypes + floatTypes

MODE_RENDER = "Render"
MODE_SELECT = "Select"
Modes = [MODE_RENDER, MODE_SELECT]

# Map object name to menu entry name.
attrsLabelMap = dict([(o, o.menuName) for o in objectTypes])
revAttrsLabelMap = dict([(o.menuName, o) for o in objectTypes])
attrsPrefMap = dict([(o.prefName, o) for o in objectTypes])

NO_ATTR = "choose attr"
NO_RENDER_DATA = "Choose attribute to show histogram"
NO_SELECT_DATA = "Choose attribute to show histogram/list"
MENU_VALUES_LABEL = "Values"

_LIST_NOVALUE = "(no value)"
class ShowAttrDialog(ModelessDialog):
	title = "Render/Select by Attribute"
	buttons = ('OK', 'Apply', 'Close')
	provideStatus = True
	name = "render/select attrs"
	help = "ContributedSoftware/render/render.html"

	dewormLabel = "non-worm"

	def __init__(self):
		self.models = []
		self.useableTypes = numericTypes
		self.additionalNumericTypes = () # boolean could be here instead
		self.additionalOtherTypes = (bool, basestring)
		self._attrVals = [None] * len(Modes)
		self._minVal = [None] * len(Modes)
		self._maxVal = [None] * len(Modes)
		ModelessDialog.__init__(self)
		chimera.triggers.addHandler(chimera.SCENE_TOOL_SAVE, self._sceneSave, None)
		chimera.triggers.addHandler(chimera.SCENE_TOOL_RESTORE, self._sceneRestore, None)

	def Apply(self):
		prefs[RESTRICT] = self.selRestrictVar.get()
		if self.modeNotebook.getcurselection() == MODE_SELECT:
			self._applySelect()
		else:
			fname = "_apply" + self.renderNotebook.getcurselection()
			getattr(self, fname)()

	def attrVals(self, mode=None):
		if mode is None:
			mode = self.modeNotebook.getcurselection()
		return self._attrVals[Modes.index(mode)]

	def configure(self, models=None, mode=None, attrsOf=None,
					attrName=None, fromModelListBox=False):
		curMenu = self._curAttrMenu()
		curAttr = curMenu.getvalue()
		curMode = self.modeNotebook.getcurselection()
		curTargetLabel = self.targetMenu.getvalue()
		curTarget = revAttrsLabelMap[curTargetLabel]
		if models != self.models and models is not None:
			newModels = None
			if fromModelListBox:
				oldSet = set(self.models)
				newSet = set(models)
				if newSet >= oldSet:
					newModels = newSet - oldSet
			else:
				self.modelListBox.setvalue(models,
							doCallback=False)
			self.models = models
			self._populateAttrsMenus(newModels=newModels)
			if not models or (curAttr is None and attrName is None):
				# _populateAttrsMenu has knocked the menu
				# button off of "choose attr"; arrange for
				# it to be restored...
				attrName = NO_ATTR
			if (mode == curMode or mode is None) \
			and (attrsOf == curTargetLabel or attrsOf is None) \
			and ([attrName] == curAttr or attrName is None):
				# no other changes
				if curAttr is not None:
					try:
						curMenu.invoke(curAttr)
					except ValueError:
						# attribute no longer present
						self._targetCB(curTargetLabel)

		if mode != curMode and mode is not None:
			self.modeNotebook.selectpage(mode)

		if attrsOf != curTargetLabel and attrsOf is not None:
			self.targetMenu.invoke(attrsOf)

		# prevent attr menu winding up on "choose attr"
		# even in attrName specified
		if self._needRefreshAttrs:
			self.refreshAttrs()

		# if an attribute name is specified, probably want an update...
		if attrName is not None:
			if attrName == NO_ATTR:
				self._targetCB(curTargetLabel)
				self.refreshMenu.entryconfigure(
					MENU_VALUES_LABEL, state="disabled")
			else:
				target = curTarget if attrsOf is None else revAttrsLabelMap[attrsOf]
				seen = self.seenAttrs[target]
				if attrName not in seen:
					self._populateAttrsMenus()
					seen = self.seenAttrs[target]
				if attrName in seen:
					if attrName in target.screenedAttrs:
						from chimera import replyobj
						replyobj.warning("Built-in attribute '%s' is"
							" automatically screened out of Render By"
							" Attribute menus" % attrName)
					else:
						self._curAttrMenu().invoke([attrName])
				else:
					self._targetCB(curTargetLabel)
				self.refreshMenu.entryconfigure(
					MENU_VALUES_LABEL, state="normal")

	def fillInUI(self, parent):
		top = parent.winfo_toplevel()
		menubar = Tkinter.Menu(top, type="menubar", tearoff=False)
		top.config(menu=menubar)

		fileMenu = Tkinter.Menu(menubar)
		menubar.add_cascade(label="File", menu=fileMenu)
		fileMenu.add_command(label="Save Attributes...",
					command=self._saveAttr)
		scalingMenu = Tkinter.Menu(menubar)
		menubar.add_cascade(label="Scaling", menu=scalingMenu)
		self.scalingVar = Tkinter.StringVar(parent)
		self.scalingVar.set(prefs[SCALING])
		scalingMenu.add_radiobutton(label="Logarithmic", value="log",
			command=self._scalingCB, variable=self.scalingVar)
		scalingMenu.add_radiobutton(label="Linear", value="linear",
			command=self._scalingCB, variable=self.scalingVar)

		refreshMenu = Tkinter.Menu(menubar)
		self.refreshMenu = refreshMenu
		menubar.add_cascade(label="Refresh", menu=refreshMenu)
		refreshMenu.add_command(label="Menus",
						command=self.refreshAttrs)
		def _cmdCB():
			menu = self._curAttrMenu()
			menu.invoke(menu.getvalue())
		refreshMenu.add_command(label=MENU_VALUES_LABEL, command=_cmdCB)

		from chimera.tkgui import aquaMenuBar
		aquaMenuBar(menubar, parent, row = 0, columnspan = 2)

		self.targetMenu = Pmw.OptionMenu(parent, command=self._targetCB,
				items=[o.menuName for o in objectTypes],
				labelpos='w', label_text="Attributes of")
		self.targetMenu.grid(row=1, column=0)

		from chimera.widgets import ModelScrolledListBox
		self._needRefreshAttrs = True
		self.modelListBox = ModelScrolledListBox(parent,
				selectioncommand=lambda: self.configure(
				models=self.modelListBox.getvalue(),
				fromModelListBox=True),
				filtFunc = self.filterModels,
				listbox_selectmode="extended",
				labelpos="nw", label_text="Models")
		self.modelListBox.grid(row=1, column=1, sticky="nsew")

		self._renderOkApply = True
		self._attrOkApply = dict.fromkeys(Modes, False)
		self.modeNotebook = Pmw.NoteBook(parent,
								raisecommand=self._pageChangeCB)
		self.modeNotebook.add(MODE_RENDER)
		self.modeNotebook.add(MODE_SELECT)
		self.modeNotebook.grid(row=2, column=0, columnspan=2,
								sticky="nsew")
		parent.rowconfigure(2, weight=1)
		parent.columnconfigure(1, weight=1)
		renderFrame = self.modeNotebook.page(MODE_RENDER)
		selectFrame = self.modeNotebook.page(MODE_SELECT)

		self.renderAttrsMenu = {}
		self.selectAttrsMenu = {}
		for o in objectTypes:
			self.renderAttrsMenu[o] = CascadeOptionMenu(renderFrame,
			command=lambda mi, o=o: self._compileAttrVals(o,
			mi), labelpos='w', label_text="Attribute:")
		for o in objectTypes:
			self.selectAttrsMenu[o] = CascadeOptionMenu(selectFrame,
			command=lambda mi, o=o: self._compileAttrVals(o,
			mi), labelpos='w', label_text="Attribute:")

		from CGLtk.Histogram import MarkedHistogram
		histKw = {
			'statusline': self.status,
			'minlabel': True,
			'maxlabel': True
		}
		if prefs[SCALING] == "log":
			histKw['scaling'] = 'logarithmic'
		else:
			histKw['scaling'] = 'linear'
		self.selFrames = []
		self.selHistFrame = Tkinter.Frame(selectFrame)
		self.selFrames.append(self.selHistFrame)
		self.selHistFrame.grid(row=1, column=0, sticky="nsew")
		self.selHistFrame.rowconfigure(0, weight=1)
		self.selHistFrame.columnconfigure(0, weight=1)
		self.selectHistogram = MarkedHistogram(self.selHistFrame,
			colorwell=False, showmarkerhelp=False, **histKw)
		self.selectHistogram['datasource'] = NO_SELECT_DATA
		self.selectHistogram.grid(row=0, column=0,
						columnspan=2, sticky="nsew")
		histKw['selectcallback'] = self._selMarkerCB
		self.renderHistogram = MarkedHistogram(renderFrame, **histKw)
		self.renderHistogram.grid(row=1, column=0, sticky="nsew")
		self.renderHistogram['datasource'] = NO_RENDER_DATA
		selModeTexts = ["between markers (inclusive)",
					"outside markers", "no value"]
		Tkinter.Label(self.selHistFrame, text="Select:").grid(
			row=1, rowspan=len(selModeTexts), column=0, sticky='e')
		self.selModeVar = Tkinter.IntVar(selectFrame)
		gridKw = { 'column': 1, 'sticky': 'w' }
		for i, text in enumerate(selModeTexts):
			b = Tkinter.Radiobutton(self.selHistFrame, text=text,
				value=i, variable=self.selModeVar)
			gridKw['row'] = i+1
			b.grid(**gridKw)
		self.selNoValueButtonInfo = (b, gridKw)
		self.selModeVar.set(0)

		self.selListFrame = Tkinter.Frame(selectFrame)
		self.selFrames.append(self.selListFrame)
		self.selListFrame.rowconfigure(0, weight=1)
		self.selListFrame.columnconfigure(0, weight=1)
		self.selectListBox = Pmw.ScrolledListBox(self.selListFrame,
					listbox_selectmode="multiple")
		self.selectListBox.grid(row=0, column=0, sticky="nsew")

		self.selBoolFrame = Tkinter.Frame(selectFrame)
		self.selFrames.append(self.selBoolFrame)
		self.selBoolVar = Tkinter.IntVar(selectFrame)
		self.selBoolVar.set(True)
		self.boolButtons = []
		for label in ["False", "True", "No value"]:
			self.boolButtons.append(Tkinter.Radiobutton(
						self.selBoolFrame, text=label,
						value=len(self.boolButtons),
						variable=self.selBoolVar))
			self.boolButtons[-1].grid(row=len(self.boolButtons)-1,
						column=0, sticky='w')

		renderFrame.rowconfigure(1, weight=1)
		renderFrame.columnconfigure(0, weight=1)
		selectFrame.rowconfigure(1, weight=1)
		selectFrame.columnconfigure(0, weight=1)

		self.renderColorMarkers = self.renderHistogram.addmarkers(
					activate=True, coordtype='relative')
		if len(prefs[COLORS]) == 1:
			self.renderColorMarkers.append(
						((0.5, 0.0), prefs[COLORS][0]))
		else:
			self.renderColorMarkers.extend(map(lambda e: ((e[0] /
				float(len(prefs[COLORS]) - 1), 0.0), e[1]),
				enumerate(prefs[COLORS])))
		self.renderRadiiMarkers = self.renderHistogram.addmarkers(
				newcolor='slate gray', activate=False,
				coordtype='relative')
		if len(prefs[ATOM_RADII]) == 1:
			self.renderRadiiMarkers.append(((0.5, 0.0), None))
		else:
			self.renderRadiiMarkers.extend(map(lambda e: ((e[0] /
				float(len(prefs[ATOM_RADII]) - 1), 0.0),
				None), enumerate(prefs[ATOM_RADII])))
		for i, rad in enumerate(prefs[ATOM_RADII]):
			self.renderRadiiMarkers[i].radius = rad
		self.renderWormsMarkers = self.renderHistogram.addmarkers(
			newcolor='pink', activate=False, coordtype='relative')
		if len(prefs[WORM_RADII]) == 1:
			self.renderWormsMarkers.append(((0.5, 0.0), None))
		else:
			self.renderWormsMarkers.extend(map(lambda e: ((e[0] /
				float(len(prefs[WORM_RADII]) - 1), 0.0),
				None), enumerate(prefs[WORM_RADII])))
		for i, rad in enumerate(prefs[WORM_RADII]):
			self.renderWormsMarkers[i].radius = rad
		self.selectMarkers = self.selectHistogram.addmarkers(
				coordtype='relative', minmarks=2, maxmarks=2)
		selMarkerColor = (0.0, 1.0, 0.0)
		self.selectMarkers.extend([((0.333, 0.0), selMarkerColor),
						((0.667, 1.0), selMarkerColor)])

		f = self.renderHistogram.component('widgetframe')
		self.radiusEntry = Pmw.EntryField(f, labelpos='w',
				validate={ 'validator': 'real', 'min': 0.001 },
				entry_width=7, entry_state='disabled')
		self.entryColumn = int(f.grid_size()[1])

		self.renderNotebook = Pmw.NoteBook(renderFrame)
		self.renderNotebook.add("Colors")
		self.renderNotebook.add("Radii")
		self.renderNotebook.add("Worms")
		self.renderNotebook.grid(row=2, column=0)

		self.selRestrictVar = Tkinter.IntVar(parent)
		self.selRestrictVar.set(prefs[RESTRICT])
		srbut = Tkinter.Checkbutton(renderFrame,
			variable=self.selRestrictVar,
			text="Restrict OK/Apply to current selection, if any")
		srbut.grid(row=3, column=0)

		f = self.renderNotebook.page("Colors")
		self.colorAtomsVar = Tkinter.IntVar(f)
		self.colorAtomsVar.set(prefs[COLOR_ATOMS])
		self.colorAtomsButton = Tkinter.Checkbutton(f, pady=0,
			text="Color atoms", variable=self.colorAtomsVar)
		self.colorAtomsButton.grid(row=0, column=0, sticky="w")
		self.opaqueAtomsVar = Tkinter.IntVar(f)
		self.opaqueAtomsVar.set(True)
		self.opaqueAtomsButton = Tkinter.Checkbutton(f, pady=0,
			text="Keep opaque", variable=self.opaqueAtomsVar)
		self.opaqueAtomsButton.grid(row=0, column=1)

		self.colorRibbonsVar = Tkinter.IntVar(f)
		self.colorRibbonsVar.set(prefs[COLOR_RIBBONS])
		self.colorRibbonsButton = Tkinter.Checkbutton(f, pady=0,
			text="Color ribbons", variable=self.colorRibbonsVar)
		self.colorRibbonsButton.grid(row=1, column=0, sticky='w')
		self.opaqueRibbonsVar = Tkinter.IntVar(f)
		self.opaqueRibbonsVar.set(True)
		self.opaqueRibbonsButton = Tkinter.Checkbutton(f, pady=0,
			text="Keep opaque", variable=self.opaqueRibbonsVar)
		self.opaqueRibbonsButton.grid(row=1, column=1)

		self.colorSurfacesVar = Tkinter.IntVar(f)
		self.colorSurfacesVar.set(prefs[COLOR_SURFACES])
		self.colorSurfacesButton = Tkinter.Checkbutton(f, pady=0,
			text="Color surfaces", variable=self.colorSurfacesVar)
		self.colorSurfacesButton.grid(row=2, column=0, sticky='w')

		from CGLtk.color.ColorWell import ColorWell
		self.noValueColorsFrame = Tkinter.Frame(f)
		self.noValueColorsFrame.gridKw = { "row": 3, "column": 0,
							"columnspan": 2 }
		self.noValueColorsFrame.grid(**self.noValueColorsFrame.gridKw)
		Tkinter.Label(self.noValueColorsFrame, text='No-value color:'
					).grid(row=0, column=0, sticky='e')
		self.noValueWell = ColorWell(self.noValueColorsFrame,
								noneOkay=True)
		self.noValueWell.grid(row=0, column=1, sticky='w')

		from SurfaceColor import gui_palette_names
		palettes = gui_palette_names.keys()
		palettes.sort()
		self.paletteMenu = Pmw.OptionMenu(f, command=self.setPalette,
			items=palettes, initialitem="Blue-Red", labelpos='w',
			label_text="Palette:")
		self.paletteMenu.component('menubutton').config(state="disabled")
		self.paletteMenu.grid(row=4, column=0, columnspan=2)

		self.reverseColorsButton = Tkinter.Button(f, pady=0, text=
			"Reverse threshold colors", state="disabled",
			command=self.reverseColors)
		self.reverseColorsButton.grid(row=5, column=0, columnspan=2)

		self.colorKeyButton = Tkinter.Button(f, pady=0, text=
			"Create corresponding color key", state="disabled",
			command=self._colorKeyCB)
		self.colorKeyButton.grid(row=6, column=0, columnspan=2)

		f = self.renderNotebook.page("Radii")
		self.radiiWarning = Tkinter.Label(f, text=
			"Radii can only be set for\n"
			"atom, residue or molecule attributes.")
		self.radiiWarning.grid() # for later setnaturalsize

		self.radiiFrame = Tkinter.Frame(f)
		from chimera.tkoptions import SymbolicEnumOption, \
						FloatOption, BooleanOption
		class AtomStyleOption(SymbolicEnumOption):
			labels = ["ball", "sphere"]
			values = [chimera.Atom.Ball, chimera.Atom.Sphere]
		self.atomStyle = AtomStyleOption(self.radiiFrame, 0,
				"Atom style", prefs[ATOM_STYLE], None, balloon=
				"How affected atoms will be depicted")
		self.doNoValueRadii = BooleanOption(self.radiiFrame, 1,
			"Affect no-value atoms", False, None, balloon=
			"Set radii for atoms not having this attribute\n"
			"or leave them as is")
		class RadiiOption(FloatOption):
			min = 0.001
		self.noValueRadii = RadiiOption(self.radiiFrame, 2,
			"No-value radius",
			prefs[NOVAL_RADIUS], None, balloon=
			"Atoms without this attribute will be given this radius")

		f = self.renderNotebook.page("Worms")
		self.wormsWarning = Tkinter.Label(f, text=
			"Worms can only be used with\n"
			"residue or molecule attributes.")
		self.wormsWarning.grid() # for later setnaturalsize

		self.wormsFrame = Tkinter.Frame(f)
		from chimera.tkoptions import EnumOption
		class WormStyleOption(EnumOption):
			values = ["smooth", "segmented", self.dewormLabel]
		self.wormStyle = WormStyleOption(self.wormsFrame, 0,
			"Worm style", prefs[WORM_STYLE], lambda o:
			self.renderNotebook.setnaturalsize(), balloon=
			"How worm radius changes between residues:\n"
			"   smooth: radius changes smoothly\n"
			"   segmented: radius changes abruptly")
		self.doNoValueWorm = BooleanOption(self.wormsFrame, 1,
			"Affect no-value residues", True, None, balloon=
			"Change worm representation for residues not having\n"
			"this attribute or leave them as is")
		self.noValueWorm = RadiiOption(self.wormsFrame, 2,
			"No-value worm radius", prefs[NOVAL_WORM], None,
			balloon="Residues without this attribute will\n"
			"be given this radius")
		self.renderNotebook.configure(raisecommand=self._raisePageCB)

		self.renderNotebook.setnaturalsize()
		self.modeNotebook.setnaturalsize()

		self.targetMenu.invoke(attrsPrefMap[prefs[TARGET]].menuName)

	def filterModels(self, model):
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		return isinstance(model, target.modelType)

	def histogram(self, frame=False):
		if self.modeNotebook.getcurselection() == MODE_RENDER:
			return self.renderHistogram
		if frame:
			return self.selHistFrame
		return self.selectHistogram

	def maxVal(self, mode=None):
		if mode is None:
			mode = self.modeNotebook.getcurselection()
		return self._maxVal[Modes.index(mode)]

	def minVal(self, mode=None):
		if mode is None:
			mode = self.modeNotebook.getcurselection()
		return self._minVal[Modes.index(mode)]

	def refreshAttrs(self):
		if not self.uiMaster().winfo_ismapped():
			# model-list widget is sleeping, delay update...
			self._needRefreshAttrs = True
			return
		self._needRefreshAttrs = False
		curMenu = self._curAttrMenu()
		curAttr = curMenu.getvalue()
		self._populateAttrsMenus()
		try:
			curMenu.index(curAttr)
		except ValueError:
			# attribute no longer present
			self._targetCB(self.targetMenu.getvalue())

	def reverseColors(self):
		if len(self.renderColorMarkers) < 2:
			return
		self.renderColorMarkers.sort()
		rgbas = [cm['rgba'] for cm in self.renderColorMarkers]
		rgbas.reverse()
		for cm, rgba in zip(self.renderColorMarkers, rgbas):
			cm['rgba'] = rgba

	def setPalette(self, paletteName):
		from SurfaceColor import gui_palette_names, standard_color_palettes
		rgbas = standard_color_palettes[gui_palette_names[paletteName]]

		self.renderColorMarkers.sort()
		for i, cm in enumerate(self.renderColorMarkers):
			place = i * (len(rgbas)-1.0) / (len(self.renderColorMarkers)-1.0)
			leftIndex = int(place)
			if leftIndex == place or leftIndex == len(rgbas) - 1:
				rgba = rgbas[leftIndex]
			else:
				f = place - leftIndex
				rgba = tuple([l * (1-f) + r * f
					for l,r in zip(rgbas[leftIndex], rgbas[leftIndex+1])])
			cm['rgba'] = rgba

	def _applyColors(self):
		colorAtoms = self.colorAtomsVar.get()
		opaqueAtoms = self.opaqueAtomsVar.get()
		colorRibbons = self.colorRibbonsVar.get()
		opaqueRibbons = self.opaqueRibbonsVar.get()
		colorSurfaces = self.colorSurfacesVar.get()
		ckw = {'colorAtoms': colorAtoms,
		       'opaqueAtoms': opaqueAtoms,
		       'colorRibbons': colorRibbons,
		       'opaqueRibbons': opaqueRibbons,
		       'colorSurfaces': colorSurfaces}
		if colorSurfaces:
			from chimera.actions import changeSurfsFromCustom
			changeSurfsFromCustom(self.models)
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		if (not (colorAtoms and target.colorAtoms) and
		    not colorSurfaces and
		    not (colorRibbons and target.colorRibbons)):
			raise chimera.UserError(
				"Nothing chosen to receive attribute coloring!")
		prefs[COLOR_ATOMS] = colorAtoms
		prefs[COLOR_RIBBONS] = colorRibbons
		prefs[COLOR_SURFACES] = colorSurfaces

		self.status("Coloring atoms/ribbons", blankAfter=0)
		def makeColors(rgba):
			c = chimera.MaterialColor(*rgba)
			if rgba[-1] < 1.0:
				orgba = list(rgba[:3]) + [1.0]
				oc = chimera.MaterialColor(*orgba)
			else:
				oc = c
			colors[val] = (c, oc)
			return c, oc
		colors = {}
		restrict = prefs[RESTRICT]
		if restrict:
			filterItems = target.selectedObjects()
			if not filterItems:
				restrict = False
		from operator import add
		attrMenu = self.renderAttrsMenu[target]
		if restrict:
			items = target.objectsInModels(filterItems, self.models)
		else:
			items = target.modelObjects(self.models)

		attrName = attrMenu.getvalue()
		if len(attrName) == 1:
			doSubitems = False
		else:
			doSubitems = True
		attrName = attrName[-1]
		self.renderColorMarkers['coordtype'] = 'absolute'
		noValRgba = self.noValueWell.rgba
		for item in items:
			if doSubitems:
				# an average/sum
				vals = []
				for sub in target.childObjects(item):
					try:
						val = getattr(sub, attrName)
					except AttributeError:
						continue
					if val is not None:
						vals.append(val)
				if vals:
					val = reduce(add, vals)
					if not summableAttrName(attrName):
						val /= float(len(vals))
				else:
					val = None
			else:
				try:
					val = getattr(item, attrName)
				except AttributeError:
					val = None

			if val is None:
				if noValRgba is not None:
					if None in colors:
						c, oc = colors[None]
					else:
						c, oc = makeColors(noValRgba)
					target.colorItem(item, c, oc, **ckw)
				continue
			if len(self.renderColorMarkers) == 0:
				continue
			for i, marker in enumerate(self.renderColorMarkers):
				if val <= self._markerVal(marker):
					break
			else:
				i = len(self.renderColorMarkers)
			if i == 0:
				val = self._markerVal(
						self.renderColorMarkers[0])
				i = 1
			elif i == len(self.renderColorMarkers):
				val = self._markerVal(
						self.renderColorMarkers[-1])
				i -= 1;
			if val in colors:
				target.colorItem(item, *colors[val], **ckw)
				continue
			if len(self.renderColorMarkers) > 1:
				left, right = map(lambda m:
					(self._markerVal(m), m['rgba']),
					self.renderColorMarkers[i-1:i+1])
				lval, lrgba = left
				rval, rrgba = right
				if rval == lval:
					pos = 0.5
				else:
					pos = (val - lval) / float(rval - lval)
				rgba = map(lambda l, r: l*(1 - pos) + r*pos,
								lrgba, rrgba)
			else:
				rgba = self.renderColorMarkers[0]['rgba']
			c, oc = makeColors(rgba)
			target.colorItem(item, c, oc, **ckw)
		self.renderColorMarkers['coordtype'] = 'relative'
		self.status("Done setting colors")

	def _applyRadii(self):
		markers, marker = self.renderHistogram.currentmarkerinfo()
		if marker is not None:
			self._setRadius(marker)
		noValRadius = self.noValueRadii.get()
		doNoVal = self.doNoValueRadii.get()
		prefs[ATOM_RADII] = map(lambda m: m.radius,
						self.renderRadiiMarkers[:])
		prefs[ATOM_STYLE] = self.atomStyle.get()

		target = revAttrsLabelMap[self.targetMenu.getvalue()]

		self.status("Setting atomic radii", blankAfter=0)

		restrict = prefs[RESTRICT]
		if restrict:
			curSel = selection.currentAtoms(asDict=True)
			if not curSel:
				restrict = False
		if restrict:
			restrict = curSel
		from operator import add
		style = prefs[ATOM_STYLE]
		attrMenu = self.renderAttrsMenu[target]
		if restrict:
			items = target.objectsInModels(target.selectedObjects(),
										self.models)
		else:
			items = target.modelObjects(self.models)
		attrName = attrMenu.getvalue()
		if len(attrName) == 1:
			doSubitems = False
		else:
			doSubitems = True
		attrName = attrName[-1]
		radMarkers = self.renderRadiiMarkers
		radMarkers['coordtype'] = 'absolute'
		for item in items:
			if doSubitems:
				# an average/sum
				vals = []
				for sub in target.childObjects(item):
					try:
						val = getattr(sub, attrName)
					except AttributeError:
						continue
					if val is not None:
						vals.append(val)
				if vals:
					val = reduce(add, vals)
					if not summableAttrName(attrName):
						val /= float(len(vals))
				else:
					val = None
			else:
				try:
					val = getattr(item, attrName)
				except AttributeError:
					val = None

			if val is None:
				if doNoVal:
					target.setRadius(item, noValRadius,
							 style, restrict)
				continue
			if len(radMarkers) == 0:
				continue
			for i, marker in enumerate(radMarkers):
				if val <= self._markerVal(marker):
					break
			else:
				i = len(radMarkers)
			if i == 0:
				rad = radMarkers[0].radius
			elif i == len(radMarkers):
				rad = radMarkers[-1].radius
			elif len(radMarkers) > 1:
				left, right = map(self._markerVal,
						radMarkers[i-1:i+1])
				if right == left:
					pos = 0.5
				else:
					pos = (val - left) / float(right - left)
				rad = radMarkers[i-1].radius * (1 -
					pos) + radMarkers[i].radius * pos
			else:
				rad = radMarkers[0].radius
			target.setRadius(item, rad, style, restrict)
		radMarkers['coordtype'] = 'relative'
		self.status("Done setting radii")

	def _applyWorms(self):
		markers, marker = self.renderHistogram.currentmarkerinfo()
		if marker is not None:
			self._setRadius(marker)
		noValRadius = self.noValueWorm.get()
		doNoVal = self.doNoValueWorm.get()
		wormStyleName = self.wormStyle.get()
		prefs[NOVAL_WORM] = noValRadius
		if wormStyleName == self.dewormLabel:
			# revert the style menu to the worm style
			self.wormStyle.set(prefs[WORM_STYLE])
		else:
			prefs[WORM_STYLE] = wormStyleName
		prefs[ATOM_RADII] = map(lambda m: m.radius,
						self.renderWormsMarkers[:])

		target = revAttrsLabelMap[self.targetMenu.getvalue()]

		self.status("Setting worm radii", blankAfter=0)

		restrict = prefs[RESTRICT]
		if restrict:
			curSel = selection.currentResidues(asDict=True)
			if not curSel:
				restrict = False
		if restrict:
			restrict = curSel
		styles = {}
		def style(rad):
			if wormStyleName == "smooth":
				# can't cache -- each different
				return chimera.RibbonStyleWorm([rad])
			elif wormStyleName == self.dewormLabel:
				return None
			if rad not in styles:
				styles[rad] = chimera.RibbonStyleFixed([rad,
									rad])
			return styles[rad]
		from operator import add
		if not hasattr(target, 'setWormRadius'):
			raise AssertionError, "Cannot worms with %s target" % target.menuName
		attrMenu = self.renderAttrsMenu[target]
		items = target.modelObjects(self.models)
		attrName = attrMenu.getvalue()
		if len(attrName) == 1:
			doSubitems = False
		else:
			doSubitems = True
		attrName = attrName[-1]
		radMarkers = self.renderWormsMarkers
		radMarkers['coordtype'] = 'absolute'
		for item in items:
			if doSubitems:
				# an average/sum
				vals = []
				for sub in target.childObjects(item):
					try:
						val = getattr(sub, attrName)
					except AttributeError:
						continue
					if val is not None:
						vals.append(val)
				if vals:
					val = reduce(add, vals)
					if not summableAttrName(attrName):
						val /= float(len(vals))
				else:
					val = None
			else:
				try:
					val = getattr(item, attrName)
				except AttributeError:
					val = None

			if val is None:
				if doNoVal:
					target.setWormRadius(item, noValRadius,
							     style(noValRadius),
							     restrict)
				continue
			if len(radMarkers) == 0:
				continue
			for i, marker in enumerate(radMarkers):
				if val <= self._markerVal(marker):
					break
			else:
				i = len(radMarkers)
			if i == 0:
				rad = radMarkers[0].radius
			elif i == len(radMarkers):
				rad = radMarkers[-1].radius
			elif len(radMarkers) > 1:
				left, right = map(self._markerVal,
						radMarkers[i-1:i+1])
				if right == left:
					pos = 0.5
				else:
					pos = (val - left) / float(right - left)
				rad = radMarkers[i-1].radius * (1 -
					pos) + radMarkers[i].radius * pos
			else:
				rad = radMarkers[0].radius
			target.setWormRadius(item, rad, style(rad), restrict)
		radMarkers['coordtype'] = 'relative'
		self.status("Done setting radii")

	def _applySelect(self):
		self.status("Selecting atoms/residues", blankAfter=0)
		from operator import add
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		attrMenu = self.selectAttrsMenu[target]
		items = target.modelObjects(self.models)
		attrName = attrMenu.getvalue()
		if len(attrName) == 1:
			doSubitems = False
		else:
			doSubitems = True
		attrName = attrName[-1]
		usingHist = False
		if self.selHistFrame.winfo_manager():
			usingHist = True
			selMode = self.selModeVar.get()
			self.selectMarkers['coordtype'] = 'absolute'
			if selMode < 2:
				m1, m2 = map(lambda m: self._markerVal(m),
							self.selectMarkers)
				if selMode == 0:
					selFunc = lambda v: v >= m1 and v <= m2
				else:
					selFunc = lambda v: v < m1 or v > m2
			else:
				selFunc = lambda v: False
		elif self.selListFrame.winfo_manager():
			selMode = 0 # i.e. not selecting None
			selValues = {}
			for v in self.selectListBox.getvalue():
				if v == _LIST_NOVALUE:
					selMode = 2 # selecting None
					continue
				selValues[v] = 1
			selFunc = lambda v: v in selValues
		else:
			# since it just so happens that the only relevant
			# value for selMode in the later code is 2...
			selMode = self.selBoolVar.get()
			selFunc = lambda v: v == selMode
		sels = []
		for item in items:
			if doSubitems:
				# an average/sum
				vals = []
				for sub in target.childObjects(item):
					try:
						val = getattr(sub, attrName)
					except AttributeError:
						continue
					if val is not None:
						vals.append(val)
				if vals:
					val = reduce(add, vals)
					if not summableAttrName(attrName):
						val /= float(len(vals))
				else:
					val = None
			else:
				try:
					val = getattr(item, attrName)
				except AttributeError:
					val = None

			if val is None:
				if selMode == 2:
					sels.append(item)
				continue
			if selFunc(val):
				sels.append(item)
		if hasattr(target, 'selectables'):
			sels = target.selectables(sels)
		from chimera.selection import ItemizedSelection
		sel = ItemizedSelection()
		sel.add(sels)
		sel.addImplied()
		from chimera.tkgui import selectionOperation
		selectionOperation(sel)
		if usingHist:
			self.selectMarkers['coordtype'] = 'relative'
		self.status("Done selecting atoms/residues")

	def _colorKeyCB(self, *args):
		if len(self.renderColorMarkers) < 2:
			raise chimera.UserError("Need at least two color bars"
				" in histogram to create key")
		prevCoordType = self.renderColorMarkers['coordtype']
		self.renderColorMarkers['coordtype'] = 'absolute'
		from Ilabel.gui import IlabelDialog
		from chimera import dialogs
		d = dialogs.display(IlabelDialog.name)
		d.keyConfigure([(m['rgba'], "%g" % self._markerVal(m))
					for m in self.renderColorMarkers])
		self.renderColorMarkers['coordtype'] = prevCoordType

	def _compileAttrVals(self, target, menuItem):
		self.status("Surveying attribute %s" % " ".join(menuItem),
								blankAfter=0)
		mode = self.modeNotebook.getcurselection()

		attrVals = []
		surveyed = target.modelObjects(self.models)
		attrName = menuItem[-1]
		hasNone = False
		if len(menuItem) == 1:
			for t in surveyed:
				try:
					val = getattr(t, attrName)
				except AttributeError:
					hasNone = True
					continue
				if val is None or (isinstance(val, basestring)
								and not val):
					hasNone = True
					continue
				attrVals.append(val)
		else:
			# average/sum of atoms/residues
			from operator import add
			for t in surveyed:
				vals = []
				for sub in target.childObjects(t):
					try:
						val = getattr(sub, attrName)
					except AttributeError:
						continue
					if val is None \
					or (isinstance(val, basestring)
								and not val):
						continue
					vals.append(val)
				if not vals:
					hasNone = True
					continue
				val = reduce(add, vals)
				if not summableAttrName(attrName):
					val /= float(len(vals))
				attrVals.append(val)
		self.status("Done surveying")
		self._attrOkApply[mode] = True
		self._setAttrVals(attrVals)
		if mode == MODE_SELECT:
			for frame in self.selFrames:
				frame.grid_forget()
		if attrVals and isinstance(attrVals[0], basestring):
			frame = self.selListFrame
			uniqueVals = {}
			for av in attrVals:
				uniqueVals[av] = 1
			listItems = uniqueVals.keys()
			listItems.sort(lambda a, b: cmp(a.lower(), b.lower()))
			if hasNone:
				listItems.append(_LIST_NOVALUE)
			self.selectListBox.setlist(listItems)
		elif attrVals and isinstance(attrVals[0], bool):
			frame = self.selBoolFrame
			self.boolButtons[-1].grid_forget()
			if hasNone:
				self.boolButtons[-1].grid(
						row=len(self.boolButtons)-1,
						column=0, sticky='w')
			elif self.selBoolVar.get() == 2:
				self.selBoolVar.set(True)
		else:
			frame = self.selHistFrame
			if not attrVals:
				self.histogram()['datasource'] = \
					"No attribute '%s' in any %s" % (
							attrName, target.menuName)
				self._attrOkApply[mode] = False
			elif self.minVal() == self.maxVal():
				self.histogram()['datasource'] = \
					"attribute has only one value: %s" \
							% str(self.minVal())
				self._attrOkApply[mode] = False
			else:
				self.histogram()['datasource'] = (self.minVal(),
					self.maxVal(), lambda numBins, mode=mode:
					self._makeBins(numBins, mode=mode))
			if hasNone:
				but, gridKw = self.selNoValueButtonInfo
				but.grid(**gridKw)
			else:
				self.selNoValueButtonInfo[0].grid_forget()
		if hasNone:
			self.noValueColorsFrame.grid(
					**self.noValueColorsFrame.gridKw)
			self.doNoValueRadii.gridManage()
			self.noValueRadii.gridManage()
			self.doNoValueWorm.gridManage()
			self.noValueWorm.gridManage()
		else:
			self.noValueColorsFrame.grid_forget()
			self.doNoValueRadii.gridUnmanage()
			self.noValueRadii.gridUnmanage()
			self.doNoValueWorm.gridUnmanage()
			self.noValueWorm.gridUnmanage()
		self.renderNotebook.setnaturalsize()
		if mode == MODE_RENDER:
			state = 'normal' if self._attrOkApply[mode] and self._renderOkApply else 'disabled'
			self.colorKeyButton.configure(state=state)
			self.reverseColorsButton.configure(state=state)
			self.paletteMenu.component('menubutton').config(state=state)
		else:
			state = 'normal' if self._attrOkApply[mode] else 'disabled'
			frame.grid(row=1, column=0, sticky="nsew")
		self.buttonWidgets['OK'].configure(state=state)
		self.buttonWidgets['Apply'].configure(state=state)
		if state == 'normal':
			if mode == MODE_RENDER or frame == self.selHistFrame:
				if mode == MODE_SELECT:
					addText = ""
				else:
					renderPage = self.renderNotebook.getcurselection()
					if renderPage == "Colors":
						addText = " or color"
					else:
						addText = " or radius"
				# report after histogram computation
				self.colorKeyButton.after(1000, lambda
					s1="Histogram bars can be moved with the mouse",
					s2="Click on histogram bar to set value" + addText:
					self.status(s1, followWith=s2, blankAfter=6))
		self.refreshMenu.entryconfigure(MENU_VALUES_LABEL, state="normal")

	def _composeAttrMenus(self):
		sortFunc = lambda a, b: cmp(a.lower(), b.lower())
		for o in objectTypes:
			self.useableAttrs[o].sort(sortFunc)
		for o in objectTypes:
			self.renderAttrsMenu[o].setitems(_menuItems(
					self.useableAttrs[o],
					self.useableAttrs.get(o.childType(),[]),
					o.screenedSubAttrs))

		# do this in a little bit of a weird order so that the 'average'
		# submenu only contains numeric quantities
		aggAveAttrs = {None:[]}
		for o in objectTypes:
			aggAveAttrs[o] = self.useableAttrs[o] \
					+ self.additionalNumericAttrs[o]
			aggAveAttrs[o].sort(sortFunc)

		for o in objectTypes:
			aggAttrs = aggAveAttrs[o] + self.additionalOtherAttrs[o]
			aggAttrs.sort(sortFunc)
			self.selectAttrsMenu[o].setitems(_menuItems(
						aggAttrs,
						aggAveAttrs[o.childType()],
						o.screenedSubAttrs))

	def _curAttrMenu(self):
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		if self.modeNotebook.getcurselection() == MODE_RENDER:
			return self.renderAttrsMenu[target]
		else:
			return self.selectAttrsMenu[target]

	def _makeBins(self, numBins, mode):
		self.status("Computing histogram bins", blankAfter=0)
		minVal, maxVal = self.minVal(mode), self.maxVal(mode)
		if isinstance(minVal, int) and isinstance(maxVal, int) \
		and maxVal - minVal + 1 <= numBins / 3.0:
			# enough room to show bars instead of lines
			numBins = maxVal - minVal + 1
		bins = [0] * numBins
		vrange = maxVal - minVal
		binSize = vrange / float(numBins - 1)
		leftEdge = minVal - 0.5 * binSize
		for val in self.attrVals(mode):
			bin = int((val - leftEdge) / binSize)
			bins[bin] += 1
		self.status("Done computing histogram bins")
		return bins

	def _markerVal(self, marker):
		rawVal = marker['xy'][0]
		if isinstance(self.minVal(), int):
			return int(rawVal + 0.5)
		return rawVal

	def _pageChangeCB(self, pageName):
		if pageName == MODE_RENDER:
			state = 'normal' if self._attrOkApply[pageName] and self._renderOkApply else 'disabled'
		else:
			state = 'normal' if self._attrOkApply[pageName] else 'disabled'
		self.buttonWidgets['OK'].configure(state=state)
		self.buttonWidgets['Apply'].configure(state=state)

	def _populateAttrsMenus(self, newModels=None):
		self.status("Compiling attribute lists...", blankAfter=0)
		if newModels is None or not hasattr(self, 'seenAttrs'):
			self.seenAttrs = {}
			self.useableAttrs = {}
			self.additionalNumericAttrs = {}
			self.additionalOtherAttrs = {}
			for o in objectTypes:
				self.seenAttrs[o] = o.screenedAttrs.copy()
				self.useableAttrs[o] = []
				self.additionalNumericAttrs[o] = []
				self.additionalOtherAttrs[o] = []
		if newModels is None:
			scanModels = self.models
		else:
			scanModels = newModels

		for o in objectTypes:
			self.status("Compiling attribute lists for %s..."
				    % o.menuName, blankAfter=0)
			models = [m for m in scanModels
				  if isinstance(m, o.modelType)]
			for item in o.modelObjects(models):
				self._reapAttrs(item, self.seenAttrs[o],
						self.useableAttrs[o],
						self.additionalNumericAttrs[o],
						self.additionalOtherAttrs[o])
		self.status("Updating attribute menus...", blankAfter=0)
		self._composeAttrMenus()
		self.status("")

	def _raisePageCB(self, page):
		entryFrame = self.renderHistogram.component('widgetframe')
		if page == "Colors":
			markers = self.renderColorMarkers
			self.renderHistogram.configure(colorwell=True)
			self.radiusEntry.grid_forget()
			entryFrame.columnconfigure(self.entryColumn, weight=0)
		else:
			if page == "Radii":
				markers = self.renderRadiiMarkers
				self.radiusEntry.component('label').configure(
							text='Atom radius')
			else:
				markers = self.renderWormsMarkers
				self.radiusEntry.component('label').configure(
							text='Worm radius')
			self.renderHistogram.configure(colorwell=False)
			self.radiusEntry.grid(row=1, column=self.entryColumn)
			entryFrame.columnconfigure(self.entryColumn, weight=2)
		self.renderHistogram.activate(markers)
		self._renderGUI()

	def _reapAttrs(self, instance, seenAttrs, useableAttrs,
				additionalNumericAttrs, additionalOtherAttrs):
		for attrName in dir(instance):
			attrType = seenAttrs.get(attrName, None)
			if isinstance(attrType, bool):
				continue
			elif attrType is None:
				if attrName[0] == '_' \
				or (attrName[0].isupper() # e.g. 'Ball'
				and not isRegisteredAttribute(instance.__class__, attrName)):
					seenAttrs[attrName] = False
					continue
				attr = getattr(instance, attrName)
				if attr is None or (isinstance(attr, basestring)
								and not attr):
					# defer judgment until
					# we see a real value
					continue
				attrType = type(attr)
			else:
				attr = attrType()
			seenAttrs[attrName] = True
			if attrType in self.useableTypes:
				useableAttrs.append(attrName)
			elif attrType in self.additionalNumericTypes:
				additionalNumericAttrs.append(attrName)
			elif isinstance(attr, self.additionalOtherTypes):
				additionalOtherAttrs.append(attrName)

	def _sceneRestore(self, trigName, myData, scene):
		data = scene.tool_settings.get(self.name, None)
		if data is None:
			self.Close()
			return
		if data['shown']:
			self.enter()
		else:
			self.Close()
		self.targetMenu.invoke(data['target'])
		from Animate.Tools import idLookup
		self.modelListBox.setvalue([idLookup(sid) for sid in data['models']])
		self.modeNotebook.selectpage(data['mode'])
		try:
			self._curAttrMenu().invoke(data['attribute'])
		except ValueError:
			# attribute not in menu
			self.Close()
			return
		self.histogram().sceneRestore(data['hist data'])
		self.renderNotebook.selectpage(data['action tab'])
		for dataName, widget in [ ('sel mode', self.selModeVar), ('sel bool', self.selBoolVar),
		('color atoms', self.colorAtomsVar), ('opaque atoms', self.opaqueAtomsVar),
		('color ribbons', self.colorRibbonsVar), ('opaque ribbons', self.opaqueRibbonsVar),
		('color surfaces', self.colorSurfacesVar), ('rad atom style', self.atomStyle),
		('rad affect no val', self.doNoValueRadii), ('rad no val', self.noValueRadii),
		('worm style', self.wormStyle), ('worm affect no val', self.doNoValueWorm),
		('worm no val', self.noValueWorm), ('restrict to sel', self.selRestrictVar)
		]:
			try:
				widget.set(data[dataName])
			except (ValueError, TypeError):
				pass
		for dataName, widget in [ ('palette', self.paletteMenu), ('radius', self.radiusEntry) ]:
			try:
				widget.setvalue(data[dataName])
			except (ValueError, TypeError):
				pass
		try:
			self.selectListBox.setvalue(data['sel list'])
		except (ValueError, TypeError):
			pass
		try:
			self.noValueWell.showColor(data['no val color'], doCallback=False)
		except (ValueError, TypeError):
			pass

	def _sceneSave(self, trigName, myData, scene):
		from Animate.Tools import sceneID, colorID
		info = {
			'shown': self.uiMaster().winfo_viewable(),
			'target': self.targetMenu.getvalue(),
			'models': [sceneID(m) for m in self.modelListBox.getvalue()],
			'mode': self.modeNotebook.getcurselection(),
			'attribute': self._curAttrMenu().getvalue(),
			'hist data': self.histogram().sceneData(),
			'sel mode': self.selModeVar.get(),
			'sel list': self.selectListBox.getvalue(),
			'sel bool': self.selBoolVar.get(),
			'action tab': self.renderNotebook.getcurselection(),
			'color atoms': self.colorAtomsVar.get(),
			'opaque atoms': self.opaqueAtomsVar.get(),
			'color ribbons': self.colorRibbonsVar.get(),
			'opaque ribbons': self.opaqueRibbonsVar.get(),
			'color surfaces': self.colorSurfacesVar.get(),
			'no val color': self.noValueWell.rgba,
			'palette': self.paletteMenu.getvalue(),
			'radius': self.radiusEntry.getvalue(),
			'rad atom style': self.atomStyle.get(),
			'rad affect no val': self.doNoValueRadii.get(),
			'rad no val': self.noValueRadii.get(),
			'worm style': self.wormStyle.get(),
			'worm affect no val': self.doNoValueWorm.get(),
			'worm no val': self.noValueWorm.get(),
			'restrict to sel': self.selRestrictVar.get()

		}
		scene.tool_settings[self.name] = info
		
	def _scalingCB(self):
		scaling = self.scalingVar.get()
		prefs[SCALING] = scaling
		for histogram in [self.renderHistogram, self.selectHistogram]:
			if scaling == "log":
				histogram.configure(scaling="logarithmic")
			else:
				histogram.configure(scaling="linear")

	def _selMarkerCB(self, prevMarkers, prevMarker, markers, marker):
		if prevMarker and prevMarkers != self.renderColorMarkers:
			self._setRadius(prevMarker)
		if markers == self.renderColorMarkers:
			return
		self.radiusEntry.component('entry').configure(state='normal')
		if marker is None:
			self.radiusEntry.clear()
			self.radiusEntry.component('entry').configure(
							state='disabled')
			return
		if not hasattr(marker, "radius"):
			# new marker
			marker.radius = 1.0
		self.radiusEntry.setentry("%g" % marker.radius)

	def _setAttrVals(self, attrVals):
		index = Modes.index(self.modeNotebook.getcurselection())
		self._attrVals[index] = attrVals
		if attrVals and type(attrVals[0]) in numericTypes:
			self._minVal[index] = min(attrVals)
			self._maxVal[index] = max(attrVals)

	def _setRadius(self, marker):
		self.radiusEntry.invoke()
		if not self.radiusEntry.valid():
			self.status("Radius value not valid: '%s'" %
				self.radiusEntry.getvalue(), color='red')
			return
		marker.radius = float(self.radiusEntry.getvalue())

	def _targetCB(self, menuItem):
		for o in objectTypes:
			self.renderAttrsMenu[o].grid_forget()
			self.selectAttrsMenu[o].grid_forget()
		self._renderGUI()
		target = revAttrsLabelMap[menuItem]
		menus = [self.renderAttrsMenu[target],
			 self.selectAttrsMenu[target]]
		atomState = "normal" if target.colorAtoms else "disabled"
		ribbonState = "normal" if target.colorRibbons else "disabled"
		for menu in menus:
			menu.grid(row=0, column=0, columnspan=2)
			menu.component('menubutton').config(text=NO_ATTR)
		for frame in self.selFrames:
			frame.grid_forget()
		for hg in [self.renderHistogram, self.selHistFrame]:
			hg.grid(row=1, column=0, sticky="nsew")
		self.renderHistogram['datasource'] = NO_RENDER_DATA
		self.selectHistogram['datasource'] = NO_SELECT_DATA
		self.colorAtomsButton.config(state=atomState)
		self.opaqueAtomsButton.config(state=atomState)
		self.colorRibbonsButton.config(state=ribbonState)
		self.opaqueRibbonsButton.config(state=ribbonState)
		for key in self._attrOkApply.keys():
			self._attrOkApply[key] = False
		self.buttonWidgets['OK'].configure(state='disabled')
		self.buttonWidgets['Apply'].configure(state='disabled')
		self.colorKeyButton.configure(state='disabled')
		self.reverseColorsButton.configure(state='disabled')
		self.paletteMenu.component('menubutton').config(state="disabled")
		# Filter models for new object type.
		self.modelListBox._modelsChange()

	def _renderGUI(self):
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		page = self.renderNotebook.getcurselection()
		if page == "Worms":
			if hasattr(target, 'setWormRadius'):
				self.wormsWarning.grid_forget()
				self.wormsFrame.grid()
				self._renderOkApply = True
			else:
				self.wormsFrame.grid_forget()
				self.wormsWarning.grid()
				self._renderOkApply = False
		elif page == "Radii":
			if hasattr(target, 'setRadius'):
				self.radiiWarning.grid_forget()
				self.radiiFrame.grid()
				self._renderOkApply = True
			else:
				self.radiiFrame.grid_forget()
				self.radiiWarning.grid()
				self._renderOkApply = False
		else:
			self._renderOkApply = True
		self.renderNotebook.setnaturalsize()
		state = 'normal' if self._attrOkApply[self.modeNotebook.getcurselection()] and self._renderOkApply else 'disabled'
		self.buttonWidgets['OK'].configure(state=state)
		self.buttonWidgets['Apply'].configure(state=state)
		self.colorKeyButton.configure(state=state)
		self.reverseColorsButton.configure(state=state)
		self.paletteMenu.component('menubutton').config(state=state)

	def _saveAttr(self):
		from chimera import dialogs
		d = dialogs.find("SaveAttrDialog", create=True)
		attrList = self._curAttrMenu().getvalue()
		if attrList:
			attrName = attrList[0]
		else:
			attrName = None
		# TODO: If attrList = ['average', 'bfactor'] the current code
		#       does not set the Save dialog attribute menu because
		#       it only gets attrName = 'average'.
		d.configure(models=self.modelListBox.getvalue(),
				attrsOf=self.targetMenu.getvalue(),
				attrName=attrName)
		d.enter()

from chimera import dialogs
dialogs.register(ShowAttrDialog.name, ShowAttrDialog)

from OpenSave import SaveModeless
class SaveAttrDialog(SaveModeless):
	title = "Save Attribute"
	name = "SaveAttrDialog"
	help = "ContributedSoftware/render/render.html#saving"

	def __init__(self, *args, **kw):
		self.havePaths = False
		self.models = []
		self.useableTypes = numericTypes
		self.additionalNumericTypes = () # boolean could be here instead
		self.additionalOtherTypes = (bool, basestring)
		SaveModeless.__init__(self, clientPos="s", clientSticky="nsew",
					*args, **kw)

	def fillInUI(self, parent):
		self.targetMenu = None
		self.modelListBox = None
		SaveModeless.fillInUI(self, parent)
		g = Pmw.Group(self.clientArea, tag_text="Attribute to Save")
		g.pack(expand=Tkinter.TRUE, fill=Tkinter.BOTH)

		f = Tkinter.Frame(g.interior())
		f.pack(side=Tkinter.TOP, expand=Tkinter.FALSE, fill=Tkinter.X)
		self.attrsMenu = {}
		for o in objectTypes:
			self.attrsMenu[o] = CascadeOptionMenu(f,
			command=lambda mi, o=o: self._compileAttrVals(o,
			mi), labelpos='w', label_text="Attribute:")
		self.attrsMenu[objectTypes[0]].grid(row=0, column=0)
		self.targetMenu = Pmw.OptionMenu(f, command=self._targetCB,
				items=[o.menuName for o in objectTypes],
				labelpos='w', label_text=" of")
		self.targetMenu.grid(row=0, column=1)

		self.includeModelVar = Tkinter.IntVar(g.interior())
		self.includeModelVar.set(0)
		self.includeModelButton = Tkinter.Checkbutton(g.interior(),
			pady=0, text="Include model numbers in output",
			variable=self.includeModelVar)
		self.includeModelButton.pack(side=Tkinter.BOTTOM)

		self.saveSelectionVar = Tkinter.IntVar(g.interior())
		self.saveSelectionVar.set(0)
		self.saveSelectionButton = Tkinter.Checkbutton(g.interior(),
			pady=0,
			text="Restrict save to current selection, if any",
			variable=self.saveSelectionVar)
		self.saveSelectionButton.pack(side=Tkinter.BOTTOM)

		from chimera.widgets import ModelScrolledListBox
		self.modelListBox = ModelScrolledListBox(g.interior(),
				selectioncommand=lambda: self.configure(
				models=self.modelListBox.getvalue(),
				fromModelListBox=True),
			        filtFunc = self.filterModels,
				listbox_selectmode="extended",
				labelpos="nw", label_text="Models")
		self.modelListBox.pack(side=Tkinter.BOTTOM, expand=Tkinter.TRUE,
					fill=Tkinter.BOTH)

		self.targetMenu.invoke(attrsPrefMap[prefs[TARGET]].menuName)

	def filterModels(self, model):
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		return isinstance(model, target.modelType)

	def Apply(self):
		paths = self.getPaths(remember=False)
		filename = paths[0]
		models = self.modelListBox.getvalue()
		if not models:
			raise chimera.UserError("No models selected")

		restrict = (self.saveSelectionVar.get()
				and not selection.currentEmpty())
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		menu = self.attrsMenu[target]
		if restrict:
			selObj = target.selectedObjects()
			objList = target.objectsInModels(selObj, models)
			target.sortObjects(objList)
		else:
			objList = target.modelObjects(models)
		if not objList:
			raise chimera.UserError("No items selected")
		attrList = menu.getvalue()
		if not attrList:
			raise chimera.UserError("No attribute selected")
		attrName = attrList[-1]
		if self.includeModelVar.get():
			level = selection.SelGraph
		else:
			level = selection.SelSubgraph
		f = open(filename, "w")
		try:
			if len(attrList) == 1:
				print >> f, "attribute:", attrName
				print >> f, "recipient:", target.menuName
				# direct attribute, just print
				for o in objList:
					try:
						val = getattr(o, attrName)
					except AttributeError:
						continue
					if val is not None:
						print >> f, "\t%s\t%s" % (
							target.objectId(o,level),
							repr(val))
			else:
				# averaged attribute, need to be more clever
				print >> f, "attribute:", '_'.join(attrList)
				print >> f, "recipient:", target.menuName
				from operator import add
				for o in objList:
					vals = []
					for sub in target.childObjects(o):
						try:
							val = getattr(sub,
								attrName)
						except AttributeError:
							continue
						if val is not None:
							vals.append(val)
					if vals:
						val = reduce(add, vals)
						if not summableAttrName(
								attrName):
							val /= float(len(vals))
						print >> f, "\t%s\t%g" % (
							target.objectId(o,level), val)
		finally:
			f.close()
		msg = "Attribute %s of %s saved in file %s" % (attrName,
							       target.menuName,
							       filename)
		from chimera import replyobj
		replyobj.status(msg)

	def configure(self, models=None, attrsOf=None, attrName=None,
							fromModelListBox=False):
		curMenu = self._curAttrMenu()
		curAttr = curMenu.getvalue()
		curTargetLabel = self.targetMenu.getvalue()
		curTarget = revAttrsLabelMap[curTargetLabel]
		refreshedAttrs = False

		if attrsOf != curTargetLabel and attrsOf is not None:
			self.targetMenu.invoke(attrsOf)

		if models != self.models and models is not None:
			newModels = None
			if fromModelListBox:
				from sets import Set
				oldSet = Set(self.models)
				newSet = Set(models)
				if newSet >= oldSet:
					newModels = newSet - oldSet
			else:
				self.modelListBox.setvalue(models,
							doCallback=False)
			self.models = models
			self._populateAttrsMenus(newModels=newModels)
			refreshedAttrs = True
			if not models or (curAttr is None and attrName is None):
				# _populateAttrsMenu has knocked the menu
				# button off of "choose attr"; arrange for
				# it to be restored...
				attrName = NO_ATTR
			if (attrsOf == curTargetLabel or attrsOf is None) \
			and ([attrName] == curAttr or attrName is None):
				# no other changes
				if curAttr is not None:
					try:
						curMenu.invoke(curAttr)
					except ValueError:
						# attribute no longer present
						self._targetCB(curTargetLabel)

		# if an attribute name is specified, probably want an update...
		if attrName is not None:
			if attrName == NO_ATTR:
				self._targetCB(curTargetLabel)
			else:
				target = curTarget if attrsOf is None else revAttrsLabelMap[attrsOf]
				seen = self.seenAttrs[target]
				if not refreshedAttrs and attrName not in seen:
					self._populateAttrsMenus()
					# 'seen' pointing to old list now...
					seen = self.seenAttrs[target]
				if attrName in seen:
					self._curAttrMenu().invoke([attrName])
				elif not attrsOf is None:
					self._targetCB(attrsOf)

		self._attrReady()

	def _compileAttrVals(self, target, menuItem):
		self.status("Surveying attribute %s" % " ".join(menuItem),
								blankAfter=0)
		attrVals = []
		surveyed = target.modelObjects(self.models)
		attrName = menuItem[-1]
		hasNone = False
		if len(menuItem) == 1:
			for t in surveyed:
				try:
					val = getattr(t, attrName)
				except AttributeError:
					hasNone = True
					continue
				if val is None or (isinstance(val, basestring)
								and not val):
					hasNone = True
					continue
				attrVals.append(val)
		else:
			# average of atoms/residues
			from operator import add
			for t in surveyed:
				vals = []
				for sub in target.childObjects(t):
					try:
						val = getattr(sub, attrName)
					except AttributeError:
						continue
					if val is None \
					or (isinstance(val, basestring)
								and not val):
						continue
					vals.append(val)
				if not vals:
					hasNone = True
					continue
				val = reduce(add, vals)
				if not summableAttrName(attrName):
					val /= float(len(vals))
				attrVals.append(val)
		self.status("Done surveying")
		self._attrReady()

	def _composeAttrMenus(self):
		sortFunc = lambda a, b: cmp(a.lower(), b.lower())
		for o in objectTypes:
			self.useableAttrs[o].sort(sortFunc)

		# do this in a little bit of a weird order so that the 'average'
		# submenu only contains numeric quantities
		aggAveAttrs = {None:[]}
		for o in objectTypes:
			aggAveAttrs[o] = self.useableAttrs[o] \
					+ self.additionalNumericAttrs[o]
			aggAveAttrs[o].sort(sortFunc)

		for o in objectTypes:
			aggAttrs = aggAveAttrs[o] + self.additionalOtherAttrs[o]
			aggAttrs.sort(sortFunc)
			self.attrsMenu[o].setitems(_menuItems(
						aggAttrs,
						aggAveAttrs[o.childType()],
						o.screenedSubAttrs))

	def _curAttrMenu(self):
		if not self.targetMenu:
			return None
		target = revAttrsLabelMap[self.targetMenu.getvalue()]
		return self.attrsMenu[target]

	def _populateAttrsMenus(self, newModels=None):
		self.status("Compiling attribute lists...", blankAfter=0)
		if newModels is None or not hasattr(self, 'seenAttrs'):
			self.seenAttrs = {}
			self.useableAttrs = {}
			self.additionalNumericAttrs = {}
			self.additionalOtherAttrs = {}
			for o in objectTypes:
				self.seenAttrs[o] = o.screenedAttrs.copy()
				self.useableAttrs[o] = []
				self.additionalNumericAttrs[o] = []
				self.additionalOtherAttrs[o] = []
		if newModels is None:
			scanModels = self.models
		else:
			scanModels = newModels

		for o in objectTypes:
			self.status("Compiling attribute lists for %s..."
				    % o.menuName, blankAfter=0)
			models = [m for m in scanModels
				  if isinstance(m, o.modelType)]
			for item in o.modelObjects(models):
				self._reapAttrs(item, self.seenAttrs[o],
						self.useableAttrs[o],
						self.additionalNumericAttrs[o],
						self.additionalOtherAttrs[o])
		self.status("Updating attribute menus...", blankAfter=0)
		self._composeAttrMenus()
		self.status("")

	def _reapAttrs(self, instance, seenAttrs, useableAttrs,
				additionalNumericAttrs, additionalOtherAttrs):
		for attrName in dir(instance):
			attrType = seenAttrs.get(attrName, None)
			if isinstance(attrType, bool):
				continue
			elif attrType is None:
				if attrName[0] == '_' \
				or (attrName[0].isupper()  # e.g. 'Ball'
				and not isRegisteredAttribute(instance.__class__, attrName)):
					seenAttrs[attrName] = False
					continue
				attr = getattr(instance, attrName)
				if attr is None or (isinstance(attr, basestring)
								and not attr):
					# defer judgment until
					# we see a real value
					continue
				attrType = type(attr)
			else:
				attr = attrType()
			seenAttrs[attrName] = True
			if attrType in self.useableTypes:
				useableAttrs.append(attrName)
			elif attrType in self.additionalNumericTypes:
				additionalNumericAttrs.append(attrName)
			elif isinstance(attr, self.additionalOtherTypes):
				additionalOtherAttrs.append(attrName)

	def _targetCB(self, menuItem):
		for o in objectTypes:
			self.attrsMenu[o].grid_forget()
		target = revAttrsLabelMap[menuItem]
		menu = self.attrsMenu[target]
		menu.grid(row=0, column=0)
		menu.component('menubutton').config(text=NO_ATTR)
		SaveModeless._millerReady(self, None)
		# Filter models for new object type.
		self.modelListBox._modelsChange()


	def _millerReady(self, paths):
		if not self.modelListBox or not self.modelListBox.getvalue():
			paths = None
		else:
			menu = self._curAttrMenu()
			if menu:
				attrList = menu.getvalue()
				if not attrList:
					paths = None
			else:
				paths = None
		SaveModeless._millerReady(self, paths)

	def _attrReady(self):
		self._millerReady(self.getPaths(remember=False))

_attrNameAnalysisCache = {
	"accessibleSurface": True,	# Attribute from "Area/Volume from Web"
}
def summableAttrName(attrName):
	# split camel case and underscored names
	if attrName not in _attrNameAnalysisCache:
		components = []
		start = 0
		for i in range(1, len(attrName)):
			p, c = attrName[i-1:i+1]
			if c == "_":
				if p != "_":
					components.append(
						attrName[start:i].lower())
				start = i+1
			elif p.islower() and c.isupper():
				components.append(attrName[start:i].lower())
				start = i
			elif p.isupper() and c.islower() and start < i-1:
				# only final cap of a stretch is part of the camel case
				components.append(attrName[start:i-1].lower())
				start = i-1
		if start < len(attrName):
			components.append(attrName[start:].lower())
		for summable in ("area", "volume", "charge"):
			if summable in components:
				_attrNameAnalysisCache[attrName] = True
				break
		else:
			_attrNameAnalysisCache[attrName] = False
	return _attrNameAnalysisCache[attrName]
				

def _menuItems(baseItems, subItems, screenedSubAttrs):
	items = baseItems
	for summable, label in [(False, "average"), (True, "total")]:
		filtered = [si for si in subItems
				if summableAttrName(si) == summable and si not in screenedSubAttrs]
		if filtered:
			items = items + [(label, filtered)]
	return items

