# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42426 2023-02-23 19:51:29Z pett $

import chimera
from chimera import Point, Element

def setBondLength(bond, bondLength, movingSide="smaller side", status=None):
	bond.molecule.idatmValid = False
	try:
		br = chimera.BondRot(bond)
	except ValueError, v:
		if "already used" in str(v):
			if status:
				status("Cannot change length of active"
					" bond rotation\nDeactivate rotation"
					" and try again", color="red")
			return
		if "cycle" not in str(v):
			raise
		if status:
			status("Bond involved in ring/cycle\n"
				"Moved bonded atoms (only) equally",
				color="blue")
		mid = Point([a.coord() for a in bond.atoms])
		for a in bond.atoms:
			v = a.coord() - mid
			v.length = bondLength/2
			a.setCoord(mid+v)
		return
	if movingSide == "smaller side":
		fixed = br.biggerSide()
		moving = bond.otherAtom(fixed)
	else:
		moving = br.biggerSide()
		fixed = bond.otherAtom(moving)
	mp = moving.coord()
	fp = fixed.coord()
	v1 = mp - fp
	v1.length = bondLength
	delta = v1 - (mp - fp)
	moved = set()
	toMove = [moving]
	while toMove:
		mover = toMove.pop()
		if mover in moved:
			continue
		moved.add(mover)
		mover.setCoord(mover.coord() + delta)
		for neighbor, nb in mover.bondsMap.items():
			if nb == bond:
				continue
			toMove.append(neighbor)
	br.destroy()

def placeHelium(resName, model="scratch", position=None):
	"""place a new helium atom

	   'resName' is the name of the new residue that will contain the
	   helium.  (It will be in the 'het' chain.)

	   'model' can either be a chimera.Molecule instance or a string.
	   If the latter, then a new model is created with the string as
	   its .name attribute.

	   'position' can either be a chimera.Point or None.  If None, then
	   the helium is positioned at the center of the view.
	"""

	if isinstance(model, basestring):
		model = _newModel(model)

	r = _newResidue(model, resName)
	if position is None:
		xf = model.openState.xform
		position = xf.inverse().apply(
				Point(*chimera.viewer.camera.center))
	from chimera.molEdit import addAtom
	return addAtom('He1', Element('He'), r, position)

def placeFragment(fragment, resName, model="scratch", position=None):
	"""place a Fragment (see Fragment.py)

	   'resName' is the name of the new residue that will contain the
	   fragment.  (It will be in the 'het' chain.)

	   'model' can either be a chimera.Molecule instance or a string.
	   If the latter, then a new model is created with the string as
	   its .name attribute.

	   'position' can either be a chimera.Point or None.  If None, then
	   the fragment is positioned at the center of the view.
	"""

	if isinstance(model, basestring):
		model = _newModel(model)
	r = _newResidue(model, resName)
	needFocus = False
	if position is None:
		if len(chimera.openModels.list()) == 1:
			needFocus = True
		xf = model.openState.xform
		position = xf.inverse().apply(
				Point(*chimera.viewer.camera.center))
	# find fragment center
	x = y = z = 0.0
	for element, xyz in fragment.atoms:
		x += xyz[0]
		y += xyz[1]
		z += xyz[2]
	numAtoms = len(fragment.atoms)
	fragCenter = Point(x / numAtoms, y / numAtoms, z / numAtoms)
	correction = position - fragCenter

	from chimera.molEdit import addAtom, genAtomName
	atoms = []
	for element, xyz in fragment.atoms:
		atoms.append(addAtom(genAtomName(element, r), Element(element),
						r, Point(*xyz) + correction))
	for indices, depict in fragment.bonds:
		r.molecule.newBond(atoms[indices[0]], atoms[indices[1]])
	if needFocus:
		chimera.runCommand("focus")
	return r

class NucleotideError(ValueError):
	pass
