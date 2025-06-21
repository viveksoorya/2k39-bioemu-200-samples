# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

class Evaluator:

	def __init__(self,molecule,mol1,mol2,callback=None,
			nogui=False,addhyd=True,exclres=set(), cache=True, prep=True,
			memorize=False):

		self.mol1 = mol1
		self.mol2 = mol2
		self.callback = self.run
		_find(molecule,exclres,nogui,addhyd,self.callback,memorize,cache,prep)
		
	#def _finishInit(self, en):
	#	self._en = en
	#	if self.callback:
	#		self.callback(self)
	#	del self.callback

	def run(self,en):
		if en is None:
			from chimera import UserError
			raise UserError("Please finish adding hydrogens and "
					"charges before trying to minimize")
		en.loadMMTKCoordinates()
		import chimera
		chimera.runCommand("wait 1")
		energy = en.energyEvaluator(self.mol1,self.mol2)
		print energy
	

_miCache=[]
def _find(molecules, exclres, nogui, addhyd, callback, memorize, cache, prep):
	global _miCache
	#print "_find", id(_miCache), _miCache
	mset = set(molecules)
	for t in _miCache:
		mols, exres, en = t
		if set(mols) == mset and exres == exclres:
			callback(en)
			return

	def cacheIt(en, molecules=molecules, exclres=exclres,
		    callback=callback, cache=_miCache):
		#print "cacheIt", id(cache), cache
		callback(en)
		cache.append((molecules, exclres, en))
		#print "end cacheIt", id(cache), cache
	#print "creating MMTKinter instance", molecules
	from energyMMTKinter import energyMMTKinter
	en = energyMMTKinter(molecules, exclres = exclres,
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
