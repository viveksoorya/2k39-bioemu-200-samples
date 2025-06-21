# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42039 2019-05-28 21:25:24Z pett $

import sys

## "real" ensemble class implements the following: a "GetDict" method
## which handles "atomnames", "renames", "bonds" and "ipres" (residue
## to bond pointers)
## and a "LoadFrame" method which loads the Nth frame.

import chimera

class NoFrameError(ValueError):
	pass

class Ensemble:
	""" Ensemble class """
	solventResNames = set(["HOH", "WAT", "H2O", "D2O", "SOL", "TIP3"])

	def __init__(self, ensemble, sesInfo=None, generateChains=True):
		if sesInfo:
			from SimpleSession import idLookup
			self.atomMap = [idLookup(a) for a in sesInfo['atomMap']]
			self._mol = idLookup(sesInfo['_mol'])
			exec("from %s import %s as ensembleClass" % (sesInfo['ensembleModule'],
				sesInfo['ensembleClassName']))
			import inspect
			inspectInfo = inspect.getargspec(ensembleClass.__init__)
			self._ensemble = ensembleClass(
				*tuple([None] * (len(inspectInfo.args) - len(inspectInfo.defaults) - 1)),
				sesInfo=sesInfo['_ensemble'])
			self._ensemble.name = sesInfo['ensembleName']
		else:
			self._ensemble = ensemble
			if hasattr(ensemble, 'molecule'):
				self._mol = ensemble.molecule
			else:
				self._mol = chimera.Molecule()
				self._mol.name = ensemble.name
				self.generateChains = generateChains

	def __getattr__(self, attrName):
		"""access as if a molecule model"""
		return getattr(self._mol, attrName)

	def AddMolecule(self, **kw):
		# needs to be here instead of CreateMolecule() because PDB trajectories
		# don't really use CreateMolecule()
		if (not getattr(self._ensemble, 'isRealMolecule', True)
							and 'noPrefs' not in kw):
			kw['noprefs'] = True
		chimera.openModels.add([self._mol], **kw)

	def DeleteMolecule(self):
		chimera.openModels.close([self._mol])

	def Molecule(self):
		return self._mol

	def CreateMolecule(self):
		if hasattr(self._ensemble, "molecule"):
			return
		atomnames = map(str.strip, self._ensemble.GetDict('atomnames'))
		elements = self._ensemble.GetDict('elements')
		resnames = map(str.strip, self._ensemble.GetDict('resnames'))
		try:
			resnums = self._ensemble.GetDict('resnums')
		except KeyError:
			resnums = range(1, len(resnames)+1)
		bonds = self._ensemble.GetDict('bonds')
		ipres = self._ensemble.GetDict('ipres')
		try:
			charges = self._ensemble.GetDict('charges')
		except KeyError:
			charges = None
		try:
			chains = self._ensemble.GetDict('chains')
		except KeyError:
			if self.generateChains:
				chains = self.findChains(bonds, ipres, resnames, len(atomnames))
			else:
				chains = None

		self.atomMap = [None] * len(atomnames)

		resMap = {}
		for rnum in range(len(resnames)):
			residue = resnames[rnum]
			if chains is None:
				if residue in self.solventResNames:
					chain = "water"
				else:
					chain = " "
			else:
				chain = chains[rnum]
			resKey = (residue, chain, resnums[rnum], ' ')
			res = self._mol.newResidue(*resKey)
			resMap.setdefault(resKey, []).append(res)
			if rnum != len(resnames)-1:
				a1, a2 = ipres[rnum]-1, ipres[rnum+1]-1
			else:
				a1, a2 = ipres[rnum]-1, len(atomnames)

			for i in range(a1, a2):
				chimera_atom = self._mol.newAtom(atomnames[i], elements[i])
				chimera_atom.serialNumber = i+1
				if charges:
					chimera_atom.charge = charges[i]
				self.atomMap[i] = chimera_atom
				res.addAtom(chimera_atom)
		try:
			segments = self._ensemble.GetDict("segments")
		except KeyError:
			pass
		else:
			for seg, res in zip(segments, self._mol.residues):
				res.segment = seg
		if len(resMap) != len(self._mol.residues):
			# CHARMM QM simulations can put parts of the same residue
			# into different parts of the PSF file; merge residues
			# with identical identifiers and types that are on the
			# same physical chain
			for residues in resMap.values():
				if len(residues) == 1:
					continue
				rootMap = {}
				for r in residues:
					# already guaranteed to be same type, due to resMap
					rootMap.setdefault(self._mol.rootForAtom(r.atoms[0], True), []).append(r)
				if len(rootMap) == len(residues):
					continue
				for mergables in rootMap.values():
					survivor = mergables[0]
					for merging in mergables[1:]:
						atoms = merging.atoms
						self._mol.deleteResidue(merging)
						for a in atoms:
							survivor.addAtom(a)

		for bond in bonds:
			a1, a2 = self.atomMap[bond[0]], self.atomMap[bond[1]]
			self._mol.newBond(a1, a2)

	def LoadFrame(self, frame, makeCurrent=True):
		cs = self._mol.findCoordSet(frame)
		if cs is not None:
			if makeCurrent:
				self._mol.activeCoordSet = cs
			return
		try:
			crds = self._ensemble[frame]
		except:
			if self._ensemble.endFrame == "pipe":
				raise NoFrameError("Couldn't read frame " + str(frame))
			else:
				raise

		cs = self._mol.newCoordSet(frame, len(self._mol.atoms))
		from chimera import fillCoordSet
		fillCoordSet(cs, self.atomMap, crds)
		if makeCurrent:
			self._mol.activeCoordSet = cs

		if len(self._mol.coordSets) == 1 and not self._mol.bonds:
			# if no connectivity, create on first coord set
			chimera.connectMolecule(self._mol)

	def findChains(self, bonds, ipres, resnames, numatoms):
		groups = {}
		groupIDs = set()
		for i1, i2 in bonds:
			grp1 = groups.get(i1, None)
			grp2 = groups.get(i2, None)
			if grp1 is None:
				if grp2 is None:
					grp = groups[i1] = groups[i2] = []
					grp.append(i1)
					grp.append(i2)
					groupIDs.add(id(grp))
				else:
					grp2.append(i1)
					groups[i1] = grp2
			else:
				if grp2 is None:
					grp1.append(i2)
					groups[i2] = grp1
				elif grp1 != grp2:
					grp1.extend(grp2)
					for index in grp2:
						groups[index] = grp1
					groupIDs.remove(id(grp2))
		chains = [' '] * len(resnames)
		import string
		legalChainIDs = string.ascii_uppercase + string.ascii_lowercase + '1234567890 '
		chainIDindex = 0
		atom2res = {}
		prevAtom = -1
		resNum = 0
		for atomNum in ipres[1:]:
			# a little funky since ipres is 1-based and everything else is 0-based
			for an in range(prevAtom+1, atomNum-1):
				atom2res[an] = resNum
			resNum += 1
			prevAtom = atomNum - 2
		for an in range(prevAtom+1, numatoms):
			atom2res[an] = resNum
		for group in groups.values():
			#many copies of group in values list...
			if id(group) not in groupIDs:
				continue
			groupIDs.remove(id(group))
			residues = set([atom2res[i] for i in group])
			if len(residues) == 1:
				resIndex = residues.pop()
				if resnames[resIndex] in self.solventResNames:
					chains[resIndex] = 'water'
				continue
			chainID = legalChainIDs[chainIDindex]
			for resIndex in residues:
				chains[resIndex] = chainID
			print "Assigning chain ID", chainID, "to", len(residues), "residues, e.g.", resnames[residues.pop()]
			if chainIDindex < len(legalChainIDs) - 1:
				chainIDindex += 1
		return chains

	def sesSave_gatherData(self):
		"""Only called on partially loaded trajectories"""
		from SimpleSession import sessionID
		if not hasattr(self._ensemble, 'sesSave_gatherData'):
			from Movie.gui import UnsupportedSesFormatError
			raise UnsupportedSesFormatError()
		mapVal = [sessionID(a) for a in self.atomMap if not a.__destroyed__]
		if len(mapVal) < len(self.atomMap):
			from chimera import LimitationError
			raise LimitationError("Cannot save session with partially played trajectory"
				" with deleted atoms.  Play through trajectory before saving session.")
		return {
			'atomMap': mapVal,
			'_mol': sessionID(self._mol),
			'_ensemble': self._ensemble.sesSave_gatherData(),
			'ensembleModule': self._ensemble.__module__,
			'ensembleClassName': self._ensemble.__class__.__name__,
			'ensembleName': self._ensemble.name
		}

