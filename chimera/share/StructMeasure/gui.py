# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: gui.py 40584 2015-05-13 17:24:03Z pett $

"""Interface to structure measurements (e.g. distances, angles)"""

import Pmw
import chimera
from chimera import replyobj, selection
from chimera.baseDialog import ModelessDialog
import Tkinter
from DistMonitor import distanceMonitor, addDistance, removeDistance, \
	precision, setPrecision, showUnits
from chimera import dihedral
from prefs import prefs, ANGLE_PRECISION, DIST_COLOR, DIST_LINE_TYPE, \
	DIST_LINE_WIDTH

DISTANCES = "Distances"
BONDROTS = "Adjust Torsions"
ANGLES = "Angles/Torsions"
GEOMETRIES = "Axes/Planes/Centroids"
# add in remaining tabs later
pageNames = [DISTANCES, ANGLES, BONDROTS, GEOMETRIES]
# the follow import needed until there's a ChimeraExtension.py
import Axes, Planes, Centroids

class StructMeasure(ModelessDialog):
	title="Structure Measurements"
	buttons=("Close", "Save")
	name="structure measurements"
	provideStatus = True
	statusPosition = "above"

	def fillInUI(self, parent):
		self.distances = []
		self.angleInfo = []

		self.numMolecules = len(chimera.openModels.list(
						modelTypes=[chimera.Molecule]))
		chimera.triggers.addHandler('Molecule', self._molChange, None)
		chimera.triggers.addHandler('PseudoBond', self._psbChange, None)
		chimera.triggers.addHandler('PseudoBondGroup', self._psgChange, None)
		chimera.triggers.addHandler('Atom', self._atomChange, None)
		chimera.triggers.addHandler('Model', self._modelChange, None)
		distanceMonitor.dmUpdateCallbacks.append(self._distUpdateCB)

		self.notebook = Pmw.NoteBook(parent,
						raisecommand=self._nbRaiseCB,
						lowercommand=self._nbLowerCB)
		self.notebook.pack(fill='both', expand=1)

		self.interfaces = {}
		for pn in pageNames:
			pageID = pn
			## when more tabs shown, maybe do this...
			#if '/' in pn:
			#	parts = pn.split('/')
			#	pn = "/ ".join(parts)
			#if ' ' in pn:
			#	parts = pn.split(' ')
			#	pn = '\n'.join(parts)
			self.notebook.add(pageID, tab_text=pn)

		dp = self.notebook.page(DISTANCES)
		from CGLtk.Table import SortableTable
		self.distTable = SortableTable(dp)
		self.distTable.grid(row=0, column=0, sticky='nsew', rowspan=7)
		dp.columnconfigure(0, weight=1)
		dp.rowconfigure(4, weight=1)
		dp.rowconfigure(5, weight=1)
		self.distTable.addColumn("ID", "id", format="%d")
		self.distTable.addColumn("Atom 1",
				lambda d, s=self: s.atomLabel(d.atoms[0]))
		self.distTable.addColumn("Atom 2",
				lambda d, s=self: s.atomLabel(d.atoms[1]))
		self.distTable.addColumn("Distance",
			lambda d, s=self: s.sortableDistanceLabel(d), font="TkFixedFont")
		self.distTable.setData(self.distances)
		self.distTable.launch(browseCmd=self._distTableSelCB)

		self.distButtons = Pmw.ButtonBox(dp, padx=0)
		self.distButtons.add("Create", command=self._createDistance)
		self.distButtons.add("Remove", command=self._removeDistance)

		# remove the extra space around buttons allocated to indicate
		# which button is the 'default', so that buttons stack closely
		for but in range(self.distButtons.numbuttons()):
			self.distButtons.button(but).config(default='disabled')
		self.distButtons.alignbuttons()
		self.distButtons.grid(row=1, column=1)

		self.distLabelChoice = Pmw.RadioSelect(dp, pady=0,
			buttontype='radiobutton',
			command=self._distLabelModeChange, orient='vertical',
			labelpos='w', label_text="Labels")
		self.distLabelChoice.grid(row=2, column=1)
		self.distLabelChoice.add("None", highlightthickness=0)
		self.distLabelChoice.add("ID", highlightthickness=0)
		self.distLabelChoice.add("Distance", highlightthickness=0)
		self.distLabelChoice.invoke("Distance")

		formattingGroup = Pmw.Group(dp, tag_text="Distance formatting options")
		from CGLtk.Font import shrinkFont
		shrinkFont(formattingGroup.component('tag'))
		formattingGroup.grid(row=3, column=1, rowspan=2)
		ff = formattingGroup.interior()
		self.distPrecisionChoice = Pmw.Counter(ff, datatype={
			'counter': self._distPrecisionChange}, labelpos='w',
			label_text="Decimal places", entry_width=1,
			entry_pyclass=PrecisionEntry,
			entryfield_value=str(precision()))
		self.distPrecisionChoice.grid(row=0, column=0)

		self.showUnitsVar = Tkinter.IntVar(dp)
		self.showUnitsVar.set(showUnits())
		Tkinter.Checkbutton(ff, text="Show Angstrom symbol",
			variable=self.showUnitsVar,
			command=self._showUnitsChangeCB).grid(row=1, column=0)

		depictionGroup = Pmw.Group(dp, tag_text="Depiction options")
		shrinkFont(depictionGroup.component('tag'))
		depictionGroup.grid(row=5, column=1)
		inside = depictionGroup.interior()
		from chimera.tkoptions import RGBAOption, LineWidthOption, \
			LineTypeOption
		self.distColorOpt = RGBAOption(inside, 0, "Distance color",
			distanceMonitor.color, self._distColorChange, noneOkay=False)
		self.distLineWidthOpt = LineWidthOption(inside, 1, "Line width",
			distanceMonitor.lineWidth, self._distLineWidthChange, min=0.1,
			balloon="Width of pseudobonds (in pixels)", width=3)
		self.distLineTypeOpt = LineTypeOption(inside, 2, "Line style",
			distanceMonitor.lineType, self._distLineTypeChange,
			balloon="Draw pseudobonds in given style")

		f = Tkinter.Frame(inside)
		f.grid(row=3, column=0, columnspan=2)
		Tkinter.Button(f, text="Save", command=self._saveDistDefaults).grid(
			row=0, column=0)
		Tkinter.Label(f, text="as defaults").grid(
			row=0, column=1)

		self.distSelectsAtomsVar = Tkinter.IntVar(dp)
		self.distSelectsAtomsVar.set(False)
		Tkinter.Checkbutton(dp, variable=self.distSelectsAtomsVar,
			text="Choosing in table selects\natoms (and pseudobond)"
			).grid(row=6, column=1)

		disclaimer = Tkinter.Label(dp, text="This panel for atom-atom"
			' distances only.  Use Axes/... tab or "distance" command'
			' for other distances.')
		from CGLtk.Font import shrinkFont
		shrinkFont(disclaimer)
		disclaimer.grid(row=7, column=0, columnspan=2)

		for d in distanceMonitor.pseudoBonds:
			self.newDistance(d)

		atp = self.notebook.page(ANGLES)
		from CGLtk.Table import SortableTable
		self.angleTable = SortableTable(atp)
		self.angleTable.grid(row=0, column=0, sticky='nsew', rowspan=4)
		atp.columnconfigure(0, weight=1, minsize="3.7i")
		atp.rowconfigure(2, weight=1)
		for i in range(4):
			self.angleTable.addColumn("Atom %d" % (i+1), lambda atoms, s=self,
					i=i: i >= len(atoms) and "N/A" or s.atomLabel(atoms[i]))
		self.angleTable.addColumn("Angle/Torsion",
			lambda atoms, s=self: s._angleLabel(atoms), font="TkFixedFont")
		self.angleTable.setData(self.angleInfo)
		self.angleTable.launch(browseCmd=self._angleTableSelCB)

		self._osHandler = None
		self.angleButtons = Pmw.ButtonBox(atp, padx=0)
		self.angleButtons.add("Create", command=self._createAngle)
		self.angleButtons.add("Remove", command=self._removeAngle,
							state='disabled')
		# remove the extra space around buttons allocated to indicate
		# which button is the 'default', so that buttons stack closely
		for but in range(self.angleButtons.numbuttons()):
			self.angleButtons.button(but).config(default='disabled')
		self.angleButtons.alignbuttons()
		self.angleButtons.grid(row=0, column=1)

		self.anglePrecisionChoice = Pmw.Counter(atp, datatype={
			'counter': self._anglePrecisionChange}, labelpos='w',
			label_text="Decimal places", entry_width=1,
			entry_pyclass=PrecisionEntry,
			entryfield_value=str(prefs[ANGLE_PRECISION]))
		self.anglePrecisionChoice.grid(row=1, column=1)

		self.angleSelectsComponentsVar = Tkinter.IntVar(atp)
		self.angleSelectsComponentsVar.set(True)
		Tkinter.Checkbutton(atp, variable=self.angleSelectsComponentsVar,
			text="Choosing in table selects\ncomponent atoms/bonds"
			).grid(row=3, column=1)

		brp = self.notebook.page(BONDROTS)
		Tkinter.Label(brp, text="%s moved to Build Structure tool" % BONDROTS
			).grid(row=0, column=0)
		def showBondRots():
			from chimera import dialogs
			from BuildStructure.gui import BuildStructureDialog, BOND_ROTS
			dialogs.display(BuildStructureDialog.name).setCategory(BOND_ROTS)

		Tkinter.Button(brp, text="Open Build Structure tool", command=showBondRots
			).grid(row=1, column=0)

		if GEOMETRIES in pageNames:
			gp = self.notebook.page(GEOMETRIES)
			def showGeoms():
				from chimera import dialogs
				dialogs.display(StructMeasure.name).setCategoryMenu(GEOMETRIES)
			from Geometry import GeometryInterface
			self.interfaces[GEOMETRIES] = GeometryInterface(gp,
												self.status, showGeoms)

		self.notebook.setnaturalsize()

	def setCategoryMenu(self, category):
		# avoid unnecessary page raises; they interfere with
		# the bond rotation mouse mode (graphics window loses
		# focus)
		if self.notebook.getcurselection() != category:
			self.notebook.selectpage(category)
	
	def atomLabel(self, atom, diffWith=None):
		if self.numMolecules > 1:
			showModel = 1
		else:
			showModel = 0
		
		from chimera.misc import chimeraLabel
		lab = chimeraLabel(atom, showModel=showModel,
							diffWith=diffWith)
		if lab == "":
			lab = atom.name
		return lab

	def sortableDistanceLabel(self, dist):
		"""prevent a distance of 10.1 from sorting ahead of 2.3"""
		rawLabel = dist.distance
		if not rawLabel:
			return rawLabel
		try:
			val = float(rawLabel)
		except ValueError:
			# trailing angstrom symbol
			val = float(rawLabel[:-1])
		from CGLutil.SortString import SortString
		return SortString(rawLabel, cmpVal=val)

	def _angleLabel(self, atoms):
		pts = tuple([a.xformCoord() for a in atoms])
		if len(pts) == 3:
			val = chimera.angle(*pts)
		else:
			val = chimera.dihedral(*pts)
		return "%.*f" % (prefs[ANGLE_PRECISION], val)

	def _anglePrecisionChange(self, text, plusMinus, increment):
		newPrecision = int(text) + plusMinus
		if newPrecision < 0:
			raise ValueError("decimal places must be non-negative")
		if newPrecision > 9:
			raise ValueError("9 decimal places is enough")
		prefs[ANGLE_PRECISION] = newPrecision
		self.angleTable.refresh()
		return str(newPrecision)

	def _angleTableSelCB(self, selAngles):
		if self.angleSelectsComponentsVar.get():
			select = []
			for atoms in selAngles:
				select.extend(atoms)
				atomSet = set(atoms)
				for a in atoms:
					for b in a.bonds:
						if b.otherAtom(a) in atomSet:
							select.append(b)
			selection.setCurrent(select)

	def _atomChange(self, trigName, myData, trigData):
		if not trigData.deleted:
			return
		# angles/dihedrals
		remove = []
		for atoms in self.angleInfo:
			for a in atoms:
				if a.__destroyed__:
					remove.append(atoms)
					break
		if remove:
			self._removeAngle(remove=remove)

	def _createAngle(self, atoms=None):
		"""'Create angle' callback"""

		if atoms is None:
			atoms = selection.currentAtoms(ordered=True)
		if len(atoms) not in [3,4]:
			replyobj.error("Either three or four atoms must be"
					" selected in graphics window\n")
			return
		if not self.angleInfo:
			from SimpleSession import SAVE_SESSION
			self._angleSesTrigID = chimera.triggers.addHandler(SAVE_SESSION,
												self._sessionAngleSaveCB, None)
		self.angleInfo.append(atoms)
		self.angleTable.setData(self.angleInfo)
		
		self.angleButtons.button("Remove").config(state='normal')

		if self._osHandler is None:
			models = set([a.molecule for a in atoms])
			if len(models) > 1:
				self._osHandler = chimera.triggers.addHandler(
					'OpenState', self._osChange, None)

	def _createDistance(self):
		"""'Create distance' callback"""

		selAtoms = selection.currentAtoms()
		if len(selAtoms) != 2:
			replyobj.error("Exactly two atoms must be selected in graphics window\n"
				"(e.g. Ctrl-click atom 1, Shift-Ctrl-click atom 2, click Create)")
			return
		addDistance(*tuple(selAtoms))

	def deadDistances(self):
		"""Remove deleted distances from the table"""

		pre = len(self.distances)
		self.distances = [d for d in self.distances
						if not d.__destroyed__]
		if len(self.distances) != pre:
			self.distTable.setData(self.distances)
			return True
		return False

	def _distColorChange(self, opt):
		distanceMonitor.color = chimera.MaterialColor(*opt.get()[:3])

	def _distLabelModeChange(self, mode):
		if mode == "None":
			distanceMonitor.fixedLabels = 1
			for d in self.distances:
				d.label = ""
		elif mode == "ID":
			distanceMonitor.fixedLabels = 1
			for d in self.distances:
				d.label = "%d" % d.id
		else:
			distanceMonitor.fixedLabels = 0
			for d in self.distances:
				d.label = d.distance

	def _distLineTypeChange(self, opt):
		distanceMonitor.lineType = opt.get()

	def _distLineWidthChange(self, opt):
		distanceMonitor.lineWidth = opt.get()

	def _distLabelModeChange(self, mode):
		if mode == "None":
			distanceMonitor.fixedLabels = 1
			for d in self.distances:
				d.label = ""
		elif mode == "ID":
			distanceMonitor.fixedLabels = 1
			for d in self.distances:
				d.label = "%d" % d.id
		else:
			distanceMonitor.fixedLabels = 0
			for d in self.distances:
				d.label = d.distance

	def _distPrecisionChange(self, text, plusMinus, increment):
		setPrecision(int(text) + plusMinus, fromGui=True)
		if precision() > 9:
			setPrecision(9, fromGui=True)
			raise ValueError, "9 decimal places is enough"
		return str(precision())

	def _distTableSelCB(self, selDists):
		if self.distSelectsAtomsVar.get():
			select = []
			select.extend(selDists)
			for sd in selDists:
				select.extend(sd.atoms)
			selection.setCurrent(select)
		else:
			selection.removeCurrent(self.distances)
			selection.addCurrent(selDists)

	def _distUpdateCB(self):
		"""Distances just updated"""
		self.distTable.refresh()

	def Help(self):
		anchor = self.notebook.getcurselection().lower().split()[0]
		if "/" in anchor:
			anchor = anchor.split('/')[0]
		chimera.help.display("ContributedSoftware/structuremeas/"
			"structuremeas.html#" + anchor)

	def _modelChange(self, trigName, myData, trigData):
		if not trigData.modified:
			return
		# both Coord and CoordSet changes fire the Model trigger
		if 'atoms moved' in trigData.reasons \
		or 'activeCoordSet changed' in trigData.reasons:
			# don't want to remake atom labels right away since
			# some of the distances may have gone away, and that
			# won't get cleaned up until the Pseudobond trigger
			# fires, so register for the monitorChanges trigger and
			# update the labels there
			chimera.triggers.addHandler(
				  'monitor changes', self.monitorCB, False)

	def _molChange(self, trigName, myData, trigData):
		n = len(chimera.openModels.list(modelTypes=[chimera.Molecule]))
		if n == 1 and self.numMolecules > 1 \
		or n > 1 and self.numMolecules == 1:
			# don't want to remake atom labels right away since
			# some of the distances may have gone away, and that
			# won't get cleaned up until the Pseudobond trigger
			# fires, so register for the monitorChanges trigger and
			# update the labels there
			chimera.triggers.addHandler(
				  'monitor changes', self.monitorCB, True)
		self.numMolecules = n


	def newDistance(self, d):
		if self.distances:
			d.id = self.distances[-1].id + 1
		else:
			d.id = 1
		if not hasattr(d, 'distance'):
			d.distance = ""
		self.distances.append(d)
		self.distTable.setData(self.distances)
		
	def monitorCB(self, trigName, updateAtoms, trigData):
		if updateAtoms:
			self.remakeAtomLabels()
		else:
			self._updateAngles()
		from chimera.triggerSet import ONESHOT
		return ONESHOT

	def _nbLowerCB(self, pageName):
		if pageName in self.interfaces:
			interface = self.interfaces[pageName]
			try:
				interface._lowerCmd()
			except AttributeError:
				self.status("")
		else:
			self.status("")

	def _nbRaiseCB(self, pageName):
		if pageName in self.interfaces:
			interface = self.interfaces[pageName]
			try:
				interface._raiseCmd()
			except AttributeError:
				pass

	def _osChange(self, trigName, myData, trigData):
		if 'transformation change' not in trigData.reasons:
			return
		self._updateAngles()

	def _psbChange(self, trigName, myData, trigData):
		"""Callback from PseudoBond trigger"""

		change = False

		# clean up deleted distances
		if trigData.deleted:
			change = self.deadDistances()
		
		# insert new distances
		for psb in trigData.created:
			if psb in distanceMonitor.pseudoBonds:
				self.newDistance(psb)
				change = True
		if change:
			self.notebook.setnaturalsize()
			
	def _psgChange(self, trigName, myData, trigData):
		"""Callback from PseudoBondGroup trigger"""
		if not trigData.modified or distanceMonitor not in trigData.modified:
			return
		self.distColorOpt.set(distanceMonitor.color)
		self.distLineWidthOpt.set(distanceMonitor.lineWidth)
		self.distLineTypeOpt.set(distanceMonitor.lineType)

	def remakeAtomLabels(self):
		self.distTable.refresh()
		self.angleTable.refresh()

	def _removeAngle(self, remove=None):
		if len(self.angleInfo) == 0:
			replyobj.error("No angles to remove\n")
			return
		if remove is None:
			if len(self.angleInfo) == 1:
				remove = self.angleInfo
			else:
				remove = self.angleTable.selected()
				if not remove:
					replyobj.error("Must select angle(s) in table\n")
					return
		for rm in remove:
			self.angleInfo.remove(rm)
		self.angleTable.setData(self.angleInfo)

		if len(self.angleInfo) == 0:
			self.angleButtons.button("Remove").config(
							state='disabled')
			from SimpleSession import SAVE_SESSION
			chimera.triggers.deleteHandler(SAVE_SESSION, self._angleSesTrigID)

		if self._osHandler:
			stillNeedHandler = False
			for info in self.angleInfo:
				models = dict.fromkeys([a.molecule for a in info])
				if len(models) > 1:
					stillNeedHandler = True
					break
			if not stillNeedHandler:
				chimera.triggers.deleteHandler('OpenState', self._osHandler)
				self._osHandler = None

	def _removeDistance(self):
		if len(self.distances) == 1:
			removeDistance(self.distances[0])
			return
		if len(self.distances) == 0:
			replyobj.error("No distances to remove\n")
			return
		if not self.distTable.selected():
			replyobj.error("Must select distance in table\n")
			return
		for d in self.distTable.selected():
			removeDistance(d)

	def Save(self):
		"""Save the displayed info to file"""
		if not hasattr(self, '_saveDialog'):
			self._saveDialog = _SaveStructInfo(self, clientPos='s',
				title='Save Structure Measurements')
		self._saveDialog.enter()
	
	def _saveDistDefaults(self):
		prefs[DIST_COLOR] = self.distColorOpt.get()
		prefs[DIST_LINE_WIDTH] = self.distLineWidthOpt.get()
		prefs[DIST_LINE_TYPE] = self.distLineTypeOpt.get()

	def _showUnitsChangeCB(self):
		showUnits(self.showUnitsVar.get(), fromGui=True)

	def _counterAngle(self, text, updown, incr, **kw):
		angle = float(text)
		if updown > 0:
			angle = angle + incr
		else:
			angle = angle - incr

		while angle < -180.0:
			angle = angle + 360.0
		while angle > 180.0:
			angle = angle - 360.0
		self._deltaCB(kw['br'], angle=angle)
		return str(angle)
	
	def _sessionAngleSaveCB(self, trigName, myData, sessionFile):
		from SimpleSession import sessionID, sesRepr
		sesData = []
		for atoms in self.angleInfo:
			sesData.append([sessionID(a) for a in atoms])
		print>>sessionFile, "angleInfo = %s" % sesRepr(sesData)
		print>>sessionFile, """
try:
	from StructMeasure.gui import restoreAngles
	restoreAngles(angleInfo)
except:
	reportRestoreError("Error restoring angle monitors in session")
"""

	def _updateAngles(self):
		self.angleTable.refresh()

