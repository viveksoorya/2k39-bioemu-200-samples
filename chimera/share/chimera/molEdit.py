# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: molEdit.py 35667 2012-02-28 02:06:26Z pett $

from math import pi, cos, sin
from chimera import cross, Xform, Coord, Point, Atom, Bond

def addAtom(name, element, residue, loc, serialNumber=None, bondedTo=None,
							occupancy=None, infoFrom=None, altLoc=None):
	"""Add an atom at the Point 'loc'
	
	   The atom is added to the given residue (and its molecule).
	   'loc' can be a sequence of Points if there are multiple
	   coordinate sets.

	   If you are adding atoms in bulk, make sure that you provide the
	   optional 'serialNumber' argument, since the code that automatically
	   determines the serial number is slow.

	   'bondedTo' is None or an Atom.  If an Atom, then the new atom
	   inherits various attributes [display, altloc, style, occupancy]
	   from that atom and a bond to that Atom is created.

	   If 'infoFrom' is supplied then the information normally garnered
	   from the 'bondedTo' atom will be obtained from the 'infoFrom'
	   atom instead. Typically used when there is no 'bondedTo' atom.

	   If 'occupancy' is not None or the 'bondedTo' atom has an
	   occupancy, the new atom will be given the corresponding occupancy.

	   If 'altLoc' is not None, use the specified value for the altLoc,
	   regardless of other arguments.

	   Returns the new atom.
	"""

	if not infoFrom:
		infoFrom = bondedTo
	mol = residue.molecule
	newAtom = mol.newAtom(name, element)
	residue.addAtom(newAtom)
	if not mol.coordSets:
		if isinstance(loc, Point):
			mol.newCoordSet(1)
		else:
			for i in range(1, len(loc)+1):
				mol.newCoordSet(i)
		mol.activeCoordSet = mol.findCoordSet(1)
	for i, coordSet in enumerate(mol.coordSets.values()):
		if isinstance(loc, Point):
			newCoord = loc
		else:
			newCoord = loc[i]
		newAtom.setCoord(newCoord, coordSet)
	if serialNumber is None:
		try:
			serialNumber = max(
					[a.serialNumber for a in mol.atoms]) + 1
		except AttributeError:
			serialNumber = len(mol.atoms)
	newAtom.serialNumber = serialNumber
	if occupancy is not None or infoFrom and hasattr(infoFrom, 'occupancy'):
		newAtom.occupancy = getattr(infoFrom, 'occupancy', occupancy)
	if infoFrom:
		newAtom.altLoc = infoFrom.altLoc
		newAtom.display = infoFrom.display
		newAtom.surfaceDisplay = infoFrom.surfaceDisplay
		newAtom.drawMode = infoFrom.drawMode
	if altLoc:
		newAtom.altLoc = altLoc
	if bondedTo:
		addBond(newAtom, bondedTo)
	return newAtom

def addDihedralAtom(name, element, n1, n2, n3, dist, angle, dihed,
		molecule=None, residue=None, bonded=False, occupancy=None,
		infoFrom=None):
	"""Add an atom given 3 Atoms/Points and angle/distance constraints
	
	   The atom is added to the given molecule.  If no molecule or
	   residue is specified, then n1/n2/n3 must be Atoms and the new atom
	   is added to n1's molecule and residue.  If just residue is
	   specified, the new atom is added to that residue and its molecule.

	   'n1' marks the position from which 'dist' is measured, and in
	   combination with 'n2' forms 'angle', and then with 'n3' forms
	   'dihed'.

	   if 'bonded' is True then n1 must be an Atom and the new atom will
	   be bonded to it.

	   If 'occupancy' is not None or the 'bonded' is True and n1 has an
	   occupancy, the new atom will be given the corresponding occupancy.

	   if 'infoFrom' is supplied (needs to be an Atom), miscellaneous
	   info (see addAtom() doc string) will be obtained from that atom.

	   Returns the new atom.
	"""

	if bonded:
		bondedTo = n1
	else:
		bondedTo = None
	if n1.__class__ is Atom:
		if not residue:
			molecule = n1.molecule
			residue = n1.residue
		n1 = n1.coord()
		n2 = n2.coord()
		n3 = n3.coord()
	if not molecule:
		molecule = residue.molecule
	
	finalPt = findPt(n1, n2, n3, dist, angle, dihed)

	return addAtom(name, element, residue, finalPt, bondedTo=bondedTo,
							occupancy=occupancy)

