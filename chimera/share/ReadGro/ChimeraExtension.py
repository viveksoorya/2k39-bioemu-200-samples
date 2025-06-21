# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera

class ReadGroEMO(chimera.extension.EMO):
	def name(self):
		return 'Read GRO'
	def description(self):
		return 'Read Gromac gro format'
	def categories(self):
		return ['MD']
	def activate(self):
		return None
	def open(self, fileName):
		return self.module().readGro(fileName)

emo = ReadGroEMO(__file__)
# don't need to register as an explicit tool, just for the file type...
#chimera.extension.manager.registerExtension(emo)

chimera.fileInfo.register(emo.module('fileInfo').fileType, emo.open,
					emo.module('fileInfo').suffixes,
					emo.module('fileInfo').prefixes,
					category=chimera.FileInfo.STRUCTURE)
del emo