from OpenSave import SaveModeless
class _SaveStructInfo(SaveModeless):
	def __init__(self, structMeasure, **kw):
		self.structMeasure = structMeasure
		SaveModeless.__init__(self, **kw)

	def fillInUI(self, parent):
		SaveModeless.fillInUI(self, parent)
		self.saveTypes = Pmw.RadioSelect(self.clientArea, pady=0,
			buttontype='checkbutton', labelpos='w',
			orient='vertical', label_text="Save:")
		self.saveTypes.grid(row=0, column=0)
		for name in self.structMeasure.notebook.pagenames():
			if name == BONDROTS:
				continue
			mode = 'normal'
			if name not in [DISTANCES, ANGLES, GEOMETRIES]:
				mode = 'disabled'
			self.saveTypes.add(name, state=mode)
			if mode == 'normal':
				self.saveTypes.invoke(name)

	def Apply(self):
		savePaths = self.getPaths()
		if not savePaths:
			replyobj.error("No save file specified\n")
			return
		from OpenSave import osOpen
		saveFile = osOpen(savePaths[0], "w")
		mols = chimera.openModels.list(modelTypes=[chimera.Molecule])
		for mol in mols:
			print>>saveFile, "Model %s is %s" % (mol.oslIdent(),
								mol.name)
		sm = self.structMeasure
		selected = self.saveTypes.getcurselection()
		if DISTANCES in selected:
			print>>saveFile, "\nDistance information"
			output = {}
			for d in sm.distances:
				a1, a2 = d.atoms
				distID = d.id
				if d.distance[-1].isdigit():
					dval = d.distance
				else:
					# omit angstrom character
					dval = d.distance[:-1]
				output[distID] = "%2d  %s <-> %s:  %s" % (
						distID, sm.atomLabel(a1),
						sm.atomLabel(a2), dval)
			ids = output.keys()
			ids.sort()
			for distID in ids:
				print>>saveFile, output[distID]

		if ANGLES in selected:
			print>>saveFile, "\nAngles/Torsions"
			printables = []
			maxLabel = 0
			for atoms in sm.angleInfo:
				labelArgs = tuple([sm.atomLabel(a)
							for a in atoms])
				if len(atoms) == 3:
					label = "%s -> %s -> %s" % labelArgs
					func = chimera.angle
				else:
					label = "%s -> %s -> %s -> %s" \
								% labelArgs
					func = chimera.dihedral
				maxLabel = max(maxLabel, len(label))
				printables.append((label, "%8.*f" % (prefs[ANGLE_PRECISION],
						func(*tuple([a.xformCoord() for a in atoms])))))
			format = "%%%ds: %%s" % maxLabel
			for printArgs in printables:
				print>>saveFile, format % printArgs
				
		if GEOMETRIES in selected:
			from Geometry import geomManager
			for mgr, geomClass in zip(geomManager.managers,
					geomManager.geomClasses):
				singular, plural = geomClass.singularPlural()
				print>>saveFile, "\n%s" % plural.capitalize()
				print>>saveFile, geomClass.strLegend()
				items = mgr.items
				items.sort(lambda i1, i2: cmp(i1.number, i2.number))
				nameSize = max([0] + [len(i.name) for i in items])
				idSize = max([0] + [len(i.id) for i in items])
				for item in items:
					print>>saveFile, item.alignedStr(nameWidth=nameSize,
						idWidth=idSize)
		saveFile.close()

class PrecisionEntry(Tkinter.Label):
	"""Fake an Entry with a Label to allow making an uneditable Pmw.Counter"""
	def delete(self, *args, **kw):
		pass
	def insert(self, pos, text):
		self['text'] = text
	def get(self):
		return self['text']
	def index(self, *args, **kw):
		return 0
	def selection_present(self):
		return 0
	def xview(self, *args, **kw):
		pass
	def icursor(self, *args, **kw):
		pass

from chimera import dialogs
dialogs.register(StructMeasure.name, StructMeasure)

def addAngle(atoms):
	d = dialogs.display(StructMeasure.name)
	d._createAngle(atoms)
	d.setCategoryMenu(ANGLES)

def restoreAngles(angleInfo):
	from SimpleSession import idLookup
	for atomIDs in angleInfo:
		addAngle([idLookup(aID) for aID in atomIDs])
	
# need restoreTorsions for old session files
def restoreTorsions(info):
	from SimpleSession import idLookup
	from BondRotMgr import bondRotMgr
	for bondID, atom1ID, atom2ID in info:
		br = bondRotMgr.rotationForBond(idLookup(bondID))
		br.anchorSide = idLookup(atom1ID)
