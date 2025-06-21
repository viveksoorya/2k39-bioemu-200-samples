# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

def run(cmdName, args):
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(cmdApbs, args, specInfo=[("molecule_spec", "molecules",
							"molecules")])

def cmdApbs(molecules=None,
		output="",
		dime="",
		cglen="",
		cgcent=True,
		_cgcentcoord="",
		fglen="",
		fgcent=True,
		_fgcentcoord="",
		bcfl="sdh",
		pdie=2.00,
		sdie=78.54,
		chgm="spl2",
		srfm="smol",
		ion=False,
		_posion="",
		_negion="",
		_equation="lpbe",
		sdens=10.00,
		srad=1.40,
		temp=298.15,
		solvent=False,
		wait=False,
		backend="",
		location=""):
	if molecules is None:
		import chimera
		molecules = chimera.openModels.list(
				modelTypes=[chimera.Molecule])
	from chimera import UserError
	if len(molecules) != 1:
		raise UserError("apbs operates on a single molecule")
	mol = molecules[0]
	try:
		# are charges missing or None?
		[a.charge + 1.0 for a in mol.atoms]
	except (AttributeError, TypeError):
		from chimera import UserError
		raise UserError("Charges are missing for some atoms.\n"
				"Please run Add Charge or PDB2PQR.")

	from ws import ChimeraPsize
	ps = ChimeraPsize(mol)
	ps.setAll()
	if not dime:
		dime = ps.getFineGridPoints()
	else:
		try:
			dime = _getGridDimensions(dime)
		except ValueError:
			raise UserError("bad grid dimensions: %s" % dime)
	if not cglen:
		cglen = ps.getCoarseGridDims()
	else:
		try:
			cglen = _getXYZ(cglen)
		except ValueError:
			raise UserError("bad coarse grid lengths: %s" % cglen)
	if not fglen:
		fglen = ps.getFineGridDims()
	else:
		try:
			fglen = _getXYZ(fglen)
		except ValueError:
			raise UserError("bad find grid lengths: %s" % fglen)
	if not cgcent:
		try:
			_cgcentcoord = _getXYZ(_cgcentcoord)
		except ValueError:
			raise UserError("bad coarse grid center: %s"
							% _cgcentcoord)
	if not fgcent:
		try:
			_fgcentcoord = _getXYZ(_fgcentcoord)
		except ValueError:
			raise UserError("bad fine grid center: %s"
							% _fgcentcoord)
	if ion:
		try:
			_posion = _getXYZ(_posion)
		except ValueError:
			raise UserError("bad ion parameters:" % _posion)
		try:
			_negion = _getXYZ(_negion)
		except ValueError:
			raise UserError("bad ion parameters:" % _negion)
	kw = {
		"output": output,
		"dime": dime,
		"cglen": cglen,
		"cgcent": cgcent,
		"_cgcentcoord": _cgcentcoord,
		"fglen": fglen,
		"fgcent": fgcent,
		"_fgcentcoord": _fgcentcoord,
		"bcfl": bcfl,
		"pdie": pdie,
		"sdie": sdie,
		"chgm": chgm,
		"srfm": srfm,
		"ion": ion,
		"_posion": _posion,
		"_negion": _negion,
		"_equation": _equation,
		"sdens": sdens,
		"srad": srad,
		"temp": temp,
		"solvent": solvent,
		"wait": wait,
	}
	if backend:
		from WebServices import prefs
		if not prefs.knownBackend(backend):
			raise UserError("unknown backend type: \"%s\"" % backend)
		if not location:
			raise UserError("location must be specified with backend")
		kw["serviceType"] = backend
		service, server = prefs.display2service(backend, location)
		kw["serviceName"] = service
		kw["serviceURL"] = server
	from ws import Apbs
	Apbs(molecule=mol, **kw)

def _getGridDimensions(s):
	grid = [ int(v) for v in s.split(',') ]
	if len(grid) != 3:
		raise ValueError("not a 3-tuple of ints")
	return grid

def _getXYZ(s):
	xyz = [ float(v) for v in s.split(',') ]
	if len(xyz) != 3:
		raise ValueError("not a 3-tuple of floats")
	return xyz
