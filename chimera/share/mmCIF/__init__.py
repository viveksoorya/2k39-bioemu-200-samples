# Use 4-space tab stops when editing.  :set ts=4

# -----------------------------------------------------------------------------
# Read mmCIF file using Python mmLib module and make a Chimera Molecule.
#
# Tested with pymmlib 0.9.7 which must be installed separately into Chimera
# Python site-packages directory.
#

# -----------------------------------------------------------------------------
#
def open_mmcif(path):

	from OpenSave import osOpen
	p = osOpen(path)
	
	#
	# No bonds are created for standard mmCIF files from the PDB unless the
	# library_bonds or distance_bonds options are given.
	#
	# It appears that mmlib 0.9.7 can only link residues of a polymer using
	# distance rules.  Residue templates are used for intra-residue bonds.
	#
	from mmLib.FileIO import LoadStructure
	from mmLib.mmCIF import mmCIFSyntaxError
	# Reset console output each time in case we are
	# executing command as part of ReadStdin or
	# RESTServer, which play with sys.stderr
	import mmLib.ConsoleOutput, sys
	mmLib.ConsoleOutput.console_output_object.stderr = sys.stderr
	try:
		struct = LoadStructure(fil=p, format="CIF", library_bonds=True,
								auto_sort=False)
	except mmCIFSyntaxError, e:
		from chimera import NotABug
		raise NotABug("%s: %s" % (path, str(e)))
	except SystemExit:
		from chimera import LimitationError
		raise LimitationError("%s: fatal error reading .cif file" % path)
	
	mList = build_chimera_molecule(struct)

	import os.path
	for m in mList:
		m.name = os.path.basename(path)

	return mList

