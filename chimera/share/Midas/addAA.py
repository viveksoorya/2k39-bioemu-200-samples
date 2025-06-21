import chimera
from chimera import replyobj
from chimera.molEdit import addBond
from chimera.molEdit import addDihedralAtom
from chimera.molEdit import addAtom
from chimera.bondGeom import bondPositions

DIST_N_C = 1.335
DIST_CA_N = 1.449
DIST_C_CA = 1.522
DIST_C_O = 1.229

class AddAAError(Exception):
	"""Error while adding amino acid"""
	pass

def terminicity(res):
	nt = True
	n_at = getBboneAtom(res, 'N')
	if not n_at:
		raise AddAAError("%s is missing backbone N" % res)
	res_id = res.id.position
	for at in n_at.neighbors:
		if at.residue.id.position != res_id:
			nt = False
			break
	ct = True
	c_at = getBboneAtom(res, 'C')
	if not c_at:
		raise AddAAError("%s is missing backbone C" % res)
	res_id = res.id.position
	for at in c_at.neighbors:
		if at.residue.id.position != res_id:
			ct = False
			break
	return nt, ct

def cleanUp(mol, new_res, atoms):
	for a in atoms:
		mol.deleteAtom(a)
	mol.deleteResidue(new_res)

def getBFactor(mol):
	bfactor = None
	for a in mol.atoms:
		try:
			if bfactor is None or a.bfactor > bfactor:
				bfactor = a.bfactor
		except AttributeError:
			pass

	return bfactor

def getBboneAtom(res, atom_name):
	"""find atom of type 'atom' in residue 'res' with
	the highest occupancy value"""

	if not res.atomsMap.has_key(atom_name):
		return None

	match_ats  = res.atomsMap[atom_name]
	match_ats.sort(lambda x,y: cmp(x.occupancy,y.occupancy))
	return match_ats[0]

def pruneCtResidue(last_C):
	to_prune = [a for a in last_C.neighbors
				if a.name not in ['CA', 'O']]
	if len(last_C.neighbors) - len(to_prune) > 2:
		if len([a for a in last_C.neighbors if a.name == 'O']) > 1:
			raise AddAAError("Multiple atoms named 'O' connected to"
				" C terminus; one needs to be named 'OXT'")
		raise AddAAError("Cannot determine what atom to prune from"
			" 'C' of preceding residue")
	if not to_prune:
		# nothing there to take off
		return
	elif len(to_prune) > 1:
		# don't recognize configuration of 'C's bond partners
		raise AddAAError("No suitable position to add new amino acid")
	else:
		to_prune = to_prune[0]

	if to_prune.neighbors != [last_C]:
		raise AddAAError("No suitable position to add new amino acid")

	last_C.molecule.deleteAtom(to_prune)

def pruneNtResidue(last_N):
	to_prune = [a for a in last_N.neighbors if a.name != 'CA']
	if len(last_N.neighbors) - len(to_prune) > 1:
		raise AddAAError("Multiple atoms named 'CA' bonded to "
			" 'N' of %s" % last_N.residue)
	for prune in to_prune:
		last_N.molecule.deleteAtom(prune)

def reposLastO(last_res, end_bbone_ats):
	# reposition the last residue's 'O' atom
	last_O = getBboneAtom(last_res, 'O')
	bFac = getattr(last_O, 'bfactor', None)
	last_res.molecule.deleteAtom(last_O)

	last_C  = end_bbone_ats['C']
	last_CA = end_bbone_ats['CA']

	old_O_bond_pos = bondPositions(bondee=last_C.coord(),
		geom=chimera.Atom.Planar, bondLen=1.229,
		bonded=[a.coord() for a in last_C.neighbors])

	# should only be one spot left
	old_O_bond_pos = old_O_bond_pos[0]
	new_O = addAtom('O', chimera.Element(8), last_res, old_O_bond_pos,
		bondedTo=last_C)
	if bFac is not None:
		new_O.bfactor = bFac

	return new_O

def addCtN(end_bbone_ats, new_res, bfactor):
	# add the N atom of new residue's backbone to the last residue
	last_C = end_bbone_ats['C']

	new_N_bond_pos = bondPositions(bondee=last_C.coord(),
		geom=chimera.Atom.Planar, bondLen=DIST_N_C,
		bonded=[a.coord() for a in last_C.neighbors])

	use_point = new_N_bond_pos[0]
	new_N = addAtom('N', chimera.Element(7), new_res, use_point,
		bondedTo=last_C)
	new_N.bfactor = bfactor

	return new_N

