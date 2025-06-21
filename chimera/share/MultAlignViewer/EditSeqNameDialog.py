# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: DelSeqsGapsDialog.py 26655 2009-01-07 22:02:30Z gregc $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
from MAViewer import MOD_ALIGN

class EditSeqNameDialog(ModelessDialog):
	"""Edit sequence names"""

	buttons = ("OK", "Apply", "Close")
	default = "OK"
	title = "Edit Sequence Name"
	help = "ContributedSoftware/multalignviewer/multalignviewer.html#seqnames"
	
	def __init__(self, mav, *args, **kw):
		self.mav = mav
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		from MAViewer import SeqMenu
		self.seqMenu = SeqMenu(parent, self.mav, labelpos='w',
			label_text="Sequence name to change:",
			command=self._seqSelection)
		self.seqMenu.grid(row=0, column=0)

		self.nameEdit = Pmw.EntryField(parent, command=self.OK,
			value=self.seqMenu.getvalue().name, labelpos="nw",
			label_text="Change name to:")
		self.nameEdit.grid(row=1, column=0, sticky="ew")

	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		newName = self.nameEdit.getvalue().strip()
		if not newName:
			self.enter()
			from chimera import UserError
			raise UserError("New sequence name cannot be blank")
		self.seqMenu.getvalue().name = newName

	def _seqSelection(self, val):
		self.nameEdit.setvalue(val.name)
