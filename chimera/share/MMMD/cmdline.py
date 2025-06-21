# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

def minimize(atoms=None, nsteps=100, stepsize=0.02,
		cgsteps=10, cgstepsize=0.02,
		interval=10, nogui=False, freeze=None, addhyd=True,
	        fragment=False, cache=True, prep=True):

	exclres = set()
	fixedAtoms = set()
	if atoms is None:
		import chimera
		molecules = chimera.openModels.list(
				modelTypes=[chimera.Molecule])
	else:
		molecules = list(set(a.molecule for a in atoms))
		if fragment:
			exclres = set(sum((m.residues for m in molecules), []))
			exclres.difference_update(set(a.residue for a in atoms))
		else:
			fixedAtoms = set(sum((m.atoms for m in molecules), []))
			fixedAtoms.difference_update(atoms)

	import base
	fixedAtoms.update(base.frozenAtoms(freeze, molecules))

	def run(minimizer):
		minimizer.run()
	minimizer = base.Minimizer(molecules, nsteps=nsteps, stepsize=stepsize,
					cgsteps=cgsteps, cgstepsize=cgstepsize,
					interval=interval,
					fixedAtoms=fixedAtoms, nogui=nogui,
					addhyd=addhyd, callback=run,
					exclres=exclres, cache=cache, prep=prep)

def dynamics(molecules=None, nsteps=100, interval=10):
	import chimera
	raise chimera.LimitationError("MD not implemented yet")