def addCtCA(end_bbone_ats, new_res, bfactor):
	last_CA = end_bbone_ats['CA']
	last_C  = end_bbone_ats['C']
	last_O  = end_bbone_ats['O']

	new_N = new_res.atomsMap['N'][0]

	# add the CA atom (not dihedral!)
	# first, find the location for the new CA atom
	new_CA_bond_pos = bondPositions(bondee=new_N.coord(),
		geom=chimera.Atom.Planar, bondLen=DIST_CA_N,
		bonded=[a.coord() for a in new_N.neighbors],
		coPlanar=[last_CA.coord(), last_O.coord()])

	shortest_point = getShortestPoint(last_O.coord(), new_CA_bond_pos)

	new_CA = addAtom('CA', chimera.Element(6), new_res, shortest_point,
		bondedTo=new_N)
	new_CA.bfactor = bfactor

	return new_CA

def addCtC(end_bbone_ats, new_res, phi, bfactor):
	last_C = end_bbone_ats['C']

	new_CA = new_res.atomsMap['CA'][0]
	new_N = new_res.atomsMap['N'][0]

	new_C = addDihedralAtom('C', chimera.Element(6), new_CA, new_N, last_C,
		DIST_C_CA, 109.5, phi, residue=new_res, bonded=True)
	new_C.bfactor = bfactor

	return new_C

def addCtOs(new_res, psi, bfactor):
	new_N  = new_res.atomsMap['N'][0]
	new_CA = new_res.atomsMap['CA'][0]
	new_C  = new_res.atomsMap['C'][0]

	new_OXT = addDihedralAtom('OXT', chimera.Element(8), new_C, new_CA, new_N,
						DIST_C_O, 114, psi, residue=new_res, bonded=True)
	new_OXT.bfactor	= bfactor

	avail_bond_pos = bondPositions(bondee=new_C.coord(),
		geom=chimera.Atom.Planar, bondLen=DIST_C_O,
		bonded=[a.coord() for a in new_C.neighbors])

	use_point = avail_bond_pos[0]

	new_O = addAtom('O', chimera.Element(8), new_res, use_point, bondedTo=new_C)
	new_O.bfactor = bfactor

	return new_O, new_OXT

def addNtC(end_bbone_ats, new_res, phi, bfactor):
	# add the C atom of new residue's backbone to the last residue
	last_N = end_bbone_ats['N']
	last_CA = end_bbone_ats['CA']
	last_C = end_bbone_ats['C']

	new_C = addDihedralAtom('C', chimera.Element(6), last_N, last_CA, last_C,
		DIST_N_C, 109.5, phi, residue=new_res, bonded=True)
	new_C.bfactor = bfactor

	return new_C

def addNtCA(end_bbone_ats, new_res, bfactor):
	last_CA = end_bbone_ats['CA']
	last_N  = end_bbone_ats['N']

	new_C = new_res.atomsMap['C'][0]

	new_CA = addDihedralAtom('CA', chimera.Element(6), new_C, last_N, last_CA,
				DIST_C_CA, 109.5, 180.0, residue=new_res, bonded=True)
	new_CA.bfactor = bfactor

	avail_bond_pos = bondPositions(bondee=new_C.coord(),
		geom=chimera.Atom.Planar, bondLen=DIST_C_O,
		bonded=[a.coord() for a in new_C.neighbors])

	use_point = avail_bond_pos[0]

	new_O = addAtom('O', chimera.Element(8), new_res, use_point, bondedTo=new_C)
	new_O.bfactor = bfactor

	return new_CA

def addNtN(end_bbone_ats, new_res, psi, bfactor):
	last_N = end_bbone_ats['N']

	new_CA = new_res.atomsMap['CA'][0]
	new_C = new_res.atomsMap['C'][0]

	new_N = addDihedralAtom('N', chimera.Element(7), new_CA, new_C, last_N,
		DIST_CA_N, 109.5, psi, residue=new_res, bonded=True)
	new_N.bfactor = bfactor

	return new_N

def getPhiPsiVals(conformation):
	# get correct phi and psi values based on conformation	
	if not conformation:
		phi = 180
		psi = 180
	else:
		# can conformation include phi and psi values ?
		if isinstance(conformation, tuple):
			if len(conformation) == 2:
				phi, psi = [float(p) for p in conformation]
			else:
				raise AddAAError("Must specify both phi and psi values"
					" or neither")
		elif conformation.lower() == 'ext':
			phi = 180
			psi = 180
		elif conformation.lower() == 'alpha':
			phi = -57
			psi = -47
		elif conformation.lower() == 'abeta':
			phi = -139
			psi =  135
		elif conformation.lower() == 'pbeta':
			phi = -119
			psi =  113
		else:
			raise AddAAError('Conformation must be one of "alpha", "abeta",'
				' "pbeta", "ext" or "phi,psi"')
	return phi,psi

