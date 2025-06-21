# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

from chimera.baseDialog import ModelessDialog
class RecoveryDialog(ModelessDialog):
	buttons = ('Recover', 'Remove', 'Ignore')
	oneshot = True

	def __init__(self, recoveryFile):
		self.recoveryFile = recoveryFile
		ModelessDialog.__init__(self)

	def fillInUI(self, parent):
		import Tkinter
		Tkinter.Label(parent, wraplength="4i", text=
		"Your last image save attempt either failed or crashed Chimera.  "
		"A checkpoint session was saved just before the attempt.  "
		"Would you like to recover from the session, remove the session,"
		" or ignore the session until you next use Chimera?  "
		"(Recovering the session will also remove it.)").grid()

	def Recover(self):
		import os
		if not os.path.exists(self.recoveryFile):
			from chimera import UserError
			raise UserError("Checkpoint session file no longer exists!")
		from chimera import openModels
		openModels.open(self.recoveryFile, type="Python", temporary=True)
		self.Remove()

	def Remove(self):
		import os
		if os.path.exists(self.recoveryFile):
			os.unlink(self.recoveryFile)
			if os.path.exists(self.recoveryFile + "c"):
				os.unlink(self.recoveryFile + "c")
		self.Close()

	Ignore = ModelessDialog.Close

