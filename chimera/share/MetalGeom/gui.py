# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: Metals.py 29850 2010-01-26 00:56:50Z pett $
#TODO:
#   [tier2] bulk dump of ligand angles [structure-analysis/10920]
#   [tier2] add missing metal based on ligands (new tool?) [structure-analysis/10921]
import chimera
from chimera import replyobj, UserError
from prefs import prefs, defaults, LIG_POS, LIG_SEP
from chimera.baseDialog import ModelessDialog

class MetalsDialog(ModelessDialog):
	name = "metal geometry"
	title = "Metal Geometry"
	help = "ContributedSoftware/metalgeom/metalgeom.html"
	provideStatus = True
	statusPosition = "left"
	buttons = ('Close',)

	coordLimit = 4.0

	def __init__(self, sessionData=None):
		from SimpleSession import SAVE_SESSION
		self._sesHandlerID = chimera.triggers.addHandler(
			SAVE_SESSION, self._sessionSaveCB, None)
		if sessionData:
			self.initialSettings, self.coordTableData, self.geomTableData = \
				sessionData
		else:
			self.initialSettings = {}
			self.coordTableData = self.geomTableData = None
		ModelessDialog.__init__(self)
		from chimera import triggers, BEGIN_RESTORE_SESSION
		triggers.addHandler(BEGIN_RESTORE_SESSION, self._beginSessionRestoreCB, None)

	def fillInUI(self, parent):
		import Tkinter, Pmw

		self._atomTrigID = chimera.triggers.addHandler('Atom', self._atomCB,
														None)
		row = 0
		f = Tkinter.Frame(parent)
		from chimera.widgets import MetalOptionMenu
		self.metalsMenu = MetalOptionMenu(f, numbering=True)
		if self.initialSettings and self.initialSettings["metal"]:
			self.metalsMenu.setvalue(self.initialSettings["metal"])
		self.metalsMenu.configure(command=self._populateTable)
		self.metalsMenu.grid(row=0, column=0)
		self.nextMetalButton = Tkinter.Button(f, text="Next metal",
			command=self._nextMetal)
		self.nextMetalButton.grid(row=0, column=1)
		f.grid(row=row, column=1)

		from CGLtk.Font import shrinkFont
		f = Tkinter.Frame(parent)
		f.grid(row=row, column=3, sticky='ew')
		scaleTitle = Tkinter.Label(f, text="Metal transparency")
		scaleTitle.grid(row=0, column=1)
		opaque = Tkinter.Label(f, text="opaque")
		shrinkFont(opaque)
		opaque.grid(row=1, column=0)
		self.metalTransparencyVar = Tkinter.DoubleVar(parent)
		self.metalTransparencyVar.set(
			self.initialSettings.get("metal transparency", 0.0))
		self._colorCache = (None, None)
		Tkinter.Scale(f, command=self._transparencyCB, from_=0.0, to=1.0,
			resolution=0.01, showvalue=0, variable=self.metalTransparencyVar,
			orient='horizontal').grid(row=1, column=1, sticky='ew')
		f.columnconfigure(1, weight=1)
		transparent = Tkinter.Label(f, text="transparent")
		shrinkFont(transparent)
		transparent.grid(row=1, column=2)
		row += 1

		from CGLtk.Table import SortableTable
		ct = self.coordinationTable = SortableTable(parent,
						allowUserSorting=False)
		ct.grid(row=row, rowspan=2, column=0, columnspan=3, sticky="nsew")
		parent.rowconfigure(row, weight=1)
		parent.columnconfigure(0, weight=1)
		parent.columnconfigure(1, weight=1)
		parent.columnconfigure(2, weight=1)
		ct.addColumn("Coordinator", str)
		dc = ct.addColumn(u"Distance (\N{ANGSTROM SIGN})",
				lambda a, mm=self.metalsMenu:
				mm.getvalue().coord().distance(a.coord()),
				format="%.2f", font="TkFixedFont")
		# have to be a little tricky since a single atom may coordinate
		# (or at least be close to) multiple metals...
		ct.addColumn("Distance RMSD", lambda a: self._avgError[a],
								format="%.3f", font="TkFixedFont")
		ct.addColumn("Best Geometry", lambda a: self._bestGeom[a] or "N/A")

		grp = Pmw.Group(parent, tag_text="Coordination Table Atoms")
		self._userLigandData = {}
		if self.initialSettings:
			for metal, data in self.initialSettings["user ligand data"].items():
				included, excluded = data
				self._userLigandData[metal] = (set(included), set(excluded))
		inside = grp.interior()
		if chimera.tkgui.windowSystem == "aqua":
			kw = {}
		else:
			kw = {'padx': 0}
		f = Tkinter.Frame(inside)
		f.grid(row=0, sticky='w')
		self.includeLigandButton = Tkinter.Button(f, text="Add", pady=0,
				command=self.addLigands, **kw)
		self.includeLigandButton.grid(row=0, column=0)
		Tkinter.Label(f, text="atoms selected in graphics window"
						).grid(row=0, column=1)
		f = Tkinter.Frame(inside)
		f.grid(row=1, sticky='w')
		self.excludeLigandButton = Tkinter.Button(f, text="Remove", pady=0,
				command=self.removeLigands, **kw)
		self.excludeLigandButton.grid(row=0, column=0)
		Tkinter.Label(f, text="atoms selected in graphics window"
						).grid(row=0, column=1)
		self.altlocMenu = Pmw.OptionMenu(inside, command=self._altlocMenuCB,
			labelpos='w', label_text="Alt loc:")
		self.altlocMenu.grid(row=2)
		grp.grid(row=row, column=3)
		row += 1
		parent.rowconfigure(row, weight=1)
		f = Tkinter.Frame(parent)
		f.grid(row=row, column=3)
		Tkinter.Button(f, text="Create/Update", pady=0,
					command=self.updateGroup, **kw).grid(row=0, column=0)
		Tkinter.Label(f, text="metal-complex pseudobonds"
						).grid(row=0, column=1)
		from chimera.pbgPanel import attributesCmd
		Tkinter.Button(f, text="Display options...", command=lambda
			cmd=attributesCmd: self.metalsMenu.getvalue() and
			cmd([self.metalsMenu.getvalue().molecule.metalComplexGroup()])
			).grid(row=1, column=0, columnspan=2)
			
		row += 1

		import sys
		if sys.platform != "darwin" or chimera.tkgui.windowSystem == "aqua":
			# Unicode arrow not depicted as such on Mac X11
			downArrow1 = Tkinter.Label(parent,
							text=u"\N{DOWNWARDS WHITE ARROW}")
			downArrow2 = Tkinter.Label(parent,
							text=u"\N{DOWNWARDS WHITE ARROW}")
			shrinkFont(downArrow1, fraction=4.0)
			shrinkFont(downArrow2, fraction=4.0)
			downArrow1.grid(row=row, column=0)
			downArrow2.grid(row=row, column=2)

		grp = Pmw.Group(parent, tag_text="Coordination/Geometry Tables")
		grp.grid(row=row, column=1)
		screenFrame = grp.interior()
		
		self.screenUnfilledVar = Tkinter.IntVar(parent)
		self.screenUnfilledVar.set(
			self.initialSettings.get("screen unfilled", False))
		Tkinter.Checkbutton(screenFrame, variable=self.screenUnfilledVar,
			text='Screen unfilled geometries',
			command=self.metalsMenu.invoke).grid(row=0, sticky='w')

		self.screenParamsVar = Tkinter.IntVar(parent)
		self.screenParamsVar.set(
			self.initialSettings.get("screen overcrowded", True))
		f = Tkinter.Frame(screenFrame)
		f.grid(row=1, sticky='w')
		Tkinter.Checkbutton(f, variable=self.screenParamsVar,
			text='Screen "overcrowded" geometries',
			command=self.metalsMenu.invoke).grid(row=0, column=0)
		self._sopButTexts = [ "Show parameters", "Hide parameters" ]
		self._soParamsButton = Tkinter.Button(f,
					text=self._sopButTexts[0], pady=0,
					command=self._hideShowSOParams)
		self._soParamsButton.grid(row=0, column=1)

		spf = self._soParamsFrame = Tkinter.Frame(screenFrame)
		self._soParamsRow = 2
		Tkinter.Label(spf, text="A geometry is considered overcrowded if"
			" hypothetical metal-\nligating atoms placed at the ideal angles"
			" for that geometry,", justify="left").grid(
			row=0, column=0, sticky='w')
		f = Tkinter.Frame(spf)
		f.grid(row=1, column=0, sticky='w')
		self._ligPosLabel2Val = {
			"minimum": "min",
			"average": "mid",
			"maximum": "max"
		}
		self._ligPosVal2Label = {}
		for k, v in self._ligPosLabel2Val.items():
			self._ligPosVal2Label[v] = k
		menuItems = self._ligPosLabel2Val.keys()
		menuItems.sort()
		self.ligPosMenu = Pmw.OptionMenu(f, command=self._paramChangeCB,
			items=menuItems, initialitem=self._ligPosVal2Label[
			self.initialSettings.get("ligand position", prefs[LIG_POS])],
			labelpos='w', label_text="at a distance equal to the")
		self.ligPosMenu.grid(row=0, column=0)
		Tkinter.Label(f, text="of the actual").grid(row=0, column=1)
		f = Tkinter.Frame(spf)
		f.grid(row=2, column=0, sticky='w')
		Tkinter.Label(f, text="chosen ligating atoms, would be less than"
			).grid(row=0, column=0)
		self.ligSepEntry = Pmw.EntryField(f, command=self._paramChangeCB,
			labelpos='e', label_text=u"\N{ANGSTROM SIGN} apart.", validate='real',
			entry_width=4, value="%g"
			% self.initialSettings.get("ligand separation", prefs[LIG_SEP]))
		self.ligSepEntry.grid(row=0, column=1)
		row += 1

		from CGLtk.Table import SortableTable
		gt = self.geometryTable = SortableTable(parent)
		gt.grid(row=row, rowspan=2, column=0, columnspan=3, sticky="nsew")
		parent.rowconfigure(row, weight=2)

		gt.addColumn("Geometry", str)
		gt.addColumn("Coord. Number", 'coordinationNumber')
		ac = gt.addColumn("Distance RMSD", lambda g: geomDistEval(g,
			self.metalsMenu.getvalue(), self.selCoordinationAtoms())[0],
			format="%.3f", font="TkFixedFont")

		self.geomModel = None
		self.showIdealGeomVar = Tkinter.IntVar(parent)
		self.showIdealGeomVar.set(self.initialSettings.get("show ideal", False))
		Tkinter.Checkbutton(parent, command=self._showGeomCB, text=
			"Depict idealized geometry", variable=self.showIdealGeomVar
			).grid(row=row, column=3)
		row += 1

		parent.rowconfigure(row, weight=2)
		f = Tkinter.Frame(parent)
		f.grid(row=row, column=3)
		Tkinter.Button(f, text="Add", pady=0, command=self.addWater, **kw
						).grid(row=0, column=0)
		Tkinter.Label(f, text="water oxygens at unfilled sites"
						).grid(row=0, column=1)
		f2 = Tkinter.Frame(f)
		f2.grid(row=1, column=0, columnspan=2)
		self.waterDistEntry = Pmw.EntryField(f2, labelpos='w', label_text=
			"at a distance of", validate='real', entry_width=5,
			value=self.initialSettings.get("water dist", '2.5'))
		self.waterDistEntry.grid(row=0, column=0)
		Tkinter.Label(f2, text=u"\N{ANGSTROM SIGN}").grid(row=0, column=1)
		row += 1

		altloc = self.initialSettings.get("altloc", None)
		if altloc is not None:
			self.altlocMenu.setitems(self.initialSettings["altloc menu items"],
				index=altloc)
		#self.metalsMenu.invoke()
		self._populateTable(self.metalsMenu.getvalue(), altloc=altloc)
		ct.launch(title="Coordination Table", selectMode="browse",
					browseCmd=self._tableCB)
		if self.coordTableData:
			self._restoreTable(ct, self.coordTableData)
		else:
			ct.sortBy(dc)
		self._fixCoordTableWidth()
		gt.launch(title="Geometry Table (for chosen coordination)", rows=5,
			browseCmd=self.geometryDepiction)
		if self.geomTableData:
			self._setGeomTableData(self.selCoordinationAtoms())
			self._restoreTable(gt, self.geomTableData)
			if self.showIdealGeomVar.get():
				self._showGeomCB()
		else:
			gt.sortBy(ac)

	def Close(self):
		self.metalTransparencyVar.set(0.0)
		metal, oldColor = self._colorCache
		if metal and not metal.__destroyed__:
			metal.color = oldColor
		self._colorCache = (None, None)
		self.showIdealGeomVar.set(False)
		self.geometryDepiction(None)
		ModelessDialog.Close(self)

	def addLigands(self, newLigands=None):
		from chimera.selection import currentAtoms
		if newLigands == None:
			newLigands = set(currentAtoms())
			if not newLigands:
				raise UserError("No atoms selected")
		else:
			newLigands = set(newLigands)
		metal = self.metalsMenu.getvalue()
		for nl in newLigands:
			if nl.molecule != metal.molecule:
				raise UserError("Ligating atoms must be in same model as metal")
		include, exclude = self._userLigandData.setdefault(metal,
															(set(), set()))
		include.update(newLigands)
		exclude.difference_update(newLigands)
		self._populateTable(metal)

	def addWater(self):
		geoms = self.geometryTable.selected()
		if not geoms:
			raise UserError("No geometry selected")
		elif len(geoms) > 1:
			raise UserError("Multiple geometries selected; choose only one")
		geom = geoms[0]
		metal = self.metalsMenu.getvalue()
		ligands = self.selCoordinationAtoms()
		if len(ligands) < 2:
			raise UserError("Need at least two coordinating atoms to"
				" orient geometry")
		elif len(ligands) >= geom.coordinationNumber:
			raise UserError("No unfilled sites for %s geometry" % geom)
		self.waterDistEntry.invoke()
		length = float(self.waterDistEntry.getvalue())
		if length < 0.0:
			raise UserError("Water distance must be non-negative")
		rmsd, center, vecs = geomDistEval(geom, metal, ligands)
		from chimera.molEdit import addAtom
		waters = []
		chain = metal.residue.id.chainId
		mol = metal.molecule
		pos = 1
		oxygen = chimera.Element("O")
		from Midas import elementColor
		ocolor = elementColor(oxygen)
		for vec in vecs[len(ligands):]:
			while mol.findResidue(chimera.MolResId(chain, pos)):
				pos += 1
			res = mol.newResidue("HOH", chain, pos, ' ')
			res.isHet = True
			vec.length = length
			waters.append(addAtom("O", oxygen, res, center+vec))
			waters[-1].drawMode = ligands[0].drawMode
			waters[-1].color = ocolor
			altloc = self.altlocMenu.getvalue()
			if len(altloc) == 1:
				waters[-1].altLoc = str(altloc)
		self.addLigands(waters)

	def destroy(self):
		chimera.triggers.deleteHandler('Atom', self._atomTrigID)
		from SimpleSession import SAVE_SESSION
		chimera.triggers.deleteHandler(SAVE_SESSION, self._sesHandlerID)
		ModelessDialog.destroy(self)

	def geometryDepiction(self, geoms):
		if self.geomModel:
			chimera.openModels.close([self.geomModel])
			self.geomModel = None
		if not geoms:
			return
		if not self.showIdealGeomVar.get():
			return
		from CGLtk.color import distinguishFrom
		if chimera.viewer.background:
			rgbs = [chimera.viewer.background.rgba()[:3]]
		else:
			rgbs = [(0.0, 0.0, 0.0)]
		rgbs.append(chimera.viewer.highlightColor.rgba()[:3])
		colors = []
		while len(colors) < len(geoms):
			# since we are "using up" candidates, need to ask for more
			# as we show more geometries...
			colors.append(distinguishFrom(rgbs, seed=14147, saveState=False,
				numCandidates=3+len(colors)))
			rgbs.append(colors[-1])
		bildString = ""
		metal = self.metalsMenu.getvalue()
		ligands = self.selCoordinationAtoms()
		if len(ligands) < 2:
			raise UserError("Need at least two coordinating atoms to"
				" orient geometry depiction")
		for rgb, geom in zip(colors[:len(geoms)], geoms):
			bildString += ".color %g %g %g\n" % tuple(rgb)
			rmsd, center, vecs = geomDistEval(geom, metal, ligands)
			for vec in vecs:
				v = center + vec
				bildString += ".arrow %g %g %g %g %g %g .1 .2 .9\n" % (
					center[0], center[1], center[2], v[0], v[1], v[2])
		from StringIO import StringIO
		bild = StringIO(bildString)
		self.geomModel = chimera.openModels.open(bild, type="Bild",
			hidden=True, identifyAs="%s coordination geometries" % metal,
			sameAs=metal.molecule)[0]
		
	def removeLigands(self):
		from chimera.selection import currentAtoms
		selAtoms = set(currentAtoms())
		if not selAtoms:
			raise UserError("No atoms selected")
		metal = self.metalsMenu.getvalue()
		include, exclude = self._userLigandData.setdefault(metal,
															(set(), set()))
		include.difference_update(selAtoms)
		exclude.update(selAtoms)
		self._populateTable(metal)

	def selCoordinationAtoms(self):
		sel = self.coordinationTable.selected()
		if sel:
			atoms = self.coordinationTable.data
			sel = atoms[:atoms.index(sel)+1]
		else:
			sel = []
		return sel

	def updateGroup(self):
		ligands = self.selCoordinationAtoms()
		if not ligands:
			raise UserError("No coordination chosen")
		metalGroup = ligands[0].molecule.metalComplexGroup()
		metal = self.metalsMenu.getvalue()
		for pb in metalGroup.pseudoBonds:
			if metal in pb.atoms:
				metalGroup.deletePseudoBond(pb)
		for ligand in ligands:
			metalGroup.newPseudoBond(metal, ligand)

	def _altlocMenuCB(self, val):
		self._populateTable(self.metalsMenu.getvalue(), altloc=val)

	def _atomCB(self, trigName, myData, trigData):
		if not trigData.deleted:
			return
		for include, exclude in self._userLigandData.values():
			include -= trigData.deleted
			exclude -= trigData.deleted
		curMetal = self.metalsMenu.getvalue()
		for metal in self._userLigandData.keys():
			if metal in trigData.deleted:
				del self._userLigandData[metal]
		if curMetal in trigData.deleted:
			return
		if not trigData.deleted.isdisjoint(self.coordinationTable.data):
			self.coordinationTable.refresh()
		
	def _beginSessionRestoreCB(self, trigName, myData, trigData):
		if dialogs.find(self.name, create=False) == self:
			dialogs.reregister(self.name, MetalsDialog)
		self.Close()
		self.destroy()
		from chimera.triggerSet import ONESHOT
		return ONESHOT

	def _fixCoordTableWidth(self):
		"""try to prevent last column from being excessively wide"""
		ct = self.coordinationTable
		hl = ct.tixTable.hlist
		reqWidth = 100
		reqWidth += int(hl.column_width(0)) + int(hl.column_width(3))
		# hlist width is in "characters", ugh
		hl.configure(width=int(reqWidth/9))

	def _nextMetal(self):
		import Pmw
		curIndex = self.metalsMenu.index(Pmw.SELECT)
		self.metalsMenu.invoke(curIndex+1)

	def _paramChangeCB(self, *args):
		if self.screenParamsVar.get():
			prefs[LIG_POS], prefs[LIG_SEP] = (
				self._ligPosLabel2Val[self.ligPosMenu.getvalue()],
				float(self.ligSepEntry.component('entry').get()))
			self.metalsMenu.invoke()

	def _populateTable(self, metal, altloc=None):
		self.status("")
		global _gdeCache
		metalDict = self.metalsMenu.valueMap
		for key in _gdeCache.keys():
			if key[1] not in metalDict:
				del _gdeCache[key]
		if len(metalDict) > 1:
			self.nextMetalButton.grid()
			import Pmw
			self.nextMetalButton.configure(state=("disabled" if
				self.metalsMenu.index(Pmw.SELECT) + 1 == len(metalDict) else "normal"))
		else:
			self.nextMetalButton.grid_remove()
		data = []
		# allow the metals to get colored
		self.uiMaster().after(40, lambda *args:
			self._transparencyCB(self.metalTransparencyVar.get()))
		if not metal:
			self.coordinationTable.setData(data)
			self.geometryTable.setData([])
			self._focusData = None
			self.includeLigandButton.configure(state="disabled")
			self.excludeLigandButton.configure(state="disabled")
			return
		self.status("Computing RMSDs")
		self.includeLigandButton.configure(state="normal")
		self.excludeLigandButton.configure(state="normal")
		userIncluded, userExcluded = self._userLigandData.get(metal,
														(set(), set()))
		from numpy import array
		atoms = array(metal.molecule.atoms)
		from _multiscale import get_atom_coordinates as gac
		from _closepoints import find_close_points, BOXES_METHOD
		ignore, close = find_close_points(BOXES_METHOD,
			gac(array([metal])), gac(atoms), self.coordLimit)
		candidates = list(set(atoms[close]) | userIncluded)
		mcrd = metal.coord()
		candidates.sort(lambda a1, a2: cmp(a1.coord().sqdistance(mcrd),
						a2.coord().sqdistance(mcrd)))
		exclude = userExcluded.copy()
		self._bestGeom = {}
		self._avgError = {}
		if self.screenParamsVar.get():
			criteria = (self._ligPosLabel2Val[self.ligPosMenu.getvalue()],
						float(self.ligSepEntry.component('entry').get()))
		else:
			criteria = None
		for candidate in candidates:
			if candidate == metal:
				continue
			if candidate in exclude:
				continue
			if candidate not in userIncluded:
				valence = (candidate.element.number - 2) % 8
				if valence < 5 or candidate.element.number == 1:
					continue
				if candidate.coord().distance(mcrd) > self.coordLimit:
					break
				if candidate not in metal.bondsMap:
					from chimera import angle
					from chimera.idatm import typeInfo
					angleOK = True
					try:
						cnGeom = typeInfo[candidate.idatmType].geometry
					except KeyError:
						cnGeom = 0
					else:
						if len(candidate.primaryNeighbors()) == cnGeom:
							# no lone pairs, no possibility of deprotonation
							continue
					angleCutoff = [0.0, 72.98, 120.0, 80.0, 72.98][cnGeom]
					for cnb in candidate.neighbors:
						if cnb == metal:
							continue
						if angle(cnb.coord(), candidate.coord(),
									metal.coord()) < angleCutoff:
							angleOK = False
							break
					if not angleOK:
						continue
			data.append(candidate)
			exclude.update([nb for nb in candidate.neighbors if nb not in userIncluded])
		if altloc:
			# called by choosing altloc menu
			data = [a for a in data if a.altLoc in [altloc, '']]
		else:
			altlocs = set([a.altLoc for a in data])
			alMB = self.altlocMenu.component('menubutton')
			alMB.configure(state="normal")
			if altlocs == set(['']):
				self.altlocMenu.setitems(["N/A"])
				alMB.configure(state="disabled")
			else:
				altlocs.discard('')
				items = list(altlocs)
				items.sort()
				self.altlocMenu.setitems(items)
				if len(items) == 1:
					choice = items[0]
				elif metal.altLoc in items:
					choice = metal.altLoc
				else:
					best = None
					for al in altlocs:
						occs = [a.occupancy for a in data if a.altLoc == al]
						score = sum(occs) / len(occs)
						if best is None or score > bestScore:
							best = al
							bestScore = score
					choice = best
				self.altlocMenu.setvalue(choice)
				data = [a for a in data if a.altLoc in [choice, '']]
		for i, candidate in enumerate(data):
			self._bestGeom[candidate], self._avgError[candidate] = \
				bestDistGeom(metal, data[:i+1], overcrowdingCriteria=criteria,
				screenUnfilled=self.screenUnfilledVar.get())
		self.status("")
		self.coordinationTable.setData(data)
		if self.coordinationTable.tixTable:
			self._fixCoordTableWidth()
			sel = self.selCoordinationAtoms()
			if sel:
				self.coordinationTable.highlight(sel)
		else:
			sel = None
		self._setGeomTableData(sel)
		if self.metalsMenu.winfo_ismapped():
			self._focus([metal] + data)
		else:
			self._focusData = [metal] + data

	def map(self, e=None):
		if self._focusData:
			self._focus([a for a in self._focusData
					if not a.__destroyed__])

	def _focus(self, focusAtoms):
		if focusAtoms:
			from Midas import focus, MidasError
			try:
				focus(focusAtoms)
			except MidasError:
				self.status("%s is not currently displayed" % focusAtoms[0],
								color="red")
		self._focusData = None


	def _getTableRestoreInfo(self, table):
		sortCol, forward = table.sorting
		sortCol = table.columns.index(sortCol)
		selected = table.selected()
		if isinstance(selected, (tuple, list)):
			sel = [table.data.index(s) for s in selected]
		elif selected is None:
			sel = None
		else:
			sel = table.data.index(selected)
		return (sortCol, forward, sel, table.highlightedIndices())

	def _hideShowSOParams(self):
		if self._soParamsFrame.winfo_ismapped():
			self._soParamsFrame.grid_forget()
			self._soParamsButton.configure(text=self._sopButTexts[0])
		else:
			self._soParamsFrame.grid(row=self._soParamsRow, column=0,
										columnspan=2, sticky='ew')
			self._soParamsButton.configure(text=self._sopButTexts[1])

	def _restoreTable(self, table, restoreInfo):
		sortColIndex, forward, selected, highlighted = restoreInfo
		sortCol = table.columns[sortColIndex]
		table.sortBy(sortCol)
		if not forward:
			table.sortBy(sortCol)
		if isinstance(selected, list):
			table.select([table.data[s] for s in selected])
		elif selected is not None:
			table.select(table.data[selected])
		if highlighted:
			table.highlight([table.data[h] for h in highlighted])

	def _sessionSaveCB(self, trigName, myData, sesFile):
		if not self.uiMaster().winfo_ismapped():
			return
		from SimpleSession import sessionID
		metal = self.metalsMenu.getvalue()
		if metal:
			metal = sessionID(metal)
		ligData = {}
		altloc = self.altlocMenu.getvalue()
		if altloc and len(altloc) != 1:
			altloc = None
		from Pmw import END
		settings = {
			"metal": metal,
			"metal transparency": self.metalTransparencyVar.get(),
			"user ligand data": ligData,
			"altloc": altloc,
			"altloc menu items": [self.altlocMenu.component("menu").entrycget(i,
				"label") for i in range(0, self.altlocMenu.index(END)+1)],
			"screen unfilled": self.screenUnfilledVar.get(),
			"screen overcrowded": self.screenParamsVar.get(),
			"ligand position": prefs[LIG_POS],
			"ligand separation": prefs[LIG_SEP],
			"show ideal": self.showIdealGeomVar.get(),
			"water dist": self.waterDistEntry.get()
		}
		for metal, userData in self._userLigandData.items():
			included, excluded = userData
			ligData[sessionID(metal)] = ([sessionID(a) for a in included],
				[sessionID(a) for a in excluded])
		# both tables include callables for column fetching, so use homebrew
		# table save/restore
		data = (1, settings, self._getTableRestoreInfo(self.coordinationTable),
			self._getTableRestoreInfo(self.geometryTable))
		print>>sesFile, """
try:
	from MetalGeom.gui import sessionRestore
	sessionRestore(%s)
except:
	reportRestoreError("Error restoring Metal Geometry interface")
""" % repr(data)

	def _setGeomTableData(self, sel):
		if not sel:
			self.geometryTable.setData([])
			return
		from geomData import geometries
		geoms = [g for g in geometries.values()
					if g.coordinationNumber >= len(sel)]
		if self.screenParamsVar.get():
			mc = self.metalsMenu.getvalue().coord()
			lcs = [l.coord() for l in sel]
			ligPos = self._ligPosLabel2Val[self.ligPosMenu.getvalue()]
			ligSep = float(self.ligSepEntry.component('entry').get())
			geoms = [g for g in geoms if g.angleSepOK(ligPos, ligSep,
											enumerateDists(mc, lcs))]
		if self.screenUnfilledVar.get():
			geoms = [g for g in geoms if len(sel) == g.coordinationNumber]

		self.geometryTable.setData(geoms)

	def _showGeomCB(self):
		geoms = self.geometryTable.selected()
		if self.showIdealGeomVar.get() and not geoms:
			self.status("No geometry selected in Geometry Table", color="blue")
		else:
			self.status("")
		self.geometryDepiction(geoms)

	def _tableCB(self, coord):
		sel = self.selCoordinationAtoms()
		for a in sel:
			if not a.display:
				a.display = True
				if a.bonds:
					for ra in a.residue.atoms:
						ra.display = True
		from chimera.selection import setCurrent
		setCurrent(sel)
		if coord:
			atoms = self.coordinationTable.data
			self.coordinationTable.highlight(atoms[:atoms.index(coord)+1])
		else:
			self.coordinationTable.highlight([])
		self._setGeomTableData(sel)
		if coord:
			bestGeom = self._bestGeom[coord]
			if bestGeom:
				self.geometryTable.select([bestGeom])
			else:
				self.geometryTable.select([])
			mc = self.metalsMenu.getvalue().coord()
			avgLen = sum([(a.coord() - mc).length for a in sel]) / len(sel)
			self.waterDistEntry.setvalue("%.3f" % avgLen)
		self.geometryDepiction(self.geometryTable.selected())

	def _transparencyCB(self, val):
		metal = self.metalsMenu.getvalue()
		if metal:
			if metal == self._colorCache[0]:
				color = metal.color
			else:
				oldMetal, oldColor = self._colorCache
				if oldMetal and not oldMetal.__destroyed__:
					oldMetal.color = oldColor
				self._colorCache = (metal, metal.color)
				if metal.color:
					color = chimera.MaterialColor(*metal.color.rgba())
				else:
					color = chimera.MaterialColor(*metal.molecule.color.rgba())
				metal.color = color
			color.opacity = 1.0 - float(val)
		else:
			self._colorCache = (None, None)

