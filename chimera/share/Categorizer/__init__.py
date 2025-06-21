# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42044 2019-06-10 19:57:37Z pett $

"""
Categorize atoms into solvent, ligand, etc. categories

The categories and criteria are:

	solvent -- The most numerous "small" (10 atom or less) single-residue
		chain that isn't a singleton atom of atomic number 9 or more
		(florine or heavier) and that occurs at least 10 times.
		Also, all singleton atoms of atomic number 8 or less.

	ions --  Singleton atoms not categorized as solvent.

	ligand --  Chains smaller than 1/4 the longest chain of the model that
		aren't solvent or ions and less than 10 residues long.

	main --  Remainder of chains.
"""
categories = set([
	intern("solvent"), intern("ions"), intern("ligand"), intern("main")
])
_models = {}
def categorize(trigger, justdoit, data):
	# can't get the molecule attribute of deleted bonds,
	# so have to be tricky
	createModels = set()
	from chimera import OpenModels, Molecule, bondMolecules
	from chimera.elements import nobleGases
	if trigger == OpenModels.ADDMODEL:
		atomOnlyModels = []
		for openedModel in data:
			if (isinstance(openedModel, Molecule) and
			    openedModel.numAtoms > 0 and
			    openedModel.numBonds == 0):
				atomOnlyModels.append(openedModel)
		changeModels = atomOnlyModels
	else:
		bonds = data
		for m in bondMolecules(tuple(bonds.created)):
			createModels.add(m)
		changeModels = list(createModels)
		for prevModel, prevBonds in _models.items():
			if prevModel in createModels:
				continue
			try:
				curBonds = prevModel.numBonds
			except:
				# molecule probably deleted
				del _models[prevModel]
				continue
			if curBonds != prevBonds:
				changeModels.append(prevModel)
	if not changeModels:
		return False # don't run presets

	for model in changeModels:
		_models[model] = model.numBonds
		solvents = {}
		roots = model.roots(1)

		# for efficiency, segregate roots into small solvents/other
		smallSolvents = []
		rootDict = set()
		for root in roots:
			if root.size.numAtoms < 4 \
			and root.residue.type in ("HOH", "WAT", "DOD"):
				smallSolvents.append(root)
			elif root.size.numAtoms == 1 \
			and root.residue.numAtoms == 1 \
			and 5 < root.atom.element.number < 9:
				smallSolvents.append(root)
			else:
				rootDict.add(root)

		# assign solvent
		if smallSolvents:
			solvents["small solvents"] = smallSolvents
		for root in rootDict:
			if root.size.numAtoms > 10:
				continue
			if root.size.numAtoms != root.residue.numAtoms:
				continue
			if set([a for a in model.traverseAtoms(root)]) != set(root.residue.atoms):
				continue
			
			# potential solvent
			resID = root.residue.type
			if solvents.has_key(resID):
				solvents[resID].append(root)
			else:
				solvents[resID] = [root]
		
		solvent = []
		for resID in solvents.keys():
			if len(solvents[resID]) < 10:
				continue
			if len(solvents[resID]) < len(solvent):
				continue
			solvent = solvents[resID]
		
		if solvent:
			for root in solvent:
				assignCategory(model, root, "solvent")
		if solvent != smallSolvents:
			for root in smallSolvents:
				assignCategory(model, root, "solvent")
			for root in solvent:
				rootDict.remove(root)
			
		# assign ions
		ions = []
		for root in rootDict:
			if root.size.numAtoms == 1:
				element = root.atom.element
				if element.number > 1 and element not in nobleGases:
					ions.append(root)
		
		# possibly expand to remainder of residue (coordination complex)
		#
		# this check is expensive for all-atoms-in-one-residue "molecules",
		# so skip unless there are bonds
		if model.numBonds > 0:
			checkedResidues = set()
			for root in ions[:]:
				if root.size.numAtoms == root.residue.numAtoms:
					continue
				if root.residue in checkedResidues:
					continue
				checkedResidues.add(root.residue)
				seenRoots = set([root])
				for a in root.residue.atoms:
					rt = model.rootForAtom(a, True)
					if rt in seenRoots:
						continue
					seenRoots.add(rt)
				# add segments of less than 5 heavy atoms
				for rt in seenRoots:
					if rt in ions:
						continue
					if len([a for a in model.traverseAtoms(rt)
							if a.element.number > 1]) < 5:
						ions.append(rt)
		for root in ions:
			rootDict.remove(root)
			assignCategory(model, root, "ions")
		
		if len(rootDict) == 0:
			continue

		# assign ligand

		# find longest chain
		longest = None
		for root in rootDict:
			if not longest \
			or root.size.numAtoms > longest.size.numAtoms:
				longest = root
		
		from chimera import atomsBonds2Residues
		ligands = []
		ligandCutoff = min(longest.size.numAtoms/4, 250)
		for root in rootDict:
			if root.size.numAtoms < ligandCutoff:
				# fewer than 10 residues?
				if len(atomsBonds2Residues(model.traverseAtoms(root), [])) < 10:
					# ensure that it isn't part of a longer chain,
					# some of which is missing...
					longChain = True
					try:
						seq = model.sequence(root.residue.id.chainId)
					except (KeyError, AssertionError):
						longChain = False
					else:
						if len(seq.residues) < 10:
							longChain = False
					if not longChain:
						ligands.append(root)
		
		for root in ligands:
			rootDict.remove(root)
			assignCategory(model, root, "ligand")
			
		# remainder in "main" category
		for root in rootDict:
			assignCategory(model, root, "main")
			# try to reclassify bound ligands as ligand
			atoms = model.traverseAtoms(root)
			rootResidues = atomsBonds2Residues(atoms, [])
			rootChainIDs = set([r.id.chainId for r in rootResidues])
			seqResidues = set()
			for rcid in rootChainIDs:
				try:
					seq = model.sequence(rcid)
				except (KeyError, AssertionError):
					continue
				seqResidues.update([r for r in seq.residues if r])
			if not seqResidues:
				continue
			bound = rootResidues - seqResidues
			for br in bound:
				for a in br.atoms:
					if a.surfaceCategory == "main":
						a.surfaceCategory = "ligand"

	if trigger == OpenModels.ADDMODEL:
		return len(atomOnlyModels) == len(data)
	return True

from _molecule import assignCategory

# make these available as selectors
from chimera.selection.manager import selMgr
selectorTemplate = """\
sel.merge(selection.REPLACE, selection.OSLSelection("@/surfaceCategory=%s"))
sel.addImplied(vertices=0)
"""
for cat in categories:
	selMgr.addSelector("surface categorizer", [selMgr.STRUCTURE,
		cat], selectorTemplate % cat)
selMgr.makeCallbacks()