# -----------------------------------------------------------------------------
#
def build_chimera_molecule(mmlib_structure):

	from mmLib.Structure import fragment_id_split
	import chimera
	import numpy
	from string import letters
	from mmLib.CIFBuilder import add_number, add_string

	modelMap = {}	   # mmLib structure to Chimera molecule
	atoms = {}		  # mmLib atom to chimera atom mapping
	residues = {}	   # fragment to chimera residue mapping
	seq2frag = {}	   # entity-sequence to fragment mapping
	sa2r = {}		   # sequence-asym_id to chimera residue mapping
	e2c = {}			# entity to chain mapping

	# if cif (rather than mmCIF) get aniso info in there if available...
	anisoTable = None
	if hasattr(mmlib_structure, 'cif_data'):
		cif_data = mmlib_structure.cif_data
		for t in cif_data.tables:
			if "atom_site_aniso_label" in t.columns:
				anisoTable = t
				anisoNameMap = {}
				for row in range(len(anisoTable.rows)):
					temp = {}
					if add_string(temp, "x", anisoTable, "atom_site_aniso_label", row):
						anisoNameMap[temp["x"]] = row
				break

	# Repackage unused data from files into "headers" analogous
	# to PDB headers
	if hasattr(mmlib_structure, 'cif_data'):
		# CIF data are in cif_data (CIF.DataBlock)
		# We convert tags into a simple dictionary
		# and each table into list of dictionaries
		import copy
		cifTags = copy.copy(mmlib_structure.cif_data.tags)
		cifTables = dict()
		for ti, table in enumerate(mmlib_structure.cif_data.tables):
			tableName = _tableNameFromColumns(table.columns, ti)
			rowList = list()
			for row in table.rows:
				rowList.append(dict(zip(table.columns, row)))
			cifTables[tableName] = rowList
		cifHeaders = { "tags": cifTags, "tables": cifTables }
		def addFileData(m, headers=cifHeaders):
			m.cifHeaders = headers
	else:
		# mmCIF data are in cifdb (mmCIFDB.mmCIFDB)
		# Each table has a name, which becomes the key into
		# the mmCIFHeaders dictionary.  Each table is turned
		# into a list of dictionaries, just like CIF above.
		mmCIFHeaders = dict()
		for table in mmlib_structure.cifdb:
			# table is an instance of mmCIFTable
			tableData = []
			for row in table:
				# row is an instance of mmCIFRow
				tableData.append(dict(row))
			mmCIFHeaders[table.name] = tableData
		def addFileData(m, headers=mmCIFHeaders):
			m.mmCIFHeaders = headers

	# Make molecules
	for mm in mmlib_structure.iter_models():
		m = chimera.Molecule()
		addFileData(m)
		m.cif_unitCell = mmlib_structure.unit_cell
		modelMap[mm] = m
		seq2frag[m] = {}
		sa2r[m] = {}
		e2c[m] = {}

	# Make atoms and residues as needed
	name_to_element = element_table()
	for mm in mmlib_structure.iter_models():
		m = modelMap[mm]
		for ma in mm.iter_all_atoms():
			mf = ma.get_fragment()
			try:
				chain_id = ma.asym_id.strip()
			except AttributeError:
				chain_id = ma.chain_id.strip()
			try:
				r = residues[mf]
			except KeyError:
				if mf.fragment_id:
					seq, icode = fragment_id_split(mf.fragment_id)
				else:
					seq, icode = 0, None
				if icode is None:
					rid = chimera.MolResId(chain_id, seq)
				else:
					rid = chimera.MolResId(chain_id, seq, insert=icode)
				r = m.newResidue(mf.res_name, rid)
				for c in chain_id:
					if c.islower():
						m.lowerCaseChains = True
				residues[mf] = r
				if not mf.is_standard_residue():
					r.isHet = True
				sf_key = (ma.label_entity_id, ma.label_seq_id)
				d = seq2frag[m].setdefault(sf_key, {})
				d[chain_id] = mf
				sa2r[m][(ma.label_seq_id, ma.label_asym_id)] = r
				s = e2c[m].setdefault(ma.label_entity_id, set([]))
				s.add(chain_id)
			if not ma.element:
				ename = ma.name[0]
				if len(ma.name) > 1 and ma.name[1] in letters:
					ename += ma.name[1].lower()
			elif len(ma.element) > 1:
				ename = ma.element[0].upper() + ma.element[1:].lower()
				while len(ename) > 1:
					if ename[-1].isalpha():
						break
					ename = ename[:-1]
			else:
				ename = ma.element
			try:
				element = name_to_element[ename]
			except KeyError:
				# Don't know what it is, guess carbon
				element = name_to_element['C']
			a = m.newAtom(ma.name.replace('*', "'"), element)
			a.altLoc = ma.alt_loc
			c = chimera.Coord()
			c.x, c.y, c.z = ma.position
			a.setCoord(c)					   # a.coord = c does not work
			if ma.temp_factor is not None:
				a.bfactor = ma.temp_factor
			if ma.occupancy is not None:
				a.occupancy = ma.occupancy
			if ma.U is not None:
				a.anisoU = numpy.array(ma.U, 'f')
			elif anisoTable and ma.name in anisoNameMap:
				anisoDict = {}
				anisoRow = anisoNameMap[ma.name]
				for pos in ["11", "22", "33", "23", "13", "12"]:
					add_number(anisoDict, "u"+pos, anisoTable, "atom_site_aniso_u_"+pos, anisoRow)
				a.anisoU = numpy.array([
						[anisoDict['u11'], anisoDict['u12'], anisoDict['u13']],
						[anisoDict['u12'], anisoDict['u22'], anisoDict['u23']],
						[anisoDict['u13'], anisoDict['u23'], anisoDict['u33']]
						], 'f')
			atoms[ma] = a
			r.addAtom(a)

	# Make bonds
	numBonds = 0
	for mm in mmlib_structure.iter_models():
		m = modelMap[mm]
		for ma in mm.iter_all_atoms():
			for mb in ma.iter_bonds():
				a1 = atoms[mb.get_atom1()]
				a2 = atoms[mb.get_atom2()]
				try:
					m.newBond(a1, a2)
				except TypeError:
					pass
				else:
					numBonds += 1

	# Hack city!  mmCIF templates for amino acids do not have
	# H1 or H3 in them, so the N-terminus amino acid may be
	# left with two connected atoms.
	for mm in mmlib_structure.iter_models():
		m = modelMap[mm]
		for mf in mm.iter_fragments():
			if not mf.is_amino_acid():
				continue
			r = residues[mf]
			h1Atoms = r.findRangeAtoms("H1")
			h3Atoms = r.findRangeAtoms("H3")
			if not h1Atoms and not h3Atoms:
				continue
			h1List = h1Atoms.get("H1", [])
			h3List = h3Atoms.get("H3", [])
			nAtoms = r.findRangeAtoms("N")
			if not nAtoms:
				continue
			nList = nAtoms.get("N", [])
			numBonds += connectHydrogen(m, h1List, nList)
			numBonds += connectHydrogen(m, h3List, nList)

	# Make inter-residue bonds
	from chimera.resCode import res3to1
	from chimera import Sequence
	residueAfter = {}
	try:
		table = mmlib_structure.cifdb["entity_poly_seq"]
	except KeyError:
		for m in modelMap.itervalues():
			connectChain(m)
	else:
		for m in modelMap.itervalues():
			seqMap = {}
			prevEntity = None
			prevDict = None
			for row in table.iter_rows():
				thisEntity = row["entity_id"]
				try:
					chains = e2c[m][thisEntity]
				except KeyError:
					pass
				else:
					try:
						three = row["mon_id"]
					except KeyError:
						monomer = 'X'
					else:
						monomer = res3to1(three)
					for chainId in chains:
						try:
							seq = seqMap[chainId]
						except KeyError:
							if chainId == " ":
								name = Sequence.PRINCIPAL
							else:
								name = Sequence.CHAIN_FMT % chainId
							seq = Sequence.Sequence(name)
							seqMap[chainId] = seq
						seq.append(monomer)
				num = row["num"]
				try:
					thisDict = seq2frag[m][(thisEntity, num)]
				except KeyError:
					# leave the prev variables so we will connect
					# residues in the same chain.
					continue
				if prevDict is not None and prevEntity == thisEntity:
					for chain_id, prevR in prevDict.iteritems():
						try:
							thisR = thisDict[chain_id]
						except KeyError:
							continue
						isAA = thisR.is_amino_acid()
						isNA = thisR.is_nucleic_acid()
						wasAA = prevR.is_amino_acid()
						wasNA = prevR.is_nucleic_acid()
						if isAA and wasAA:
							numBonds += connectResidues(prevR, [ "C" ],
														thisR, [ "N" ],
														atoms, residueAfter)
						if isNA and wasNA:
							numBonds += connectResidues(prevR, [ "O3'", "O3*" ],
														thisR, [ "P" ],
														atoms, residueAfter)
				prevDict = thisDict
				prevEntity = thisEntity
			m.cifPolySeq = seqMap

	# If no bonds were made, make them
	if numBonds == 0:
		import chimera
		for m in modelMap.itervalues():
			chimera.connectMolecule(m)
	else:
		# Sometimes CIF files leave off connectivity for
		# hydrogen atoms.  If a molecule consists of a
		# single residue and it has disconnected atoms,
		# try to connect them up.
		for m in modelMap.itervalues():
			if len(m.residues) != 1:
				continue
			for a in m.atoms:
				if len(a.bonds) == 0:
					chimera.connectMolecule(m)
					break

	# Assign helix secondary structure
	try:
		table = mmlib_structure.cifdb["struct_conf"]
	except KeyError:
		pass
	else:
		for m in modelMap.itervalues():
			for row in table.iter_rows():
				typeId = row["conf_type_id"]
				if typeId.startswith("HELX"):
					ssType = "isHelix"
				else:
					continue
				bAsymId = row["beg_label_asym_id"]
				bSeqId = row["beg_label_seq_id"]
				eAsymId = row["end_label_asym_id"]
				eSeqId = row["end_label_seq_id"]
				try:
					bRes = sa2r[m][(bSeqId, bAsymId)]
				except KeyError:
					print "No residue match asym_id=%s seq_id=%s" % (bAsymId,
																		bSeqId)
					continue
				try:
					eRes = sa2r[m][(eSeqId, eAsymId)]
				except KeyError:
					print "No residue match asym_id=%s seq_id=%s" % (eAsymId,
																		eSeqId)
					continue
				# Make sure we have a clear list of residues
				# from beginning to end
				r = bRes
				while r is not eRes and r is not None:
					r = residueAfter.get(r, None)
				if r is None:
					print "Non-consecutive residues (%s.%s) -> (%s.%s)" % (
							bSeqId, bAsymId, eSeqId, eAsymId)
					continue
				r = bRes
				while r is not eRes:
					setattr(r, ssType, True)
					r = residueAfter[r]
				setattr(eRes, ssType, True)
	# Assign secondary structure (sheet)
	try:
		table = mmlib_structure.cifdb["struct_sheet_range"]
	except KeyError:
		pass
	else:
		for m in modelMap.itervalues():
			for row in table.iter_rows():
				bAsymId = row["beg_label_asym_id"]
				bSeqId = row["beg_label_seq_id"]
				eAsymId = row["end_label_asym_id"]
				eSeqId = row["end_label_seq_id"]
				try:
					bRes = sa2r[m][(bSeqId, bAsymId)]
				except KeyError:
					print "No residue match asym_id=%s seq_id=%s" % (bAsymId,
																		bSeqId)
					continue
				try:
					eRes = sa2r[m][(eSeqId, eAsymId)]
				except KeyError:
					print "No residue match asym_id=%s seq_id=%s" % (eAsymId,
																		eSeqId)
					continue
				# Make sure we have a clear list of residues
				# from beginning to end
				r = bRes
				while r is not eRes and r is not None:
					r = residueAfter.get(r, None)
				if r is None:
					print "Non-consecutive residues (%s.%s) -> (%s.%s)" % (
							bSeqId, bAsymId, eSeqId, eAsymId)
					continue
				r = bRes
				while r is not eRes:
					r.isSheet = True
					r = residueAfter[r]
				eRes.isSheet = True

	# Add any modres information to resCode dictionaries
	try:
		table = mmlib_structure.cifdb["struct_conn"]
	except KeyError:
		pass
	else:
		from chimera import resCode
		dicts = (resCode.regex3to1, resCode.nucleic3to1, resCode.protein3to1,
						resCode.standard3to1)
		for row in table.iter_rows():
			if row["conn_type_id"] != "modres":
				continue
			try:
				name = row["ptnr1_auth_comp_id"]
			except KeyError:
				name = row["ptnr1_label_comp_id"]
			stdName = row["pdbx_ptnr1_standard_comp_id"]
			for d in dicts:
				if stdName in d:
					d[name] = d[stdName]
	return modelMap.values()