def placeNucleotide(sequence, form, type="dna", model="scratch", position=None,
			chainID='A'):
	"""place a nucletide sequence (and it complementary chain)

	   'sequence' contains the sequence of the first chain

	   'form' is the (upper case) form (e.g. A); the supported forms are
	   listed in the nuc-data subdirectory

	   If type is "dna", then both strands are DNA.  If "rna", then both are RNA.
	   If "hybrid", then the first is DNA (and the sequence should be a DNA
	   sequence) and the second RNA.

	   'model' and 'position' are treated the same as in the placePeptide
	   function

	   The first chain will be given the 'chainID' chain ID.  The complementary
	   chain will be given the next letter/number in sequence.
	"""

	if not sequence:
		raise NucleotideError("No sequence supplied")
	sequence = sequence.upper()
	type = type.lower()
	if type == "rna":
		alphabet = "ACGU"
	else:
		alphabet = "ACGT"
	for let in sequence:
		if let not in alphabet:
			raise NucleotideError("Sequence letter %s illegal for %s" %
				(let, "RNA" if type == "rna" else "DNA"))
	if type == "rna":
		# treat U as T for awhile...
		sequence = sequence.replace('U', 'T')
	if isinstance(model, basestring):
		model = _newModel(model)
	needFocus = False
	if position is None:
		if len(chimera.openModels.list()) == 1:
			needFocus = True
		xf = model.openState.xform
		position = xf.inverse().apply(
				Point(*chimera.viewer.camera.center))
	import os
	head, tail = os.path.split(__file__)
	nucDataDir = os.path.join(head, "nuc-data")
	xformFile = os.path.join(nucDataDir, form + ".xform")
	if not os.path.exists(xformFile):
		raise NucleotideError(form + "-form RNA/DNA not supported")

	xformValues = []
	f = open(xformFile, "r")
	for line in f:
		line = line.strip()
		if not line:
			continue
		xformValues.extend([float(x) for x in line.split()])
	xform = chimera.Xform.xform(*xformValues, orthogonalize=True)
	f.close()

	chainID2 = chr(ord(chainID)+1)
	if not chainID2.isalnum():
		if chainID == '9':
			chainID2 = 'A'
		elif chainID == 'Z':
			chainID2 = 'a'
		else:
			chainID2 = '0'

	# build nucleotide
	from chimera.molEdit import addAtom
	serialNumber = None
	residues1 = []
	residues2 = []
	curXform = chimera.Xform()
	seqNum1 = seqNum2 = 1
	complement = { 'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A' }
	coordCache = {}
	# find consecutive streach of residue numbers long enough to
	# accomodate each chain (so that we can easily reverse the
	# second chain's numbers)
	startSeqNums = []
	for cid in [chainID, chainID2]:
		start = 1
		while True:
			for i in range(len(sequence)):
				if model.findResidue(chimera.MolResId(cid, start + i)):
					start += 1
					break
			else:
				startSeqNums.append(start)
				break
	# get bond info
	try:
		f = open(os.path.join(nucDataDir, "bonds"), "r")
	except IOError:
		raise AssertionError("Cannot read nucleic acid bonding info")
	bonds = []
	for line in f:
		fields = line.strip().split()
		if len(fields) < 3:
			fields.append(None)
		bonds.append(fields)
	f.close()

	prevResidues = model.residues
	for i, let in enumerate(sequence):
		if let not in coordCache:
			coordFile = os.path.join(nucDataDir,
				"%s-%s%s.coords" % (form, let, complement[let]))
			try:
				f = open(coordFile, "r")
			except IOError:
				raise AssertionError("Cannot read nucleic template coordinates"
					" for residue type %s of %s-form DNA/RNA" % (let, form))
			coordCache[let] = coords = {}
			for line in f:
				strand, atName, x, y, z = line.strip().split()
				strand = int(strand)
				x = float(x)
				y = float(y)
				z = float(z)
				coords[(strand, atName)] = Point(x, y, z)
			f.close()
		else:
			coords = coordCache[let]
		type1 = let
		type2 = complement[let]
		if type != "rna":
			type1 = 'D' + type1
		if type == "dna":
			type2 = 'D' + type2
		#TODO
		r1 = model.newResidue(type1, chainID, startSeqNums[0]+i, ' ')
		r2 = model.newResidue(type2, chainID2, startSeqNums[1]+len(sequence)-i-1, ' ')
		residues1.append(r1)
		residues2.append(r2)
		for atInfo, crd in coords.items():
			strand, atName = atInfo
			if strand == 0:
				residue = r1
			else:
				residue = r2
			a = addAtom(atName, Element(atName[0]), residue, curXform.apply(crd),
				serialNumber=serialNumber)
			serialNumber = a.serialNumber + 1
		for b1, b2, restriction in bonds:
			for r in (r1, r2):
				if restriction and r.type[-1] not in restriction:
					continue
				if b1 in r.atomsMap and b2 in r.atomsMap:
					model.newBond(r.atomsMap[b1][0], r.atomsMap[b2][0])
		if len(residues1) > 1:
			for resList, a1, a2 in [(residues1, "O3'", "P"), (residues2, "P", "O3'")]:
				r1, r2 = resList[-2:]
				model.newBond(r1.atomsMap[a1][0], r2.atomsMap[a2][0])
		curXform.multiply(xform)
	model.reorderResidues(prevResidues + residues1 + list(reversed(residues2)))

	# strip dangling phosphorus
	for res in [residues1[0], residues2[-1]]:
		for aname in ["P", "OP1", "OP2"]:
			model.deleteAtom(res.atomsMap[aname][0])

	# if RNA: modify sugar ring, swap U for T (including changing res type)
	if type != "dna":
		if type == "rna":
			residues = residues1 + residues2
		else:
			residues = residues2
		from chimera.bondGeom import bondPositions, tetrahedral, planar
		from chimera.molEdit import addAtom
		oxygen = Element("O")
		for res in residues:
			c1p = res.atomsMap["C1'"][0]
			c2p = res.atomsMap["C2'"][0]
			c3p = res.atomsMap["C3'"][0]
			o3p = res.atomsMap["O3'"][0]
			positions = bondPositions(c2p.coord(), tetrahedral,  1.43,
				[c1p.coord(), c3p.coord()])
			# want the position nearer the O3'
			angle = chimera.angle(positions[0] - c2p.coord(),
				o3p.coord() - c3p.coord())
			if angle < 90.0:
				pos = positions[0]
			else:
				pos = positions[1]
			a = addAtom("O2'", oxygen, res, pos, serialNumber=serialNumber,
				bondedTo=c2p)
			serialNumber = a.serialNumber + 1

		for res in residues:
			if res.type != "T":
				continue
			model.deleteAtom(res.atomsMap["C7"][0])
			res.type = "U"

	if needFocus:
		chimera.runCommand("focus")
	return residues1 + residues2


