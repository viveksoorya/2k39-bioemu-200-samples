# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension

class mmmdEMO(chimera.extension.EMO):
	def name(self):
		return 'Molecular Dynamics Simulation'
	def description(self):
		return 'Prepare a Molecular Dynamics Simulation for a given system'
	def categories(self):
		return ['MD/Ensemble Analysis']
	#def icon(self):
	#	return self.path("Template.png")
	def activate(self):
		from chimera.dialogs import display
		display(self.module('gui').MolecularDynamicsDialog.name)
		return None
	def cmdMMMD(self, cmdName, args):
		from Midas.midas_text import doExtensionFunc
		func = getattr(self.module('cmdline'), cmdName)
		doExtensionFunc(func, args,
				specInfo=[("spec", "molecules", "molecules")])

emo = mmmdEMO(__file__)

chimera.extension.manager.registerExtension(emo)

