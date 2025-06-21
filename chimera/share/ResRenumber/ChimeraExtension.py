# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: ChimeraExtension.py 26655 2009-01-07 22:02:30Z gregc $

import chimera.extension

class ResRenumberEMO(chimera.extension.EMO):
	help = "renumber residues"
	def name(self):
		return 'Renumber Residues'
	def description(self):
		return self.help
	def categories(self):
		return ['Structure Editing']
	def activate(self):
		from chimera import dialogs
		dialogs.display(self.module('gui').ResRenumberDialog.name)
		return None

chimera.extension.manager.registerExtension(ResRenumberEMO(__file__))

def cmdResRenumber(cmdName, args):
	from ResRenumber import renumberResidues
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(renumberResidues, args,
				specInfo=[("spec", "residues", "residues")])

from Midas.midas_text import addCommand
addCommand("resrenumber", cmdResRenumber, help=True, changesDisplay=False)

