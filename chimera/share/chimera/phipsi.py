class AtomsMissingError(ValueError):
	pass

def getPhi(res, missingIsError=False):
	try:
		prevC, n, ca, c = phiAtoms(res)
	except AtomsMissingError:
		if missingIsError:
			raise
		return None
	from chimera import dihedral
	return dihedral(prevC.coord(), n.coord(), ca.coord(), c.coord())

def getPsi(res, missingIsError=False):
	try:
		n, ca, c, nextN = psiAtoms(res)
	except AtomsMissingError:
		if missingIsError:
			raise
		return None
	from chimera import dihedral
	return dihedral(n.coord(), ca.coord(), c.coord(), nextN.coord())

def getChi1(res, missingIsError=False):
	return getChi(res, 1, missingIsError=missingIsError)

def getChi2(res, missingIsError=False):
	return getChi(res, 2, missingIsError=missingIsError)

def getChi3(res, missingIsError=False):
	return getChi(res, 3, missingIsError=missingIsError)

def getChi4(res, missingIsError=False):
	return getChi(res, 4, missingIsError=missingIsError)

chiSymInfo = set([('PHE', 2), ('TYR', 2), ('ASP', 2), ('GLU', 3)])

def getChi(res, chiNum, missingIsError=False, accountForSymmetry=False):
	try:
		atoms = chiAtoms(res, chiNum)
	except AtomsMissingError:
		if missingIsError:
			raise
		return None
	from chimera import dihedral
	chi = dihedral(*tuple([a.coord() for a in atoms]))
	if accountForSymmetry:
		# 'standardize' modified residue types registered
		# through MODRES records
		from resCode import protein3to1, protein1to3
		resType = protein1to3[protein3to1[res.type]]
		if (resType, chiNum) in chiSymInfo:
			while chi > 90.0:
				chi -= 180.0
			while chi <= -90.0:
				chi += 180.0
	return chi

def phiAtoms(res):
	try:
		n = res.atomsMap['N'][0]
		ca = res.atomsMap['CA'][0]
		c = res.atomsMap['C'][0]
	except KeyError:
		raise AtomsMissingError("Missing backbone atom")
	for nb in n.neighbors:
		if nb.residue == res:
			continue
		if nb.name == 'C':
			prevC = nb
			break
	else:
		raise AtomsMissingError("No C in previous residue")
	return prevC, n, ca, c

def psiAtoms(res):
	try:
		n = res.atomsMap['N'][0]
		ca = res.atomsMap['CA'][0]
		c = res.atomsMap['C'][0]
	except KeyError:
		raise AtomsMissingError("Missing backbone atom")
	for nb in c.neighbors:
		if nb.residue == res:
			continue
		if nb.name == 'N':
			nextN = nb
			break
	else:
		raise AtomsMissingError("No N in next residue")
	return n, ca, c, nextN

def chiAtoms(res, chiNum):
	from Rotamers.data import chiInfo
	from resCode import protein3to1, protein1to3
	try:
		# 'standardize' modified residue types registered
		# through MODRES records
		resType = protein1to3[protein3to1[res.type]]
		atomNames = chiInfo[resType][chiNum-1]
		atoms = [res.atomsMap[an][0] for an in atomNames]
	except (KeyError, IndexError):
		raise AtomsMissingError("Missing backbone atom")
	return atoms

def setPhi(res, phi, anchorSide=None):
	"""'anchorSide' is the atom whose side shouldn't move.  If None, the bigger side is anchored"""
	try:
		n, ca = res.atomsMap['N'][0], res.atomsMap['CA'][0]
		bond = n.bondsMap[ca]
		_setAngle(bond, phi, getPhi(res, missingIsError=True), "phi", anchorSide)
	except (KeyError, AtomsMissingError):
		# to allow inspectors to work
		return

def setPsi(res, psi, anchorSide=None):
	"""'anchorSide' is the atom whose side shouldn't move.  If None, the bigger side is anchored"""
	try:
		ca, c = res.atomsMap['CA'][0], res.atomsMap['C'][0]
		bond = ca.bondsMap[c]
		_setAngle(bond, psi, getPsi(res, missingIsError=True), "psi", anchorSide)
	except (KeyError, AtomsMissingError):
		# to allow inspectors to work
		return

def setChi1(res, chi, anchorSide=None):
	"""'anchorSide' is the atom whose side shouldn't move.  If None, the bigger side is anchored"""
	setChi(res, chi, 1, anchorSide=anchorSide)

def setChi2(res, chi, anchorSide=None):
	"""'anchorSide' is the atom whose side shouldn't move.  If None, the bigger side is anchored"""
	setChi(res, chi, 2, anchorSide=anchorSide)

def setChi3(res, chi, anchorSide=None):
	"""'anchorSide' is the atom whose side shouldn't move.  If None, the bigger side is anchored"""
	setChi(res, chi, 3, anchorSide=anchorSide)

def setChi4(res, chi, anchorSide=None):
	"""'anchorSide' is the atom whose side shouldn't move.  If None, the bigger side is anchored"""
	setChi(res, chi, 4, anchorSide=anchorSide)

def setChi(res, chi, chiNum, anchorSide=None):
	"""'anchorSide' is the atom whose side shouldn't move.  If None, the bigger side is anchored"""
	try:
		a1, a2, a3, a4 = chiAtoms(res, chiNum)
		bond = a2.bondsMap[a3]
		_setAngle(bond, chi, getChi(res, chiNum, missingIsError=True), "chi" + str(chiNum),
			anchorSide)
	except (KeyError, AtomsMissingError):
		# to allow inspectors to work
		return

def _setAngle(bond, newAngle, curAngle, attrName, anchorSide):
	from BondRotMgr import bondRotMgr
	br = bondRotMgr.rotationForBond(bond, create=False)
	if br:
		br.increment(newAngle - curAngle)
	else:
		from chimera import BondRot
		br = BondRot(bond)
		anchor = anchorSide if anchorSide is not None else br.biggerSide()
		br.angle = (newAngle - curAngle, anchor)
		br.destroy()
	res = bond.atoms[0].residue
	from chimera import TrackChanges
	track = TrackChanges.get()
	track.addModified(res, attrName + " changed")
