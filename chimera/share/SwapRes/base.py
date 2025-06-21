# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: base.py 42146 2020-05-28 16:17:55Z pett $

from math import pi, cos, sin
import chimera
from chimera import angle, dihedral, cross, Coord
from chimera.molEdit import addAtom, addDihedralAtom, addBond
from chimera.idatm import tetrahedral, planar, linear, single, typeInfo
from chimera.bondGeom import bondPositions
from chimera.match import matchPositions

class SwapResError(ValueError):
	pass
class BackboneError(SwapResError):
	pass
class TemplateError(SwapResError):
	pass

def swap(res, newRes, preserve=False, bfactor=True):
	"""change 'res' into type 'newRes'"""

	fixed, buds, start, end = getResInfo(res)
	
	if newRes == "HIS":
		newRes = "HIP"
	if newRes in ["A", "C", "G", "T"] and res.type in ["DA", "DC", "DT", "DG"]:
		newRes = "D" + newRes
	tmplRes = chimera.restmplFindResidue(newRes, start, end)
	if not tmplRes:
		raise TemplateError("No connectivity template for residue '%s'" % newRes)
	# sanity check:  does the template have the bud atoms?
	for bud in buds:
		if not tmplRes.atomsMap.has_key(bud):
			raise TemplateError("New residue type (%s) not compatible with"
				" starting residue type (%s)" % (newRes, res.type))
		
	# if bfactor not specified, find highest bfactor in molecule
	# and use that for swapped-in atoms
	if bfactor is False:
		bfactor = None
	if bfactor is True:
		for a in res.molecule.atoms:
			try:
				if bfactor is True or a.bfactor > bfactor:
					bfactor = a.bfactor
			except AttributeError:
				pass

	if preserve:
		if "CA" in fixed and newRes not in ['GLY', 'ALA']:
			raise SwapResError(
				"'preserve' keyword not yet implemented for amino acids")
		atomsMap = res.atomsMap
		try:
			a1 = atomsMap["O4'"][0]
			a2 = atomsMap["C1'"][0]
		except KeyError:
			preservePos = None
		else:
			dihedNames = {
				"N9": ["C4", "C8"],
				"N1": ["C2", "C6"]
			}
			try:
				a3 = atomsMap["N9"][0]
				if a2 not in a3.bondsMap:
					raise KeyError()
				preservePos = a3.coord()
			except KeyError:
				try:
					a3 = atomsMap["N1"][0]
					if a2 not in a3.bondsMap:
						raise KeyError()
					preservePos = a3.coord()
				except KeyError:
					preservePos = None
		if preservePos:
			from chimera import dihedral
			p1, p2, p3 = [a.coord() for a in (a1, a2, a3)]
			preservedPos = False
			try:
				prevName, altName = dihedNames[a3.name]
				a4 = atomsMap[prevName][0]
				if a3 not in a4.bondsMap:
					raise KeyError()
				p4 = a4.coord()
				preserveDihed = dihedral(p1, p2, p3, p4)
			except KeyError:
				preserveDihed = None
		else:
			preserveDihed = None

	# prune non-backbone atoms
	for a in res.oslChildren():
		if a.name not in fixed:
			a.molecule.deleteAtom(a)

	# add new sidechain
	newAtoms = []
	xf = None
	while len(buds) > 0:
		bud = buds.pop()
		tmplBud = tmplRes.atomsMap[bud]
		resBud = res.atomsMap[bud][0]

		try:
			info = typeInfo[tmplBud.idatmType]
			geom = info.geometry
			subs = info.substituents
		except KeyError:
			print tmplBud.idatmType
			raise AssertionError, "Can't determine atom type" \
				" information for atom %s of residue %s" % (
				bud, res.oslIdent())

		# use coord() rather than xformCoord():  we want to set
		# the new atom's coord(), to which the proper xform will
		# then be applied
		for a, b in tmplBud.bondsMap.items():
			if a.element.number == 1:
				# don't add hydrogens
				continue
			if res.atomsMap.has_key(a.name):
				resBonder = res.atomsMap[a.name][0]
				if not resBud.bondsMap.has_key(resBonder):
					addBond(resBud, resBonder)
				continue

			newAtom = None
			numBonded = len(resBud.bonds)
			if numBonded >= subs:
				raise AssertionError, \
					"Too many atoms bonded to %s of" \
					" residue %s" % (bud, res.oslIdent())
			if numBonded == 0:
				raise AssertionError, \
					"Atom %s of residue %s has no" \
					" neighbors after pruning?!?" % (
					bud, res.oslIdent())
			# since fused ring systems may have distorted bond angles,
			# always use dihedral placement
			real1 = resBud.neighbors[0]
			kw = {}
			if preserve:
				if preservePos and not preservedPos:
					kw['pos'] = preservePos
					preservedPos = True
					preservedName = a.name
				elif preserveDihed is not None:
					prevName, altName = dihedNames[preservedName]
					if a.name == prevName:
						kw['dihed'] = preserveDihed
					elif a.name == altName:
						kw['dihed'] = preserveDihed + 180.0
			if not kw and xf is not None:
				kw['pos'] = xf.apply(a.coord())

			newAtom = formDihedral(resBud, real1, tmplRes, a, b, **kw)
			newAtom.drawMode = resBud.drawMode
			if bfactor is not None and bfactor is not True:
				newAtom.bfactor = bfactor
			newAtoms.append(newAtom)

			# TODO: need to iterate over coordSets
			for bonded in a.bondsMap.keys():
				if not res.atomsMap.has_key(bonded.name):
					continue
				addBond(newAtom, res.atomsMap[bonded.name][0])
			buds.append(newAtom.name)

		# once we've placed 3 side chain atoms, we use superpositioning to
		# place the remainder of the side chain, since dihedrals will
		# likely distort ring closures if 'preserve' is true
		if buds and not xf and len(newAtoms) >= 3:
			placedPositions = []
			tmplPositions = []
			for na in newAtoms:
				placedPositions.append(na.coord())
				tmplPositions.append(tmplRes.atomsMap[na.name].coord())
			import numpy
			xf = matchPositions(numpy.array(placedPositions),
				numpy.array(tmplPositions))[0]

	from BuildStructure import changeResidueType
	changeResidueType(res, newRes)