class PeptideError(ValueError):
	pass
def placePeptide(sequence, phiPsis, model="scratch", position=None,
						rotlib=None, chainID='A'):
	"""place a peptide sequence

	   'sequence' contains the sequence

	   'phiPsis' is a list of phi/psi tuples, one per residue

	   'model' can either be a chimera.Molecule instance or a string.
	   If the latter, then a new model is created with the string as
	   its .name attribute.

	   'position' can either be a chimera.Point or None.  If None, then
	   the fragment is positioned at the center of the view.
	"""

	if not sequence:
		raise PeptideError("No sequence supplied")
	sequence = sequence.upper()
	if not sequence.isupper():
		raise PeptideError("Sequence contains non-alphabetic characters")
	from chimera.resCode import protein1to3
	for c in sequence:
		if c not in protein1to3:
			raise PeptideError("Unrecognized protein 1-letter code:"
								" %s" % c)
	if len(sequence) != len(phiPsis):
		raise PeptideError("Number of phi/psis not equal to"
							" sequence length")
	if isinstance(model, basestring):
		model = _newModel(model)
	needFocus = False
	if position is None:
		if len(chimera.openModels.list()) == 1:
			needFocus = True
		xf = model.openState.xform
		position = xf.inverse().apply(
				Point(*chimera.viewer.camera.center))
	prev = [None] * 3
	pos = 1
	from Midas.addAA import DIST_N_C, DIST_CA_N, DIST_C_CA, DIST_C_O
	from chimera.molEdit import findPt, addAtom, addDihedralAtom
	serialNumber = None
	residues = []
	prevPsi = 0
	for c, phiPsi in zip(sequence, phiPsis):
		phi, psi = phiPsi
		while model.findResidue(chimera.MolResId(chainID, pos)):
			pos += 1
		r = model.newResidue(protein1to3[c], chainID, pos, ' ')
		residues.append(r)
		for backbone, dist, angle, dihed in (
				('N', DIST_N_C, 116.6, prevPsi),
				('CA', DIST_CA_N, 121.9, 180.0),
				('C', DIST_C_CA, 110.1, phi)):
			if prev[0] == None:
				pt = Point(0.0, 0.0, 0.0)
			elif prev[1] == None:
				pt = Point(dist, 0.0, 0.0)
			elif prev[2] == None:
				pt = findPt(prev[0].coord(), prev[1].coord(),
					Point(0.0, 1.0, 0.0), dist, angle, 0.0)
			else:
				pt = findPt(prev[0].coord(), prev[1].coord(),
					prev[2].coord(), dist, angle, dihed)
			a = addAtom(backbone, Element(backbone[0]), r, pt,
				serialNumber=serialNumber, bondedTo=prev[0])
			serialNumber = a.serialNumber + 1
			prev = [a] + prev[:2]
		o = addDihedralAtom("O", Element("O"), prev[0], prev[1],
			prev[2], DIST_C_O, 120.4, 180.0 + psi, bonded=True)
		prevPsi = psi
	# C terminus O/OXT at different angle than mainchain O
	model.deleteAtom(o)
	addDihedralAtom("O", Element("O"), prev[0], prev[1],
			prev[2], DIST_C_O, 117.0, 180.0 + psi, bonded=True)
	addDihedralAtom("OXT", Element("O"), prev[0], prev[1], prev[2],
					DIST_C_O, 117.0, psi, bonded=True)
	from Rotamers import useBestRotamers
	# have to process one by one, otherwise side-chain clashes will occur
	kw = {}
	if rotlib:
		kw['lib'] = rotlib
	for r in residues:
		useBestRotamers("same", [r], criteria="cp", log=False, **kw)
				
	# find peptide center
	coords = []
	for r in residues:
		coords.extend([a.coord() for a in r.atoms])
	center = Point(coords)
	correction = position - center
	for r in residues:
		for a in r.atoms:
			a.setCoord(a.coord() + correction)
	from Midas import ksdssp
	ksdssp([model])
	if needFocus:
		chimera.runCommand("focus")
	return residues

from chimera import elements
elementRadius = {}
for i in range(len(chimera.elements.name)):
	element = Element(i)
	elementRadius[element] = 0.985 * Element.bondRadius(element)
elementRadius[elements.C] = 0.7622
elementRadius[elements.H] = 0.1869
elementRadius[elements.N] = 0.6854
elementRadius[elements.O] = 0.6454
elementRadius[elements.P] = 0.9527
elementRadius[elements.S] = 1.0428

class ParamError(ValueError):
	pass

def bondLength(a1, geom, e2, a2info=None):
	if e2.number == 1:
		from AddH import bondWithHLength
		return bondWithHLength(a1, geom)
	e1 = a1.element
	baseLen = elementRadius[e1] + elementRadius[e2]
	if geom == 1:
		return baseLen
	neighbor, numBonds = a2info
	try:
		ngeom = chimera.idatm.typeInfo[neighbor.idatmType].geometry
	except KeyError:
		return baseLen
	if ngeom == 1:
		return baseLen
	if numBonds == 1 or len(neighbor.primaryBonds()) == 1:
		# putative double bond
		return 0.88 * baseLen
	elif geom == 4 or ngeom == 4:
		return baseLen
	return 0.92 * baseLen

