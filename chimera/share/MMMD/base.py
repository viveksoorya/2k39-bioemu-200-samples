FreezeNone = "none"
FreezeSelected = "selected"
FreezeUnselected = "unselected"

class Minimizer:

	def __init__(self, molecules, nsteps=100, stepsize=0.02,
			cgsteps=100, cgstepsize=0.02,
			interval=10, fixedAtoms=set(), memorize=False,
			nogui=False, addhyd=True, callback=None,
			exclres=set(), cache=True, prep=None):
		self._mi = None
		self.molecules = molecules
		# nsteps and interval are public and may be changed by caller
		self.nsteps = nsteps
		self.stepsize = stepsize
		self.cgsteps = cgsteps
		self.cgstepsize = cgstepsize
		self.interval = interval
		self.fixedAtoms = fixedAtoms
		if prep is None:
			from DockPrep import needPrep
			prep = needPrep(molecules)
		self.callback = callback
		_find(molecules, exclres, nogui, addhyd, self._finishInit,
		      memorize, cache, prep)

	def _finishInit(self, mi):
		self._mi = mi
		if self.callback:
			self.callback(self)
		del self.callback

	def updateCoords(self, mi):
		import chimera
		assert(self._mi is mi)
		self._mi.saveMMTKCoordinates()
		chimera.runCommand("wait 1")

	def run(self):
		if self._mi is None:
			from chimera import UserError
			raise UserError("Please finish adding hydrogens and "
					"charges before trying to minimize")
		self._mi.setFixed(self.fixedAtoms)
		self._mi.loadMMTKCoordinates()
		import chimera
		chimera.runCommand("wait 1")
		self._mi.minimize(nsteps=self.nsteps, stepsize=self.stepsize,
					cgsteps=self.cgsteps,
					cgstepsize=self.cgstepsize,
					interval=self.interval,
					action=self.updateCoords)

def frozenAtoms(freeze, molecules):
	from chimera import selection
	if freeze is None or FreezeNone.startswith(freeze):
		atoms = set()
	elif FreezeSelected.startswith(freeze):
		atoms = set(selection.currentAtoms())
	elif FreezeUnselected.startswith(freeze):
		atoms = set(sum([m.atoms for m in molecules], []))
		atoms.difference_update(selection.currentAtoms())
	else:
		from chimera import specifier
		try:
			atoms = specifier.evalSpec(freeze).atoms()
		except:
			from chimera import UserError
			raise UserError("unknown freeze mode: \"%s\"" % freeze)
	return atoms

# Private functions below here

_miCache = []

def _find(molecules, exclres, nogui, addhyd, callback, memorize, cache, prep):
	global _miCache
	#print "_find", id(_miCache), _miCache
	mset = set(molecules)
	for t in _miCache:
		mols, exres, mi = t
		if set(mols) == mset and exres == exclres:
			callback(mi)
			return
	def cacheIt(mi, molecules=molecules, exclres=exclres,
		    callback=callback, cache=_miCache):
		#print "cacheIt", id(cache), cache
		callback(mi)
		cache.append((molecules, exclres, mi))
		#print "end cacheIt", id(cache), cache
	#print "creating MMTKinter instance", molecules
	from MMTKinter import MMTKinter
	mi = MMTKinter(molecules, exclres = exclres,
		       nogui=nogui, addhyd=addhyd,
		       callback=(cacheIt if cache else callback),
		       memorize=memorize, prep=prep)

def _moleculeCheck(triggerName, data, mols):
	# Remove all entries that refer to a molecule that is being closed
	_removeFromCache(mols)

def _removeFromCache(mols):
	global _miCache
	#print "Remove from cache", id(_miCache), _miCache
	junk = []
	for t in _miCache:
		molecules = t[0]
		for m in mols:
			if m in molecules:
				junk.append(t)
				break
	for t in junk:
		_miCache.remove(t)

def _atomCheck(trigger, closure, atoms):
	# If an atom is deleted, we invalidate the entire cache because
	# there's no easy way to find out the molecule from which the
	# atom was deleted (the C++ object is already gone).  If an atom
	# is added, we can do partial invalidation of the cache.
	if atoms.deleted:
		global _miCache
		while _miCache:
			_miCache.pop()
		#print "clear miCache, atom delete", id(_miCache), _miCache
		return
	if atoms.created:
		mols = set([])
		for a in atoms.created:
			mols.add(a.molecule)
		_removeFromCache(mols)

def _bondCheck(trigger, closure, bonds):
	# See _atomCheck comment
	if bonds.deleted:
		global _miCache
		while _miCache:
			_miCache.pop()
		#print "clear miCache, bond delete", id(_miCache), _miCache
		return
	if bonds.created:
		mols = set([])
		for b in bonds.created:
			mols.add(b.molecule)
		_removeFromCache(mols)

# Register for model removal so we can clean up our cache

import chimera
chimera.openModels.addRemoveHandler(_moleculeCheck, None)
chimera.triggers.addHandler("Atom", _atomCheck, None)
chimera.triggers.addHandler("Bond", _bondCheck, None)
