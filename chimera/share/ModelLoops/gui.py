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

def modelLoops():
	from chimera import openModels, Molecule
	seqs = [s for m in openModels.list(modelTypes=[Molecule]) for s in m.sequences()]
	if len(seqs) == 1:
		launchModelingInterface(seqs[0])
	else:
		ModelLoopsDialog()

def launchModelingInterface(seq):
	from ModelPanel.base import seqCmd
	mav = seqCmd([seq])[0]
	mav.structureMenu.invoke(mav.MODEL_LOOPS_MENU_TEXT)

from chimera.baseDialog import ModelessDialog
class ModelLoopsDialog(ModelessDialog):
	buttons = ('OK', 'Close')
	default = 'OK'
	title = "Choose Chain for Modeling"

	def fillInUI(self, parent):
		from chimera.widgets import MoleculeChainOptionMenu
		self.chainMenu = MoleculeChainOptionMenu(parent)
		self.chainMenu.grid(row=0, column=0)

		from chimera import tkgui
		if tkgui.windowSystem == "aqua":
			minsize = "4.17i"
		else:
			minsize = "3i"
		parent.columnconfigure(0, minsize=minsize, weight=1)
		parent.rowconfigure(1, weight=1)
		from CGLtk.WrappingLabel import WrappingLabel
		WrappingLabel(parent, text="Choosing a chain from the above menu and clicking 'OK' will show the sequence of that chain and an interface for using MODELLER to model missing parts of that structure or to remodel existing parts.").grid(row=1, column=0, sticky="nsew")

	def Apply(self):
		chain = self.chainMenu.getvalue()
		if chain:
			launchModelingInterface(chain)
