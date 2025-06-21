# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: ChimeraExtension.py 28856 2009-09-24 21:08:06Z pett $

import chimera.extension

class SeqAnnotationsEMO(chimera.extension.EMO):
	def name(self):
		return 'PDB/UniProt Info'
	def description(self):
		return 'Information from UniProt about PDB structures'
	def categories(self):
		return ['Sequence']
	def activate(self, *modelPanelArgs):
		dialog = self.module('gui').FetchAnnotationsDialog
		from chimera import dialogs
		dialogs.display(dialog.name)
		return None
	def showUniprotSeq(self, ident):
		self.module().showUniprotSeq(ident)
		return []

emo = SeqAnnotationsEMO(__file__)
chimera.extension.manager.registerExtension(emo)

import ModelPanel
ModelPanel.addButton("UniProt info...", emo.activate, defaultFavorite=False)

from chimera import fileInfo, FileInfo
fileInfo.register("UniProt",	# name of file type
	emo.showUniprotSeq,			# function to call
	[],							# extensions
	["uniprot"],				# prefixes
	category=FileInfo.STRUCTURE)# category

import chimera.fetch
chimera.fetch.registerIdType(
	"UniProt",			# name of database
	12,					# identifier length
	"P01138\nNGF_HUMAN",# example
	emo.showUniprotSeq,	# handler
	"www.uniprot.org",  # home page
	"http://www.uniprot.org/uniprot/%s"
						# info url
)
