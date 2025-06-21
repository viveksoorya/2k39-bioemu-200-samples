# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: AddSeqDialog.py 27358 2009-04-21 00:32:47Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
from MAViewer import SeqMenu

class BlastPdbDialog(ModelessDialog):
	"""Blast sequence"""

	buttons = ("OK", "Apply", "Close")
	default = "OK"
	title = "Blast Sequence"
	#help = "ContributedSoftware/multalignviewer/multalignviewer.html#blast"
	
	def __init__(self, mav, *args, **kw):
		self.mav = mav
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		self.menu = SeqMenu(parent, self.mav, labelpos='w', label_text="Blast")
		self.menu.grid()

	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		self.mav.blast(self.menu.getvalue())
