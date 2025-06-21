# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: ChimeraExtension.py 26655 2009-01-07 22:02:30Z gregc $

import chimera.extension

class AlignChainsEMO(chimera.extension.EMO):
	def name(self):
		return 'Align Chain Sequences'
	def description(self):
		return 'create sequence alignment from chains'
	def categories(self):
		return ['Sequence']
	def icon(self):
		#return self.path('matchmaker.png')
		return None
	def activate(self):
		from chimera import dialogs
		d = dialogs.display(self.module('gui').AlignChainsDialog.name)
		return None

emo = AlignChainsEMO(__file__)
chimera.extension.manager.registerExtension(emo)
"""
if not chimera.nogui:
	import ModelPanel
	ModelPanel.addButton("match...", emo.activate, minModels=2,
		moleculesOnly=True, balloon="align sequences/structures")

def cmdMatchMaker(cmdName, args):
	from MatchMaker import cmdMatch
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(cmdMatch, args, specInfo=[("refSpec", "refSel", None),
					("matchSpec", "matchSel", None)])
from Midas.midas_text import addCommand
addCommand("mmaker", cmdMatchMaker, help=True)
addCommand("matchmaker", cmdMatchMaker, help=True)
"""
