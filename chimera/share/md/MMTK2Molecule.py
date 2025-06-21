def convert(universe, defaultCS=None, usePDBnames=True):
	"""Accepts an MMTK universe and returns (Chimera molecule,
	map from MMTK atom to Chimera atom) tuple"""

	c = _Converter(universe)
	return c.convert(defaultCS=defaultCS, usePDBnames=usePDBnames)

class _Converter:

	def __init__(self, universe):
		self.universe = universe

	def convert(self, defaultCS, usePDBnames):
		# First create the reference molecule
		self.usePDBnames = usePDBnames
		from chimera import Molecule
		m = Molecule()
		if defaultCS is not None:
			m.activeCoordSet = m.newCoordSet(defaultCS)
		self._wholeSeq = 1
		self._mmtk2chimera = {}		# For updating coordinates
		for obj in self.universe.objectList():
			if not obj.is_chemical_object:
				continue
			# Add the atoms
			try:
				resList = obj.residues()
			except:
				# No residues in the object, so just
				# fake one for the entire object
				self._addWholeMolecule(m, obj)
			else:
				# Add residues one by one
				self._addResidues(m, resList)
			# Add the bonds
			self._addBonds(m, obj)
		return m, self._mmtk2chimera

	def _addWholeMolecule(self, m, obj):
		# This code is untested.  It "should" work.
		r = m.newResidue("UNK", "het", self._wholeSeq, " ")
		self._wholeSeq += 1
		self._addAtoms(m, r, obj)

	def _addResidues(self, m, resList):
		# This code is untested.  It "should" work.
		# This code has only been tested with "bala1" which happens
		# to be a protein whose atom names map well to PDB
		# conventions.  Changes will be needed for chains whose
		# residues are not amino acids or nucleic bases.
		for mr in resList:
			seq = mr.sequence_number
			rtype = mr.symbol
			if self.usePDBnames:
				rtype = rtype.upper()[:3]
			if mr.parent.is_chain:
				chainId = mr.parent.name
				if self.usePDBnames:
					chainId = chainId.replace("chain", "")
					chainId = chainId.upper()[:1]
			else:
				chainId = ' '
			r = m.newResidue(rtype, chainId, seq, " ")
			self._addAtoms(m, r, mr)

	def _addAtoms(self, m, r, obj):
		from chimera import Element, Coord
		# The MMTK atom names look like "C_beta" while Chimera really
		# expects something like "CB".  So we pull the conversion
		# map out from the residue type's "pdbmap" attribute.
		# The data structures are a little convoluted, but constructed
		# "mmtk2pdb" is a dictionary whose keys are MMTK names
		# and whose values are PDB names.  If an MMTK name
		# is not found in mmtk2pdb, we just use the MMTK name and
		# hope for the best.
		mmtk2pdb = {}
		try:
			if not self.usePDBnames:
				raise AttributeError("skip PDB name code")
			for _, atomMap in obj.type.pdbmap:
				for name, atom in atomMap.iteritems():
					mname = obj.type.atoms[atom.number].name
					mmtk2pdb[mname] = name
		except AttributeError:
			pass
		for ma in obj.atomList():
			aname = mmtk2pdb.get(ma.name, ma.name)
			e = Element(ma.type.symbol)
			a = m.newAtom(aname, e)
			r.addAtom(a)
			x, y, z = ma.position() * 10
			# Multiply coordinates by 10 to convert from MMTK nm
			# to Chimera Angstrom
			a.setCoord(Coord(x, y, z))
			# Cache MMTK->Chimera atom mapping.  We can do this
			# using an attribute in ma, but I prefer to leave
			# MMTK instances pristine
			self._mmtk2chimera[ma] = a

	def _addBonds(self, m, obj):
		for mbu in obj.bondedUnits():
			try:
				bonds = mbu.bonds
			except AttributeError:
				continue
			for mb in bonds:
				try:
					a1 = self._mmtk2chimera[mb.a1]
					a2 = self._mmtk2chimera[mb.a2]
				except KeyError:
					pass
				else:
					b = m.newBond(a1, a2)

def updateChimera(thread, universe, atomMap, frames, callback=None):
	"Update Chimera coordinates from MMTK coordinates periodically."
	from chimera import triggers
	updater = _ChimeraUpdater(thread, universe, atomMap, frames, callback)
	h = triggers.addHandler("check for changes", updater.update, None)
	updater.setHandler(h)

class _ChimeraUpdater:

	def __init__(self, thread, universe, atomMap, frames, callback):
		self.thread = thread
		self.universe = universe
		self.atomMap = atomMap
		self.frames = frames
		self.callback = callback
		self.handler = None
		self.curFrame = 0

	def setHandler(self, h):
		self.handler = h

	def update(self, triggerName, myData, triggerData):
		self.curFrame += 1
		if self.curFrame < self.frames:
			return
		from chimera import replyobj
		self.curFrame = 0
		self._getCoords()
		replyobj.status("MMTK updated coordinates", log=True)
		if not self.thread.is_alive():
			if self.handler is not None:
				from chimera import triggers
				triggers.deleteHandler("check for changes",
							self.handler)
				self.handler = None
			replyobj.status("MMTK operation finished", log=True)

	def _getCoords(self):
		from chimera import Point,Coord
		conf = self.universe.copyConfiguration()
		for  ma in self.universe.atomList():
			x, y, z = conf[ma] * 10
			self.atomMap[ma].setCoord(Coord(x, y, z))
		if self.callback:
			self.callback(self.universe, self.atomMap)
