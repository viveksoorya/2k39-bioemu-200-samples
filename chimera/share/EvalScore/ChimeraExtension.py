# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension

class EvalScoreEMO(chimera.extension.EMO):
	def name(self):
		return "EvalScore"
	def description(self):
		return "Evaluate structure scores"
	def categories(self):
		return ["Utilities"]
	def open(self, path):
		#self.module("filetype").openScores(path)
		self.module().openScores(path)

emo = EvalScoreEMO(__file__)

from chimera import fileInfo, FileInfo
fileInfo.register("EvalScore",			# name of file type
			emo.open,			# function to call
			['.score'],			# extensions
			['score'])			# prefixes