def connectResidues(prev, prevAtoms, this, thisAtoms, atoms, residueAfter):
	numAdded = 0
	prevList = [ ma for ma in prev.iter_all_atoms() if ma.name in prevAtoms ]
	thisList = [ ma for ma in this.iter_all_atoms() if ma.name in thisAtoms ]
	for prevA in prevList:
		for thisA in thisList:
			if alt_loc_match(prevA.alt_loc, thisA.alt_loc):
				a1 = atoms[prevA]
				m1 = a1.molecule
				a2 = atoms[thisA]
				m2 = a2.molecule
				if m1 != m2:
					continue
				try:
					m1.newBond(a1, a2)
				except TypeError:
					# This may happen if the bond was already
					# specified in struct_conn section
					pass
				else:
					numAdded += 1
				residueAfter[a1.residue] = a2.residue
	return numAdded

def connectChain(m):
	# Called when poly_seq is missing.
	# Connect residues in model m if they have the same
	# chain id and are of the same type (amino acid/nucleotide).
	# We should probably check sequence to make sure they are
	# adjacent but we will rely on long-bond postprocessing for now.
	prevType = prevAtoms = prevChain = None
	for r in m.residues:
		n = r.findRangeAtoms("N")
		ca = r.findRangeAtoms("CA")
		c = r.findRangeAtoms("C")
		if n and ca and c:
			rType = "AA"
		else:
			o3p = r.findRangeAtoms("O3'")
			p = r.findRangeAtoms("P")
			if o3p.values() and p.values():
				rType = "Nuc"
			else:
				rType = None
		if rType is None:
			# Not AA or nucleotide, break chain
			prevType = prevAtoms = prevChain = None
			continue
		elif rType == "AA":
			chief = n["N"]
			link = c["C"]
		else:
			chief = p["P"]
			link = o3p["O3'"]
		chain = r.id.chainId
		if prevType == rType and prevAtoms is not None and prevChain == chain:
			# Same type and chain as previous residue, connect
			for prevA in prevAtoms:
				for thisA in chief:
					if alt_loc_match(prevA.altLoc, thisA.altLoc):
						m.newBond(prevA, thisA)
		prevType = rType
		prevAtoms = link
		prevChain = chain