aminoInfo = (("N", "CA", "C", "O", "OXT"), ("CA", "C", ("O", "OXT")))
nucleicInfo = (("O1P", "OP1", "O2P", "OP2", "O3P", "OP3", "P", "O5'", "C5'",
	"C4'", "C3'", "O3'", "C2'", "O2'", "C1'", "O4'"), ("C1'", "O4'", "C4'"))
def getResInfo(res):
	"""return a list of the fixed atoms of the residue, a list of
	   the fixed atoms that non-fixed atoms attach to, and whether
	   this residue is the start and/or end of a chain"""
	
	errmsg =  "Cannot identify backbone of residue %s (%s)" % (
						res.oslIdent(), res.type)
	backbone = []
	if res.atomsMap.has_key("N"):
		# putative amino acid
		basicInfo = aminoInfo
		start = len(res.atomsMap["N"][0].bonds) != 2
		end = res.atomsMap.has_key("OXT")
	elif res.atomsMap.has_key("O3'"):
		# putative nucleic acid
		basicInfo = nucleicInfo
		start = not res.atomsMap.has_key("P")
		end = len(filter(lambda a: a.element.name == "P",
				res.atomsMap["O3'"][0].neighbors)) == 0
		if end and res.atomsMap.has_key("O2'"):
			end = len(filter(lambda a: a.element.name == "P",
				res.atomsMap["O2'"][0].neighbors)) == 0
	else:
		raise BackboneError(errmsg)
	fixed, bud = basicInfo

	# must have the bud atoms present, (and resolve O/OXT ambiguity)
	finalBud = []
	for atName in bud:
		if isinstance(atName, tuple):
			for ambig in atName:
				if res.atomsMap.has_key(ambig):
					finalBud.append(ambig)
					break
			else:
				raise BackboneError(errmsg)
			continue
		if res.atomsMap.has_key(atName):
			finalBud.append(atName)
		else:
			raise BackboneError(errmsg)
	return (list(fixed), finalBud, start, end)

def formDihedral(resBud, real1, tmplRes, a, b, pos=None, dihed=None):
	res = resBud.residue
	if pos:
		return addAtom(a.name, a.element, res, pos, infoFrom=real1)
	# use neighbors of resBud rather than real1 to avoid clashes with
	# other resBud neighbors in case bond to real1 neighbor freely rotates
	inres = [nb for nb in resBud.neighbors if nb != real1 and nb.residue == res]
	if len(inres) < 1:
		inres = [x for x in res.atoms if x not in [resBud, real1]]
	if real1.residue != res or len(inres) < 1:
		raise AssertionError, "Can't form in-residue dihedral for" \
				" %s of residue %s" % (resBud, res.oslIdent())
	if dihed:
		real1 = res.atomsMap["C1'"][0]
		real2 = res.atomsMap["O4'"][0]
	else:
		real2 = inres[0]
	xyz0, xyz1, xyz2 = map(lambda a, tr=tmplRes:
			tr.atomsMap[a.name].coord(), (resBud, real1, real2))

	xyz = a.coord()
	blen = b.length()
	ang = angle(xyz, xyz0, xyz1)
	if dihed is None:
		dihed = dihedral(xyz, xyz0, xyz1, xyz2)
	return addDihedralAtom(a.name, a.element, resBud,
						real1, real2, blen, ang, dihed, infoFrom=real1)