def changeAtom(atom, element, geometry, numBonds, autoClose=True, name=None):
	if len(atom.primaryBonds()) > numBonds:
		raise ParamError("Atom already has more bonds than requested.\n"
			"Either delete some bonds or choose a different number"
			" of requested bonds.")
	from chimera.molEdit import addAtom, addBond, genAtomName
	changedAtoms = [atom]
	if not name:
		name = genAtomName(element, atom.residue)
	changeAtomName(atom, name)
	atom.element = element
	if hasattr(atom, 'mol2type'):
		delattr(atom, 'mol2type')
		
	# if we only have one bond, correct its length
	if len(atom.primaryBonds()) == 1:
		neighbor = atom.primaryNeighbors()[0]
		newLength = bondLength(atom, geometry, neighbor.element,
						a2info=(neighbor, numBonds))
		setBondLength(atom.primaryBonds()[0], newLength,
					movingSide="smaller side")

	if numBonds == len(atom.primaryBonds()):
		return changedAtoms

	from chimera.bondGeom import bondPositions
	coPlanar = None
	if geometry == 3 and len(atom.primaryBonds()) == 1:
		n = atom.primaryNeighbors()[0]
		if len(n.primaryBonds()) == 3:
			coPlanar = [nn.coord() for nn in n.primaryNeighbors()
								if nn != atom]
	away = None
	if geometry == 4 and len(atom.primaryBonds()) == 1:
		n = atom.primaryNeighbors()[0]
		if len(n.primaryBonds()) > 1:
			nn = n.primaryNeighbors()[0]
			if nn == atom:
				nn = n.primaryNeighbors()[1]
			away = nn.coord()
	hydrogen = Element("H")
	positions = bondPositions(atom.coord(), geometry,
		bondLength(atom, geometry, hydrogen),
		[n.coord() for n in atom.primaryNeighbors()], coPlanar=coPlanar,
		away=away)[:numBonds-len(atom.primaryBonds())]
	if autoClose:
		if len(atom.molecule.atoms) < 100:
			testAtoms = atom.molecule.atoms
		else:
			from CGLutil.AdaptiveTree import AdaptiveTree
			tree = AdaptiveTree([a.coord().data()
						for a in atom.molecule.atoms],
						a.molecule.atoms, 2.5)
			testAtoms = tree.searchTree(atom.coord().data(), 5.0)
	else:
		testAtoms = []
	hnum = 1
	for pos in positions:
		for ta in testAtoms:
			if ta == atom:
				continue
			testLen = bondLength(ta, 1, hydrogen)
			testLen2 = testLen * testLen
			if (ta.coord() - pos).sqlength() < testLen2:
				bonder = ta
				# possibly knock off a hydrogen to
				# accomodate the bond...
				for bn in bonder.primaryNeighbors():
					if bn.element.number > 1:
						continue
					if chimera.angle(atom.coord()
							- ta.coord(), bn.coord()
							- ta.coord()) > 45.0:
						continue
					if bn in testAtoms:
						testAtoms.remove(bn)
					atom.molecule.deleteAtom(bn)
					break
				addBond(atom, bonder)
				break
		else:
			bondedHs = [h for h in atom.neighbors if h.element.number == 1]
			if bondedHs:
				if len(bondedHs) == 1:
					bondedName = bondedHs[0].name
					if bondedName[-1].isdigit():
						nameBase = bondedName[:-1]
					else:
						nameBase = "H%s" % atom.name
				else:
					useDefault = False
					from os.path import commonprefix
					nameBase = commonprefix([h.name for h in bondedHs])
					if not nameBase:
						useDefault = True
					else:
						for h in bondedHs:
							if not h.name[len(nameBase)+1:].isdigit():
								useDefault = True
								break
					if useDefault:
						nameBase = "H%s" % atom.name
				n = 1
				while True:
					name = nameBase + str(n)
					if name not in [h.name for h in bondedHs]:
						hname = name
						break
					n += 1
			else:
				hname = None
				if len(positions) == 1:
					possName = "H" + atom.name[1:]
					if possName not in atom.residue.atomsMap:
						hname = possName
				if hname == None and len(atom.name) < 4:
					for n in range(hnum, len(positions)+1):
						possName = "H%s%d" % (atom.name[1:], n)
						if possName in atom.residue.atomsMap:
							break
					else:
						hname = "H%s%d" % (atom.name[1:], hnum)
				if hname == None:
					hname = genAtomName(hydrogen, atom.residue)
			bonder = addAtom(hname, hydrogen, atom.residue,
							pos, bondedTo=atom)
			changedAtoms.append(bonder)
			hnum += 1
	return changedAtoms

def changeAtomName(atom, name):
	if replaceableLabel(atom.name, atom.label):
		atom.label = atom.label.replace(atom.name, name, 1)
	atom.name = name

def changeResidueType(res, name):
	if replaceableLabel(res.type, res.label):
		res.label = res.label.replace(res.type, name, 1)
	res.type = name
	from chimera.resCode import origStandard3to1
	res.isHet = name not in origStandard3to1