def addBond(a1, a2, drawMode=None, halfbond=None, color=None):
	if a1.bonds:
		sampleBond = a1.bonds[0]
	elif a2.bonds:
		sampleBond = a2.bonds[0]
	else:
		sampleBond = None
	if drawMode is None:
		if sampleBond:
			drawMode = sampleBond.drawMode
		elif a1.drawMode == Atom.Dot:
			drawMode = Bond.Wire
		else:
			drawMode = Bond.Stick
	if halfbond is None:
		if sampleBond:
			halfbond = sampleBond.halfbond
		else:
			halfbond = True
	try:
		b = a1.molecule.newBond(a1, a2)
	except TypeError, v:
		if str(v).startswith("Attempt to form duplicate covalent bond"
					) or str(v).startswith("Cannot form"
					" covalent bond joining two molecules"):
			from chimera import UserError
			raise UserError(v)
		else:
			raise
	b.drawMode = drawMode
	b.halfbond = halfbond
	if not halfbond:
		if color is None:
			if sampleBond:
				color = sampleBond.color
			else:
				color = a1.color
		b.color = color
	if a1.residue == a2.residue:
		return b

	# this is a cross-residue bond, may need to reorder residues
	isStart = []
	isEnd = []
	from chimera import bondsBetween
	allResidues = a1.molecule.residues
	# order the two residues based on sequence number/insertion code,
	# so that the most "natural" reordering occurs if possible
	r1, r2 = a1.residue, a2.residue
	if r1.id < r2.id:
		residues = (r1, r2)
	else:
		residues = (r2, r1)
	indices = [allResidues.index(r) for r in residues]
	if indices[0] + 1 == indices[1] or indices[1]+1 == indices[0]:
		# already adjacent
		return b
	for i, r in zip(indices, residues):
		isStart.append(i == 0 or not bondsBetween(r,
							allResidues[i-1], onlyOne=True))
		isEnd.append(i == len(allResidues)-1 or not bondsBetween(r,
							allResidues[i+1], onlyOne=True))
	if isEnd[0] and isStart[1]:
		if indices[0] < indices[1]:
			# move rear residues forward, closing gap
			closeGap, i1, i2 = True, indices[0], indices[1]
		else:
			# move forward residues back, across rear residues
			closeGap, i1, i2 = False, indices[1], indices[0]
	elif isStart[0] and isEnd[1]:
		if indices[0] < indices[1]:
			# move forward residues back, across rear residues
			closeGap, i1, i2 = False, indices[0], indices[1]
		else:
			# move rear residues forward, closing gap
			closeGap, i1, i2 = True, indices[1], indices[0]
	else:
		return b
	def findEnd(pos, dir=1):
		def test(pos):
			if dir == 1:
				return pos < len(allResidues) - 1
			return pos > 0
		while test(pos):
			if bondsBetween(allResidues[pos],
					allResidues[pos+dir], onlyOne=True):
				pos += dir
			else:
				break
		return pos
	if closeGap:
		endRange = findEnd(i2)
		newResidues = allResidues[0:i1+1] + allResidues[i2:endRange+1] \
			+ allResidues[i1+1:i2] + allResidues[endRange+1:]
	else:
		er1 = findEnd(i1)
		er2 = findEnd(i2, dir=-1)
		newResidues = allResidues[0:i1] + allResidues[er1+1:i2+1] \
			+ allResidues[i1:er1+1] + allResidues[i2+1:]
	a1.molecule.reorderResidues(newResidues)
	return b

def findPt(n1, n2, n3, dist, angle, dihed):
	# cribbed from Midas addgrp command
	v12 = n2 - n1
	v13 = n3 - n1
	v12.normalize()
	x = cross(v13, v12)
	x.normalize()
	y = cross(v12, x)
	y.normalize()

	mat = [0.0] * 12
	for i in range(3):
		mat[i*4] = x[i]
		mat[1 + i*4] = y[i]
		mat[2 + i*4] = v12[i]
		mat[3 + i*4] = n1[i]
	
	xform = Xform.xform(*mat)

	radAngle = pi * angle / 180.0
	tmp = dist * sin(radAngle)
	radDihed = pi * dihed / 180.0
	pt = Point(tmp*sin(radDihed), tmp*cos(radDihed), dist*cos(radAngle))
	return xform.apply(pt)

def genAtomName(element, residue):
	"""generate non-hydrogen atom name"""
	n = 1
	while True:
		name = "%s%d" % (str(element).upper(), n)
		if name not in residue.atomsMap:
			break
		n += 1
	return name
