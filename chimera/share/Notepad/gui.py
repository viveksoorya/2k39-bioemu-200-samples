# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import dialogs

class NotepadDialog(ModelessDialog):
	buttons = ("Clear", "Close")
	title = "Notes"
	name = "simple notepad"
	help = "ContributedSoftware/notepad/notepad.html"

	def fillInUI(self, parent):
		from CGLtk.PeerText import PeerText
		import Pmw
		from SimpleSession.gui import SaveSessionDialog
		dlg = dialogs.find(SaveSessionDialog.name)
		if dlg:
			peer = dlg.description.component('text')
		else:
			peer = None
		self.text = Pmw.ScrolledText(parent, text_pyclass=PeerText, text_peer=peer)
		self.text.grid(sticky="nsew")
		self.text.focus_set()
		if not peer and chimera._lastSessionDescriptKw is not None:
			self.text.setvalue(chimera._lastSessionDescriptKw.get('description', ''))
			self.text.component('text').edit_modified(False)

		from SimpleSession import SAVE_SESSION
		chimera.triggers.addHandler(SAVE_SESSION, self._sessionSave, None)
		chimera.triggers.addHandler(chimera.CONFIRM_CLOSE_SESSION, self._confirmCloseSes, None)
		chimera.triggers.addHandler(chimera.CONFIRM_APPQUIT, self._confirmCloseSes, None)
		chimera.triggers.addHandler(chimera.CLOSE_SESSION, self._closeSes, None)

	def Clear(self):
		self.text.clear()

	def _confirmCloseSes(self, trigName, myData, msgList):
		if self.text.component('text').edit_modified():
			msgList.append("Notepad text changed since last session save.")

	def _closeSes(self, *args):
		self.text.setvalue("")
		self.text.component('text').edit_modified(False)

	def _sessionSave(self, trigName, myData, sessionFile):
		self.text.component('text').edit_modified(False)
		# restore dialog is showing and not empty
		if not self.text.winfo_ismapped():
			return
		text = self.text.getvalue()
		if not text or text.isspace():
			return
		print>>sessionFile, """
try:
	from Notepad.gui import sessionRestore
	sessionRestore(2, %s)
except:
	reportRestoreError("Error restoring Notepad")
""" % repr(text)

dialogs.register(NotepadDialog.name, NotepadDialog)

def sessionRestore(version, text):
	dlg = dialogs.display(NotepadDialog.name)
	if version == 1:
		from SimpleSession import modelOffset
		if modelOffset != 0:
			text = dlg.text.getvalue() + text
		dlg.text.setvalue(text)
		dlg.text.component('text').edit_modified(False)