def determineElementFromMass(mass, considerHydrogens=True):
	from chimera import Element
	H = Element('H')
	nearest = None
	for high in range(1, 93):
		if Element(high).mass > mass:
			break
	else:
		high = 93

	if considerHydrogens:
		maxHyds = 6
	else:
		maxHyds = 0
	for numHyds in range(maxHyds+1):
		adjMass = mass - numHyds * H.mass
		lowMass = Element(high-1).mass
		while lowMass > adjMass and high > 1:
			high -= 1
			lowMass = Element(high-1).mass
		highMass = Element(high).mass
		lowDiff = abs(adjMass - lowMass)
		highDiff = abs(adjMass - highMass)
		if lowDiff < highDiff:
			diff = lowDiff
			element = high - 1
		else:
			diff = highDiff
			element = high
		if nearest is None or diff < nearest[1]:
			nearest = (element, diff)
	return Element(nearest[0])

class MultiFileTrajectory:
	def __init__(self, addFunc):
		self.addFunc = addFunc
		self.trajs = []

	def addFile(self, trajFile):
		self.trajs.append(self.addFunc(trajFile))

	def __getitem__(self, i):
		# zero based
		for traj in self.trajs:
			if len(traj) > i:
				return traj[i]
			i -= len(traj)
		raise IndexError("No such frame")

	def __len__(self):
		return reduce(lambda x, y: x+y, [len(t) for t in self.trajs], 0)

def findTrajFile(origPath):
	from OpenSave import OpenModal
	dlg = OpenModal(title="Specify Trajectory Location", clientPos='s')
	from CGLtk.WrappingLabel import WrappingLabel
	WrappingLabel(dlg.clientArea, text="The original trajectory input file %s"
		"  was not found.  Please indicate its current location or click Cancel."
		" Clicking Cancel will cause the MD Movie interface not to be shown and"
		" only those trajectory frames that were loaded when the session was"
		" saved will be restored." % origPath, width=75).grid(sticky="ew")
	from chimera.tkgui import app
	retVal = dlg.run(app)
	if retVal is None:
		from chimera import CancelOperation
		raise CancelOperation("Cancel MD Movie restore")
	return retVal[0][0]
