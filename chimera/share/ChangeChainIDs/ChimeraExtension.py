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

class ChangeChainsEMO(chimera.extension.EMO):
	help = "change chain IDs"
	def name(self):
		return 'Change Chain IDs'
	def description(self):
		return self.help
	def categories(self):
		return ['Structure Editing']
	def activate(self):
		from chimera import dialogs
		dialogs.display(self.module('gui').ChangeChainsDialog.name)
		return None

chimera.extension.manager.registerExtension(ChangeChainsEMO(__file__))

def cmdChangeChains(cmdName, args):
	from Midas import MidasError, evalSpec
	try:
		fromChains, toChains, spec = args.split(None, 2)
	except ValueError:
		try:
			fromChains, toChains = args.split()
			spec = "#"
		except ValueError:
			raise MidasError("usage: %s from-chains to-chains [atom spec]" % cmdName)
	fc = fromChains.split(',')
	tc = toChains.split(',')
	if len(fc) != len(tc):
		raise MidasError("(comma separated) from-chain list not same length as"
			" to-chain list")
	mols = evalSpec(spec).molecules()
	if not mols:
		raise MidasError("No molecules selected by atom spec")
	from ChangeChainIDs import changeChains
	changeChains(mols, zip(fc, tc))

from Midas.midas_text import addCommand
addCommand("changechains", cmdChangeChains, help=True, changesDisplay=False)