def replaceableLabel(oldName, label):
	stripped = label.strip()
	if stripped == oldName or (stripped.startswith(oldName)
							and not stripped[len(oldName)].isalpha()):
		return True
	return False

def bind(a1, a2, length, dihedInfo, preAddCB=None):
	"""Make bond between two models.

	   The models will be combined and the originals closed.
	   The new model will be opened in the same id/subid as the
	       non-moving model.

	   a1/a2 are atoms in different models, each bonded to exactly
	       one other atom.  In the final structure, a1/a2 will be
		   eliminated and their bond partners will be bonded together.
	   a2 and atoms in its model will be moved to form the bond.
		'length' is the bond length.
		'dihedInfo' is a two-tuple of sequence of four atoms and
			a dihedral angle that the four atoms should form.
		dihedInfo can be None if insufficient atoms
	   if 'preAddCB' is specified, it will be called before the
	     new model is added to chimera.openModels.  It will be
		 called with two arguments, the atoms in the new model
		 that correspond to the atoms bonded to a1 and a2 in the
		 old models.
	"""

	if a1.molecule == a2.molecule:
		raise ValueError("Atoms must be in different models")

	try:
		b1, b2 = a1.neighbors + a2.neighbors
		if b1.molecule == b2.molecule:
			raise ValueError()
	except ValueError:
		raise AssertionError("Atoms must be bonded to exactly one atom")

	# move b2 to a1's position
	from chimera import Xform, cross, angle, Point, dihedral
	mv = a1.xformCoord() - b2.xformCoord()
	openState = b2.molecule.openState
	openState.globalXform(Xform.translation(mv))

	# rotate to get b1-a1 colinear with b2-a2
	curAng = angle(b1.xformCoord(), a1.xformCoord(), a2.xformCoord())
	rotAxis = cross(b1.xformCoord() - b2.xformCoord(),
					a2.xformCoord() - a1.xformCoord())
	toOrigin = Point() - b2.xformCoord()
	if rotAxis.sqlength() > 0.0:
		openState.globalXform(Xform.translation(toOrigin))
		openState.globalXform(Xform.rotation(rotAxis, -curAng))
		openState.globalXform(Xform.translation(-toOrigin))

	# then get the distance correct
	dv = b1.xformCoord() - b2.xformCoord()
	dv.length = dv.length - length
	openState.globalXform(Xform.translation(dv))

	# then dihedral
	if dihedInfo:
		atoms, dihedVal = dihedInfo
		p1, p2, p3, p4 = [a.xformCoord() for a in atoms]
		if atoms[2].molecule != a2.molecule:
			p1, p2, p3, p4 = p4, p3, p2, p1
		axis = p3 - p2
		if axis.sqlength() > 0.0:
			curDihed = dihedral(p1, p2, p3, p4)
			delta = dihedVal - curDihed
			v2 = p3 - Point(0.0, 0.0, 0.0)
			trans1 = Xform.translation(v2)
			v2.negate()
			trans2 = Xform.translation(v2)
			trans1.multiply(Xform.rotation(axis, delta))
			trans1.multiply(trans2)
			openState.globalXform(trans1)

	# delete a1/a2
	a1.molecule.deleteAtom(a1)
	a2.molecule.deleteAtom(a2)

	# combine
	from Combine import combine
	atomMap, copyMol = combine([b1.molecule, b2.molecule], b1.molecule,
								returnMapping=True)
	copyMol.name = b1.molecule.name

	# prep a1/a2 chain IDs for upcoming bond
	c1, c2 = atomMap[b1], atomMap[b2]
	chain1 = c1.residue.id.chainId
	chain2 = c2.residue.id.chainId
	if chain1 == chain2:
		# just renumbering required
		keep, change = c1, c2
	else:
		if chain2 == "het":
			keep, change = c1, c2
		elif chain1 == "het" or chain1 == " ":
			keep, change = c2, c1
		else:
			keep, change = c1, c2
	_adjustChainInfo(keep, change)
			
	# bond b1/b2
	from chimera.molEdit import addBond
	b = addBond(c1, c2)
	from chimera.Sequence import invalidate
	invalidate(copyMol)

	if preAddCB:
		preAddCB(c1, c2)

	# close original models; open combined
	from chimera import openModels
	# We need to close the source models after adding the combined
	# model, since we use the first source model to position
	# the combination, but as the combination gets opened it's
	# metal-complex pseudobond group gets renamed to correspond to
	# the combination name, which is the same as the first source
	# model.  This causes havoc when the source models get closed
	# as that group is then listed in the combination's associated models
	# but not by the pseudobond manager!  So close the first model's
	# associated models before doing any of that.
	if b1.molecule.associatedModels():
		openModels.close(b1.molecule.associatedModels())
	openModels.add([copyMol], noprefs=True, sameAs=b1.molecule)
	openModels.close([b1.molecule, b2.molecule])

