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
	doExtensionFunc(cmdPdb2pqr, args, specInfo=[("molecule_spec",
							"molecules",
							"molecules")])

from ws import ForceFields, FFDefault
def cmdPdb2pqr(molecules=None, ligands=False,
		forcefield=ForceFields[FFDefault], hbonds=False,
		propkaph=None, debump=True, neutraln=False, neutralc=False,
		optHbond=True, angleCutoff=30.0, distCutoff=3.4,
		apbs=False, pqr="", wait=False,
		backend="", location=""):
	if molecules is None:
		import chimera
		molecules = chimera.openModels.list(
				modelTypes=[chimera.Molecule])
	if len(molecules) != 1:
		from chimera import UserError
		raise UserError("pdb2pqr operates on a single molecule")
	import ws
	ff = forcefield.lower()
	if ff not in ws.ForceFieldsLowercase:
		from chimera import UserError
		raise UserError("Unknown forcefield \"%s\"" % forcefield)
	kw = {
		"ligands": ligands,
		"forcefield": ff,
		"hbonds": hbonds,
		"propkaph": propkaph,
		"debump": debump,
		"neutraln": neutraln,
		"neutralc": neutralc,
		"optHbond": optHbond,
		"angleCutoff": angleCutoff,
		"distCutoff": distCutoff,
		"apbs": apbs,
		"pqr": pqr,
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
	from ws import Pdb2pqr
	for m in molecules:
		Pdb2pqr(molecule=m, **kw)
