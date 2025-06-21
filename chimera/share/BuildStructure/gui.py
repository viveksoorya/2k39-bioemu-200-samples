#  --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: gui.py 42527 2024-06-27 22:20:27Z pett $

ADD_ATOMS = "Start Structure"
CHANGE_ATOM = "Modify Structure"
ADJUST_BONDS = "Adjust Bonds"
BOND_ROTS = "Adjust Torsions"
JOIN_MODELS = "Join Models"
CHIRALITY = "Invert"
BOND_ANGLES = "Adjust Bond Angles"
pageNames = [ADD_ATOMS, CHANGE_ATOM, ADJUST_BONDS, BOND_ROTS,
				JOIN_MODELS, CHIRALITY, BOND_ANGLES]
from StructMeasure.prefs import prefs, ROT_LABEL, ROT_DIAL_SIZE, \
				TORSION_PRECISION, SHOW_DEGREE_SYMBOL

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import UserError, selection, mousemodes
from BuildStructure import setBondLength, placeHelium, changeAtom, ParamError, \
	placeFragment, placePeptide, elementRadius, bind, cnPeptideBond, placeNucleotide, \
	PeptideError, NucleotideError
from BondRotMgr import bondRotMgr
import Tkinter, Pmw

class BuildStructureDialog(ModelessDialog):
	title = "Build Structure"
	name = "build structure"
	help = "ContributedSoftware/editing/editing.html"
	buttons = ("Close",)
	provideStatus = True
	statusPosition = "left"

	RES_NOOP = 0
	RES_RENAME = 1
	RES_MAKENEW = 2

	PLACE_ATOM = "atom"
	PLACE_FRAGMENT = "fragment"
	PLACE_SMILES = "SMILES string"
	PLACE_PUBCHEM = "PubChem CID"
	PLACE_PEPTIDE = "peptide"
	PLACE_NUCLEIC = "helical DNA/RNA"
	PLACE_RNA = "more RNA..."

	dialSizes = [".1i", ".2i", ".3i"]

	def fillInUI(self, parent):
		self._mapped = False
		self.notebookMenu = Pmw.OptionMenu(parent, items=pageNames,
			initialitem=pageNames[0],
			command=lambda pn: self.notebook.selectpage(pn))
		self.notebookMenu.grid(row=0, column=0)
		self.notebook = Pmw.NoteBook(parent, tabpos=None,
				raisecommand=self._raiseCB, lowercommand=self._lowerCB)
		self.notebook.grid(sticky="nsew")
		parent.rowconfigure(1, weight=1)
		parent.columnconfigure(0, weight=1)

		for pn in pageNames:
			self.notebook.add(pn)

		self.resNameVar = Tkinter.StringVar(parent)
		self.resNameVar.set("UNK")
		self.chainNameVar = Tkinter.StringVar(parent)
		self.colorByElementVar = Tkinter.IntVar(parent)
		self.colorByElementVar.set(True)
		self._countMolecules()
		chimera.openModels.addAddHandler(self._countMolecules, None)
		chimera.openModels.addRemoveHandler(self._countMolecules, None)
		self._fillPlaceAtomPage()
		self._fillChangeAtomPage()
		self._fillAdjustBondsPage()
		self._fillJoinModelsPage()
		self._fillChiralityPage()
		self._fillBondAnglesPage()
		self._fillBondRotsPage()
		self.notebook.setnaturalsize()

		self.buttonWidgets['Help'].config(state='normal',
							command=self.Help)

		from SimpleSession import SAVE_SESSION
		chimera.triggers.addHandler(SAVE_SESSION, self._sessionSave, None)
		chimera.triggers.addHandler('Atom', self._atomChange, None)

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

	def dihedChoices(self, baseAtom, otherAtom):
		# sort choices so they are always in the same order
		default = None
		info = []
		for a in baseAtom.neighbors:
			if a is otherAtom:
				continue
			name = self.atomLabel(a, diffWith=baseAtom)
			info.append((name, a))
			if a.element.number > 1:
				default = a
		info.sort()
		names = map(lambda items: items[0], info)
		bonded = map(lambda items: items[1], info)
		if default is None:
			if len(names) > 0:
				default = 0
		else:
			default = bonded.index(default)
		return default, names, bonded

	def dihedEndAtoms(self, br):
		widgets, nearIndex, nearAtoms, farIndex, farAtoms = \
								self.rotInfo[br]
		if nearIndex is None or farIndex is None:
			return None, None
		return nearAtoms[nearIndex], farAtoms[farIndex]

	def dihedral(self, br):
		near, far = self.dihedEndAtoms(br)
		if not near or not far:
			return br.get()
		widgets, nearIndex, nearAtoms, farIndex, farAtoms = \
								self.rotInfo[br]
		return chimera.dihedral(near.xformCoord(), br.atoms[0].xformCoord(),
				br.atoms[1].xformCoord(), far.xformCoord())

	def map(self):
		self._mapped = True
		pageName = self.notebook.getcurselection()
		if pageName == ADJUST_BONDS:
			self._abSelChange()
			from chimera import triggers
			self._abSelChangeHandler = triggers.addHandler("selection changed",
					self._abSelChange, None)
		elif pageName == BOND_ANGLES:
			self._baSelChange()
			from chimera import triggers
			self._baSelChangeHandler = triggers.addHandler("selection changed",
					self._baSelChange, None)
		elif pageName == CHANGE_ATOM:
			self._genAtomNameCB()
			from chimera import triggers
			self._caSelChangeHandler = triggers.addHandler('selection changed',
					lambda *args: self._genAtomNameCB(), None)
		elif pageName == JOIN_MODELS:
			from chimera import triggers
			self._jmSelChangeHandler = triggers.addHandler("selection changed",
					self._jmConfig, None)

	def remakeAtomLabels(self):
		newLabels = []
		for br in self.rotations:
			newLabels.append(self.rotLabel(br))
			rotMenu = self.rotInfo[br][0][2]
			rotMenu.configure(text=newLabels[-1])
		if newLabels:
			modeTors = self.rotModeTorsMenu.index(Pmw.SELECT)
			if not modeTors:
				modeTors = None
		else:
			modeTors = None
		self.rotModeTorsMenu.setitems(newLabels, index=modeTors)

	def rotChange(self, trigger, brInfo):
		needResize = False
		if trigger == bondRotMgr.DELETED:
			self._delRots(brInfo)
			needResize = True
		elif trigger == bondRotMgr.CREATED:
			self._addRot(brInfo)
			needResize = True
		elif trigger == bondRotMgr.REVERSED:
			# since the bond has reversed, need to switch
			# near/far labels as well
			widgets, nearIndex, nearAtoms, farIndex, farAtoms = \
							self.rotInfo[brInfo]
			row = self.rotations.index(brInfo)
			self.rotInfo[brInfo] = [widgets, farIndex, farAtoms,
							nearIndex, nearAtoms]
			# swap torsion-end menus
			widgets[1], widgets[3] = widgets[3], widgets[1]
			widgets[2].configure(text=self.rotLabel(brInfo))
			if self.angleTitle.get() == "Torsion":
				widgets[1].grid_forget()
				widgets[3].grid_forget()
				widgets[1].grid(row=row, column=1, sticky='ew')
				widgets[3].grid(row=row, column=3, sticky='ew')
			self.rotModeTorsMenu.setitems([self.rotLabel(r)
				for r in self.rotations],
				index=self.rotModeTorsMenu.index(Pmw.SELECT))
		else:
			self._updateRot(brInfo)

		if needResize:
			self.notebook.setnaturalsize()
	
	def rotLabel(self, br):
		return "%s -> %s" % (self.atomLabel(br.atoms[0]),
			self.atomLabel(br.atoms[1], diffWith=br.atoms[0]))

	def setCategory(self, category):
		# avoid unnecessary page raises; they interfere with
		# the bond rotation mouse mode (graphics window loses
		# focus)
		if self.notebook.getcurselection() != category:
			self.notebookMenu.invoke(category)

	def unmap(self):
		self._mapped = False
		pageName = self.notebook.getcurselection()
		if pageName == ADJUST_BONDS:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._abSelChangeHandler)
			delattr(self, "_abSelChangeHandler")
		elif pageName == BOND_ANGLES:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._baSelChangeHandler)
			delattr(self, "_baSelChangeHandler")
			self.baMenuOrder = None # don't hold reference to bonds
		elif pageName == CHANGE_ATOM:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._caSelChangeHandler)
			delattr(self, "_caSelChangeHandler")
		elif pageName == JOIN_MODELS:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._jmSelChangeHandler)
			delattr(self, "_jmSelChangeHandler")
		self.status("")

	def _addBonds(self):
		atoms = selection.currentAtoms()
		if len(atoms) < 2:
			raise UserError("Must have at least 2 atoms selected")
		doAll = self.addBondsMenu.getvalue() != "reasonable"
		bondLength = chimera.Element.bondLength
		from chimera.molEdit import addBond
		for i, a1 in enumerate(atoms):
			for a2 in atoms[i+1:]:
				if a1.molecule != a2.molecule:
					continue
				if a2 in a1.bondsMap:
					continue
				if a1.altLoc and a2.altLoc \
				and a1.altLoc != a2.altLoc:
					continue
				if not doAll:
					if a1.xformCoord().distance(
					a2.xformCoord()) - bondLength(
					a1.element, a2.element) > 0.4:
						continue
				addBond(a1, a2)

	def _abSelChange(self, *args):
			bonds = selection.currentBonds()
			if len(bonds) == 1:
				self.blEntry.set_value(bonds[0].length())
				self.blSideLabel.config(text="%s)" % self._blSideText(bonds[0]))
			else:
				self.blSideLabel.config(text=")")
			from weakref import WeakKeyDictionary
			self.blStartCache = WeakKeyDictionary(dict([
				(b, b.length()) for b in bonds
			]))

	def _addParamBond(self):
		a1, a2 = selection.currentAtoms()
		if self._jmBondTypeSelect.getvalue() == "other":
			if a1.oslIdent() > a2.oslIdent():
				a1, a2 = a2, a1
			side = self._apobSideMenu.getvalue()
			from chimera.misc import chimeraLabel
			sides = [chimeraLabel(a) for a in (a1, a2)]
			movingSide = sides.index(side)
			moving = (a1, a2)[movingSide]
			nonMoving = (a1, a2)[1-movingSide]
			args = [nonMoving, moving, self._apobLength.get()]
			choice = self._apobDihedralMenu.getvalue()
			for name, atoms in zip(*self._enumerateDihedrals(a1, a2)):
				if name == choice:
					args.append((atoms, self._apobDihedral.get()))
					break
			else:
				args.append(None)
			bind(*tuple(args))
		else:
			if a1.element.name == "C":
				c, n = a1, a2
			else:
				c, n = a2, a1
			if self._appbSideMenu.getvalue() == "selected C atom":
				moving = c
			else:
				moving = n
			try:
				cn = cnPeptideBond(c, n, moving, self._appbLength.get(),
						self._appbDihedral.get(), phi=self._appbPhi.get())
			except AssertionError, v:
				self.status(unicode(v), color="red", blankAfter=15)
				raise UserError(unicode(v))
			from chimera.selection import setCurrent
			setCurrent(cn)

	def _addRot(self, br, row=-1):
		self._setTorWidgetsState("normal")
		if row == -1:
			# by default, append bond rotation
			row = len(self.rotInfo)
		else:
			# insert bond rotation at given row, so make room
			for i in range(len(self.rotations), row, -1):
				nbr = self.rotations[i - 1]
				widgets = self.rotInfo[nbr][0]
				for w in widgets:
					gi = w.grid_info()
					if gi.has_key('column'):
						# otherwise presumably unmapped
						column = gi['column']
						w.grid_forget()
						w.grid(row=i, column=column,
								sticky='ew')

		# if adding a rotation where no torsion angle exists (no bonds off
		# one end), then switch to Delta if this is the only rotation
		a1, a2 = br.atoms
		useDelta = len(a1.neighbors) < 2 or len(a2.neighbors) < 2
		if not self.rotations and self.angleTitle.get() == "Torsion" and useDelta:
			self._toggleAngleType()

		self.rotations.insert(row, br)
		nearIndex, nearNames, nearAtoms = self.dihedChoices(a1, a2)
		farIndex, farNames, farAtoms = self.dihedChoices(a2, a1)
		# need to do this here so that self.dihedral(br) works
		widgets = []
		self.rotInfo[br] = [widgets,
				nearIndex, nearAtoms, farIndex, farAtoms]

		ID = Tkinter.Label(self.rotTable.interior(), text=str(br.id))
		widgets.append(ID)
		ID.grid(row=row, column=0)

		near = Pmw.OptionMenu(self.rotTable.interior(),
				menubutton_highlightthickness=0,
				initialitem=nearIndex, items=nearNames)
		near.configure(command=lambda x, br=br, n=near, s=self:
						s._setDihedEnd(br, n))
		widgets.append(near)
		if self.angleTitle.get() == "Torsion":
			near.grid(row=row, column=1, sticky='ew')
			
		actions = PmwableMenuButton(self.rotTable.interior(),
			text=self.rotLabel(br), indicatoron=1,
			relief='raised', bd=2, justify='right',
			states=['normal', 'normal', 'normal', 'normal'],
			items=['Revert', 'Reverse', 'Deactivate', 'Select'],
			command=lambda c, s=self, br=br: s._menuCB(c, br))
		widgets.append(actions)
		actions.grid(row=row, column=2, sticky='ew')

		far = Pmw.OptionMenu(self.rotTable.interior(),
				menubutton_highlightthickness=0,
				initialitem=farIndex, items=farNames)
		far.configure(command=lambda x, br=br, n=far, s=self:
						s._setDihedEnd(br, n))
		widgets.append(far)
		if self.angleTitle.get() == "Torsion":
			far.grid(row=row, column=3, sticky='ew')
			
		from CGLtk.AngleCounter import AngleCounter
		delta = AngleCounter(self.rotTable.interior(), dialpos='e',
			angle=float("%.*f" % (prefs[TORSION_PRECISION],
			br.get())),
			dial_zeroAxis='y', dial_radius=self.dialSizes[
			prefs[ROT_DIAL_SIZE]], dial_rotDir='clockwise',
			command=lambda d, s=self, br=br: s._deltaCB(br, d))

		dihed = AngleCounter(self.rotTable.interior(), dialpos='e',
			angle=float("%.*f" % (prefs[TORSION_PRECISION],
			self.dihedral(br))),
			dial_zeroAxis='y', dial_radius=self.dialSizes[
			prefs[ROT_DIAL_SIZE]], dial_rotDir='clockwise',
			command=lambda d, s=self, br=br: s._dihedCB(br, d))
		if self.angleTitle.get() == "Delta":
			delta.grid(row=row, column=4, sticky='ew')
			widgets.extend([delta, dihed])
		else:
			dihed.grid(row=row, column=4, sticky='ew')
			widgets.extend([dihed, delta])

		modeTors = self.rotModeTorsMenu.getvalue()
		if not modeTors:
			modeTors = None
		items = [self.rotLabel(r) for r in self.rotations]
		self.rotModeTorsMenu.setitems(items, index=modeTors)

		self._labelRot(br)

		if useDelta:
			self._menuCB("Reverse", br)

	def _atomChange(self, trigName, myData, trigData):
		# torsions
		for br, info in self.rotInfo.items():
			if br.bond.__destroyed__:
				continue
			widgets, ni, nearAtoms, fi, farAtoms = info
			for menu, index, atoms, brAtom, infoIndex in (
					(widgets[1], ni, nearAtoms, br.atoms[0], 2),
					(widgets[3], fi, farAtoms, br.atoms[1], 4)):
				dead = [a.__destroyed__ for a in atoms]
				if dead.count(True) == 0:
					continue
				if dead.count(False) == 0:
					br.destroy()
					break
				survivors = [a for a in atoms if not a.__destroyed__]
				if atoms[index] in survivors:
					si = survivors.index(atoms[index])
					menu.setitems([self.atomLabel(a, diffWith=brAtom)
							for a in survivors], index=si)
					info[infoIndex] = survivors
					info[infoIndex-1] = si
				else:
					menu.setitems([self.atomLabel(a, diffWith=brAtom)
							for a in survivors])
					info[infoIndex] = survivors
					info[infoIndex-1] = 0
					menu.invoke(0)
					self.status("Dihedral endpoint atom deleted; new"
						" endpoint randomly chosen")

	def _baAngleChange(self, degrees):
		if not self.baMenuOrder:
			return
		moving = self.baMenuOrder[self.baMover.index(Pmw.SELECT)]
		from BuildStructure import setBondAngle, BondInCycleError
		fixed = self.baMenuOrder[0] if moving == self.baMenuOrder[1] else self.baMenuOrder[1]
		try:
			setBondAngle(moving, fixed, degrees)
		except BondInCycleError:
			self.baStatus.config(text="The %s bond is part of a cycle.\n"
				"To adjust the bond angle you must first delete some other bond\n"
				"that forms the cycle and then recreate it afterwards.  You can\n"
				"do both with the %s tab." % (self.baMover.getvalue(), ADJUST_BONDS),
				foreground="red")
			junction = (set(moving.atoms) & set(fixed.atoms)).pop()
			self.baAngleWidget.configure(angle=chimera.angle(
				fixed.otherAtom(junction).coord() - junction.coord(),
				moving.otherAtom(junction).coord() - junction.coord()))
			return

	def _baMoverChange(self, *args):
		movingRef, fixedRef, angleVal, moverIndex = getattr(self, 'baStartingInfo',
				(None, None, None, None))
		if angleVal is None:
			return
		if moverIndex == self.baMover.index(Pmw.SELECT):
			return
		self.baStartingInfo = (fixedRef, movingRef,
				float(self.baAngleWidget.getvalue()), self.baMover.index(Pmw.SELECT))

	def _baRevert(self):
		movingRef, fixedRef, angleVal, moverIndex = getattr(self, 'baStartingInfo',
				(None, None, None, None))
		def _statusClear(s=self):
			s.baStatus.config(text="")
		if angleVal is None:
			self.baStatus.config(text="Nothing to revert", foreground="red")
			self.baStatus.after(5000, _statusClear)
			return
		if (movingRef() is None or fixedRef() is None) \
		or (movingRef().__destroyed__ or fixedRef().__destroyed__):
			self.baStatus.config(text="Parts of the bond angle no longer exist",
					foreground="red")
			self.baStatus.after(5000, _statusClear)
			return
		from BuildStructure import setBondAngle
		setBondAngle(movingRef(), fixedRef(), angleVal)
		self.baAngleWidget.configure(angle=angleVal)

	def _baSelChange(self, *args):
		self.baStatus.config(text="")
		prevOrder = self.baMenuOrder
		self.baMenuOrder = None
		bonds = selection.currentBonds()
		if len(bonds) != 2:
			if not bonds:
				self.baStatus.config(text="No bonds selected", foreground="black")
			else:
				if len(bonds) == 1:
					bondText = "bond"
				else:
					bondText = "bonds"
				self.baStatus.config(text="%s %s selected" % (len(bonds), bondText),
					foreground="red")
			self.baHelp.config(text=self.baHelpText)
			self.baTitle.config(text="")
			self.baMover.setitems([])
			self.baAngleWidget.configure(angle=0)
			return

		from BuildStructure import smallerBranch, BondsNotAdjacentError
		try:
			moving = smallerBranch(bonds)
		except BondsNotAdjacentError:
			self.baStatus.config(text="Selected bonds are not adjacent", foreground="red")
			self.baHelp.config(text=self.baHelpText)
			self.baTitle.config(text="")
			self.baMover.setitems([])
			self.baAngleWidget.configure(angle=0)
			return

		fixed = bonds[0] if bonds[1] == moving else bonds[1]
		self.baHelp.config(text="")
		junction = (set(moving.atoms) & set(fixed.atoms)).pop()
		from chimera.misc import chimeraLabel as cl
		otherFixed = fixed.otherAtom(junction)
		otherMoving = moving.otherAtom(junction)
		self.baTitle.config(text=u"%s \N{EM DASH} %s \N{EM DASH} %s" % (cl(otherFixed),
			cl(junction, diffWith=otherFixed), cl(otherMoving, diffWith=junction)))
		self.baMenuOrder = (moving, fixed)
		self.baMover.setitems([cl(b, showModel=False) for b in self.baMenuOrder], index=0)
		curAngle = chimera.angle(otherFixed.coord() - junction.coord(),
				otherMoving.coord() - junction.coord())
		if prevOrder != self.baMenuOrder:
			from weakref import ref
			self.baStartingInfo = (ref(moving), ref(fixed), curAngle,
					self.baMover.index(Pmw.SELECT))
		self.baAngleWidget.configure(angle=curAngle)

	def _blRevert(self):
		from BuildStructure import setBondLength
		side = self.blSideMenu.getvalue()
		widgetVal = None
		changeWidget = False
		for b, bl in self.blStartCache.items():
			if b.__destroyed__:
				continue
			setBondLength(b, bl, movingSide=side, status=self.status)
			if widgetVal is None:
				widgetVal = bl
				changeWidget = True
			elif widgetVal != bl:
				changeWidget = False
		if changeWidget:
			self.blEntry.set_value(widgetVal, invoke_callbacks=False)

	def _blSideText(self, bond):
		a1, a2 = bond.atoms
		a1done = set([a1])
		a2done = set([a2])
		a1todo = a1.neighbors
		a2todo = a2.neighbors
		a1todo.remove(a2)
		a2todo.remove(a1)
		while a1todo and a2todo:
			a1a = a1todo.pop(0)
			a1done.add(a1a)
			for a1nb in a1a.neighbors:
				if a1nb == a2:
					break
				if a1nb in a1done:
					continue
				a1todo.append(a1nb)
			a2a = a2todo.pop(0)
			a2done.add(a2a)
			for a2nb in a2a.neighbors:
				if a2nb == a1:
					break
				if a2nb in a2done:
					continue
				a2todo.append(a2nb)
		if (a1todo and a2todo) or (not a1todo and not a2todo):
			return ""
		if a1todo:
			bigger = a1
		else:
			bigger = a2
		if self.blSideMenu.getvalue() == "smaller side":
			labeled = bond.otherAtom(bigger)
		else:
			labeled = bigger
		return chimera.misc.chimeraLabel(labeled)

	def _changeAtom(self):
		selAtoms = selection.currentAtoms()
		if len(selAtoms) > 4:
			from chimera.baseDialog import AskYesNoDialog
			if AskYesNoDialog("Really change %d atoms?" %
			len(selAtoms)).run(self.uiMaster()) == 'no':
				self.enter()
				return
		if self.retainAtomNamesVar.get():
			for atom in selAtoms:
				if not self._changeSingleAtom(atom, atom.name):
					break
		elif self.atomNameInfo.get():
			assert(len(self._atomNameCache) == len(selAtoms))
			for atom, name in zip(selAtoms, self._atomNameCache):
				if not self._changeSingleAtom(atom, name):
					break
		else:
			for atom in selAtoms:
				if not self._changeSingleAtom(atom):
					break

	def _checkPrecision(self, text, plusMinus, increment):
		newPrecision = int(text) + plusMinus
		if newPrecision < 0:
			raise ValueError("decimal places must be non-negative")
		if newPrecision > 9:
			raise ValueError("9 decimal places is enough")
		return newPrecision

	def _countMolecules(self, *args):
		prevNum = getattr(self, 'numMolecules', None)
		self.numMolecules = len(chimera.openModels.list(modelTypes=[chimera.Molecule]))
		if prevNum != None:
			if prevNum == 1 and self.numMolecules > 1 \
			or prevNum > 1 and self.numMolecules == 1:
				# don't want to remake atom labels right away since
				# some of the distances may have gone away, and that
				# won't get cleaned up until the Pseudobond trigger
				# fires, so register for the monitorChanges trigger and
				# update the labels there
				chimera.triggers.addHandler('monitor changes', self._monitorCB, None)

	def _createRotation(self):
		selBonds = selection.currentBonds()
		if len(selBonds) == 1:
			addRotation(selBonds[0])
			return
		raise UserError("Exactly one bond must be selected "
							"in graphics window")

	def _changeSingleAtom(self, atom, name=None):
		resMode = self.newresVar.get()
		if resMode == self.RES_MAKENEW:
			newResName = self._getResName()
			if newResName == None:
				return False
			oldRes = atom.residue
			oldRes.removeAtom(atom)
			chain = self.chainNameVar.get()
			oldID = oldRes.id
			if len(atom.bonds) > 0 and oldID == chain:
				pos = oldID.position + 1
			else:
				pos = 1
			while True:
				mid = chimera.MolResId(chain, pos)
				if not atom.molecule.findResidue(mid):
					break
				pos += 1
			newRes = atom.molecule.newResidue(newResName,
							chain, pos, ' ')
			newRes.addAtom(atom)
			if not oldRes.atoms:
				atom.molecule.deleteResidue(oldRes)
			chimera.selection._currentSelection._cache = {}
		elif resMode == self.RES_RENAME:
			newResName = self._getResName()
			if newResName == None:
				return False
			from BuildStructure import changeResidueType
			changeResidueType(atom.residue, newResName)
		numBonds = int(self.bondsMenu.getvalue())
		elementVal = self.elementMenu.getvalue()
		if type(elementVal) == str:
			element = chimera.Element(elementVal)
		else:
			element = chimera.Element(elementVal[-1])
		if numBonds < 2:
			if element.number > 2:
				geom = 4
			else:
				geom = 1
		else:
			geom = self.geometryMenu.index(Pmw.SELECT) + numBonds
		if name == None:
			name=self.atomNameOption.get()
		try:
			changed = changeAtom(atom, element, geom, numBonds,
				autoClose=self.autocloseVar.get(), name=name)
		except ParamError, v:
			raise UserError(str(v))

		if self.autoFocusVar.get():
			from Midas import focus, MidasError
			try:
				focus(atom.residue.atoms)
			except MidasError:
				pass
		if self.colorByElementVar.get():
			from Midas import color
			color("byelement", changed)
		return True

	def _delBonds(self):
		bonds = selection.currentBonds()
		if not bonds:
			raise UserError("Select at least one bond")
		for bond in bonds:
			bond.molecule.deleteBond(bond)

	def _delRots(self, brs):
		for br in brs:
			row = self.rotations.index(br)
			widgets = self.rotInfo[br][0]
			for w in widgets:
				w.grid_forget()
				w.destroy()
			del self.rotInfo[br]

			for i in range(row + 1, len(self.rotations)):
				nbr = self.rotations[i]
				widgets = self.rotInfo[nbr][0]
				for w in widgets:
					gi = w.grid_info()
					if gi.has_key('column'):
						# otherwise presumably unmapped
						column = gi['column']
						w.grid_forget()
						w.grid(row=i-1, column=column,
								sticky='ew')
			self.rotations.remove(br)

		modeTors = self.rotModeTorsMenu.getvalue()
		items = [self.rotLabel(br) for br in self.rotations]
		if modeTors in items:
			self.rotModeTorsMenu.setitems(items, index=modeTors)
		else:
			self.rotModeTorsMenu.setitems(items)
			if self.mouseModeVar.get():
				self.mouseModeVar.set(False)
				self._mouseModeCB()
			if not items:
				self._setTorWidgetsState("disabled")

	def _delSelAtomsBonds(self):
		selAtoms = selection.currentAtoms()
		selBonds = selection.currentBonds()
		if not selAtoms and not selBonds:
			self.status("No atoms or bonds selected", color="red")
		else:
			from Midas import deleteAtomsBonds
			deleteAtomsBonds(selAtoms, selBonds)

	def _deltaCB(self, br, degrees):
		# callback from delta AngleCounter
		br.set(degrees)

	def _dialSizeChangeCB(self, dialSizeLabel):
		dialSize = self.dialSizeLabels.index(dialSizeLabel)
		prefs[ROT_DIAL_SIZE] = dialSize
		for info in self.rotInfo.values():
			for angleCounter in info[0][-2:]:
				angleCounter.configure(dial_radius=
						self.dialSizes[dialSize])
		self.notebook.setnaturalsize()

	def _dihedCB(self, br, degrees):
		# callback from dihedral AngleCounter
		curDihed = self.dihedral(br)
		br.set(br.get() + degrees - curDihed)

	def _drawFragment(self, frag):
		self.fragCanvas.delete("all")
		self.fragmentLookup[frag[-1]].depict(self.fragCanvas, scale=15)
		left, top, right, bottom = self.fragCanvas.bbox("all")
		self.fragCanvas.configure(width=right-left, height=bottom-top,
			scrollregion=(left, top, right, bottom))
		self.notebook.setnaturalsize()

	def _enumerateDihedrals(self, a1, a2):
		names, atoms = [], []
		from chimera.misc import chimeraLabel
		b1, b2 = a1.neighbors + a2.neighbors
		for nb1 in b1.neighbors:
			if nb1 == a1:
				continue
			for nb2 in b2.neighbors:
				if nb2 == a2:
					continue
				names.append(u"%s\u2194%s\u2194%s\u2194%s" % (
					chimeraLabel(nb1),
					chimeraLabel(b1, diffWith=nb1),
					chimeraLabel(b2, diffWith=b1),
					chimeraLabel(nb2, diffWith=b2)))
				atoms.append((nb1, b1, b2, nb2))
		return names, atoms

	def _fillPlaceAtomPage(self):
		atomPage = self.notebook.page(ADD_ATOMS)
		self.placeTypeVar = Tkinter.StringVar(atomPage)
		self.apGroups = {}
		for row, val in enumerate([self.PLACE_ATOM, self.PLACE_FRAGMENT,
				self.PLACE_SMILES, self.PLACE_PUBCHEM,
				self.PLACE_PEPTIDE, self.PLACE_NUCLEIC, self.PLACE_RNA]):
			rb = Tkinter.Radiobutton(atomPage, text=val,
				value=val, variable=self.placeTypeVar,
				command=lambda val=val:
				self._showPlaceGroup(val, 0))
			rb.grid(row=row, column=1, sticky="w")
			if val == self.PLACE_RNA:
				addText = ""
			else:
				addText = " parameters"
			self.apGroups[val] = Pmw.Group(atomPage, tag_text=
					paramTitle(val + addText))
		Tkinter.Label(atomPage, text="Add"
			).grid(row=0, column=0, rowspan=len(self.apGroups))
		self.apModelNameFrame = f = Tkinter.Frame(atomPage)
		f.grid(row=len(self.apGroups), column=0, columnspan=3)
		from chimera.widgets import NewMoleculeOptionMenu
		self.molMenu = NewMoleculeOptionMenu(f, labelpos='w',
			label_text="Put atoms in", command=self._molMenuCB)
		self.molMenu.grid(row=0, column=0, sticky='e')
		from chimera.tkoptions import StringOption
		self.molName = StringOption(f, 0, "named", "scratch", None,
							startCol=2)
		self._molMenuCB()
		self.apColorButton = Tkinter.Checkbutton(atomPage,
			variable=self.colorByElementVar,
			text="Color new atoms by element")
		self.apColorButton.grid(row=len(self.apGroups)+1,
								column=0, columnspan=3)
		Tkinter.Button(atomPage, text="Apply", command=self._placeAtoms
			).grid(row=len(self.apGroups)+2, column=0, columnspan=3)


		atomGroup = self.apGroups[self.PLACE_ATOM]
		Tkinter.Label(atomGroup.interior(), text= "Place helium atom at:"
			).grid(row=0, column=0)
		self.atomPosVar = Tkinter.StringVar(atomGroup.interior())
		self.atomPosVar.set("view")
		f = Tkinter.Frame(atomGroup.interior())
		f.grid(row=1, column=0)
		Tkinter.Radiobutton(f, variable=self.atomPosVar, value="view",
			text="Center of view").grid(row=0, column=0, sticky='w')
		f2 = Tkinter.Frame(f)
		f2.grid(row=1, column=0, sticky='w')
		Tkinter.Radiobutton(f2, variable=self.atomPosVar, value="xyz",
			).grid(row=0, column=0)
		mod = lambda s=self: s.atomPosVar.set("xyz")
		self.xEntry = Pmw.EntryField(f2, command=self._placeAtoms, labelpos='w',
			value="0", modifiedcommand=mod, label_text='x:', validate='real',
			entry_width=5)
		self.xEntry.grid(row=0, column=1)
		self.yEntry = Pmw.EntryField(f2, command=self._placeAtoms, labelpos='w',
			value="0", modifiedcommand=mod, label_text='y:', validate='real',
			entry_width=5)
		self.yEntry.grid(row=0, column=2)
		self.zEntry = Pmw.EntryField(f2, command=self._placeAtoms, labelpos='w',
			value="0", modifiedcommand=mod, label_text='z:', validate='real',
			entry_width=5)
		self.zEntry.grid(row=0, column=3)
		Tkinter.Label(atomGroup.interior(), text="Use '%s' tab to change\nelement"
			" type and add bonded atoms." % CHANGE_ATOM).grid(row=2, column=0)
		self.placeTypeVar.set("atom")
		lw = Pmw.LabeledWidget(atomGroup.interior(), labelpos='w',
			label_text="Residue name:")
		lw.grid(row=3, column=0)
		Tkinter.Entry(lw.interior(), width=4,
					textvariable=self.resNameVar).grid()
		self.autoselAtomVar = Tkinter.IntVar(atomGroup.interior())
		self.autoselAtomVar.set(True)
		Tkinter.Checkbutton(atomGroup.interior(),
			variable=self.autoselAtomVar, text="Select placed atom"
			).grid(row=4, column=0)
		self._showPlaceGroup("atom", 0)

		fragmentGroup = self.apGroups[self.PLACE_FRAGMENT]
		from Fragment import fragments, RING6
		menuItems, self.fragmentLookup = self._processFragments(
								fragments)
		from CGLtk.optCascade import CascadeOptionMenu
		self.fragMenu = CascadeOptionMenu(fragmentGroup.interior(),
			labelpos="w", label_text="Fragment", items=menuItems,
			buttonStyle="final", command=self._drawFragment)
		self.fragMenu.grid(row=1, column=0)
		self.fragCanvas = Tkinter.Canvas(fragmentGroup.interior())
		self.fragCanvas.grid(row=1, column=1)
		self.fragMenu.invoke([RING6, "benzene"])
		lw = Pmw.LabeledWidget(fragmentGroup.interior(), labelpos='w',
			label_text="Residue name:")
		lw.grid(row=2, columnspan=2)
		Tkinter.Entry(lw.interior(), width=4,
					textvariable=self.resNameVar).grid()

		smilesGroup = self.apGroups[self.PLACE_SMILES]
		from chimera.tkoptions import StringOption
		self.smilesEntry = StringOption(smilesGroup.interior(), 0,
			"SMILES string", "", None, width=25)
		smilesGroup.interior().columnconfigure(1, weight=1)
		StringOption(smilesGroup.interior(), 1, "Residue name",
						self.resNameVar.get(), None,
						textvariable=self.resNameVar)
		from chimera.HtmlText import HtmlText
		plainTexts = [ "SMILES support courtesy of ", "NCI CADD Group", " or ", "CICC@iu",
			"web services" ]
		urls = [
			'<a href="http://cactus.nci.nih.gov">', '</a>',
			'<a href="http://www.soic.indiana.edu/faculty-research/research/chemical-informatics-center.html">', '</a>',
			""]
		html = HtmlText(smilesGroup.interior(),
				width=len("".join(plainTexts)), height=1, bd=0)
		for plain, url in zip(plainTexts, urls):
			html.insert("end", plain+url)
		html.tag_add("center", "0.0", "end")
		html.tag_configure("center", justify="center")
		html.configure(state="disabled")
		html.grid(row=2, column=0, columnspan=2)

		pubChemGroup = self.apGroups[self.PLACE_PUBCHEM]
		from chimera.tkoptions import StringOption
		self.pubChemEntry = StringOption(pubChemGroup.interior(), 0,
			"PubChem CID", "", None, width=6)
		pubChemGroup.interior().columnconfigure(1, weight=1)
		StringOption(pubChemGroup.interior(), 1, "Residue name",
						self.resNameVar.get(), None,
						textvariable=self.resNameVar)
		from chimera.HtmlText import HtmlText
		plainTexts = [ "PubChem CID support courtesy of ",
						"PubChem Power User Gateway (PUG) web services" ]
		urls = ['<a href="https://pubchem.ncbi.nlm.nih.gov/pug/pughelp.html">', "</a>"]
		html = HtmlText(pubChemGroup.interior(),
				width=len("".join(plainTexts)), height=1, bd=0)
		for plain, url in zip(plainTexts, urls):
			html.insert("end", plain+url)
		html.tag_add("center", "0.0", "end")
		html.tag_configure("center", justify="center")
		html.configure(state="disabled")
		html.grid(row=2, column=0, columnspan=2)

		peptideGroup = self.apGroups[self.PLACE_PEPTIDE]
		pgi = peptideGroup.interior()
		# below widget must be at least 3 high or else
		# the scroller gets all infinite-loopy on OS X
		self.peptideSequence = Pmw.ScrolledText(pgi,
			text_height=3, text_width=30, text_wrap='char',
			labelpos='n', label_text="Peptide Sequence")
		self.peptideSequence.grid(row=1, sticky='nsew')
		Tkinter.Label(pgi, text=u"'Apply' button will bring up dialog"
			u" for setting \u03A6/\u03A8 angles").grid(row=2,
			column=0)

		nucleicGroup = self.apGroups[self.PLACE_NUCLEIC]
		ngi = nucleicGroup.interior()
		# below widget must be at least 3 high or else
		# the scroller gets all infinite-loopy on OS X
		self.nucleicSequence = Pmw.ScrolledText(ngi,
			text_height=3, text_width=30, text_wrap='char',
			labelpos='n', label_text="Sequence")
		self.nucleicSequence.grid(row=1, sticky='nsew', columnspan=2)
		lab = Tkinter.Label(ngi, text="Enter single strand;"
			" double helix will be generated")
		lab.grid(row=2, column=0, columnspan=2)
		from CGLtk.Font import shrinkFont
		shrinkFont(lab)
		self.nucType = Pmw.RadioSelect(ngi, buttontype='radiobutton',
			orient='vertical', pady=0)
		self.nucType.add("DNA", justify="left")
		self.nucType.add("RNA", justify="left")
		self.nucType.add("Hybrid DNA/RNA (enter DNA)", justify="left")
		self.nucType.setvalue("DNA")
		self.nucType.grid(row=3, column=0, sticky='ew')
		self.nucForm = Pmw.RadioSelect(ngi, buttontype='radiobutton',
			orient='vertical', pady=0)
		self.nucForm.add("A-form", justify="left")
		self.nucForm.add("B-form", justify="left")
		self.nucForm.setvalue("B-form")
		self.nucForm.grid(row=3, column=1, sticky='ew')

		# below widget must be at least 3 high or else
		# the scroller gets all infinite-loopy on OS X
		self.peptideSequence = Pmw.ScrolledText(pgi,
			text_height=3, text_width=30, text_wrap='char',
			labelpos='n', label_text="Peptide Sequence")
		self.peptideSequence.grid(row=1, sticky='nsew')
		Tkinter.Label(pgi, text=u"'Apply' button will bring up dialog"
			u" for setting \u03A6/\u03A8 angles").grid(row=2,
			column=0)

		rnaGroup = self.apGroups[self.PLACE_RNA]
		rgi = rnaGroup.interior()
		from CGLtk.WrappingLabel import WrappingLabel
		WrappingLabel(rgi, text="The Assemble2 plugin to Chimera allows"
			" designing RNA in 2D and predicting corresponding"
			" 3D structures.  Assemble2 is developed by"
			" Dr. Fabrice Jossinet, University of Strasbourg.").grid(
			row=0, column=0, sticky='ew')
		from chimera.help import display
		Tkinter.Button(rgi, text="Get Assemble2",
			command=lambda disp=display: disp("http://bioinformatics.org/assemble/index.html")
			).grid(row=1, column=0, padx="1i")

	def _fillChangeAtomPage(self):
		caPage = self.notebook.page(CHANGE_ATOM)
		
		row = 0
		Tkinter.Label(caPage, text="Change selected atoms to...").grid(row=0,
			column=0)
		row += 1

		paramFrame = Tkinter.Frame(caPage, bd=1, relief='solid')
		paramFrame.grid(row=row, column=0)
		row += 1

		from chimera.selection.element \
				import frequentElements, elementRanges
		elementNames = chimera.elements.name[:]
		elementNames.remove("LP")
		elementNames.sort()
		menuItems = frequentElements[:]
		subItems = []
		for start, end in elementRanges:
			subItems.append(("%s-%s" % (start, end),
				elementNames[elementNames.index(start):
					elementNames.index(end)+1]))
		menuItems.append(("other", subItems))
		from CGLtk.optCascade import CascadeOptionMenu
		self.elementMenu = CascadeOptionMenu(paramFrame, labelpos="n",
				label_text="Element", items=menuItems,
				command=lambda *args: self._genAtomNameCB(),
				initialitem=["C"], buttonStyle="final")
		self.elementMenu.grid(row=0, column=0)

		self.bondsJustChanged = False
		self.bondsMenu = Pmw.OptionMenu(paramFrame, labelpos="n",
			label_text="Bonds", command=self._newBonds,
			items=[str(x) for x in range(5)], initialitem=4)
		self.bondsMenu.grid(row=0, column=1)

		from chimera.bondGeom import geometryName
		self.geometryMenu = Pmw.OptionMenu(paramFrame, labelpos="n",
			label_text="Geometry", command=self._geomChangeCB,
			items=geometryName[4:], initialitem=geometryName[4])
		self.geometryMenu.grid(row=0, column=2)

		nameFrame = Tkinter.Frame(paramFrame)
		nameFrame.grid(row=1, column=0, columnspan=3)
		self.retainAtomNamesVar = Tkinter.IntVar(nameFrame)
		self.retainAtomNamesVar.set(True)
		self.retainAtomNameButton = Tkinter.Radiobutton(nameFrame,
			text="Retain current atom names",
			variable=self.retainAtomNamesVar, value=True)
		self.retainAtomNameButton.grid(row=0, sticky='w')
		customNameFrame = Tkinter.Frame(nameFrame)
		customNameFrame.grid(row=1, sticky='w')
		self.customAtomNameButton = Tkinter.Radiobutton(customNameFrame,
			text="Set atom names to:",
			variable=self.retainAtomNamesVar, value=False)
		self.customAtomNameButton.grid(row=0, sticky='w')
		from chimera.tkoptions import StringOption
		self.atomNameOption = StringOption(customNameFrame, 0, "", "",
			lambda opt: self._genAtomNameCB(infoOnly=True),
			startCol=1, width=4)
		self.atomNameInfo = Tkinter.StringVar(paramFrame)
		self.atomNameInfo.set("")
		Tkinter.Label(customNameFrame, textvariable=self.atomNameInfo
						).grid(row=0, column=3)
		self.newresVar = Tkinter.IntVar(caPage)
		self.newresVar.set(self.RES_RENAME)
		self._genAtomNameCB()

		paramFrame.columnconfigure(0, pad="0.1i")
		paramFrame.columnconfigure(1, pad="0.1i")
		paramFrame.columnconfigure(2, pad="0.1i")

		cbFrame = Tkinter.Frame(caPage)
		cbFrame.grid(row=row, column=0)
		row += 1

		self.autocloseVar = Tkinter.IntVar(caPage)
		self.autocloseVar.set(True)
		Tkinter.Checkbutton(cbFrame, variable=self.autocloseVar,
			text="Connect to pre-existing atoms if appropriate"
			).grid(row=0, column=0, sticky='w')
		self.autoFocusVar = Tkinter.IntVar(caPage)
		self.autoFocusVar.set(False)
		Tkinter.Checkbutton(cbFrame, variable=self.autoFocusVar,
			text="Focus view on modified residue"
			).grid(row=1, column=0, sticky='w')
		Tkinter.Checkbutton(cbFrame, variable=self.colorByElementVar,
			text="Color new atoms by element"
			).grid(row=2, column=0, sticky='w')
		resGroup = Pmw.Group(cbFrame, tag_text="Residue Name")
		resGroup.grid(row=3, column=0)
		rgFrame = resGroup.interior()
		Tkinter.Radiobutton(rgFrame, variable=self.newresVar,
			text="Leave unchanged", value=self.RES_NOOP).grid(
			row=0, sticky='w')
		f1 = Tkinter.Frame(rgFrame)
		f1.grid(row=1, sticky='w')
		Tkinter.Radiobutton(f1, variable=self.newresVar,
			text="Change modified residue's name to",
			command=self._genAtomNameCB, value=self.RES_RENAME
			).grid(row=0, column=0, sticky='w')
		Tkinter.Entry(f1, width=4, textvariable=self.resNameVar
			).grid(row=0, column=1, sticky='w')
		f2 = Tkinter.Frame(rgFrame)
		f2.grid(row=2, sticky='w')
		Tkinter.Radiobutton(f2, variable=self.newresVar,
			text="Put just changed atoms in new residue named",
			command=self._genAtomNameCB, value=self.RES_MAKENEW
			).grid(row=0, column=0, sticky='w')
		Tkinter.Entry(f2, width=4, textvariable=self.resNameVar
			).grid(row=0, column=1, sticky='w')
		Tkinter.Label(f2, text="in chain").grid(row=0, column=2)
		Tkinter.Entry(f2, width=3, textvariable=self.chainNameVar
			).grid(row=0, column=4)

		Tkinter.Button(caPage, text="Apply", command=self._changeAtom
			).grid(row=row, column=0)
		row += 1

		# horizontal separator (Frame in Frame)
		f = Tkinter.Frame(caPage, bd=2, relief="raised")
		Tkinter.Frame(f).grid()
		f.grid(row=row, column=0, sticky='ew')
		row += 1

		f = Tkinter.Frame(caPage)
		f.grid(row=row, column=0)
		Tkinter.Button(f, text="Delete", command=self._delSelAtomsBonds).grid(
			row=0, column=0)
		Tkinter.Label(f, text="selected atoms/bonds").grid(row=0, column=1)
		row += 1

	def _fillAdjustBondsPage(self):
		abPage = self.notebook.page(ADJUST_BONDS)

		row = 0

		addDelGroup = Pmw.Group(abPage, tag_text="Add/Delete")
		addDelGroup.grid(row=row, sticky="ew")
		inside = addDelGroup.interior()
		f = Tkinter.Frame(inside)
		f.grid(row=0, sticky='w')
		Tkinter.Button(f, text="Delete", command=self._delBonds, pady=0
			).grid(row=0, column=0)
		Tkinter.Label(f, text="selected bonds").grid(row=0, column=1)
		f = Tkinter.Frame(inside)
		f.grid(row=1, sticky='w')
		Tkinter.Button(f, text="Add", command=self._addBonds, pady=0
			).grid(row=0, column=0)
		self.addBondsMenu = Pmw.OptionMenu(f, initialitem=
			"reasonable", items=["reasonable", "all possible"],
			labelpos='e', label_text="bonds between selected atoms")
		self.addBondsMenu.grid(row=0, column=1)
		row += 1


		setGroup = Pmw.Group(abPage, tag_text="Set Length")
		setGroup.grid(row=row, sticky="ew")
		inside = setGroup.interior()
		f = Tkinter.Frame(inside)
		f.grid(row=0, sticky='w')
		from CGLtk.Hybrid import Scale
		self.blEntry = Scale(f, "Set length of selected bonds to:", 0.5, 4.5, 0.01, 1.5)
		self.blEntry.scale.config(tickinterval=1.0, length='3i')
		self.blEntry.callback(self._setBondLength)
		self.blEntry.frame.grid(row=0, column=0, columnspan=2)

		self.blSideMenu = Pmw.OptionMenu(f, labelpos='w', label_text="(move atoms on",
			items= ["smaller side", "larger side"], initialitem="smaller side")
		self.blSideMenu.grid(row=1, column=0, sticky='e')
		self.blSideLabel = Tkinter.Label(f, text=")")
		self.blSideLabel.grid(row=1, column=1, sticky='w')

		f = Tkinter.Frame(inside)
		f.grid(row=1)
		Tkinter.Button(f, text="Revert", pady=0, command=self._blRevert).grid(row=0, column=0)
		Tkinter.Label(f, text="bond lengths to their original values").grid(row=0, column=1)
		row += 1

	def _fillBondAnglesPage(self):
		baPage = self.notebook.page(BOND_ANGLES)
		row = 0

		self.baHelpText = "Select two adjacent bonds to adjust their bond angle"
		self.baHelp = Tkinter.Label(baPage, text=self.baHelpText)
		self.baHelp.grid(row=row, column=0)
		row += 1

		self.baTitle = Tkinter.Label(baPage)
		self.baTitle.grid(row=row, column=0)
		row += 1

		f = Tkinter.Frame(baPage)
		f.grid(row=row, column=0)
		self.baMenuOrder = None
		self.baMover = Pmw.OptionMenu(f, labelpos='w', label_text="Move",
				command=self._baMoverChange)
		self.baMover.grid(row=0, column=0)
		from CGLtk.AngleCounter import AngleCounter
		self.baAngleWidget = AngleCounter(f, labelpos='w', label_text="side ", minangle=0,
				dial_zeroAxis='y', dial_rotDir='clockwise', command=self._baAngleChange)
		self.baAngleWidget.grid(row=0, column=1)
		row += 1

		f = Tkinter.Frame(baPage)
		f.grid(row=row, column=0)
		Tkinter.Button(f, text="Revert", command=self._baRevert).grid(row=0, column=0)
		Tkinter.Label(f, text="bond angle to starting value").grid(row=0, column=1)
		row += 1

		# add a little buffer to the status
		Tkinter.Label(baPage).grid(row=row, column=0)
		row += 1

		self.baStatus = Tkinter.Label(baPage)
		self.baStatus.grid(row=row, column=0)
		row += 1

	def _fillJoinModelsPage(self):
		fmPage = self.notebook.page(JOIN_MODELS)

		bts = self._jmBondTypeSelect = Pmw.RadioSelect(fmPage, labelpos='w',
			buttontype="radiobutton", command=self._jmChangeBondType,
			label_text="Form", orient="vertical", pady=0)
		bts.add("peptide", text="C-N peptide bond", justify='left')
		bts.add("other", text="other bond", justify='left')
		bts.grid(row=0, column=0, sticky='w')
		obf = self.jmGenBondFrame = Tkinter.Frame(fmPage, bd=3, relief="raised")
		obf.grid(row=1, column=0)

		row = 0
		Tkinter.Label(obf, text="Delete selected atoms and add bond as"
			" follows:").grid(row=row)

		row += 1
		interior = Tkinter.Frame(obf)
		interior.grid(row=row)
		from chimera.tkoptions import FloatOption
		Tkinter.Label(interior, text="length:").grid(row=0, column=0,
								sticky='e')
		self._apobLength = FloatOption(interior, 0, "", 1.54, None,
							min=0.0, startCol=1)
		f = Tkinter.Frame(interior)
		f.grid(row=1, column=0, sticky='e')
		self._apobDihedralMenu = Pmw.OptionMenu(f)
		self._apobDihedralMenu.grid(row=0, column=0)
		Tkinter.Label(f, text=" dihedral:").grid(row=0, column=1)
		self._apobDihedral = FloatOption(interior, 1, "", 180.0, None,
							startCol=1)
		f = Tkinter.Frame(interior)
		f.grid(row=2, column=0, columnspan=3)
		Tkinter.Label(f, text="Move atoms on").grid(row=0, column=0)
		self._apobSideMenu = Pmw.OptionMenu(f)
		self._apobSideMenu.grid(row=0, column=1)
		Tkinter.Label(f, text="side").grid(row=0, column=2)

		row += 1
		reminder = Tkinter.Label(obf, text="(Selected atoms must be in"
			" different models and bonded to at most one atom each)")
		from CGLtk.Font import shrinkFont
		shrinkFont(reminder)
		reminder.grid(row=row)

		pbf = self.jmPeptideBondFrame = Tkinter.Frame(fmPage,
												bd=3, relief="raised")
		pbf.grid(row=1, column=0)

		row = 0
		Tkinter.Label(pbf, text="Form bond between selected C-terminal carbon\n"
			"and N-terminal nitrogen as follows:").grid(row=row)

		row += 1
		interior = Tkinter.Frame(pbf)
		interior.grid(row=row)
		from chimera.tkoptions import FloatOption
		self._appbLength = FloatOption(interior, 0, "C-N length", 1.33, None,
							min=0.0)
		self._appbDihedral = FloatOption(interior, 1,
			u"C\N{GREEK SMALL LETTER ALPHA}-C-N-C\N{GREEK SMALL LETTER ALPHA}"
			u" dihedral (\N{GREEK SMALL LETTER OMEGA} angle)", 180.0, None)
		self._appbPhi = FloatOption(interior, 2,
			u"C-N-C\N{GREEK SMALL LETTER ALPHA}-C"
			u" dihedral (\N{GREEK SMALL LETTER PHI} angle)", -120.0, None)
		self._appbPsi = Tkinter.Label(interior)
		self._appbPsi.grid(row=3, column=0, columnspan=2)
		f = Tkinter.Frame(interior)
		f.grid(row=4, column=0, columnspan=2)
		Tkinter.Label(f, text="Move atoms on").grid(row=0, column=0)
		self._appbSideMenu = Pmw.OptionMenu(f,
			items=["selected %s atom" % aname for aname in ["N", "C"]])
		self._appbSideMenu.grid(row=0, column=1)
		Tkinter.Label(f, text="side").grid(row=0, column=2)

		row += 1
		reminder = Tkinter.Label(pbf, text="(Selected atoms must be in"
			' different models and each bonded to exactly one carbon atom)\n'
			"[exception: N-terminal proline nitrogen can be bonded to"
			" two carbons]")
		from CGLtk.Font import shrinkFont
		shrinkFont(reminder)
		reminder.grid(row=row, column=0)

		self._addParamBondButton = Tkinter.Button(fmPage, text="Apply",
			command=self._addParamBond)
		self._addParamBondButton.grid(row=2, column=0)

		bts.invoke("other")

		self._jmConfig()

	def _fillBondRotsPage(self):
		brPage = self.notebook.page(BOND_ROTS)
		self.rotations = []
		self.rotInfo = {}

		labeledButton = Pmw.LabeledWidget(brPage, labelpos="e",
				label_text="selected bond as torsion")
		labeledButton.grid(row=0, column=0, columnspan=2)
		self.createRotButton = Tkinter.Button(labeledButton.interior(),
			text="Activate", command=self._createRotation, pady=0)
		self.createRotButton.grid()

		tableFrame = Tkinter.Frame(brPage, pady="0.1i")
		tableFrame.grid(row=1, column=0, columnspan=2, sticky='ns')
		from CGLtk.Table import ScrolledTable
		self.rotTable = ScrolledTable(tableFrame, hscrollmode='none')
		self.rotTable.setColumnTitle(0, "ID")
		self.rotTable.setColumnTitle(1, "Near")
		self.rotTable.setColumnTitle(2, "Bond")
		self.rotTable.setColumnTitle(3, "Far")
		self.angleTitle = Tkinter.StringVar(brPage)
		self.angleTitle.set("Torsion")
		self.rotTable.setColumnTitle(4, self.angleTitle,
						pyclass=Tkinter.Button, pady=0,
						command=self._toggleAngleType)
		brPage.rowconfigure(1, weight=1)
		brPage.columnconfigure(0, weight=1)
		brPage.columnconfigure(1, weight=1)
		tableFrame.rowconfigure(0, weight=1)
		tableFrame.columnconfigure(0, weight=1)
		self.rotTable.columnconfigure(4, weight=1)
		self.rotTable.grid(row=0, column=0, sticky='news')

		self.dialSizeLabels = ["small", "medium", "large"]
		Pmw.OptionMenu(tableFrame,
			items=self.dialSizeLabels, labelpos='w',
			initialitem=self.dialSizeLabels[prefs[ROT_DIAL_SIZE]],
			label_text="Dial size:", command=self._dialSizeChangeCB,
			).grid(row=1, column=0, sticky='e')

		f = Tkinter.Frame(brPage)
		f.grid(row=2, column=0, columnspan=2)
		self.mouseModeVar = Tkinter.IntVar(f)
		self.mouseModeVar.set(False)
		self.needTorWidgets = []
		self.needTorWidgets.append(Tkinter.Checkbutton(f, text="Rotate",
			variable=self.mouseModeVar, command=self._mouseModeCB))
		self.needTorWidgets[-1].grid(row=0, column=0)
		self.rotModeTorsMenu = Pmw.OptionMenu(f)
		self.rotModeTorsMenu.grid(row=0, column=1)
		self.needTorWidgets.append(self.rotModeTorsMenu)
		self.buttonLabels = []
		self.labelValues = {}
		for mod in ("",) + mousemodes.usedMods:
			for but in mousemodes.usedButtons:
				if mod:
					self.buttonLabels.append(
						mod.lower() + " button " + but)
					self.labelValues[self.buttonLabels[-1]]\
						= (but, (mod,))
				else:
					self.buttonLabels.append("button "+but)
					self.labelValues[self.buttonLabels[-1]]\
						= (but, ())
		self._modeButton = self.buttonLabels[0]
		self.rotModeButMenu = Pmw.OptionMenu(f, labelpos='w',
			command=self._modeButtonCB,
			label_text="using", items=self.buttonLabels)
		self.rotModeButMenu.grid(row=0, column=2)
		self.needTorWidgets.append(self.rotModeButMenu)

		self.rotLabelChoice = Pmw.RadioSelect(brPage, pady=0,
			buttontype='radiobutton', hull_pady=".1i",
			command=self._rotLabelModeChange, orient='vertical',
			labelpos='w', label_text="Labels")
		self.rotLabelChoice.grid(row=3, rowspan=2, column=0)
		self.rotLabelChoice.add("None", highlightthickness=0)
		self.rotLabelChoice.add("ID", highlightthickness=0)
		self.rotLabelChoice.add("Name", highlightthickness=0)
		self.rotLabelChoice.add("Angle", highlightthickness=0)
		self.rotLabelChoice.invoke(prefs[ROT_LABEL])

		from StructMeasure.gui import PrecisionEntry
		self.torsionPrecisionChoice = Pmw.Counter(brPage, datatype={
			'counter': self._torsionPrecisionChange}, labelpos='w',
			label_text="Decimal places", entry_width=1,
			entry_pyclass=PrecisionEntry,
			entryfield_value=str(prefs[TORSION_PRECISION]))
		self.torsionPrecisionChoice.grid(row=3, column=1)

		self.showDegreeSymbolVar = Tkinter.IntVar(brPage)
		self.showDegreeSymbolVar.set(prefs[SHOW_DEGREE_SYMBOL])
		Tkinter.Checkbutton(brPage, text="Show degree symbol",
			variable=self.showDegreeSymbolVar,
			command=self._showDegreeSymbolChangeCB).grid(
							row=4, column=1)

		self._setTorWidgetsState("disabled")

		mousemodes.addFunction("rotate bond", (lambda v, e:
			v.recordPosition(e.time, e.x, e.y, "rotate"),
			self._mouseSphere,
			lambda v, e: v.setCursor(None)))

		row = 0

	def _fillChiralityPage(self):
		cPage = self.notebook.page(CHIRALITY)
		
		row = 0
		from CGLtk.WrappingLabel import WrappingLabel
		WrappingLabel(cPage, text="Select one atom to swap the two smallest"
			" substituents bonded to that atom, or select two atoms to swap"
			" those specific substituents").grid(row=row, column=0, sticky='ew')
		cPage.columnconfigure(0, weight=1)
		row += 1

		Tkinter.Button(cPage, text="Swap", command=self._swapSubstituents
			).grid(row=row, column=0)

	def _finishPlace(self, atoms):
		for a in atoms:
			a.drawMode = chimera.Atom.EndCap
			for b in a.bonds:
				b.drawMode = chimera.Bond.Stick
		if self.colorByElementVar.get():
			from Midas import color
			color("byelement", atoms)
		
	def _genAtomNameCB(self, infoOnly=False):
		self.bondsJustChanged = False
		selResidues = chimera.selection.currentResidues()
		selAtoms = chimera.selection.currentAtoms()
		atomName = element = self.elementMenu.getvalue()[-1].upper()
		if not infoOnly:
			for a in selAtoms:
				if a.element.name != element:
					self.retainAtomNamesVar.set(False)
					self.retainAtomNameButton.configure(
							state="disabled")
					break
			else:
				self.retainAtomNameButton.configure(
							state="normal")
				self.retainAtomNamesVar.set(True)
		self.atomNameInfo.set("")
		if self.newresVar.get() == self.RES_MAKENEW:
			atomName += "1"
		elif len(selAtoms) == 1 \
		and selAtoms[0].name.startswith(atomName):
			atomName = selAtoms[0].name
		elif len(selResidues) == 1:
			from chimera.molEdit import genAtomName
			if infoOnly:
				atomName = self.atomNameOption.get()
			else:
				atomName = genAtomName(element, selResidues[0])
			if len(selAtoms) > 1:
				if atomName == element:
					atomName += "1"
				self._atomNameCache = [atomName]
				rem = atomName[len(element):]
				try:
					num = int(rem)
				except ValueError:
					pass
				else:
					needed = len(selAtoms) - 1
					selSet = set(selAtoms)
					remResAtoms = set(selResidues[0].atoms
								) - selSet
					remNames = set([a.name
							for a in remResAtoms])
					while needed:
						num += 1
						while element + str(num) \
								in remNames:
							num += 1
						self._atomNameCache.append(
							"%s%d" % (element, num))
						needed -= 1
					self.atomNameInfo.set("through %s%d"
							% (element, num))
		if infoOnly:
			return
					
		self.atomNameOption.set(atomName)
		chains = set([r.id.chainId for r in selResidues])
		if len(chains) != 1:
			self.chainNameVar.set("het")
		else:
			chain = chains.pop()
			if chain == "water":
				self.chainNameVar.set("het")
			else:
				self.chainNameVar.set(chain)

	def _getMol(self):
		m = self.molMenu.getvalue()
		if type(m) == str:
			m = self.molName.get()
		return m

	def _getResName(self):
		rn = self.resNameVar.get().strip()
		if not rn:
			self.enter()
			raise UserError("Must specify a residue name")
		if len(rn) > 4 or not rn.isalnum():
			from chimera.baseDialog import AskYesNoDialog
			if AskYesNoDialog(
			"Residue names longer than 4 characters\n"
			"or containing non-alphanumeric characters\n"
			"can be problematic when saving to certain\n"
			"file formats (e.g. PDB).\n"
			"\n"
			"Really use residue name '%s'?" % rn).run(
			self.uiMaster()) == 'no':
				self.enter()
				return None
		return rn

	def Help(self):
		chimera.help.display("ContributedSoftware/editing/editing.html#"
			+ "setbond")

	def _geomChangeCB(self, val):
		if not self.bondsJustChanged:
			from chimera.bondGeom import geometryName
			maxBonds = geometryName.index(val)
			self.bondsMenu.setvalue(str(maxBonds))

	def _jmChangeBondType(self, btype):
		if btype == "other":
			self.jmGenBondFrame.grid()
			self.jmPeptideBondFrame.grid_remove()
		else:
			self.jmGenBondFrame.grid_remove()
			self.jmPeptideBondFrame.grid()
		self._jmConfig()

	def _jmConfig(self, *args):
		selAtoms = selection.currentAtoms()
		twoOkayAtoms = False
		if not hasattr(self, "_jmBondHandler"):
			self._jmBondHandler = None
		if len(selAtoms) == 2:
			if not self._jmBondHandler:
				self._jmBondHandler = \
						chimera.triggers.addHandler(
						"Bond", self._jmConfig, None)
			a1, a2 = selAtoms
			if a1.oslIdent() > a2.oslIdent():
				a1, a2 = a2, a1
			if a1.molecule != a2.molecule:
				if self._jmBondTypeSelect.getvalue() == "peptide":
					if set([a1.element.name,a2.element.name]) == set(["N","C"]):
						ca1 = [nb for nb in a1.primaryNeighbors()
								if nb.element.name == "C"]
						ca2 = [nb for nb in a2.primaryNeighbors()
								if nb.element.name == "C"]
						if a1.residue.type in ["PRO", "HYP"]:
							testValues1 = [1,2]
						else:
							testValues1 = [1]
						if a2.residue.type in ["PRO", "HYP"]:
							testValues2 = [1,2]
						else:
							testValues2 = [1]
						if len(ca1) in testValues1 and len(ca2) in testValues2:
							twoOkayAtoms = True
				else:
					rootA1 = a1.molecule.rootForAtom(a1, True)
					rootA2 = a2.molecule.rootForAtom(a2, True)
					if rootA1 != rootA2 \
					and len(a1.neighbors) == len(a2.neighbors) == 1:
						twoOkayAtoms = True
		elif self._jmBondHandler:
			chimera.triggers.deleteHandler("Bond",
							self._jmBondHandler)
			self._jmBondHandler = None
			
		if twoOkayAtoms:
			self._addParamBondButton.config(state="normal")
			if self._jmBondTypeSelect.getvalue() != "other":
				self._appbPsi.grid()
				if a1.element.name == "N":
					psi = a1.residue.psi
				else:
					psi = a2.residue.psi
				if psi is None:
					psiText = "N/A"
				else:
					psiText = "%.1f" % psi
				self._appbPsi.configure(text=u"(Existing "
					u"N-C\N{GREEK SMALL LETTER ALPHA}-C-N"
					u" dihedral (\N{GREEK SMALL LETTER PSI}"
					u" angle): %s)" % psiText)
				return
			osls = [a1.oslIdent(), a2.oslIdent()]
			if not hasattr(self, "_jmPrevAtoms"):
				self._jmPrevAtoms = None
			self._jmPrevAtoms = osls
			if self._jmPrevAtoms != osls:
				self._apobLength.set(elementRadius[a1.element] +
						elementRadius[a2.element])
			names, atoms = self._enumerateDihedrals(a1, a2)
			prevName = self._apobDihedralMenu.getvalue()
			kw = {}
			if prevName in names:
				kw['index'] = prevName
			self._apobDihedralMenu.setitems(names, **kw)
			kw = {}
			prevSide = self._apobSideMenu.getvalue()
			from chimera.misc import chimeraLabel
			sides = [chimeraLabel(a) for a in (a1, a2)]
			if prevSide in sides:
				kw['index'] = prevSide
			else:
				if rootA1.size.numAtoms < rootA2.size.numAtoms:
					kw['index'] = sides[0]
				else:
					kw['index'] = sides[1]
			self._apobSideMenu.setitems(sides, **kw)
		else:
			self._addParamBondButton.config(state="disabled")
			if self._jmBondTypeSelect.getvalue() != "other":
				self._appbPsi.grid_remove()
				return
			self._apobDihedralMenu.setitems([])
			self._apobSideMenu.setitems([])
		if self._addParamBondButton.winfo_ismapped():
			self.notebook.setnaturalsize()

	def _labelRot(self, br, mode=None):
		if mode is None:
			mode = self.rotLabelChoice.getvalue()
		if mode == "None":
			for br in self.rotations:
				br.bond.label = ""
		elif mode == "Name":
			for br in self.rotations:
				br.bond.label = self.rotLabel(br)
		elif mode == "Angle":
			isDihed = self.angleTitle.get() == "Torsion"
			if prefs[SHOW_DEGREE_SYMBOL]:
				suffix = "\260"
			else:
				suffix = ""
			for br in self.rotations:
				if isDihed:
					val = self.dihedral(br)
				else:
					val = br.get()
					while val < -180.0:
						val += 180.0
					while val > 180.0:
						val -= 180.0
				br.bond.label = "%.*f%s" % (
					prefs[TORSION_PRECISION], val, suffix)
		elif mode == "ID":
			br.bond.label = str(br.id)

	def _lowerCB(self, pageName):
		if not self._mapped:
			return
		if pageName == ADJUST_BONDS:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._abSelChangeHandler)
			delattr(self, "_abSelChangeHandler")
		elif pageName == BOND_ANGLES:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._baSelChangeHandler)
			delattr(self, "_baSelChangeHandler")
			self.baMenuOrder = None # don't hold reference to bonds
		elif pageName == CHANGE_ATOM:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._caSelChangeHandler)
			delattr(self, "_caSelChangeHandler")
		elif pageName == JOIN_MODELS:
			from chimera import triggers
			triggers.deleteHandler("selection changed", self._jmSelChangeHandler)
			delattr(self, "_jmSelChangeHandler")
		self.status("") # can fire pending map/unmap trigger (some platforms), so do last

	def _menuCB(self, cmdText, br):
		# callback from angle pull-down menu

		if cmdText == "Revert":
			br.set(0)
		elif cmdText == "Deactivate":
			br.bond.label = ""
			br.destroy()
		elif cmdText == "Select":
			selectables = []
			selectables.extend(br.atoms)
			selectables.append(br.bond)
			if self.angleTitle.get() == "Torsion":
				near, far = self.dihedEndAtoms(br)
				if near and far:
					selectables.extend([near, far])
					selectables.append(br.atoms[0].bondsMap[near])
					selectables.append(br.atoms[1].bondsMap[far])
			from chimera.tkgui import selectionOperation
			sel = selection.ItemizedSelection()
			sel.add(selectables)
			selectionOperation(sel)
		elif cmdText == "Reverse":
			br.anchorSide = br.bond.otherAtom(br.anchorSide)

	def _modeButtonCB(self, but):
		if self.mouseModeVar.get():
			# "manually" turn off, then on with new value
			self.mouseModeVar.set(False)
			self._mouseModeCB()
			self._modeButton = but
			self.mouseModeVar.set(True)
			self._mouseModeCB()
		else:
			self._modeButton = but

	def _molMenuCB(self, val=None):
		val = self.molMenu.getvalue()
		if type(val) == str:
			self.molName.gridManage()
		else:
			self.molName.gridUnmanage()

	def _monitorCB(self, trigName, myData, trigData):
		from chimera.triggerSet import ONESHOT
		self.remakeAtomLabels()
		return ONESHOT

	def _mouseModeCB(self):
		but, mods = self.labelValues[self._modeButton]
		if self.mouseModeVar.get():
			self._formerMouseMode = mousemodes.getFuncName(but,mods)
			mousemodes.setButtonFunction(but, mods, "rotate bond")
		else:
			mousemodes.setButtonFunction(but, mods, self._formerMouseMode)

	def _mouseSphere(self, viewer, event):
		xf = viewer.vsphere(event.time, event.x, event.y,
							event.state % 2 == 1)
		if xf.isIdentity():
			return
		axis, angle = xf.getRotation()
		br = self.rotations[self.rotModeTorsMenu.index(Pmw.SELECT)]
		rotVec = br.atoms[1].xformCoord() - br.atoms[0].xformCoord()
		axis.normalize()
		rotVec.normalize()
		turn = angle * (axis * rotVec)
		br.set(turn + br.get())

	def _newBonds(self, val):
		self.bondsJustChanged = True
		numBonds = int(val)
		mb = self.geometryMenu.component('menubutton')
		if numBonds < 2:
			mb.configure(state="normal")
			self.geometryMenu.setvalue("N/A")
			mb.configure(state="disabled")
			return
		mb.configure(state="normal")
		from chimera.bondGeom import geometryName
		availGeoms = geometryName[numBonds:]
		self.geometryMenu.setitems(availGeoms, index=availGeoms[0])
			
	def _placeAtoms(self):
		placeType = self.placeTypeVar.get()

		if placeType in [self.PLACE_ATOM, self.PLACE_FRAGMENT,
				self.PLACE_SMILES, self.PLACE_PUBCHEM]:
			resName = self._getResName()
			if resName is None:
				return
		m = self._getMol()
		if placeType == self.PLACE_ATOM:
			if self.atomPosVar.get() == "view":
				h = placeHelium(resName, model=m)
			else:
				xyz = []
				for lab, entry in [("x", self.xEntry), ("y", self.yEntry),
						("z", self.zEntry)]:
					if not entry.valid():
						self.enter()
						raise UserError(lab + " entry invalid")
					xyz.append(float(entry.getvalue()))
				h = placeHelium(resName, model=m, position=chimera.Point(*xyz))
			if self.autoselAtomVar.get():
				chimera.selection.setCurrent(h)
			atoms = [h]
		elif placeType in [self.PLACE_FRAGMENT, self.PLACE_SMILES,
						self.PLACE_PUBCHEM]:
			if placeType == self.PLACE_FRAGMENT:
				frag = self.fragmentLookup[
						self.fragMenu.getvalue()[-1]]
				r = placeFragment(frag, resName, model=m)
			elif placeType == self.PLACE_SMILES:
				from Smiles import openSmiles, SmilesTranslationError
				try:
					m = openSmiles(self.smilesEntry.get(),
							resName=resName)
				except SmilesTranslationError, v:
					raise UserError(unicode(v))
				r = m.residues[0]
			else:
				from PubChem import openPubChem, InvalidPub3dID
				try:
					m = openPubChem(self.pubChemEntry.get(),
							resName=resName)
				except InvalidPub3dID, v:
					raise UserError(unicode(v))
				r = m.residues[0]
			atoms = r.atoms
		elif placeType == self.PLACE_NUCLEIC:
			nucType = self.nucType.getvalue()
			if nucType.startswith("Hybrid"):
				nucType = "hybrid"
			else:
				nucType = nucType.lower()
			try:
				residues = placeNucleotide(self.nucleicSequence.getvalue().strip(),
					self.nucForm.getvalue()[0], type=nucType, model=self._getMol())
			except NucleotideError, v:
				raise UserError(v)
			atoms = []
			for r in residues:
				atoms.extend(r.atoms)
		else:
			seq = self.peptideSequence.get().strip()
			PeptideDialog(seq, self._placePeptideCB)
			return

		self._finishPlace(atoms)

	def _placePeptideCB(self, seq, phiPsis, chainID, libName):
		try:
			residues = placePeptide(seq, phiPsis, rotlib=libName,
				model=self._getMol(), chainID=chainID)
		except PeptideError, v:
			raise UserError(v)
		atoms = []
		for r in residues:
			atoms.extend(r.atoms)

		self._finishPlace(atoms)

	def _processFragments(self, fragments):
		menuItems = []
		lookup = {}
		for item in fragments:
			if type(item) == list:
				# submenu
				subitems, sublookup = self._processFragments(
								item[1])
				menuItems.append([item[0], subitems])
				lookup.update(sublookup)
			else:
				# Fragment
				menuItems.append(item.name)
				lookup[item.name] = item
		return menuItems, lookup

	def _raiseCB(self, pageName):
		if not self._mapped:
			return
		self.bondsJustChanged = False
		if pageName == ADJUST_BONDS:
			self._abSelChange()
			from chimera import triggers
			self._abSelChangeHandler = triggers.addHandler("selection changed",
					self._abSelChange, None)
		elif pageName == BOND_ANGLES:
			self._baSelChange()
			from chimera import triggers
			self._baSelChangeHandler = triggers.addHandler("selection changed",
					self._baSelChange, None)
		elif pageName == CHANGE_ATOM:
			self._genAtomNameCB()
			self._caSelChangeHandler = chimera.triggers.addHandler('selection changed',
					lambda *args: self._genAtomNameCB(), None)
		elif pageName == JOIN_MODELS:
			from chimera import triggers
			self._jmSelChangeHandler = triggers.addHandler("selection changed",
					self._jmConfig, None)

	def _rotLabelModeChange(self, mode):
		prefs[ROT_LABEL] = mode
		for br in self.rotations:
			self._labelRot(br, mode)

	def _sessionSave(self, trigName, myData, sessionFile):
		info = {'mapped': self.uiMaster().winfo_ismapped()}
		if bondRotMgr.rotations:
			info['adjust torsions'] = {
				'labels': self.rotLabelChoice.getvalue(),
				'decimal places': int(self.torsionPrecisionChoice.getvalue()),
				'show degree symbol': self.showDegreeSymbolVar.get()
			}
		print>>sessionFile, """
try:
	from BuildStructure.gui import _sessionRestore
	_sessionRestore(%s)
except:
	reportRestoreError("Failure restoring Build Structure")
""" % repr(info)

	def _sessionRestore(self, info):
		if info['mapped']:
			self.enter()
		else:
			self.Close()
		if 'adjust torsions' in info:
			atInfo = info['adjust torsions']
			showSymbol = atInfo['show degree symbol']
			if showSymbol != self.showDegreeSymbolVar.get():
				self.showDegreeSymbolVar.set(showSymbol)
			precision = atInfo['decimal places']
			diff = precision - int(self.torsionPrecisionChoice.getvalue())
			while diff > 0:
				diff -= 1
				self.torsionPrecisionChoice.decrement()
			while diff < 0:
				diff += 1
				self.torsionPrecisionChoice.increment()
			labels = atInfo['labels']
			if labels != self.rotLabelChoice.getvalue():
				self.rotLabelChoice.invoke(labels)

	def _setBondLength(self):
		self.status("")
		bondLength = self.blEntry.value()
		if bondLength is None or bondLength == 0:
			# typed text can temporarily go through non-numeric
			# or zero values: ignore
			return
		if bondLength < 0:
			raise UserError("Invalid bond length specified")

		cbs = selection.currentBonds()
		if not cbs:
			raise UserError("No bonds selected")

		side = self.blSideMenu.getvalue()
		for bond in cbs:
			setBondLength(bond, bondLength, movingSide=side,
							status=self.status)

	def _setDihedEnd(self, br, dihedMenu):
		"""callback when a 'near atoms' menu is set"""

		widgets, nearIndex, nearAtoms, farIndex, farAtoms = \
								self.rotInfo[br]
		index = dihedMenu.index(Pmw.SELECT)
		if dihedMenu is widgets[1]:
			nearIndex = index
		else:
			farIndex = index
		self.rotInfo[br] = [widgets, nearIndex, nearAtoms,
							farIndex, farAtoms]
		widgets[4].configure(angle=float("%.*f" %
			(prefs[TORSION_PRECISION], self.dihedral(br))))
		self._labelRot(br)
	
	def _setTorWidgetsState(self, state):
		for w in self.needTorWidgets:
			if isinstance(w, Pmw.OptionMenu):
				if w['labelpos']:
					w.configure(label_state=state)
				w.configure(menubutton_state=state)
			else:
				w.configure(state=state)

	def _showDegreeSymbolChangeCB(self):
		prefs[SHOW_DEGREE_SYMBOL] = self.showDegreeSymbolVar.get()
		if self.rotLabelChoice.getvalue() == "Angle":
			for br in self.rotations:
				self._labelRot(br)

	def _showPlaceGroup(self, val, row):
		for group in self.apGroups.values():
			group.grid_forget()
		self.apGroups[val].grid(row=row, column=2,
						rowspan=len(self.apGroups))
		if val in [self.PLACE_SMILES, self.PLACE_PUBCHEM]:
			self.apModelNameFrame.grid_remove()
			self.apColorButton.grid_remove()
		else:
			self.apModelNameFrame.grid()
			self.apColorButton.grid()
		self.notebook.setnaturalsize()

	def _swapSubstituents(self):
		selAtoms = selection.currentAtoms()
		if len(selAtoms) == 1:
			center = selAtoms[0]
			kw = {}
		elif len(selAtoms) == 2:
			centers = set(selAtoms[0].neighbors) & set(selAtoms[1].neighbors)
			if not centers:
				raise UserError("Selected atoms have no neighbor atom in common!")
			elif len(centers) > 1:
				raise UserError("Selected atoms have more than one neighbor atom"
					" in common!")
			center = centers.pop()
			kw = {'swapees': selAtoms}
		else:
			raise UserError("Please select either one or two atoms.")
		from BuildStructure import invertChirality, InvertChiralityError
		try:
			invertChirality(center, **kw)
		except InvertChiralityError, v:
			raise UserError(unicode(v))

	def _toggleAngleType(self):
		if self.angleTitle.get() == "Torsion":
			self.angleTitle.set("Delta")
			self.rotTable.setColumnTitle(1, None)
			self.rotTable.setColumnTitle(3, None)
			for i in range(len(self.rotations)):
				br = self.rotations[i]
				ID, near, menu, far, dihed, delta = \
							self.rotInfo[br][0]
				dihed.grid_forget()
				near.grid_forget()
				far.grid_forget()
				delta.grid(row=i, column=4, sticky='ew')
				self.rotInfo[br][0][-2:] = delta, dihed
		else:
			self.angleTitle.set("Torsion")
			self.rotTable.setColumnTitle(1, "Near")
			self.rotTable.setColumnTitle(3, "Far")
			for i in range(len(self.rotations)):
				br = self.rotations[i]
				ID, near, menu, far, delta, dihed = \
							self.rotInfo[br][0]
				delta.grid_forget()
				dihed.grid(row=i, column=4, sticky='ew')
				near.grid(row=i, column=1, sticky='ew')
				far.grid(row=i, column=3, sticky='ew')
				self.rotInfo[br][0][-2:] = dihed, delta
		if self.rotLabelChoice.getvalue() == "Angle":
			for br in self.rotations:
				self._labelRot(br, "Angle")

	def _torsionPrecisionChange(self, *args):
		newPrecision = self._checkPrecision(*args)
		prefs[TORSION_PRECISION] = newPrecision
		for br in self.rotations:
			self._updateRot(br)
		return str(newPrecision)

	def _updateRot(self, br):
		if self.angleTitle.get() == "Torsion":
			dihed, delta = self.rotInfo[br][0][-2:]
		else:
			delta, dihed = self.rotInfo[br][0][-2:]
		delta.configure(angle = float("%.*f" %
			(prefs[TORSION_PRECISION], br.get())))
		dihed.configure(angle = float("%.*f" %
			(prefs[TORSION_PRECISION], self.dihedral(br))))
		if self.rotLabelChoice.getvalue() == "Angle":
			self._labelRot(br, "Angle")