def cnPeptideBond(c, n, moving, length, dihedral, phi=None):
	"""Make bond between C-terminal carbon in one model and N-terminal
	   nitrogen in another.

	   'c' is the carbon and 'n' is the nitrogen.  'moving' should either
	   be c or n again, depending on which model you want moved.

	   If you want a particular value for the newly-established phi
	   angle, provide the 'phi' parameter.
	"""
	from chimera.bondGeom import bondPositions
	from chimera.molEdit import addAtom

	# process C terminus
	if c.element.name != "C":
		raise AssertionError('C-terminal "carbon" is a %s!' % c.element.name)
	# Cterm: find CA
	pn = c.primaryNeighbors()
	if len(pn) > 3:
		raise AssertionError("More than 3 atoms connected to C-terminal"
					" carbon [%s]" % c)
	pnElements = [a.element.name for a in pn]
	if pnElements.count("C") != 1:
		raise AssertionError("C-terminal carbon not bonded to exactly one"
			" carbon")
	cca = pn[pnElements.index("C")]
	# Cterm: find OXT or equivalent
	added = False
	oxys = [a for a in pn if a.element.name == "O"]
	if len(oxys) == 0:
		if len(pn) > 1:
			raise AssertionError("C-terminal carbon bonded to no oxygens"
				" yet bonded to %d other atoms" % len(pn))
		pos = bondPositions(c.coord(), 3, 1.0, [cca.coord()])[0]
		ac = addAtom("TMP", c.element, c.residue, pos, serialNumber=0,
			bondedTo=c)
		added = True
	elif len(oxys) == 1:
		if len([o for o in oxys if o.name == "OXT"]) == 1:
			ac = oxys[0]
		else:
			if len(pn) == 2:
				pos = bondPositions(c.coord(), 3, 1.0,
						[cca.coord(), oxys[0].coord()])[0]
				ac = addAtom("TMP", c.element, c.residue, pos, serialNumber=0,
					bondedTo=c)
				added = True
			elif len(pn) == 3:
				ac = [a for a in pn if a not in (c, oxys[0])][0]
				if len(ac.neighbors) > 1:
					raise AssertionError("Unexpected branching atom (%s)"
						" connected to C-terminal carbon" % ac)
	else:
		oxts = [o for o in oxys if o.name == "OXT"]
		if len(oxts) == 1:
			ac = oxts[0]
		else:
			ac = oxys[0]

	# process N terminus
	if n.element.name != "N":
		if added:
			ac.molecule.deleteAtom(ac)
		raise AssertionError('N-terminal "nitrogen" is a %s!' % n.element.name)
	# Nterm: find CA
	pn = n.primaryNeighbors()
	pnElements = [a.element.name for a in pn]
	ncs = [nb for i, nb in enumerate(pn) if pnElements[i] == "C"]
	if len(ncs) == 1:
		nca = ncs[0]
	else:
		if n.residue.type in ["PRO", "HYP"]:
			if pnElements.count("C") != 2:
				raise AssertionError("Proline N-terminal nitrogen not bonded to exactly two"
					" carbons")
			ncas = [nc for nc in ncs if nc.name == "CA"]
			if len(ncas) == 1:
				nca = ncas[0]
			else:
				raise AssertionError("Not exactly one CA bonded to N-terminal nitrogen")
		else:
			raise AssertionError("Non-proline N-terminal nitrogen not bonded to exactly one"
				" carbon")
	# Nterm: clean the N
	for nb in pn:
		if nb not in ncs and len(nb.neighbors) > 1:
			if added:
				ac.molecule.deleteAtom(ac)
			raise AssertionError("Unexpected branching atom [%s] attached"
				" to N terminus" % nb)
	hyds = [a for a in pn if a.element.name == "H"]
	hs = [h for h in hyds if h.name == "H"]
	if hs:
		h = hs[0]
	else:
		h = None
	for nb in pn:
		if nb not in [n, h] + ncs:
			nb.molecule.deleteAtom(nb)
	coords = [nc.coord() for nc in ncs]
	if h:
		coords.append(h.coord())
	pos = bondPositions(n.coord(), 3, 1.0, coords)[0]
	an = addAtom("TMP", n.element, n.residue, pos, serialNumber=0,
		bondedTo=n)

	# call bind
	if moving == c:
		a1, a2 = an, ac
	else:
		a1, a2 = ac, an
	dihedInfo = ([cca, c, n, nca], dihedral)
	cn = []
	def cb(b1, b2, hyds=hyds, cn=cn):
		if b1.element.name == "C":
			c, n = b1, b2
		else:
			c, n = b2, b1
		c.idatmType = "Cac"
		n.idatmType = "Npl"
		pn = c.primaryNeighbors()
		if len(pn) < 3:
			pos = bondPositions(c.coord(), 3, 1.23, [a.coord() for a in pn])[0]
			addAtom("O", Element("O"), c.residue, pos, bondedTo=c)
		pn = n.primaryNeighbors()
		if hyds and len(pn) < 3:
			pos = bondPositions(n.coord(), 3, 1.01, [a.coord() for a in pn])[0]
			addAtom("H", Element("H"), n.residue, pos, bondedTo=n)
		cn.append(c)
		cn.append(n)

	bind(a1, a2, length, dihedInfo, preAddCB=cb)
	if phi is not None:
		# need to do some special footwork to make sure correct side doesn't
		# move as the phi angle is set (can't just res.phi = val)
		res = cn[1].residue
		if moving == c:
			# anchor is the Ca
			anchor = res.atomsMap['CA'][0]
		else:
			# anchor is the N
			anchor = cn[1]
		from chimera.phipsi import setPhi
		setPhi(res, phi, anchorSide=anchor)
	return cn

