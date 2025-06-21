# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 26655 2009-01-07 22:02:30Z gregc $

def readGro(fileName):
	from OpenSave import osOpen
	from chimera import UserError, Molecule, Element, openModels, replyobj
	from chimera import Coord, connectMolecule
	state = "init"
	f = osOpen(fileName)
	anums = {}
	m = None
	for line in f:
		line = line.rstrip()
		if line.startswith("#"):
			continue
		if state == "init":
			state = "post line 1"
			m = Molecule()
			if ", t=" in line:
				m.name = line[:line.index(", t=")]
			else:
				m.name = line
			continue
		if state == "post line 1":
			state = "atoms"
			numAtoms = int(line.strip())
			curResNum = None
			continue
		if not line: continue

		try:
			resNum = int(line[:5].strip())
			resName = line[5:10].strip()
			atomName = line[10:15].strip()
			atomNum = int(line[15:20].strip())
			x = float(line[20:28].strip()) * 10.0
			y = float(line[28:36].strip()) * 10.0
			z = float(line[36:44].strip()) * 10.0
		except ValueError:
			raise UserError("Atom line of gro file %s does not conform to"
				" format\nLine: '%s'" % (fileName, line))
		if curResNum != resNum:
			r = m.newResidue(resName, " ", resNum, " ")
			curResNum = resNum
		if atomName[0].upper() in "COPSHN" or len(atomName) == 1:
			element = Element(atomName[0].upper())
		else:
			from chimera import elements
			twoLetter = atomName[0].upper() + atomName[1].lower()
			if twoLetter in elements.name:
				element = Element(twoLetter)
			else:
				element = Element(atomName[0].upper())
		if element.number == 0:
			raise UserError("Cannot guess atomic element from atom name in file"
				" %s\nLine: %s" % (fileName, line))
		anum = anums.get(element.name, 0) + 1
		anums[element.name] = anum
		a = m.newAtom(atomName, element)
		r.addAtom(a)
		a.setCoord(Coord(x, y, z))
		a.serialNumber = atomNum
		if len(m.atoms) == numAtoms:
			break
	f.close()
	if m is None:
		raise UserError("'%s' has no non-comment lines!" % fileName)
	connectMolecule(m)
	return [m]
