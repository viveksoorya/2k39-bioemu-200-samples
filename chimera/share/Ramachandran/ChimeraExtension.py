# --- UCSF Chimera Copyright ---
# Copyright (c) 2010 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension

class RamachandranEMO(chimera.extension.EMO):
	def name(self):
		return "Ramachandran Plot"
	def description(self):
		return "Display amino acid phi-psi plot"
	def categories(self):
		return ["Structure Analysis"]
	def icon(self):
		return self.path("ramachandran.png")
	def cmdLine(self, cmdName, args):
		self.module().cmdLine(cmdName, args)
	def modelPanelCB(self, molecules):
		self.module().modelPanel(molecules)

emo = RamachandranEMO(__file__)

import ModelPanel
ModelPanel.addButton("Ramachandran plot...", emo.modelPanelCB)

from Midas.midas_text import addCommand
addCommand("ramachandran", emo.cmdLine, help=True)