def _adjustChainInfo(keep, change):
	"""Adjust residues in 'change' atom's chain to have same chain ID
	   and no numbering conflicts with residues in 'keep' atom's chain
	   so that they can be bonded
	"""
	mol = keep.molecule
	kID = keep.residue.id.chainId
	kRoot = mol.rootForAtom(keep, True)
	kResidues = set([a.residue for a in mol.traverseAtoms(kRoot)])
	kResNums = [r.id.position for r in kResidues]
	klow, khigh = min(kResNums), max(kResNums)

	cRoot = mol.rootForAtom(change, True)
	cResidues = set([a.residue for a in mol.traverseAtoms(cRoot)])
	cResNums = [r.id.position for r in cResidues]
	clow, chigh = min(cResNums), max(cResNums)
	if clow > khigh or chigh < klow:
		offset = 0
		after = clow > khigh
	else:
		if khigh > klow and keep.residue.id.position == klow:
			offset = klow - 1 - chigh
			after = False
		else:
			offset = khigh + 1 - clow
			after = True
	keepers = [r for r in mol.residues if r not in cResidues]
	movers = [r for r in mol.residues if r in cResidues]
	if after:
		keepers.reverse()
		for i, r in enumerate(keepers):
			if r in kResidues:
				break
		keepers.reverse()
		index = len(keepers) - i
		newOrder = keepers[:index] + movers + keepers[index:]
	else:
		for i, r in enumerate(keepers):
			if r in kResidues:
				break
		newOrder = keepers[:i] + movers + keepers[i:]
	mol.reorderResidues(newOrder)
	if change.residue.id.chainId == kID and offset == 0:
		return
	from chimera import MolResId
	for r in cResidues:
		newID = MolResId(kID, r.id.position + offset, insert=r.id.insertionCode)
		r.id = newID

class InvertChiralityError(ValueError):
	pass

def invertChirality(center, swapees=(None, None)):
	from BondRotMgr import bondRotMgr
	mol = center.molecule
	if not swapees[0]:
		candidates = []
		for bondee, b in center.bondsMap.items():
			br = bondRotMgr.rotationForBond(b, create=False)
			if br:
				size = mol.rootForAtom(bondee, False).size.numAtoms
			else:
				try:
					br = chimera.BondRot(b)
				except (chimera.error, ValueError):
					# presumbly part of ring
					continue
				size = mol.rootForAtom(bondee, False).size.numAtoms
				br.destroy()
			candidates.append((size, bondee.element.number, bondee))
		# implicit hydrogens...
		from chimera.idatm import typeInfo
		if center.idatmType in typeInfo:
			from chimera.bondGeom import bondPositions
			hPositions = bondPositions(center.coord(), typeInfo[center.idatmType]
				.geometry, 1.0, [nb.coord() for nb in center.neighbors])
			candidates.extend([(1, 1, hp) for hp in hPositions])
		if len(candidates) < 2:
			raise InvertChiralityError("%s doesn't have at least 2 non-ring"
				" substituents to swap!" % center)
		candidates.sort()
		swapees = [c[-1] for c in candidates[:2]]
	else:
		for swapee in swapees:
			if not isinstance(swapee, chimera.Atom):
				continue
			try:
				b = center.bondsMap[swapee]
			except KeyError:
				raise InvertChiralityError("Atom to invert (%s) is not bonded to"
					" center (%s)!" % (swapee, center))
			if b.minimumRings(True):
				raise InvertChiralityError("Cannot invert chirality because %s and"
					" %s are in same ring/cycle" % (center, swapee))

	atomSets = []
	coords = []
	for swapee in swapees:
		atomSet = set()
		atomSets.append(atomSet)
		if isinstance(swapee, chimera.Atom):
			coords.append(swapee.coord())
		else:
			coords.append(swapee)
			continue
		b = center.bondsMap[swapee]
		br = bondRotMgr.rotationForBond(b, create=False)
		if br:
			atomSet.update(mol.traverseAtoms(mol.rootForAtom(swapee, False)))
		else:
			br = chimera.BondRot(b)
			atomSet.update(mol.traverseAtoms(mol.rootForAtom(swapee, False)))
			br.destroy()
		_expandAtomSet(bondRotMgr.rotations.values(), atomSet)

	p1, p2, p3 = center.coord(), coords[0], coords[1]
	angle = chimera.angle(p2, p1, p3)
	cv = chimera.cross(p2-p1, p3-p1)
	rot1 = chimera.Xform.rotation(cv, angle)
	rot2 = chimera.Xform.rotation(cv, -angle)
	xyz = [c for c in p1.data()]
	trans1 = chimera.Xform.translation(*[0-c for c in xyz])
	trans2 = chimera.Xform.translation(*xyz)
	for atoms, rot in [(atomSets[0], rot1), (atomSets[1], rot2)]:
		for a in atoms:
			a.setCoord(trans2.apply(rot.apply(trans1.apply(a.coord()))))

