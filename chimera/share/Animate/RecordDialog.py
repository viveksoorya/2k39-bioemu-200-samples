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

from OpenSave import SaveModeless
from MovieRecorder.commonOptions import BaseRecordDialog

class RecordDialog(BaseRecordDialog):
	title = "Record Animation"
	help = "ContributedSoftware/animation/animation.html#recording"

	def __init__(self, keyframes):
		self.keyframes = keyframes
		BaseRecordDialog.__init__(self, historyID="Animate movies")

	def Apply(self):
		kfs = self.keyframes
		kfs.movie_record_args, kfs.movie_encode_args = self.commonOptionStrings()
		kfs.movie_record(source=self.source)

	def Close(self):
		if self.keyframes.recordDialog:
			self.keyframes.triggerOut('record_stopped')
		BaseRecordDialog.Close(self)