_gdeCache = {}
def geomDistEval(geom, metal, ligands):
	"""method:
		(1) pick any metal-ligand pair (as "primary")
		(2) pick any other pair (as "secondary")
		(3) for each vector in the geometry:
			(3a) orient towards primary
			(3b) for each other vector in the geometry:
				(3b1) orient towards secondary (rotate)
				(3b2) find correspondences between remaining
					ligands and other vectors, closest first
				(3b3) get RMSD based on these pairings (incl. metal)
		(4) return lowest RMSD pairing
	"""
	global _gdeCache
	key = (geom, metal) + tuple(ligands)
	if key in _gdeCache:
		return _gdeCache[key]
	if len(ligands) == 1:
		return (0.0, None, None)
	from chimera import Vector, cross, Xform, Plane, angle, Point
	from math import acos, degrees
	mc = metal.coord()
	lcoords = [l.coord() for l in ligands]
	lvecs = [lc - mc for lc in lcoords]
	for lv in lvecs:
		lv.normalize()
	# (1), (2): pick primary, secondary
	npv, nsv = lvecs[:2]
	nsvpt = Point(*nsv.data())
	origin = Point()
	# (3) for each vector in the geometry
	bestCorrespondence = None
	for i1, nv1 in enumerate(geom.normVecs):
		# (3a) orient towards primary
		rotAxis = cross(nv1, npv)
		cos = nv1 * npv
		ang = degrees(acos(cos))
		# Xform.rotation does a "fuzzy" test against zero and will
		# throw an error if the fuzzy test fails, so we need to
		# do the same fuzzy test
		if rotAxis.length > 0.00001:
			xf1 = Xform.rotation(rotAxis, ang)
		elif cos > 0:
			xf1 = Xform.identity()
		else:
			xf1 = Xform.rotation(1.0, 0.0, 0.0, 180.0)
		plane1 = Plane(origin, cross(npv, nsv))
		# (3b) for each other vector in the geometry
		for i2, nv2 in enumerate(geom.normVecs):
			if i1 == i2:
				continue
			# (3b1) orient towards secondary
			xfnv2 = xf1.apply(nv2)
			# Vectors have no rounding tolerance for equality tests
			#if npv == xfnv2 or npv == -xfnv2:
			ang = angle(npv, xfnv2)
			if ang < 0.00001 or ang > 179.99999:
				xf2 = Xform.identity()
			else:
				plane2 = Plane(origin, cross(npv, xfnv2))
				ang = angle(plane1.normal, plane2.normal)
				if plane1.distance(Point(*xfnv2.data())) > 0.0:
					angles = [0.0 - ang, 180.0 - ang]
				else:
					angles = [ang, ang - 180.0]
				bestD = None
				for ang in angles:
					xf = Xform.rotation(npv, ang)
					d = nsvpt.sqdistance(Point(*xf.apply(xfnv2)))
					if bestD == None or d < bestD:
						bestD = d
						xf2 = xf
			# (3b2) find correspondences between remaining
			#	ligands and other vectors, closest first
			xf = Xform.identity()
			xf.multiply(xf2)
			xf.multiply(xf1)
			correspondences = { npv: nv1, nsv: nv2 }
			used = set([i1, i2])
			xfnvs = [xf.apply(nv) for nv in geom.normVecs]
			diffs = []
			for i, xfnv in enumerate(xfnvs):
				if i in used:
					continue
				for lv in lvecs[2:]:
					diffs.append((angle(xfnv, lv), lv, i))
			# use 'key' to prevent the vector second arg from ever being used (has no '<' operator)
			diffs.sort(key=lambda diff: diff[0])
			while len(used) < len(ligands):
				ang, lv, i = diffs.pop(0)
				if i in used or lv in correspondences:
					continue
				correspondences[lv] = geom.normVecs[i]
				used.add(i)
			# (3b3) get RMSD based on these pairings (incl. metal)
			from chimera.match import matchPositions
			realPts = [mc] + lcoords
			idealVecs = []
			for lv, lc in zip(lvecs, lcoords):
				nv = correspondences[lv]
				idealVecs.append(xf.apply(nv) * (lc - mc).length)
			idealPts = [origin] + [origin + iv for iv in idealVecs]
			rmsdXf, rmsd = matchPositions(realPts, idealPts)
			if bestCorrespondence == None or rmsd < bestRmsd:
				bestCorrespondence = correspondences
				bestRmsd = rmsd
				# have to also supply vectors for the ideal
				# geometry at unfilled positions...
				avgLen = sum([(lc - mc).length for lc in lcoords]
							) / len(lcoords)
				unfilled = []
				for i, nv in enumerate(geom.normVecs):
					if i in used:
						continue
					unfilled.append(rmsdXf.apply(xf.apply(nv) * avgLen))
				# addWater() method depends on unfilled being last
				bestResult = (bestRmsd, rmsdXf.apply(origin),
					[rmsdXf.apply(iv) for iv in idealVecs] + unfilled)
	#(4) return lowest RMSD pairing
	_gdeCache[key] = bestResult
	return bestResult