def cmdInvertShim(atoms):
	from Midas import MidasError
	if len(atoms) == 1:
		try:
			invertChirality(atoms[0])
		except InvertChiralityError, v:
			raise MidasError(unicode(v))
	elif len(atoms) == 2:
		commonNeighbors = set(atoms[0].neighbors) & set(atoms[1].neighbors)
		if len(commonNeighbors) == 1:
			try:
				invertChirality(commonNeighbors.pop(), swapees=atoms)
			except InvertChiralityError, v:
				raise MidasError(unicode(v))
		elif commonNeighbors:
			raise MidasError("%s and %s have more than one neighbor atom in common!"
				% (atoms[0], atoms[1]))
		else:
			raise MidasError("%s and %s have no neighbor atoms in common!"
				% (atoms[0], atoms[1]))
	else:
		raise MidasError("'invert' atom spec should be 1 or 2 atoms (not %d)"
			% len(atoms))

class BondsNotAdjacentError(ValueError):
	pass
def smallerBranch(bonds):
	""" can be inaccurate if there are other active bond rotations """
	try:
		junction = (set(bonds[0].atoms) & set(bonds[1].atoms)).pop()
	except KeyError, v:
		raise BondsNotAdjacentError("bonds are not adjacent")
	if bonds[0].molecule.findBondRot(bonds[0]):
		destroy0 = False
	else:
		try:
			br0 = chimera.BondRot(bonds[0])
		except ValueError, v:
			if "cycle" in unicode(v):
				return bonds[1]
			raise
		destroy0 = True
	if bonds[1].molecule.findBondRot(bonds[1]):
		destroy1 = False
	else:
		try:
			br1 = chimera.BondRot(bonds[1])
		except ValueError, v:
			if "cycle" in unicode(v):
				if destroy0:
					br0.destroy()
				return bonds[0]
			raise
		destroy1 = True
	other0 = bonds[0].otherAtom(junction)
	other1 = bonds[1].otherAtom(junction)
	size0 = other0.molecule.rootForAtom(other0, False).size.numAtoms
	size1 = other1.molecule.rootForAtom(other1, False).size.numAtoms
	if destroy0:
		br0.destroy()
	if destroy1:
		br1.destroy()
	return bonds[0] if size0 < size1 else bonds[1]

class BondInCycleError(ValueError):
	pass
_bondAngleCache = {}
def setBondAngle(moving, fixed, degrees):
	if moving.minimumRings(crossResidues=True):
		raise BondInCycleError("bond in cycle")
	try:
		junction = (set(moving.atoms) & set(fixed.atoms)).pop()
	except KeyError, v:
		raise BondsNotAdjacentError("bonds are not adjacent")

	key = (id(moving), id(fixed))
	prevAxis, prevVal = _bondAngleCache.get(key, (None, None))
	mv = moving.otherAtom(junction).coord() - junction.coord()
	fv = fixed.otherAtom(junction).coord() - junction.coord()
	# due to numeric roundoff, a bond angle previously set to 180
	# degrees won't be exactly at 180, so axis.normalize() will
	# "succeed", so we need another kind of test for this 
	# degenerate condition
	mv.normalize()
	fv.normalize()
	if (mv + fv).sqlength() < 0.0001 or (mv - fv).sqlength() < 0.0001:
		if prevAxis:
			axis = prevAxis
		else:
			crossAxis = chimera.Vector(1, 0, 0)
			# use a different arbitrary vector if the bonds lie on the X axis...
			if (crossAxis + mv).sqlength() < 0.0001 or (crossAxis - mv).sqlength() < 0.0001:
				crossAxis = chimera.Vector(0, 0, 1)
			axis = chimera.cross(crossAxis, mv)
			axis.normalize()
	else:
		axis = chimera.cross(fv, mv)
		axis.normalize()
	if prevAxis:
		if (axis - prevAxis).sqlength() > 0.0001:
			# cross product flips direction at 180 degrees...
			if (axis + prevAxis).sqlength() > 0.0001:
				prevAxis, prevVal = None, None
			else:
				axis = prevAxis

	if prevVal:
		amount = degrees - prevVal
	else:
		amount = degrees - chimera.angle(fv, mv)

	# gather atoms to rotate
	todo = [moving.otherAtom(junction)]
	targets = set([junction])
	while todo:
		a = todo.pop(0)
		targets.add(a)
		for nb in a.neighbors:
			if nb not in targets:
				todo.append(nb)
	targets.remove(junction)

	# rotate them
	toOrigin = Point() - junction.coord()
	xf = chimera.Xform.translation(-toOrigin)
	xf.rotate(axis, amount)
	xf.translate(toOrigin)
	for a in targets:
		a.setCoord(xf.apply(a.coord()))

	_bondAngleCache[key] = (axis, degrees)

def _expandAtomSet(brs, atomSet):
	for br in brs:
		a1, a2 = br.atoms
		if a1 in atomSet and a2 not in atomSet:
			outA = a2
		elif a2 in atomSet and a1 not in atomSet:
			outA = a1
		else:
			continue
		atomSet.update(outA.molecule.traverseAtoms(
					outA.molecule.rootForAtom(outA, False)))
		_expandAtomSet(brs, atomSet)
		break
	return atomSet

def _newModel(name):
	m = chimera.Molecule()
	m.name = name
	chimera.openModels.add([m])
	return m

def _newResidue(model, name):
	# find an number unused in both the 'het' and 'water' chains...
	pos = 1
	while model.findResidue(chimera.MolResId('het', pos)) \
	or model.findResidue(chimera.MolResId('water', pos)):
		pos += 1
	res = model.newResidue(name, 'het', pos, ' ')
	res.isHet = True
	return res
