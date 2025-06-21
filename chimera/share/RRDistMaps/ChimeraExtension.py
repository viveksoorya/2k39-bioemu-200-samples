# --- UCSF Chimera Copyright ---
# Copyright (c) 2014 Regents of the University of California.
# All rights reserved. This software proved pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use. This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension

class RRDistMapsEMO(chimera.extension.EMO):
	def name(self):
		return 'RR Distance Maps'
	def description(self):
		return 'Plots 2D maps of residue-residue distances'
	def categories(self):
		return ['Structure Comparison']
	def activate(self):
		self.module('gui').display()
		return None
	def cmdRRdm(self, cmdName, args):
		self.module('cmdline').run(cmdName, args)

emo = RRDistMapsEMO(__file__)
chimera.extension.manager.registerExtension(emo)	# Register Tool
from Midas.midas_text import addCommand			# Add cmdline
addCommand('rrdm', emo.cmdRRdm, help = False)
