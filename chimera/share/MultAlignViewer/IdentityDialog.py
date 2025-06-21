# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: IdentityDialog.py 39672 2014-04-15 22:10:03Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
from chimera.Sequence import percentIdentity
from MAViewer import SeqMenu

class IdentityDialog(ModelessDialog):
	"""Compute percent identity for sequence pairs"""

	buttons = ("OK", "Apply", "Close")
	help = "ContributedSoftware/multalignviewer/multalignviewer.html#pid"
	
	ALL = "all sequences"

	def __init__(self, mav, *args, **kw):
		self.mav = mav
		self.title = "Compute Percent Identities for %s" % (mav.title,)
		ModelessDialog.__init__(self, *args, **kw)
		self.uiMaster().winfo_toplevel().wm_transient(
						mav.uiMaster().winfo_toplevel())

	def fillInUI(self, parent):
		import Tkinter
		Tkinter.Label(parent, text="Compare:").grid(row=0, column=0, sticky='e')
		self.seqMenu1 = SeqMenu(parent, self.mav, includeAllOption=True,
			initialitem=SeqMenu.AllOptionText)
		self.seqMenu1.grid(row=0, column=1, sticky='w')
		Tkinter.Label(parent, text="with:").grid(row=1, column=0, sticky='e')
		self.seqMenu2 = SeqMenu(parent, self.mav, includeAllOption=True,
			initialitem=SeqMenu.AllOptionText)
		self.seqMenu2.grid(row=1, column=1, sticky='w')
		from chimera.tkoptions import SymbolicEnumOption
		class DenomOption(SymbolicEnumOption):
			labels = ["shorter sequence length",
						"longer sequence length",
						"non-gap columns in common"]
			values = ["shorter", "longer", "in common"]
		self.denominator = DenomOption(parent, 2, "divide by",
							"shorter", None)
	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		seqs1 = self.seqMenu1.getvalue()
		seqs2 = self.seqMenu2.getvalue()

		denom = self.denominator.get()
		for s1 in seqs1:
			for s2 in seqs2:
				pi = percentIdentity(s1, s2, denominator=denom)
				self.mav.status("%s vs. %s:\n"
					"   %.2f%% identity" % (s1.name,
					s2.name, pi))
				# since once OK is clicked, the mouse may be
				# over a part of the alignment that causes a
				# status message, also send to regular status
				# line
				replyobj.status("%s vs. %s: %.2f%% identity"
					% (s1.name, s2.name, pi), log=True)
		if len(seqs1) > 1 or len(seqs2) > 1:
			self.mav.status("Percent identity info in Reply Log")
			from chimera import dialogs, tkgui
			dialogs.display(tkgui._ReplyDialog.name)
