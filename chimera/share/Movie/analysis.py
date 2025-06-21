# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: analysis.py 38983 2013-08-02 00:00:24Z pett $

from chimera import selection, elements

class AnalysisError(ValueError):
	pass

def analysisAtoms(mol, useSel, ignoreBulk, ignoreHyds, metalIons, polymericOnly=False):
	""" 'metalIons' has priority over 'polymericOnly' and 'ignoreBulk'"""
	if useSel:
		selAtoms = selection.currentAtoms()
		if selAtoms:
			# reduce to just ours
			sel1 = selection.ItemizedSelection()
			sel1.add(selAtoms)
			sel2 = selection.ItemizedSelection()
			sel2.add(mol.atoms)
			sel1.merge(selection.INTERSECT, sel2)
			atoms = sel1.atoms()
			if not atoms:
				raise AnalysisError("No selected atoms in"
							" trajectory!")
		else:
			atoms = mol.atoms
	else:
		atoms = mol.atoms

	metals = [a for a in atoms if a.element in elements.metals and not a.bonds]

	if ignoreBulk:
		bulkSel = selection.OSLSelection("@/surfaceCategory="
				"solvent or surfaceCategory=ions")
		atomSel = selection.ItemizedSelection()
		atomSel.add(atoms)
		atomSel.remove(metals)
		atomSel.merge(selection.REMOVE, bulkSel)
		atoms = atomSel.atoms()
		if not atoms:
			raise AnalysisError("No atoms remaining after ignoring"
							" solvent/ions")
	if ignoreHyds:
		atoms = [a for a in atoms if a.element.number != 1]
		if not atoms:
			raise AnalysisError("No atoms remaining after ignoring hydrogens")

	if polymericOnly:
		atoms = [a for a in atoms
			if len(a.residue.atoms) < mol.rootForAtom(a, True).size.numAtoms]
		atoms += metals
		if not atoms:
			raise AnalysisError("No atoms remaining after eliminating non-polymers")

	if metalIons == False:
		metalSet = set(metals)
		atoms = [a for a in atoms if a not in metalSet]
	elif metalIons == "non-alkali":
		alkaliSet = set([a for a in metals if a.element in elements.alkaliMetals])
		atoms = [a for a in atoms if a not in alkaliSet]

	return atoms
