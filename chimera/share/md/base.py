
class Dynamics:
	def __init__(self, molecules, trajectory, frame,
			dynVar = None, heatMD = None, prodMD = None, minMD = None,
			fixed = None, filename = None, outside = False, generate = False, multi = 1, live = None,
			nogui = False, addhyd = True, callback = None,
			exclres = set(), cache = True, prep = None,
			trans = True, rot = True,
			memorize = False,
			esOptions = None, lenOptions=None, interval = 10):
			
		self._md = None
		self.heatMD = heatMD
		self.prodMD = prodMD
		self.minMD = minMD
		self.interval = interval
		self.esOptions=esOptions
		self.lenOptions=lenOptions
		self.molecules = molecules
		self.dynVar = dynVar
		self.fixed = fixed
		self.filename = filename
		self.outside = outside
		self.generate = generate
		self.multi = multi
		self.frame = frame
		self.onLive = live
		self.callback = self._loadCoord
		self.rot = rot
		self.trans = trans

		if prep is None:
			prep = self.needDockPrep()
		else:
			pass

		_find(molecules, exclres, nogui, addhyd, self.callback, 
		      memorize, cache, prep, trajectory, self.esOptions, self.dynVar,self.lenOptions)
	
	def needDockPrep(self):
		for m in self.molecules:
			if getattr(m, 'chargeModel', None) is None:
				return True
		for a in m.atoms:
			if getattr(a, 'charge', None) is None or getattr(a, 'gaffType', None) is None:
				return True
		return False

	def updateCoords(self, md):
		import chimera
		md.saveMMTKCoordinates()
		chimera.runCommand("wait 1")

 	def _loadCoord(self, md):
		md.setFixed(self.fixed.atoms())
 		md.loadMMTKCoordinates()

		if self.dynVar["PBC"] and self.dynVar["autoPBC"]:
			md.setAutoPBCUniverse()
	
		if self.minMD:
			import chimera
			chimera.runCommand("wait 1")
			md.minimize(self.minMD["sdSteps"],
				stepsize=self.minMD["sdStepSize"],
				cgsteps=self.minMD["cgSteps"],
				cgstepsize=self.minMD["cgStepSize"],
				interval = self.interval,
				action = self.updateCoords,
				threads=self.multi)
			md.loadMMTKCoordinates()

		if self.heatMD or self.prodMD:	
			md.dynamics(self.frame,
					heatMD = self.heatMD, prodMD = self.prodMD, dynVar = self.dynVar,
					fixed = self.fixed.atoms(), filename = self.filename, outside = self.outside, generate = self.generate, multi=self.multi,
					live = self.onLive, rot = self.rot, trans = self.trans)
 	
_miCache = []

def _find(molecules, exclres, nogui, addhyd, callback, memorize, cache, prep, trajectory, esOptions, dynVar,lenOptions):
	global _miCache
	#print "_find", id(_miCache), _miCache
	mset = set(molecules)
	for t in _miCache:
		mols, exres, md = t
		if set(mols) == mset and exres == exclres:
			md.traj = trajectory
			callback(md)
			return
	def cacheIt(md, molecules=molecules, exclres=exclres,
		    callback=callback, cache=_miCache):
		#print "cacheIt", id(cache), cache
		callback(md)
		cache.append((molecules, exclres, md))
		#print "end cacheIt", id(cache), cache
	#print "creating MMTKinter instance", molecules
	from mdMMTKinter import mdMMTKinter
	if dynVar["PBC"]:
		pbcBox = list()
		if not dynVar["autoPBC"]:
			pbcBox.append(dynVar["xPBC"])
			pbcBox.append(dynVar["yPBC"])
			pbcBox.append(dynVar["zPBC"])
		md = mdMMTKinter(molecules, trajectory, exclres = exclres,
				nogui=nogui, addhyd=addhyd,
				callback=(cacheIt if cache else callback),
				 memorize=memorize, prep=prep, esOptions = esOptions, PBCbox=pbcBox, autoPBC=dynVar["autoPBC"], ljOptions=lenOptions)
	else:
		md = mdMMTKinter(molecules, trajectory, exclres = exclres,
				nogui=nogui, addhyd=addhyd,
				callback=(cacheIt if cache else callback),
				 memorize=memorize, prep=prep, esOptions = esOptions,ljOptions=lenOptions)

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
