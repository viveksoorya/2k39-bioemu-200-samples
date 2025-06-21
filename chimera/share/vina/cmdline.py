# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

def run(cmdName, args):
	fields = args.split(None, 1)
	if len(fields) > 1:
		opt, args = fields
	elif len(fields) == 0:
		from chimera import UserError
		raise UserError("\"%s\" requires arguments; "
				"use \"help %s\" for more information"
				% (cmdName, cmdName))
	else:
		opt = fields[0]
		args = ""
	bestMatch = None
	for optName in _optArgsTable.iterkeys():
		if optName.startswith(opt):
			if bestMatch is not None:
				from chimera import UserError
				raise UserError("option \"%s\" is ambiguous"
						% opt)
			else:
				bestMatch = optName
	if bestMatch is None:
		from chimera import UserError
		raise UserError("unknown option \"%s\"; "
				"use \"help %s\" for more information"
				% (opt, cmdName))
	func, kw = _optArgsTable[bestMatch]
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(func, args, **kw)

def docking(receptor=None,
		ligand=None,
		output="vina",
		num_modes=9,
		exhaustiveness=8,
		energy_range=3,
		search_center="",
		search_size="",
		r_addh=True,
		r_nphs=True,
		r_lps=True,
		r_waters=True,
		r_nonstdres=True,
		r_nonstd=False,
		l_nphs=True,
		l_lps=True,
		backend="",
		location="",
		wait=False,
		prep=False):

	# Check arguments
	from chimera import UserError
	if receptor is None or len(receptor) != 1:
		raise UserError("Receptor must be a single molecule")
	receptor = receptor[0]
	if ligand is None or len(ligand) != 1:
		raise UserError("Ligand must be a single molecule")
	ligand = ligand[0]
	if receptor is ligand:
		raise UserError("Receptor and ligand must be different")

	# Get base name for input files
	from OpenSave import tildeExpand
	output = tildeExpand(output)
	import os.path
	basename, ext = os.path.splitext(output)
	def pathForExtension(ext):
		return basename + ext

	# Prepare receptor and config files
	receptorFile, confFile = _prepReceptorAndConf(receptor,
				num_modes, exhaustiveness, energy_range,
				search_center, search_size,
				r_addh, r_nphs, r_lps,
				r_waters, r_nonstdres,
				r_nonstd, pathForExtension)

	# Prepare ligand
	from ws import checkLigand
	try:
		checkLigand(ligand)
	except ValueError as e:
		raise UserError(str(e))
	pdbFile = pathForExtension(".ligand.pdb")
	ligandFile = pathForExtension(".ligand.pdbqt")
	import Midas
	Midas.write(ligand, None, pdbFile)
	from ws import prepareLigand
	prepareLigand(pdbFile, ligandFile, l_nphs, l_lps)

	# If only preparation, we're done
	if prep:
		from chimera import replyobj
		replyobj.info("Autodock Vina ligand docking "
				"files generated for %s\n" % receptor.name)
		return

	# Invoke AutoDock Vina
	kw = {}
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
	from ws import VinaDocking
	VinaDocking(receptorFile=receptorFile,
				receptor=receptor,
				ligandFile=ligandFile,
				ligand=ligand,
				confFile=confFile,
				output=output,
				wait=wait,
				**kw)
	from chimera import replyobj
	replyobj.info("Autodock Vina ligand docking "
			"initiated for %s\n" % receptor.name)

def _prepReceptorAndConf(receptor,
				num_modes,
				exhaustiveness,
				energy_range,
				search_center,
				search_size,
				r_addh,
				r_nphs,
				r_lps,
				r_waters,
				r_nonstdres,
				r_nonstd,
				pathForExtension):

	# Get search volume if necessary
	if search_center and search_size:
		center = _getXYZ("search_center", search_center)
		size = _getXYZ("search_size", search_size)
	elif search_center or search_size:
		from chimera import UserError
		raise UserError("search center and size must be "
					"specified together")
	else:
		center = None
		size = None

	# Add hydrogens
	if r_addh:
		from AddH import hbondAddHydrogens as addHFunc
		addHFunc([ receptor ])

	# Prepare receptor
	pdbFile = pathForExtension(".receptor.pdb")
	receptorFile = pathForExtension(".receptor.pdbqt")
	import Midas
	Midas.write(receptor, receptor, pdbFile)
	from ws import prepareReceptor
	prepareReceptor(pdbFile, receptorFile,
			r_nphs, r_lps, r_waters,
			r_nonstdres, r_nonstd)

	# Prepare config file
	if not center:
		valid, bbox = receptor.openState.bbox()
		if not valid:
			raise ValueError("cannot get receptor bounding box")
		llf = bbox.llf
		urb = bbox.urb
		center = [ (urb[i] + llf[i]) / 2 for i in range(3) ]
		size = [ (urb[i] - llf[i]) + 10 for i in range(3) ]
		# Add some extra space in case binding modes stick
		# out from surface of receptor
	confFile = pathForExtension(".conf")
	from ws import prepareConf
	opts = {
		"num_modes": num_modes,
		"exhaustiveness": exhaustiveness,
		"energy_range": energy_range,
	}
	prepareConf(confFile, center, size, opts)
	return receptorFile, confFile

def _getXYZ(name, s):
	try:
		parts = s.split(',')
		if len(parts) != 3:
			raise ValueError("bad value")
		return [ float(v) for v in parts ]
	except ValueError:
		from chimera import UserError
		raise UserError("%s must be a comma-separated x,y,z value "
				"(no whitespace allowed)" % name)

def screening(receptor=None,
		database=None,
		output="",
		num_modes=9,
		exhaustiveness=8,
		energy_range=3,
		search_center="",
		search_size="",
		r_addh=True,
		r_nphs=True,
		r_lps=True,
		r_waters=True,
		r_nonstdres=True,
		r_nonstd=False,
		backend="",
		location="",
		wait=False):

	# Check arguments
	from chimera import UserError
	if len(receptor) != 1:
		raise UserError("Receptor must be a single molecule")
	receptor = receptors[0]

	# Get base name for input files
	from OpenSave import tildeExpand
	output = tildeExpand(output)
	import os.path
	basename, ext = os.path.splitext(output)
	def pathForExtension(ext):
		return basename + ext

	# Prepare receptor and config files
	receptorFile, confFile = _prepReceptorAndConf(receptor,
				num_modes, exhaustiveness, energy_range,
				search_center, search_size,
				r_addh, r_nphs, r_lps,
				r_waters, r_nonstdres,
				r_nonstd, pathForExtension)

	# Invoke AutoDock Vina
	kw = {}
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
	from ws import VinaScreening
	VinaScreening(receptorFile=receptorFile,
				receptor=receptor,
				database=database,
				confFile=confFile,
				output=output,
				wait=wait,
				**kw)
	from chimera import replyobj
	replyobj.info("Autodock Vina virtual screening "
			"initiated for %s\n" % receptor.name)

# Supply appropriate arguments for each command
_optArgsTable = {
	"docking":
		(docking,
			{ "specInfo":[
				("receptor_spec", "receptor", "molecules"),
				("ligand_spec", "ligand", "molecules"),
				] } ),
#	"screening":
#		(screening,
#			{ "specInfo":[("spec", "receptor", "molecules")
#					] } ),
}