class PmwableMenuButton(Tkinter.Menubutton):
	def __init__(self, *args, **kw):
		try:
			items = kw['items']
			del kw['items']
		except KeyError:
			items = []
		try:
			command = kw['command']
			del kw['command']
		except KeyError:
			command = None
		try:
			states = kw['states']
			del kw['states']
		except KeyError:
			states = ['normal'] * len(items)
		Tkinter.Menubutton.__init__(self, *args, **kw)
		self.menu = Tkinter.Menu(self)
		for i in range(len(items)):
			item = items[i]
			state = states[i]
			if command:
				self.menu.add_command(label=item, state=state,
					command=lambda c=command, i=item: c(i))
			else:
				self.menu.add_command(label=item, state=state)
		self.configure(menu=self.menu)

def paramTitle(startText):
	if '(' in startText:
		parened = startText.split('(')
		for i, trailer in enumerate(parened[1:]):
			parenthetical, rem = trailer.split(')')
			parts = parenthetical.split()
			parened[i+1] = "-".join([part.capitalize()
				for part in parts]) + " " + rem
		text = " ".join(parened)
	else:
		text = startText
	return " ".join([x[1:].islower() and x.capitalize()
				or x for x in text.split()])

class PeptideDialog(ModelessDialog):
	oneshot = True
	title = "Add Peptide Sequence"
	help = "ContributedSoftware/editing/editing.html#peptide-angles"

	def __init__(self, seq, cb):
		self.seq = seq
		self.cb = cb
		ModelessDialog.__init__(self)
	
	def fillInUI(self, parent):
		from CGLtk.Table import SortableTable
		table = self.table = SortableTable(parent,
							allowUserSorting=False)
		table.addColumn("Res", "code")
		table.addColumn(u"\u03A6", "phi", format="%g")
		table.addColumn(u"\u03A8", "psi", format="%g")
		class ResData:
			pass
		self.data = data = []
		for c in self.seq:
			rd = ResData()
			rd.code = c
			rd.phi, rd.psi = PhiPsiOption.values[0]
			data.append(rd)
		table.setData(data)
		table.launch()
		table.grid(row=0, column=0, sticky="nsew", columnspan=6)
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(5, weight=1)
		from chimera import tkgui
		if tkgui.windowSystem == "aqua":
			padx = None
		else:
			padx = 0
		Tkinter.Button(parent, text="Set", command=self._setPhiPsi,
			pady=0, padx=padx).grid(row=1, column=0)
		Tkinter.Label(parent, text="selected rows to").grid(row=1,
								column=1)
		from chimera.tkoptions import FloatOption
		self.phi = FloatOption(parent, 1, u"\u03A6", 0.0, None, width=6,
								startCol=2)
		self.psi = FloatOption(parent, 1, u"\u03A8", 0.0, None, width=6,
								startCol=4)
		f = Tkinter.Frame(parent)
		f.grid(row=2, columnspan=6)
		self._seedPhiPsi(
			PhiPsiOption(f, 0, u"Seed above \u03A6/\u03A8 with"
					u" values for", PhiPsiOption.values[0],
					self._seedPhiPsi))
		from Rotamers.gui import RotLibOption, defaultLib
		f2 = Tkinter.Frame(parent)
		f2.grid(row=3, columnspan=6)
		self.rotlib = RotLibOption(f2, 0, "Rotamer library",
							defaultLib(), None)
		from chimera.tkoptions import StringOption
		self.chainID = StringOption(f2, 0, "chain ID", "A", None,
							width=1, startCol=2)

	def Apply(self):
		self.cb(self.seq, [(d.phi, d.psi) for d in self.data],
			self.chainID.get(), self.rotlib.get().importName)

	def _seedPhiPsi(self, opt):
		phi, psi = opt.get()
		self.phi.set(phi)
		self.psi.set(psi)

	def _setPhiPsi(self):
		residues = self.table.selected()
		if not residues:
			raise UserError("No table rows selected")
		phi = self.phi.get()
		psi = self.psi.get()
		for r in residues:
			r.phi = phi
			r.psi = psi
		self.table.refresh()

