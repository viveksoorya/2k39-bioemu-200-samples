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
class ChainChangeError(MidasError):
	pass

def changeChains(mols, chainSwaps, limitTo=None):
	fromChains, toChains = zip(*chainSwaps)
	change = dict(chainSwaps)
	revChange = {}
	for k, v in change.items():
		revChange.setdefault(v, []).append(k)
	for mol in mols:
		molChains = set([r.id.chainId for r in mol.residues])
		molChains.difference(fromChains)
		molChains.intersection(toChains)
		if limitTo:
			residues = [r for r in limitTo.residues if r]
		else:
			residues = mol.residues
		for checkChain in molChains:
			orig = set([(r.id.position, r.id.insertionCode) for r in residues
					if r.id.chainId == checkChain and r.id.chainId not in change])
			new = set([(r.id.position, r.id.insertionCode) for r in residues
					if checkChain in revChange
					and r.id.chainId in revChange[checkChain]])
			dups = orig & new
			if dups:
				for r in residues:
					if r.id.chainId == checkChain and (
					r.id.position, r.id.insertionCode) in dups:
						break
				raise ChainChangeError("Chain changes not done; changing chain %s to"
					" %s in %s would produce residues with identical IDs (e.g. %s)"
					% ("/".join(revChange[checkChain]), checkChain, mol, r.id))
		for k, v in revChange.items():
			if len(v) < 2:
				continue
			redone = {}
			for r in residues:
				if r.id.chainId in v:
					after = (r.id.position, r.id.insertionCode)
					if after in redone:
						r1, r2 = redone[after], r
						raise ChainChangeError("Chain changes not done; changing"
							" chains %s and %s to %s in %s would produce residues"
							" with identical IDs (e.g. %s and %s become identical)"
							% (r1.id.chainId, r2.id.chainId, k, mol, r1, r2))
					redone[after] = r

	from chimera import MolResId, Sequence, replyobj
	for mol in mols:
		if limitTo:
			residues = [r for r in limitTo.residues if r]
		else:
			residues = mol.residues
		mol.lowerCaseChains = False
		for r in residues:
			if r.id.chainId in change:
				r.id = MolResId(change[r.id.chainId],
						r.id.position, insert=r.id.insertionCode)
			if r.id.chainId.islower():
				mol.lowerCaseChains = True
		replyobj.info("Chains %s in %s changed to %s\n" % (",".join(fromChains),
			mol, ",".join(toChains)))
		Sequence.invalidate(mol)
