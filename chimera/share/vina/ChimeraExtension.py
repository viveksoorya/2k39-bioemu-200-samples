# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension

class VinaEMO(chimera.extension.EMO):
	def name(self):
		return "AutoDock Vina"
	def description(self):
		return "AutoDock Vina web service at NBCR"
	def categories(self):
		return ["Surface/Binding Analysis"]
	#def icon(self):
	#	return self.path("vina.png")
	def activate(self):
		# Comment out if no GUI is needed
		from chimera.dialogs import display
		display(self.module("gui").VinaDialog.name)
		return None
	def cmdLine(self, cmdName, args):
		# Comment out if no command is needed
		self.module("cmdline").run(cmdName, args)

vinaEmo = VinaEMO(__file__)

# Don't register if no GUI
chimera.extension.manager.registerExtension(vinaEmo)

# Don't register if no command line (Shame on you!)
from Midas.midas_text import addCommand
addCommand("vina", vinaEmo.cmdLine, help=True)
# Above registration actually handles both docking and screening