from chimera.tkoptions import SymbolicEnumOption
class PhiPsiOption(SymbolicEnumOption):
	values = ((-57, -47),
		(-139, 135),
		(-119, 113),
		(-49, -26),
		(-57, -70))
	## Tk 8.4 rendering of Unicode pretty yucky
	#labels = ("alpha helix", "3/10 helix",
	#	"pi helix", "parallel beta strand",
	#	"anti-parallel beta strand")
	# but Tk 8.5 rendering is okay
	labels = (u"\u03B1 helix",
		u"antiparallel \u03B2 strand",
		u"parallel \u03B2 strand",
		# subscripts look shitty and subscript zero doesn't even work,
		# so instead of using:
		#u"3\u2081\u2080 helix",
		# use:
		"3/10 helix",
		u"\u03C0 helix")

from chimera import dialogs
dialogs.register(BuildStructureDialog.name, BuildStructureDialog)

def addRotation(bond):
	d = dialogs.find(BuildStructureDialog.name)
	import types
	br = bondRotMgr.rotationForBond(bond, create=False)
	if br == None:
		br = bondRotMgr.rotationForBond(bond)
	else:
		d.enter()
		d.setCategory(BOND_ROTS)
	return br

def _showBondRotUI(trigger, myData, br):
	if chimera.nogui:
		return
	if trigger == bondRotMgr.CREATED:
		# some window managers are slow to raise windows
		# only auto-raise the dialog if a new rotation is created
		d = dialogs.display(BuildStructureDialog.name)
		d.setCategory(BOND_ROTS)
	d = dialogs.find(BuildStructureDialog.name)
	d.rotChange(trigger, br)
for trigger in bondRotMgr.triggerNames:
	bondRotMgr.triggers.addHandler(trigger, _showBondRotUI, None)
if bondRotMgr.rotations:
	d = dialogs.display(BuildStructureDialog.name)
	d.setCategory(BOND_ROTS)
	for br in bondRotMgr.rotations.values():
		d.rotChange(bondRotMgr.CREATED, br)

def _sessionRestore(info):
	d = dialogs.display(BuildStructureDialog.name)
	d._sessionRestore(info)
