
def open_maestro(path, keepBlocks=False, addProperties=False):
	from maestro import MaestroFile
	try:
		mf = MaestroFile(path)
	except (ValueError, SyntaxError), e:
		from traceback import format_exception_only
		msg = ''.join(format_exception_only(type(e), e)).strip()
		from chimera import UserError
		raise UserError(msg)

	# Make sure we have the right type and version of data
	# from initial block
	mfIter = iter(mf)
	block0 = mfIter.next()
	try:
		if block0.getAttribute("s_m_m2io_version") != "2.0.0":
			raise ValueError("version mismatch")
		#print "Maestro v2.0.0 file recognized"
	except:
		from chimera import UserError
		raise UserError("%s: not a v2.0.0 Maestro file" % path)

	# Convert all subsequent blocks named "f_m_ct" to molecules
	import os.path
	filename = os.path.basename(path)
	molecules = list()
	for block in mfIter:
		if block.name != "f_m_ct":
			print "%s: Skipping \"%s\" block" % (path, block.name)
		#print "Convert %s block to molecule" % block.name
		mol = _convertToMolecule(block)
		if mol:
			molecules.append(mol)
			mol.name = filename
			if keepBlocks:
				mol.maeBlock = block
			if addProperties:
				_addProperties(mol, block)
	return molecules

def _convertToMolecule(block):
	atoms = block.getSubBlock("m_atom")
	if atoms is None:
		print "No m_atom block found"
		return None
	bonds = block.getSubBlock("m_bond")
	import chimera
	mol = chimera.Molecule()
	residueMap = dict()
	atomMap = dict()
	from maestro import IndexAttribute
	for row in range(atoms.size):
		attrs = atoms.getAttributeMap(row)
		index = attrs[IndexAttribute]

		# Get residue data and create if necessary
		resSeq = attrs["i_m_residue_number"]
		insertCode = attrs.get("s_m_insertion_code", None)
		if not insertCode:
			insertCode = ' '
		chainId = attrs.get("s_m_chain_name", ' ')
		resKey = (chainId, resSeq, insertCode)
		try:
			r = residueMap[resKey]
		except KeyError:
			resId = chimera.MolResId(chainId, resSeq,
							insert=insertCode)
			resName = attrs.get("s_m_pdb_residue_name", "UNK")
			r = mol.newResidue(resName.strip(), resId)
			residueMap[resKey] = r
		rgb = attrs.get("s_m_ribbon_color_rgb", None)
		if rgb:
			r.ribbonColor = _getColor(rgb)

		# Get atom data and create
		try:
			name = attrs["s_m_pdb_atom_name"]
		except KeyError:
			name = attrs.get("s_m_atom_name", "")
		atomicNumber = attrs.get("i_m_atomic_number", 6)
		element = chimera.Element(atomicNumber)
		name = name.strip()
		if not name:
			name = element.name
		a = mol.newAtom(name, element)
		c = chimera.Coord()
		c.x = atoms.getAttribute("r_m_x_coord", row)
		c.y = atoms.getAttribute("r_m_y_coord", row)
		c.z = atoms.getAttribute("r_m_z_coord", row)
		try:
			a.bfactor = attrs["r_m_pdb_tfactor"]
		except (KeyError, TypeError):
			a.bfactor = 0.0
		try:
			a.occupancy = attrs["r_m_pdb_occupancy"]
		except (KeyError, TypeError):
			a.occupancy = 1.0
		a.setCoord(c)
		rgb = attrs.get("s_m_color_rgb", None)
		if rgb:
			a.color = _getColor(rgb)

		# Add atom to residue and to atom map for bonding later
		r.addAtom(a)
		atomMap[index] = a
	if bonds is None or bonds.size == 0:
		chimera.connectMolecule(mol)
	else:
		for row in range(bonds.size):
			attrs = bonds.getAttributeMap(row)
			fi = attrs["i_m_from"]
			ti = attrs["i_m_to"]
			if ti < fi:
				# Bonds are reported in both directions
				# We only need one
				continue
			afi = atomMap[fi]
			ati = atomMap[ti]
			b = mol.newBond(afi, ati)
			b.order = attrs["i_m_order"]
	return mol

def _addProperties(mol, block):
	"""Add properties to molecule assuming that it was opened with
	"open_maestro(path, keepBlocks=True)" """
	from maestro import getValue
	attrs = block.getAttributeMap()
	rawText = list()
	d = dict()
	for key, value in attrs.iteritems():
		isValid = True
		parts = key.split('_', 2)
		if len(parts) != 3:
			name = key
		else:
			if parts[1] != "i" and parts[1] != "m":
				isValid = False
			name = parts[2]
		if isValid:
			try:
				convertedValue = getValue(key, value)
			except ValueError:
				isValid = False
		if isValid:
			d[name] = convertedValue
		rawText.append("%s: %s" % (name, value))
	mol.maeText = '\n'.join(rawText)
	mol.maeAttr = d

def _getColor(rgb):
	name = "maestro_" + rgb
	from chimera import MaterialColor
	c = MaterialColor.lookup(name)
	if not c:
		r = int(rgb[0:2], 16) / 255.0
		g = int(rgb[2:4], 16) / 255.0
		b = int(rgb[4:6], 16) / 255.0
		c = MaterialColor(r, b, g)
		c.save(name)
	return c
