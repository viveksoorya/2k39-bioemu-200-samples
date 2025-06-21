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
from MAViewer import ADDDEL_SEQS, SeqMenu

class CopySeqDialog(ModelessDialog):
	"""copy sequence to system pasteboard"""

	buttons = ("OK", "Close")
	default = "OK"
	title = "Copy Sequence"
	help = "ContributedSoftware/multalignviewer/multalignviewer.html#copy"
	
	def __init__(self, mav, *args, **kw):
		self.mav = mav
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		Tkinter.Label(parent, text="Copy").grid(row=0, column=0)
		self.menu = SeqMenu(parent, self.mav)
		self.menu.grid(row=0, column=1)
		Tkinter.Label(parent, text="to system paste buffer").grid(
							row=0, column=2)
		self.ungappedVar = Tkinter.IntVar(parent)
		self.ungappedVar.set(True)
		Tkinter.Checkbutton(parent, text="Remove gaps from copy",
				variable=self.ungappedVar).grid(
				row=1, column=0, columnspan=3)
		self.regionRestrictVar = Tkinter.IntVar(parent)
		self.regionRestrictVar.set(False)
		Tkinter.Checkbutton(parent, variable=self.regionRestrictVar,
				text="Restrict copy to active region"
				).grid(row=2, column=0, columnspan=3)
	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		import Pmw
		seq = self.menu.getvalue()
		index = self.mav.seqs.index(seq)
		if self.regionRestrictVar.get():
			region = self.mav.currentRegion()
			from chimera import UserError
			if region is None:
				self.enter()
				raise UserError("No current region!")
			text = ""
			for line1, line2, pos1, pos2 in region.blocks:
				try:
					i1 = self.mav.seqs.index(line1)
				except ValueError:
					i1 = 0
				if index < i1:
					continue
				try:
					i2 = self.mav.seqs.index(line2)
				except ValueError:
					continue
				if index > i2:
					continue
				if self.ungappedVar.get():
					text += "".join([seq[p] for p in range(pos1, pos2+1)
									if seq.gapped2ungapped(p) is not None])
				else:
					text += seq[pos1:pos2+1]
			if not text:
				self.enter()
				raise UserError("Active region is all gaps")
		elif self.ungappedVar.get():
			text = seq.ungapped()
		else:
			text = seq[:]
		w = self.menu
		w.clipboard_clear()
		w.clipboard_append(text)