def bestDistGeom(metal, ligands, overcrowdingCriteria=None, screenUnfilled=False):
	from geomData import geomData, geometries
	if len(ligands) not in geomData:
		return "N/A", 0.0
	bestRmsd = None
	mc = metal.coord()
	lcs = [l.coord() for l in ligands]
	for geom in geometries.values():
		if len(ligands) > geom.coordinationNumber:
			continue
		if overcrowdingCriteria:
			ligLoc, minSep = overcrowdingCriteria
			dists = enumerateDists(mc, lcs)
			if not geom.angleSepOK(ligLoc, minSep, dists):
				continue
		if screenUnfilled and len(ligands) < geom.coordinationNumber:
			continue
		rmsd, center, vecs = geomDistEval(geom, metal, ligands)
		if bestRmsd is None or rmsd < bestRmsd:
			bestRmsd = rmsd
			bestGeom = geom
	if bestRmsd == None:
		return None, None
	return bestGeom, bestRmsd

def bestAngleGeom(metal, ligands, overcrowdingCriteria=None, screenUnfilled=False):
	from geomData import geomData, minAngles, geometries
	if len(ligands) not in geomData:
		return "N/A", 0.0
	angleSets = geomData[len(ligands)]
	mc = metal.coord()
	lcs = [l.coord() for l in ligands]
	if overcrowdingCriteria:
		dists = enumerateDists(mc, lcs)
	angles = []
	from chimera import angle
	for i, l1 in enumerate(lcs):
		for l2 in lcs[i+1:]:
			angles.append(angle(l1, mc, l2))
	angles.sort()
	bestErrorSq = None
	exclude = {}
	for testAngles, fullCoordination, description in angleSets:
		if screenUnfilled and len(ligands) < fullCoordination:
			continue
		geom = geometries[description]
		if overcrowdingCriteria:
			if geom not in exclude:
				ligLoc, minSep = overcrowdingCriteria
				exclude[geom] = not geom.angleSepOK(ligLoc, minSep, dists)
			if exclude[geom]:
				continue
		errorSq = 0.0
		for a, ta in zip(angles, testAngles):
			d = a - ta
			errorSq += d * d
		if bestErrorSq is None or errorSq < bestErrorSq or (
		errorSq == bestErrorSq and fullCoordination < bestCoord):
			bestErrorSq = errorSq
			bestGeom = geom
			bestCoord = fullCoordination
	if bestErrorSq == None:
		return None, None
	from math import sqrt
	return bestGeom, sqrt(bestErrorSq / len(angles))

def enumerateDists(mc, lcs):
	dists = []
	for lc in lcs:
		dists.append(lc.distance(mc))
	return dists

def sessionRestore(data):
	version, settings, coordTableData, geomTableData = data
	from SimpleSession import idLookup
	if settings["metal"] is not None:
		settings["metal"] = idLookup(settings["metal"])
	uld = settings["user ligand data"]
	settings["user ligand data"] = newULD = {}
	for metal, userData in uld.items():
		included, excluded = userData
		newULD[idLookup(metal)] = ([idLookup(i) for i in included],
			[idLookup(e) for e in excluded])
	d = MetalsDialog(sessionData=(settings, coordTableData, geomTableData))
	if dialogs.find(MetalsDialog.name, create=False) == None:
		dialogs.reregister(MetalsDialog.name, d)

from chimera import dialogs
dialogs.register(MetalsDialog.name, MetalsDialog)