def addAA(residue_type, residue_seq, last_res, conformation=None):
	"""add an amino acid to a model."""

	phi, psi = getPhiPsiVals(conformation)

	nt, ct = terminicity(last_res)
	if not nt and not ct:
		raise AddAAError("Can only add to N- or C-terminal residue.")
	if nt and ct:
		if residue_seq < last_res.id.position:
			ct = False
		else:
			nt = False

	end_bbone_ats = {}

	# find 'C' atom of last residue
	last_C = getBboneAtom(last_res, 'C')
	if not last_C:
		raise AddAAError("Couldn't find 'C' backbone atom of %s" % last_res)
	else:
		end_bbone_ats['C'] = last_C

	# find 'CA' atom of last residue
	last_CA = getBboneAtom(last_res, 'CA')
	if not last_CA:
		raise AddAAError("Couldn't find 'CA' backbone atom of %s" % last_res)
	else:
		end_bbone_ats['CA'] = last_CA

	# find 'N' atom of last residue
	last_N = getBboneAtom(last_res, 'N')
	if not last_N:
		raise AddAAError("Couldn't find 'N' backbone atom of %s" % last_res)
	else:
		end_bbone_ats['N'] = last_N

	# find 'O' atom of last residue
	last_O = getBboneAtom(last_res, 'O')
	if not last_O:
		raise AddAAError("Couldn't find 'O' backbone atom of %s" % last_res)
	else:
		end_bbone_ats['O'] = last_O

	# make a new residue
	insert_char = residue_seq[-1]
	if insert_char.isalpha():
		# insertion specified
		residue_seq = residue_seq[:-1]
	else:
		insert_char = ' '
	if residue_seq.isdigit():
		residue_seq = int(residue_seq)
	else:
		raise AddAAError("Residue sequence argument can contain at most one"
			" insertion character")

	mol = last_res.molecule
	mrid = chimera.MolResId(last_res.id.chainId, residue_seq,
		insert=insert_char)
	if mol.findResidue(mrid):
		raise AddAAError("Can't add amino acid, model already contains residue"
			" with sequence '%s'." % residue_seq)

	new_res = mol.newResidue(residue_type, mrid, neighbor=last_res, after=ct)

	if conformation == 'alpha':
		new_res.isHelix = True
	elif conformation in ('abeta', 'pbeta'):
		new_res.isSheet = True

	bFac = getBFactor(mol)

	if nt:
		addNtBBone(new_res, last_res, phi, psi, end_bbone_ats, bFac)
	else:
		addCtBBone(new_res, last_res, phi, psi, end_bbone_ats, bFac)

	# swap residues type
	import Midas
	try:
		Midas.swapres(residue_type, sel=new_res.oslIdent(), bfactor=bFac)
	except:
		cleanUp(mol, new_res, new_res.atoms)

		import sys
		error, val = sys.exc_info()[:2]
		raise AddAAError(val)

def addNtBBone(new_res, last_res, phi, psi, end_bbone_ats, bFac):
	# delete any terminal atoms from the last residue, if there is one
	# there.
	mol = last_res.molecule
	try:
		pruneNtResidue(end_bbone_ats['N'])
	except AddAAError, what:
		cleanUp(mol, new_res, [])
		raise AddAAError(what)

	# add the C atom for the new residue's backbone
	new_C = addNtC(end_bbone_ats, new_res, phi, bFac)

	# add the CA (and O) atom for the new residue's backbone
	new_CA = addNtCA(end_bbone_ats, new_res, bFac)

	# add the N atom for the new residue's backbone
	new_N = addNtN(end_bbone_ats, new_res, psi, bFac)

def addCtBBone(new_res, last_res, phi, psi, end_bbone_ats, bFac):
	# delete any terminal atoms from the last residue, if there is one
	# there.
	mol = last_res.molecule
	try:
		pruneCtResidue(end_bbone_ats['C'])
	except AddAAError, what:
		cleanUp(mol, new_res, [])
		raise AddAAError(what)

	# add the N atom for the new residue's backbone
	new_N = addCtN(end_bbone_ats, new_res, bFac)

	# add the CA atom for the new residue's backbone
	new_CA = addCtCA(end_bbone_ats, new_res, bFac)

	# add the C atom for the new residue's backbone
	new_C = addCtC(end_bbone_ats, new_res, phi, bFac)

	# add the oxygens for the new residue's backbone
	new_O, new_OXT = addCtOs(new_res, psi, bFac)

def getShortestPoint(ref_point, point_list):

	shortest_point = None
	shortest_dist  = None

	for p in point_list:
		dist = chimera.distance(p, ref_point)
		if (not shortest_dist) or dist < shortest_dist:
			shortest_point = p
			shortest_dist  = dist

	return shortest_point
