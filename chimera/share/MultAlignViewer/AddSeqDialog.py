# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: AddSeqDialog.py 42518 2024-03-18 19:12:44Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
from prefs import MATRIX, GAP_OPEN, GAP_EXTEND, \
	USE_SS, SS_MIXTURE, SS_SCORES, HELIX_OPEN, STRAND_OPEN, OTHER_OPEN

class AddSeqDialog(ModelessDialog):
	"""Insert all-gap columns"""

	buttons = ("OK", "Apply", "Close")
	help = "ContributedSoftware/multalignviewer/multalignviewer.html#add"
	
	def __init__(self, mav, *args, **kw):
		self.mav = mav
		self.title = "Add Sequence to %s" % (mav.title,)
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		self.seqNameEntry = Pmw.EntryField(parent, labelpos='w',
			label_text='Sequence name:', value= "added")
		self.seqNameEntry.grid(row=0, column=0, sticky="ew")

		f = Tkinter.Frame(parent)
		f.grid(row=1, column=0, sticky='ew')
		f.columnconfigure(0, weight=1)
		f.columnconfigure(1, weight=1)

		paramGroup = Pmw.Group(f, tag_text="Alignment Parameters")
		paramGroup.grid(row=0, column=0)

		import SmithWaterman
		matrixNames = SmithWaterman.matrices.keys()
		matrixNames.sort()
		if self.mav.prefs[MATRIX] in SmithWaterman.matrices:
			initialMatrix = self.mav.prefs[MATRIX]
		else:
			from prefs import defaultMatrix
			if defaultMatrix in SmithWaterman.matrices:
				initialMatrix = defaultMatrix
			else:
				initialMatrix = matrixNames[0]
		self.matrixMenu = Pmw.OptionMenu(paramGroup.interior(),
			command=lambda m: self.mav.prefs.update({MATRIX: m}),
			initialitem=initialMatrix, labelpos='w',
			label_text="Matrix:", items=matrixNames)
		self.matrixMenu.grid(row=0, column=0)

		gapGroup = Pmw.Group(paramGroup.interior(), tag_text="Gaps")
		gapGroup.grid(row=0, column=1)
		self.gapOpenEntry = Pmw.EntryField(gapGroup.interior(),
			labelpos='w', label_text="Opening penalty",
			validate='real', command=lambda : self.mav.prefs.update(
			{GAP_OPEN: float(self.gapOpenEntry.getvalue())}),
			entry_width=2, entry_justify='right',
			value="%g"%(self.mav.prefs[GAP_OPEN]))
		self.gapOpenEntry.grid(row=0, column=0, sticky='w')
		self.gapExtendEntry = Pmw.EntryField(gapGroup.interior(),
			labelpos='w', label_text="Extension penalty",
			validate='real', command=lambda : self.mav.prefs.update(
			{GAP_EXTEND: float(self.gapExtendEntry.getvalue())}),
			entry_width=2, entry_justify='right',
			value="%g"%(self.mav.prefs[GAP_EXTEND]))
		self.gapExtendEntry.grid(row=1, column=0, sticky='w')
		import string
		self.gapCharMenu = Pmw.OptionMenu(gapGroup.interior(), labelpos='w',
			label_text="Character", items=list(string.punctuation),
			initialitem=self.mav.gapChar())
		self.gapCharMenu.grid(row=2, column=0, sticky='w')
		Pmw.alignlabels([self.gapOpenEntry, self.gapExtendEntry,
						self.gapCharMenu], sticky='e')

		Tkinter.Button(paramGroup.interior(), text="Reset to defaults",
			command=self._reset2defaultsCB, pady=0).grid(
			row=1, column=0, columnspan=2)

		seqsFrame = Tkinter.Frame(f)
		seqsFrame.grid(row=0, column=1)
		Tkinter.Label(seqsFrame, text="Guide for aligning in new sequence..."
			).grid(row=0, column=0)
		self.guideVar = Tkinter.StringVar(parent)
		self.guideVar.set("alignment")
		subf = Tkinter.Frame(seqsFrame)
		subf.grid(row=1, column=0)
		Tkinter.Radiobutton(subf, text="All sequences", value="alignment",
			variable=self.guideVar, command=self._guideChange).grid(
			row=0, column=0, sticky='w')
		seqsGuideF = Tkinter.Frame(subf)
		seqsGuideF.grid(row=1, column=0, sticky='w')
		Tkinter.Radiobutton(seqsGuideF, text="Specified sequences...",
			value="seqs", variable=self.guideVar, command=self._guideChange
			).grid(row=0, column=0)
		self.guideSeqsList = Pmw.ScrolledListBox(seqsGuideF,
				listbox_exportselection=0, listbox_selectmode="extended")

		self.notebook = nb = Pmw.NoteBook(parent)
		nb.grid(row=2, column=0, sticky="nsew")

		textPage = nb.add("Plain Text")
		self.seqText = Pmw.ScrolledText(textPage, labelpos='nw',
					label_text='Sequence')
		self.seqText.grid(row=0, column=0, sticky="nsew")
		textPage.rowconfigure(0, weight=1)
		textPage.columnconfigure(0, weight=1)

		self.textAppendVar = Tkinter.IntVar(textPage)
		self.textAppendVar.set(True)
		Tkinter.Checkbutton(textPage, variable=self.textAppendVar,
			text="Simply append to alignment if sequence same"
			" length").grid(row=1, column=0)

		structPage = nb.add("From Structure")
		from chimera.widgets import MoleculeChainOptionMenu
		self.chainMenu = MoleculeChainOptionMenu(structPage)
		self.chainMenu.grid(row=0)
		from MatchMaker.gui import SSParams
		self.ssParams = SSParams(structPage, self.mav.prefs,
						useSSCB=self._useSSCB)
		self.ssParams.grid(row=1)

		filePage = nb.add("From File")
		from startup import openDialogFilters
		from chimera.tkoptions import InputFileTypeOption
		self.fileNameOption = InputFileTypeOption(filePage, 0, "File name",
			("", None), None, filters=openDialogFilters())
		self.fileAppendVar = Tkinter.IntVar(filePage)
		self.fileAppendVar.set(True)
		Tkinter.Checkbutton(filePage, variable=self.fileAppendVar,
			text="Simply append to alignment if all sequences same"
			" length as alignment").grid(row=1, column=0, columnspan=2)

		uniprotPage = nb.add("From UniProt")
		upWidth = 14
		uae = self.uniprotAccessionEntry = Pmw.EntryField(uniprotPage,
			labelpos='w', label_text="UniProt name/ID"
			" (e.g. P0AEE5 or DGAL_ECOLI):", entry_width=upWidth,
			command=self.OK)
		uae.grid(row=0, column=0, columnspan=2)
		uniprotPage.rowconfigure(1, minsize=".15i")
		Tkinter.Label(uniprotPage, text="You can convert other database"
			' identifiers to UniProt accession codes').grid(row=2, column=0,
			columnspan=2)
		Tkinter.Label(uniprotPage, text='by using the "ID'
			' Mapping" tab on the').grid(row=3, column=0, sticky='e')
		import webbrowser
		Tkinter.Button(uniprotPage, text="UniProt main page", pady=0,
			command=lambda wb=webbrowser, url="http://www.uniprot.org":
			wb.open(url)).grid(row=3, column=1, sticky='w')

		nb.setnaturalsize()
		nb.configure(raisecommand=self._pageRaised)

	def destroy(self):
		if getattr(self, '_gsHandler', None):
			from MAViewer import ADDDEL_SEQS
			self.mav.triggers.deleteHandler(ADDDEL_SEQS, self._gsHandler)
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		from chimera import UserError
		for entry in [self.seqNameEntry, self.gapOpenEntry,
							self.gapExtendEntry]:
			entry.invoke()
		seqName = self.seqNameEntry.getvalue().strip()
		if not seqName:
			self.enter()
			raise UserError("Must supply a sequence name")
		kw = { 'ssFraction': None, 'ssMatrix': None }
		pageName = self.notebook.getcurselection()
		if pageName == "Plain Text":
			import string
			seqString = "".join([c
					for c in self.seqText.getvalue().upper()
					if c not in string.whitespace])
			if not seqString:
				self.enter()
				raise UserError(
					"Must supply contents of sequence")

			if not seqString.isalpha() and not (self.textAppendVar.get()
			and len(seqString) == len(self.mav.seqs[0])):
				from chimera.baseDialog import AskYesNoDialog
				answer = AskYesNoDialog("Sequence contains gap characters"
					" and/or other non-alphabetic characters.  Such characters"
					" cannot be used when aligning the sequence with the"
					" existing alignment.  Remove these characters before"
					" aligning?").run(self.uiMaster())
				if answer == "no":
					self.enter()
					return
				seqString = "".join([c for c in seqString if c.isalpha()])
			seq = chimera.Sequence.Sequence(seqName)
			seq.extend(seqString)
			if self.textAppendVar.get() \
			and len(seq) == len(self.mav.seqs[0]):
				self.mav.addSeqs([seq])
				return
			seqs = [seq]
		elif pageName == "From Structure":
			seq = self.chainMenu.getvalue()
			if not seq:
				raise UserError("No structure sequence")
			if self.ssParams.useSSVar.get():
				kw['ssFraction'] = self.ssParams.ssMixture.get()
				kw['ssMatrix'] = self.ssParams.getMatrix()
				hg, sg, og = self.ssParams.getGaps()
				(kw['gapOpenHelix'], kw['gapOpenStrand'],
					kw['gapOpenOther']) = (0-hg, 0-sg, 0-og)
			seqs = [seq]
		elif pageName == "From File":
			filePath, fileType = self.fileNameOption.get()
			if not filePath:
				raise UserError("No file name specified")
			import os.path
			if not os.path.exists(filePath):
				raise UserError("File (%s) does not exist!" % filePath)
			from parse import parseFile
			seqs, fileAttrs, fileMarkups = parseFile(filePath, fileType,
												minSeqs=1, uniformLength=False)
			if self.fileAppendVar.get():
				sameLength = True
				for seq in seqs:
					if len(seq) != len(self.mav.seqs[0]):
						sameLength = False
						break
				if sameLength:
					self.mav.addSeqs(seqs)
					return
			seqName = None
			for seq in seqs:
				if not str(seq).isalpha():
					answer = AskRemoveCharsDialog().run(self.uiMaster())
					if answer == "remove":
						for s in seqs:
							s[:] = s.ungapped()
						break
					else:
						self.enter()
						return
		else: # UniProt
			from SeqAnnotations import uniprotFetch, InvalidAccessionError, \
				mapUniprotNameID

			nameID = self.uniprotAccessionEntry.component('entry').get().strip()
			try:
				uniprotID = mapUniprotNameID(nameID)
			except InvalidAccessionError:
				self.enter()
				replyobj.error("Invalid UniProt name/ID: %s" % nameID)
				return
			from chimera import CancelOperation
			try:
				seqString, fullName, features = uniprotFetch(uniprotID)
			except CancelOperation:
				self.mav.status("Fetch of %s cancelled" % uniprotID)
				return
			if seqName == "(UniProt name/ID)":
				seqName = nameID
			seq = chimera.Sequence.Sequence(seqName)
			seq.extend(seqString)
			seqs = [seq]

		if self.guideVar.get() == "seqs":
			guideIndices = self.guideSeqsList.component('listbox').curselection()
			if guideIndices:
				kw["guideSeqs"] = [self.mav.seqs[int(i)] for i in guideIndices]
			else:
				raise UserError("Specific-sequences-guidance option chosen"
					" but no sequences selected")
				self.enter()
		for seq in seqs:
			self.mav.alignSeq(seq, displayName=seqName,
				matrix=self.mav.prefs[MATRIX],
				gapChar=self.gapCharMenu.getvalue(),
				scoreGapOpen=0-self.mav.prefs[GAP_OPEN],
				scoreGap=0-self.mav.prefs[GAP_EXTEND], **kw)
		if pageName == "From UniProt":
			from SeqAnnotations import showUniprotFeatures
			showUniprotFeatures(self.mav, features)

	def _chainMenuCB(self, chain):
		if chain:
			if len(chain.molecule.sequences()) > 1:
				self.seqNameEntry.setvalue(
					"%s %s" % (chain.molecule.name, chain.name))
			else:
				self.seqNameEntry.setvalue(chain.molecule.name)
		else:
			self.seqNameEntry.setvalue("added")

	def _guideChange(self):
		from MAViewer import ADDDEL_SEQS
		if self.guideVar.get() == "alignment":
			if getattr(self, '_gsHandler', None):
				self.guideSeqsList.grid_remove()
				self.mav.triggers.deleteHandler(ADDDEL_SEQS, self._gsHandler)
				self._gsHandler = None
		else:
			if not hasattr(self, '_gsHandler'):
				self.guideSeqsList.setlist([s.name for s in self.mav.seqs])
			self.guideSeqsList.grid(row=0, column=1, sticky="nsew")
			self._gsHandler = self.mav.triggers.addHandler(ADDDEL_SEQS,
				self._seqsChangeCB, None)

	def _pageRaised(self, newPage):
		if newPage == "Plain Text":
			self.seqNameEntry.configure(entry_state="normal")
			self.seqNameEntry.setvalue("added")
			self.chainMenu.configure(command=None)
			self.gapOpenEntry.configure(label_state="normal",
						entry_state="normal")
		elif newPage == "From Structure":
			self.seqNameEntry.configure(entry_state="normal")
			self.chainMenu.configure(command=self._chainMenuCB)
			if self.chainMenu.getvalue():
				self.chainMenu.invoke()
			self._useSSCB()
		elif newPage == "From File":
			self.seqNameEntry.setvalue("from file")
			self.seqNameEntry.configure(entry_state="disabled")
			self.chainMenu.configure(command=None)
			self.gapOpenEntry.configure(label_state="normal",
						entry_state="normal")
		else: # UniProt
			self.seqNameEntry.configure(entry_state="normal")
			self.seqNameEntry.setvalue("(UniProt name/ID)")
			self.chainMenu.configure(command=None)
			self.gapOpenEntry.configure(label_state="normal",
						entry_state="normal")

	def _reset2defaultsCB(self):
		import SmithWaterman
		from prefs import defaults, MATRIX, GAP_OPEN, GAP_EXTEND
		if defaults[MATRIX] in SmithWaterman.matrices:
			self.matrixMenu.setvalue(defaults[MATRIX])
		self.gapOpenEntry.setvalue(str(defaults[GAP_OPEN]))
		self.gapExtendEntry.setvalue(str(defaults[GAP_EXTEND]))
		self.gapCharMenu.setvalue(self.mav.gapChar())

	def _seqsChangeCB(self, *args):
		newNames = [s.name for s in self.mav.seqs]
		oldNames = self.guideSeqsList.getvalue()
		self.guideSeqsList.setlist(newNames)
		reselect = []
		for on in oldNames:
			if newNames.count(on) == 1:
				reselect.append(on)
		if reselect:
			self.guideSeqsList.setvalue(reselect)

	def _useSSCB(self):
		if self.ssParams.useSSVar.get():
			state = 'disabled'
		else:
			state = 'normal'
		self.gapOpenEntry.configure(label_state=state,entry_state=state)

from chimera.baseDialog import AskYesNoDialog
class AskRemoveCharsDialog(AskYesNoDialog):
	buttons = ("Remove Non-Alphabetic Characters", "Return to Add-Seqs Dialog")

	def __init__(self):
		AskYesNoDialog.__init__(self, "Some of the sequences in the file contain"
			" gap characters and/or other non-alphabetic characters.  Such"
			" characters cannot be used when aligning a sequence with the"
			" existing alignment.  You can either choose to have these characters"
			" removed before aligning, or return to the Add Sequence dialog.\n\n"
			"If you are trying to add a sequence from a structure to an alignment,"
			" you should open the alignment first and then add the sequence from"
			" the structure to that.")

	def RemoveNonAlphabeticCharacters(self):
		AskYesNoDialog.Cancel(self, value='remove')

	def ReturntoAddSeqsDialog(self):
		AskYesNoDialog.Cancel(self, value='return')
