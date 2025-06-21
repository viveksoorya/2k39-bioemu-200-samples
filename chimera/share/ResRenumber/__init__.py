# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

from Midas import MidasError
class ResRenumberError(MidasError):
	pass

def renumberResidues(start, residues):
	byChain = {}
	for r in residues:
		byChain.setdefault((r.molecule, r.id.chainId), []).append(r)
	staticResidues = {}
	sortedResidues = {}
	resOrder = {}
	for key, changed in byChain.items():
		mol, chainID = key
		if mol in staticResidues:
			static = staticResidues[mol]
		else:
			staticResidues[mol] = static = set([r for r in mol.residues])
			resOrder[mol] = dict(zip(mol.residues, range(len(mol.residues))))
		# put in same order as mol.residues...
		changed.sort(lambda r1, r2, ro=resOrder[mol]: cmp(ro[r1], ro[r2]))
		static.difference_update(changed)
	from chimera import MolResId
	staticIDs = {}
	renumberedIDs = {}
	for key, changed in byChain.items():
		mol, chainID = key
		if mol in staticIDs:
			static = staticIDs[mol]
		else:
			staticIDs[mol] = static = set([r.id for r in staticResidues[mol]])
		renumbered = renumberedIDs[key] = [MolResId(r.id.chainId, start+i)
					for i, r in enumerate(changed)]
		dups = static & set(renumbered)
		if dups:
			numDups = len(dups)
			raise ResRenumberError("Renumbering not done; would produce %d duplicate"
				" number(s) with other residues in the same chain (e.g. %s %s).  "
				"Please specify a renumbering that does not give duplicates."
				% (numDups, mol, dups.pop()))

	from chimera import replyobj
	for key, changed in byChain.items():
		chainStr = changed[0].id.chainId
		if len(changed) < 2:
			plural = ""
			preNumStr = "%d" % changed[0].id.position
		else:
			plural = "s"
			ranges = []
			index = start = 0
			while start < len(changed):
				if index == len(changed) - 1 or \
				changed[index+1].id.position - changed[index].id.position > 1:
					if index == start:
						ranges.append("%d" % changed[start].id.position)
					else:
						ranges.append("%d-%d" % (changed[start].id.position,
							changed[index].id.position))
					index += 1
					start = index
					continue
				index += 1
			preNumStr = ",".join(ranges)
		for newID, res in zip(renumberedIDs[key], changed):
			res.id = newID
		if len(changed) < 2:
			postNumStr = "%d" % changed[0].id.position
		else:
			postNumStr = "%d-%d" % (changed[0].id.position, changed[-1].id.position)
		replyobj.info("Residue%s %s in chain %s renumbered as %s\n" % (plural,
			preNumStr, chainStr, postNumStr))
