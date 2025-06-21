# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

from chimera.baseDialog import ModelessDialog

class ResRenumberDialog(ModelessDialog):
	name = "renumber residues"
	buttons = ('OK', 'Apply', 'Close')
	default = 'OK'
	help = "ContributedSoftware/editing/renumber.html"

	def fillInUI(self, parent):
		import Tkinter, Pmw
		row = 0

		Tkinter.Label(parent, text="Renumber...").grid(row=0, column=0)
		row += 1

		self.selectionMode = Tkinter.StringVar(parent)
		self.selectionMode.set("chain")
		Tkinter.Radiobutton(parent, text="selected residues",
			variable=self.selectionMode, value="selection").grid(row=row,
			column=0, sticky='w')
		row += 1
		f = Tkinter.Frame(parent)
		f.grid(row=row, column=0, sticky='w')
		Tkinter.Radiobutton(f, text="chains:", variable=self.selectionMode,
			value="chain").grid(row=0, column=0)
		from chimera.widgets import MoleculeChainScrolledListBox
		self.chainList = MoleculeChainScrolledListBox(f,
							listbox_selectmode="extended")
		self.chainList.grid(row=0, column=1, sticky="nsew")
		f.rowconfigure(0, weight=1)
		f.columnconfigure(1, weight=1)
		parent.rowconfigure(row, weight=1)
		parent.columnconfigure(0, weight=1)
		row += 1


		self.startNumber = Pmw.EntryField(parent, command=self.OK, labelpos='w',
			label_text="starting from", value="1", validate='integer')
		self.startNumber.grid(row=row, column=0)
		row += 1

	def Apply(self):
		from chimera import UserError, selection
		if not self.startNumber.checkentry():
			self.enter()
			UserError('Enter an integer in the "starting from" field')

		sn = int(self.startNumber.getvalue())

		if self.selectionMode.get() == "chain":
			residues = []
			for chain in self.chainList.getvalue():
				residues.extend([r for r in chain.residues if r])
		else:
			residues = selection.currentResidues()
			if not residues:
				self.enter()
				raise UserError("No residues selected")

		from ResRenumber import renumberResidues, ResRenumberError
		try:
			renumberResidues(sn, residues)
		except ResRenumberError, v:
			self.enter()
			raise UserError(str(v))

from chimera import dialogs
dialogs.register(ResRenumberDialog.name, ResRenumberDialog)
