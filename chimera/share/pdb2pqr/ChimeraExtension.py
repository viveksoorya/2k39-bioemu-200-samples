# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension

class Pdb2pqrEMO(chimera.extension.EMO):
	def name(self):
		return "PDB2PQR"
	def description(self):
		return "PDB2PQR web service for assigning charges"
	def categories(self):
		return ['Structure Editing']
	#def icon(self):
	#	return self.path("pdb2pqr.png")
	def activate(self):
		# Comment out if no GUI is needed
		from chimera.dialogs import display
		display(self.module("gui").Pdb2pqrDialog.name)
		return None
	def cmdLine(self, cmdName, args):
		# Comment out if no command is needed
		self.module("cmdline").run(cmdName, args)
	def modelPanelCB(self, molecules):
		# Comment out if no model panel button is needed
		self.module("modelpanel").callback(molecules)
		# Add any default arguments you need

emo = Pdb2pqrEMO(__file__)

# Don't register if no GUI
chimera.extension.manager.registerExtension(emo)

# Don't add if no Model Panel button
#import ModelPanel
#ModelPanel.addButton("PDB2PQR", emo.modelPanelCB)

# Don't register if no command line (Shame on you!)
from Midas.midas_text import addCommand
addCommand("pdb2pqr", emo.cmdLine, help=True)
