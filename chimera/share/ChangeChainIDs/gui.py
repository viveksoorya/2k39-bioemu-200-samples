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

class ChangeChainsDialog(ModelessDialog):
	name = "change chains"
	buttons = ('OK', 'Apply', 'Close')
	default = 'OK'
	help = "ContributedSoftware/editing/changechains.html"

	def fillInUI(self, parent):
		import Tkinter, Pmw
		row = 0

		from chimera.widgets import MoleculeChainScrolledListBox
		self.chainList = MoleculeChainScrolledListBox(parent, labelpos='w',
			label_text="Rename chains:", listbox_selectmode="extended",
			selectioncommand=self._selCB)
		self.chainList.grid(row=row, column=0, sticky="nsew")
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(0, weight=1)
		self.entriesFrame = Tkinter.Frame(parent)
		self.entriesFrame.grid(row=row, column=1)
		self.entriesFrame.grid_remove()
		self.chooseChainsText = Tkinter.Label(parent, text=
			"Choose one or more chains\n"
			"from the list; for each, an\n"
			"entry field will be provided\n"
			"for entering the new ID")
		self.chooseChainsText.grid(row=row, column=1)
		row += 1

		from weakref import WeakKeyDictionary
		self.defaultVals = WeakKeyDictionary()
		self.entries = {}

	def Apply(self):
		from chimera import UserError
		from ChangeChainIDs import changeChains, ChainChangeError
		changes = {}
		for chain in self.chainList.getvalue():
			entry = self.entries[chain]
			entry.invoke()
			val = entry.getvalue().strip()
			if not val:
				val = entry.getvalue()
				if val != ' ':
					raise UserError("No value given to change %s to"
								% chain.fullName())
			if [c.chainID for c in chain.molecule.sequences()
					].count(chain.chainID) > 1:
				try:
					changeChains([chain.molecule], [(chain.chainID, val)],
						limitTo=chain)
				except ChainChangeError, v:
					self.enter()
					raise UserError(str(v))
			else:
				changes.setdefault(chain.molecule, []).append((chain.chainID, val))
		for mol, swaps in changes.items():
			try:
				changeChains([mol], swaps)
			except ChainChangeError, v:
				self.enter()
				raise UserError(str(v))

	def _selCB(self):
		curChains = self.chainList.getvalue()
		if curChains:
			self.chooseChainsText.grid_remove()
			self.entriesFrame.grid()
		else:
			self.entriesFrame.grid_remove()
			self.chooseChainsText.grid()
		for chain, entry in self.entries.items():
			if chain in curChains:
				entry.grid_configure(row=curChains.index(chain))
			else:
				entry.invoke()
				self.defaultVals[chain] = entry.getvalue()
				entry.grid_remove()
				entry.destroy()
				del self.entries[chain]

		for i, chain in enumerate(curChains):
			if chain in self.entries:
				continue
			import Pmw
			entry = Pmw.EntryField(self.entriesFrame, labelpos='w',
				label_text="%s %s to:" % (chain.molecule, chain.chainID),
				value=self.defaultVals.get(chain, ''), entry_width=1)
			entry.grid(row=i, column=0, sticky="e")
			self.entries[chain] = entry

from chimera import dialogs
dialogs.register(ChangeChainsDialog.name, ChangeChainsDialog)