def _tableNameFromColumns(columns, tableIndex):
	shortest = min([ len(c) for c in columns ])
	class Found(Exception): pass
	try:
		for i in range(shortest):
			ch = columns[0][i]
			for c in columns[1:]:
				if c[i] != ch:
					raise Found(i)
	except Found, found:
		n = found.args[0]
		name = columns[0][:n]
		while not name[-1].isalnum():
			name = name[:-1]
		return name
	else:
		return "table%d" % tableIndex

def alt_loc_match(al1, al2):
	return al1 == al2 or al1 == '' or al2 == ''

def connectHydrogen(m, hList, nList):
	nb = 0
	for h in hList:
		for n in nList:
			if h.altLoc and n.altLoc and h.altLoc != n.altLoc:
				continue
			try:
				m.newBond(n, h)
			except TypeError:
				pass
			else:
				nb += 1
	return nb

def dump_attributes(obj):
	import pprint
	for a in dir(obj):
		if a.startswith("_"):
			continue
		v = getattr(obj, a)
		if callable(v):
			continue
		print " %s:" % a,
		pprint.pprint(v)

# -----------------------------------------------------------------------------
#
name_to_element_dict = None
def element_table():

	global name_to_element_dict
	if name_to_element_dict == None:
		name_to_element_dict = {}
		from chimera import elements
		for name in elements.name:
			name_to_element_dict[name] = getattr(elements, name)
	return name_to_element_dict
