# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

ADD_ASSOC = "new association"
DEL_ASSOC = "delete association"
MOD_ASSOC = "association modified"
ADD_SEQS = "add sequences"
DEL_SEQS = "delete sequences"
PRE_DEL_SEQS = "before delete sequences"
ADDDEL_SEQS = "add or delete sequences"
SEQ_RENAMED = "sequence renamed"
MOD_ALIGN = "alignment composition changed" # includes reordering sequences
MATCHED_REGION_INFO = ("matched residues", (1, .88, .8), "orange red")

from SeqCanvas import ADD_HEADERS, DEL_HEADERS, SHOW_HEADERS, HIDE_HEADERS, \
							DISPLAY_TREE

from chimera.baseDialog import ModelessDialog
import os
import Tkinter, Pmw
from SeqCanvas import SeqCanvas
from RegionBrowser import RegionBrowser
import chimera
from chimera.Sequence import Sequence, StructureSequence, \
	StaticStructureSequence
from chimera import replyobj, CLOSE_SESSION, UserError, CancelOperation
from PrefDialog import PrefDialog
from prefs import prefs, LOAD_PDB_AUTO, LOAD_SCOP, \
	LOAD_PDB_NAME_EXACT, LOAD_PDB_NAME_START, LOAD_PDB_NAME_NCBI, \
	LOAD_PDB_NAME_VARSTART, LOAD_PDB_NAME_VARSTART_VAL, LOAD_PDB_DO_LIMIT, \
	LOAD_PDB_LIMIT, SHOW_SEL, CONSERVATION_STYLE, SHOW_RULER_AT_STARTUP, \
	MATCH_REG_ACTIVE, MATCH_REG_EDGE, MATCH_REG_FILL, \
	SINGLE_PREFIX, ERROR_REG_ACTIVE, ERROR_REG_EDGE, ERROR_REG_FILL, \
	GAP_REG_ACTIVE, GAP_REG_EDGE, GAP_REG_FILL, RESIDUE_COLORING
from SimpleSession import SAVE_SESSION

class MAViewer(ModelessDialog):
	"""
	MAViewer displays a multiple alignment
	"""

	buttons = ('Quit', 'Hide')
	help = "ContributedSoftware/multalignviewer/framemav.html"
	provideStatus = True
	statusWidth = 15
	statusPosition = "left"
	provideSecondaryStatus = True
	secondaryStatusPosition = "left"

	ConsAttr = "mavPercentConserved"

	MATCH_REG_NAME_START = "matches"
	ERROR_REG_NAME_START = "mismatches"
	GAP_REG_NAME_START = "missing structure"

	# so Model Loops tool can invoke it...
	MODEL_LOOPS_MENU_TEXT = "Modeller (loops/refinement)..."
	import RegionBrowser
	SEL_REGION_NAME = RegionBrowser.SEL_REGION_NAME

	def __init__(self, fileNameOrSeqs, fileType=None, autoAssociate=True,
				title=None, quitCB=None, frame=None, numberingDisplay=None,
				sessionSave=True):
		""" if 'autoAssocate' is None then it is the same as False except
		    that any StructureSequences in the alignment will be associated
			with their structures
		"""
		from chimera import triggerSet
		self.triggers = triggerSet.TriggerSet()
		self.triggers.addTrigger(ADD_ASSOC)
		self.triggers.addTrigger(DEL_ASSOC)
		self.triggers.addTrigger(MOD_ASSOC)
		self.triggers.addHandler(ADD_ASSOC, self._fireModAssoc, None)
		self.triggers.addHandler(DEL_ASSOC, self._fireModAssoc, None)
		self.triggers.addTrigger(ADD_SEQS)
		self.triggers.addTrigger(PRE_DEL_SEQS)
		self.triggers.addTrigger(DEL_SEQS)
		self.triggers.addTrigger(ADDDEL_SEQS)
		self.triggers.addTrigger(SEQ_RENAMED)
		self.triggers.addHandler(ADD_SEQS, self._fireAddDelSeq, None)
		self.triggers.addHandler(DEL_SEQS, self._fireAddDelSeq, None)
		self.triggers.addHandler(ADDDEL_SEQS, self._fireModAlign, None)
		self.triggers.addTrigger(MOD_ALIGN)
		self.associations = {}
		self._resAttrs = {}
		self._edited = False

		from common import getStaticSeqs
		seqs, fileMarkups, fileAttrs = getStaticSeqs(fileNameOrSeqs, fileType=fileType)
		self.seqs = seqs
		self.prefs = prefs
		from SeqCanvas import shouldWrap
		if numberingDisplay:
			defaultNumbering = numberingDisplay
		else:
			defaultNumbering = (True,
				not shouldWrap(len(seqs), self.prefs))
		self.numberingsStripped = False
		if getattr(seqs[0], 'numberingStart', None) is None:
			# see if sequence names imply numbering...
			startInfo = []
			for seq in seqs:
				try:
					name, numbering = seq.name.rsplit('/',1)
				except ValueError:
					break
				try:
					start, end = numbering.split('-')
				except ValueError:
					start = numbering
				try:
					startInfo.append((name, int(start)))
				except ValueError:
					break
			if len(startInfo) == len(seqs):
				self.numberingsStripped = True
				for i, seq in enumerate(seqs):
					seq.name, seq.numberingStart = \
								startInfo[i]
			else:
				for seq in seqs:
					if hasattr(seq, 'residues'):
						for i, r in enumerate(seq.residues):
							if r:
								seq.numberingStart = r.id.position - 1
								break
						else:
							seq.numberingStart = 1
					else:
						seq.numberingStart = 1
				if not numberingDisplay:
					defaultNumbering = (False, False)

		self._seqRenameHandlers = {}
		for seq in seqs:
			self._seqRenameHandlers[seq] = seq.triggers.addHandler(
				seq.TRIG_RENAME, self._seqRenameCB, None)
		self._defaultNumbering = defaultNumbering
		self.fileAttrs = fileAttrs
		self.fileMarkups = fileMarkups
		if not title:
			if isinstance(fileNameOrSeqs, basestring):
				title = os.path.split(fileNameOrSeqs)[1]
			else:
				title = "MultAlignViewer"
		self.title = title
		self.autoAssociate = autoAssociate
		self.quitCB = quitCB
		self.sessionSave = sessionSave
		self._frame = frame
		self._runModellerWSList = []
		self._runModellerLocalList = []
		self._realignmentWSJobs = {'self': [], 'new': []}
		self._blastAnnotationServices = {}
		ModelessDialog.__init__(self)
		chimera.extension.manager.registerInstance(self)

	def customUI(self, parent):
		"""Function to allow customization of the interface

		   'parent' is the interior frame of the dialog.
		   It can be populated with custom widgets as desired.
		   A frame should be returned by this function, in which
		   the MAViewer UI will be placed.
		"""
		return parent

	def fillInUI(self, parent):
		# allow for customization into other interfaces
		dialogParent = parent
		if self._frame:
			parent = self._frame
		else:
			parent = self.customUI(parent)
		delattr(self, '_frame')

		# SeqCanvas will use these...
		leftNums, rightNums = self._defaultNumbering
		self.leftNumberingVar = Tkinter.IntVar(parent)
		self.leftNumberingVar.set(leftNums)
		self.rightNumberingVar = Tkinter.IntVar(parent)
		self.rightNumberingVar.set(rightNums)

		self.seqCanvas = SeqCanvas(parent, self, self.seqs)
		self.regionBrowser = RegionBrowser(self.seqCanvas)
		if self.fileMarkups:
			from HeaderSequence import FixedHeaderSequence
			headers = []
			for name, val in self.fileMarkups.items():
				headers.append(
					FixedHeaderSequence(name, self, val))
			self.addHeaders(headers)
		self.prefDialog = PrefDialog(self)
		top = parent.winfo_toplevel()
		cb = lambda e, rb=self.regionBrowser: rb.deleteRegion(
								rb.curRegion())
		top.bind('<Delete>', cb)
		top.bind('<BackSpace>', cb)
		self.menuBar = Tkinter.Menu(top, type="menubar", tearoff=False)
		top.config(menu=self.menuBar)

		self.fileMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="File", menu=self.fileMenu)
		self.fileMenu.add_command(label="Save As...", command=self.save)
		self.epsDialog = None
		self.fileMenu.add_command(label="Save EPS...",
						command=self._showEpsDialog)
		self.fileMenu.add_command(label="Save Association Info...",
			state='disabled', command=self._showAssocInfoDialog)
		self.fileMenu.add_separator()
		self.fileMenu.add_command(label="Load SCF/Seqsel File...",
				command=lambda: self.loadScfFile(None))
		self.fileMenu.add_command(label="Load Color Scheme...",
					command=self._showColorSchemeDialog)
		self.fileMenu.add_separator()
		self.fileMenu.add_command(label="Hide", command=self.Hide)
		self.fileMenu.add_command(label="Quit", command=self.Quit)
		if parent == dialogParent:
			# if we're not part of a custom interface,
			# override the window-close button to quit, not hide
			top.protocol('WM_DELETE_WINDOW', self.Quit)

		self.editMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="Edit", menu=self.editMenu)
		self.editMenu.add_command(label="Copy Sequence...",
					command=self._showCopySeqDialog)
		self.editMenu.add_command(label="Reorder Sequences...",
					command=self._showReorderDialog)
		self.editMenu.add_command(label="Insert All-Gap Columns...",
					command=self._showInsertGapDialog)
		self.editMenu.add_command(label="Delete Sequences/Gaps...",
					command=self._showDelSeqsGapsDialog)
		self.editMenu.add_command(label="Add Sequence...",
					command=self._showAddSeqDialog)
		self.editMenu.add_command(label="Realign Sequences...",
					command=self._showRealignmentDialog)
		self.editMenu.add_command(label="Alignment Annotations...",
					command=self._showAlignAttrDialog)
		self.editMenu.add_command(label="Edit Sequence Name...",
					command=self._showSeqNameEditDialog)
		self.editMenu.add_command(label="Show Editing Keys...",
					command=self._showEditKeysDialog)
		self.editMenu.add_command(label=u"Region \N{RIGHTWARDS ARROW} New Window",
					command=self.exportActiveRegion)
		self.editMenu.add_separator()
		self.editMenu.add_command(label="Find Subsequence...",
					command=self._showFindDialog)
		self.editMenu.add_command(label="Find Regular Expression...",
					command=self._showRegexDialog)
		self.editMenu.add_command(label="Find PROSITE Pattern...",
					command=self._showPrositeDialog)
		self.editMenu.add_command(label="Find Sequence Name...",
					command=self._showFindSeqNameDialog)

		self.structureMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="Structure",
							menu=self.structureMenu)
		self.structureMenu.add_command(label="Load Structures",
						command=self._loadStructures)
		self.alignDialog = self.assessDialog = self.findDialog = None
		self.prositeDialog = self.regexDialog = None
		self.associationsDialog = self.findSeqNameDialog = None
		self.saveHeaderDialog = self.alignAttrDialog = None
		self.assocInfoDialog = self.loadHeaderDialog = None
		self.identityDialog = self.colorSchemeDialog = None
		self.modellerHomologyDialog = self.fetchAnnotationsDialog = None
		self.treeDialog = self.reorderDialog = self.blastPdbDialog = None
		self.delSeqsGapsDialog = self.insertGapDialog = None
		self.addSeqDialog = self.numberingsDialog = None
		self.editKeysDialog = self.copySeqDialog = None
		self.modellerLoopsDialog = self.seqNameEditDialog = None
		self.realignDialog = None
		self.structureMenu.add_command(label="Match...",
				state='disabled', command=self._showAlignDialog)
		
		self.structureMenu.add_command(label="Assess Match...",
			state='disabled', command=self._showAssessDialog)

		if len(self.seqs) <= 1:
			state = "disabled"
		else:
			state = "normal"
		self.structureMenu.add_command(label="Modeller (homology)...",
			state=state, command=self._showModellerHomologyDialog)
		self.structureMenu.add_command(label=self.MODEL_LOOPS_MENU_TEXT,
			state="disabled", command=self._showModellerLoopsDialog)

		if chimera.openModels.list(modelTypes=[chimera.Molecule]):
			assocState = 'normal'
		else:
			assocState = 'disabled'
		self.structureMenu.add_command(label="Associations...",
			state=assocState, command=self._showAssociationsDialog)
		self.ssMenu = Tkinter.Menu(self.structureMenu)
		self.structureMenu.add_cascade(label="Secondary Structure",
							menu=self.ssMenu)
		self.showSSVar = Tkinter.IntVar(parent)
		self.showSSVar.set(False)
		self.showPredictedSSVar = Tkinter.IntVar(parent)
		self.showPredictedSSVar.set(False)
		self.ssMenu.add_checkbutton(label="show actual",
			variable=self.showSSVar, command=lambda s=self: s.showSS(show=None))
		self.ssMenu.add_checkbutton(label="show predicted",
			variable=self.showPredictedSSVar,
			command=lambda s=self: s.showSS(show=None, ssType="predicted"))
		# actual SS part of MOD_ASSOC handler...
		self._predSSHandler = self.triggers.addHandler(ADD_SEQS,
			lambda a1, a2, a3, s=self:
			s.showSS(show=None, ssType="predicted"), None)
		self._resChangeHandler = chimera.triggers.addHandler(
			"Residue", self._resChangeCB, None)

		self.structureMenu.add_command(state='disabled',
				label="Select by Conservation...",
				command=lambda: self._doByConsCB("Select"))
		self.structureMenu.add_command(state='disabled',
				label="Render by Conservation...",
				command=lambda: self._doByConsCB("Render"))
		self.structureMenu.add_command(label="Expand Selection to"
				" Columns", state=assocState,
				command=self.expandSelectionByColumns)
		self._modAssocHandlerID = self.triggers.addHandler(
					MOD_ASSOC, self._modAssocCB, None)

		self.headersMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="Headers", menu=self.headersMenu)
		self.headersMenu.add_command(label="Save...",
			command=self._showSaveHeaderDialog)
		self.headersMenu.add_command(label="Load...",
					command=self._showLoadHeaderDialog)
		self.headersMenu.add_separator()
		for trig in [ADD_HEADERS,DEL_HEADERS,SHOW_HEADERS,HIDE_HEADERS,
								MOD_ALIGN]:
			self.triggers.addHandler(trig,
						self._rebuildHeadersMenu, None)
		self._rebuildHeadersMenu()

		self.numberingsMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="Numberings",
						menu=self.numberingsMenu)
		self.showRulerVar = Tkinter.IntVar(self.headersMenu)
		self.showRulerVar.set(
				len(self.seqs) > 1 and self.prefs[SHOW_RULER_AT_STARTUP])
		self.numberingsMenu.add_checkbutton(label="Overall Alignment",
						selectcolor="black",
						variable=self.showRulerVar,
						command=self.setRulerDisplay)
		self.numberingsMenu.add_separator()
		self.numberingsMenu.add_checkbutton(
					label="Left Sequence",
					selectcolor="black",
					variable=self.leftNumberingVar,
					command=self.setLeftNumberingDisplay)
		self.numberingsMenu.add_checkbutton(
					label="Right Sequence",
					selectcolor="black",
					variable=self.rightNumberingVar,
					command=self.setRightNumberingDisplay)
		self.numberingsMenu.add_command(
					label="Adjust Sequence Numberings...",
					command = self._showNumberingsDialog)

		self.treeMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="Tree", menu=self.treeMenu)
		self.treeMenu.add_command(label="Load...",
					command=self._showTreeDialog)
		self.showTreeVar = Tkinter.IntVar(self.menuBar)
		self.showTreeVar.set(True)
		self.treeMenu.add_checkbutton(label="Show Tree",
			selectcolor="black",
			variable=self.showTreeVar, command=self._showTreeCB,
			state='disabled')
		self.treeMenu.add_separator()
		self.treeMenu.add_command(label="Extract Subalignment",
			state="disabled", command=self.extractSubalignment)

		self.infoMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="Info", menu=self.infoMenu)
		if len(self.seqs) == 1:
			state = "disabled"
		else:
			state = "normal"
		self.infoMenu.add_command(label="Percent Identity...",
				state=state, command=self._showIdentityDialog)
		self.infoMenu.add_command(label="Region Browser",
					command=self.regionBrowser.enter)
		self.infoMenu.add_command(label="Blast Protein...",
					command=self._showBlastPdbDialog)
		self.infoMenu.add_command(label="UniProt Annotations...",
					command=self._showFetchAnnotationsDialog)
		self.preferencesMenu = Tkinter.Menu(self.menuBar)
		self.menuBar.add_cascade(label="Preferences",
						menu=self.preferencesMenu)

		from chimera.tkgui import aquaMenuBar
		aquaMenuBar(self.menuBar, parent, row = 0, columnspan = 4)

		for tab in self.prefDialog.tabs:
			self.preferencesMenu.add_command(label=tab,
				command=lambda t=tab: [self.prefDialog.enter(),
				self.prefDialog.notebook.selectpage(t)])

		self.status("Mouse drag to create region (replacing current)\n",
			blankAfter=30, followTime=40, followWith=
			"Shift-drag to add to current region\n"
			"Control-drag to add new region")
		self._addHandlerID = chimera.openModels.addAddHandler(
						self._newModelsCB, None)
		self._removeHandlerID = chimera.openModels.addRemoveHandler(
						self._closeModelsCB, None)
		self._closeSessionHandlerID = chimera.triggers.addHandler(
			CLOSE_SESSION, lambda t, a1, a2, s=self: s.Quit(), None)
		self._monitorChangesHandlerID = None
		# deregister other handlers on APPQUIT...
		chimera.triggers.addHandler(chimera.APPQUIT, self.destroy, None)
		if self.autoAssociate == None:
			if len(self.seqs) == 1:
				self.intrinsicStructure = True
			else:
				self.autoAssociate = False
				self.associate(None)
		else:
			self._newModelsCB(models=chimera.openModels.list())
		self._makeSequenceRegions()
		if self.prefs[LOAD_PDB_AUTO]:
			# delay calling _loadStructures to give any structures
			# opened along with MAV a chance to load
			parent.after_idle(lambda: self._loadStructures(auto=1))

	def addHeaders(self, headers):
		"""add header sequences -- implies show"""
		self.seqCanvas.addHeaders(headers)
	
	def addSeqs(self, seqs, addAssoc=True):
		self.intrinsicStructure = False
		for seq in seqs:
			if seq.numberingStart is None:
				seq.numberingStart = 1
		from SeqCanvas import shouldWrap
		self.seqCanvas.addSeqs(seqs)
		self.seqs.extend(seqs)
		if shouldWrap(len(self.seqs), self.prefs) == shouldWrap(
								len(self.seqs) - len(seqs), self.prefs):
			self.seqCanvas.refreshTree()
		else:
			self.seqCanvas._newWrap()
		# block the association trigger until sequence menus have
		# a chance to update themselves
		self.triggers.blockTrigger(ADD_ASSOC)
		if addAssoc:
			for seq in seqs:
				self.associate(chimera.openModels.list(),
							seq=seq, force=False)
		if len(seqs) == len(self.seqs) - 1:
			# going from single sequence to multiple...
			if self.seqCanvas.lineWidth != self.seqCanvas.lineWidthFromPrefs():
				self.seqCanvas._newWrap()
			else:
				self.seqCanvas._reformat()
			if self.prefs[SHOW_RULER_AT_STARTUP]:
				self.setRulerDisplay(showRuler=True)
			self.seqCanvas.setColorFunc(self.prefs[RESIDUE_COLORING])

		self.triggers.activateTrigger(ADD_SEQS, seqs)
		self.triggers.releaseTrigger(ADD_ASSOC)
		self.setResidueAttrs()
		for seq in seqs:
			self._seqRenameHandlers[seq] = seq.triggers.addHandler(
				seq.TRIG_RENAME, self._seqRenameCB, None)

	def alignSeq(self, newSeq, displayName=None, matrix="BLOSUM-62", gapChar='.',
			ssFraction=None, honorMarkups=True, guideSeqs=None, **kw):
		"""align in a new sequence"""
		if isinstance(newSeq, StructureSequence) \
		and newSeq.molecule in self.associations:
			self.status("disassociating previous sequence association")
			self.disassociate(newSeq.molecule)
		self.status("collating sequences")
		import SmithWaterman
		simMatrix = SmithWaterman.matrices[matrix]
		protoFreqDict = {}
		for rt1, rt2 in simMatrix.keys():
			protoFreqDict[rt1] = 0
		profileSeq = Sequence('profile')
		profileSeq.extend('a' * len(self.seqs[0]))
		helix, strand, other = Sequence.SS_HELIX, Sequence.SS_STRAND, \
							Sequence.SS_OTHER
		if not guideSeqs:
			guideSeqs = self.seqs
		profileSeq.occupancy = []
		if ssFraction != None:
			profileSeq.ssFreqs = []
			profileSeq.gapFreqs = []
			def ssType(r):
				if r.isHelix:
					return helix
				elif r.isStrand:
					return strand
				return other
		freqDicts = [None] * len(self.seqs[0])
		for i in range(len(self.seqs[0])):
			numGaps = 0
			if ssFraction != None:
				ssFreqs = {}
				profileSeq.ssFreqs.append(ssFreqs)
				gapFreqs = {helix: 0, strand: 0, other: 0}
				profileSeq.gapFreqs.append(gapFreqs)
				numSS = ssGaps = 0
			freqDicts[i] = fd = protoFreqDict.copy()
			endSeq = (i+1) >= len(self.seqs[0])
			for seq in guideSeqs:
				hasSS = hasattr(seq, 'matchMaps') or (
					honorMarkups and 'SS' in seq.markups)
				ungapped = seq.gapped2ungapped(i)
				if ungapped == None:
					numGaps += 1
					if ssFraction != None and hasSS:
						ssGaps += 1
					continue
				try:
					for rt in fd.keys():
						fd[rt] += simMatrix[
								(rt, seq[i].upper())]
				except KeyError:
					raise UserError("Residue type (%s or %s) not found in"
						" similarity matrix.\nEnsure you are using a type"
						" of similarity matrix appropriate for your sequence,"
						" namely a protein matrix (i.e. BLOSUM/PAM) for"
						" proteins or 'nucleic' for nucleic acids." %
						(rt, seq[i].upper()))
				if ssFraction == None or not hasSS:
					continue
				ssVals = []
				if not endSeq:
					nextUngapped = seq.gapped2ungapped(i+1)
					if nextUngapped == None:
						ssGaps += 1
						continue
				if hasattr(seq, 'matchMaps'):
					for matchMap in seq.matchMaps.values():
						if ungapped not in matchMap:
							continue
						ssVal = ssType(
							matchMap[ungapped])
						if endSeq or (nextUngapped not
								in matchMap):
							ssVals.append((ssVal,
									None))
						else:
							ssVals.append((ssVal,
								ssType(matchMap[
								nextUngapped])))
					if not ssVals:
						continue
				else:
					ssVal = seq.ssType(ungapped,
							locIsUngapped=True)
					if endSeq:
						ssVals.append((ssVal, None))
					else:
						ssVals.append((ssVal,
							seq.ssType(nextUngapped,
							locIsUngapped=True)))
				numSS += 1
				ssValIncr = 1.0 / float(len(ssVals))
				for ssVal, nextSSVal in ssVals:
					ssFreqs[ssVal] = ssFreqs.get(ssVal,
							0) + ssValIncr
				if endSeq:
					continue

				for ssVal, nextSSVal in ssVals:
					gapType = other
					if ssVal == nextSSVal:
						gapType = ssVal
					gapFreqs[gapType] += ssValIncr

			occupancy = (len(guideSeqs) - numGaps) \
					/ float(len(guideSeqs))
			profileSeq.occupancy.append(occupancy)
			if numGaps > 0:
				for k, v in fd.items():
					fd[k] = fd[k] * occupancy
			if ssFraction != None and numSS + ssGaps == 0:
				ssFraction = None
			if ssFraction != None and numSS > 0:
				occ = numSS / float(numSS + ssGaps)
				for let, num in gapFreqs.items():
					gapFreqs[let] = occ * num / float(numSS)

				if numSS > 0:
					for let, num in ssFreqs.items():
						ssFreqs[let] = occ * num \
							/ float(numSS)
		div = float(len(guideSeqs))
		for fd in freqDicts:
			for k, v in fd.items():
				fd[k] = fd[k] / div
		self.status("running Needleman-Wunsch")
		from NeedlemanWunsch import nw
		score, gappedSeqs = nw(newSeq, profileSeq,
				returnSeqs=True, frequencyMatrix=freqDicts,
				gapChar=gapChar, ssFraction=ssFraction, **kw)
		self.status("adjust gapping")
		# adjust alignment for gapping of reference seq
		gapStart = None
		gaps = []
		for i, c in enumerate(gappedSeqs[1]):
			if c == 'a':
				if gapStart is None:
					continue
				gaps.append((i - gapStart, gapStart -
						gappedSeqs[1][:gapStart]
						.count(gapChar)))
				gapStart = None
			else:
				if gapStart is None:
					gapStart = i
		if gapStart is not None:
			gaps.append((len(gappedSeqs[1]) - gapStart, gapStart
				- gappedSeqs[1][:gapStart].count(gapChar)))
		if gaps:
			# avoid calling self.insertGap() since it in turn
			# calls self.realign() every time, which is quite
			# slow and really only needs to be called once at
			# the end
			seqs2 = []
			for seq in self.seqs:
				seq2 = Sequence(seq.name)
				seqs2.append(seq2)
				prevColumn = 0
				for amount, column in gaps:
					insert = gapChar * amount
					seq2.extend(seq[prevColumn:column])
					seq2.extend(insert)
					prevColumn = column
				seq2.extend(seq[prevColumn:])
				self._gapMarkups(seq, gaps)
			self._gapFixedHeaders(gaps)
			self.seqCanvas.realign(seqs2, handleRegions=False)
		# need a Sequence, not a StructureSequence
		if isinstance(newSeq, StructureSequence) \
		and not isinstance(newSeq, StaticStructureSequence):
			alignSeq = newSeq.static()
		else:
			from copy import copy
			alignSeq = copy(newSeq)
		alignSeq[:] = gappedSeqs[0]
		if displayName:
			alignSeq.name = displayName
		alignGaps = []
		ungappedIndex = 0
		gapStart = None
		for i, c in enumerate(alignSeq):
			if ungappedIndex < len(newSeq) and c == newSeq[ungappedIndex]:
				ungappedIndex += 1
				if gapStart != None:
					alignGaps.append((i - gapStart, gapStart))
					gapStart = None
			elif gapStart == None:
				gapStart = ungappedIndex
		if gapStart is not None:
			alignGaps.append((len(newSeq) - gapStart, gapStart))
		self._gapMarkups(alignSeq, alignGaps)
		self.status("add sequence to alignment")
		addAssoc = not isinstance(alignSeq, StructureSequence)
		self.addSeqs([alignSeq], addAssoc=addAssoc)
		cumAmount = 0
		for amount, column in gaps:
			self.regionBrowser.moveRegions(amount, exceptBottom=alignSeq,
						startOffset=column+cumAmount)
			cumAmount += amount
		if not addAssoc:
			self.status("associate structure with new sequence")
			self.associate(None, seq=alignSeq)
		self.status("done adding sequence to alignment")
		self._edited = True

	def assessMatch(self, refMol, evalMols, attrName):
		from chimera.misc import stringToAttr
		attrName = stringToAttr(attrName, collapse=False)
		refSeq = self.associations[refMol]
		refMatchMap = refSeq.matchMaps[refMol]
		for evalMol in evalMols:
			evalSeq = self.associations[evalMol]
			matchMap = evalSeq.matchMaps[evalMol]
			for i in range(len(evalSeq.ungapped())):
				gi = evalSeq.ungapped2gapped(i)
				refUngapped = refSeq.gapped2ungapped(gi)
				if refUngapped is None \
				or not refMatchMap.has_key(refUngapped) \
				or not matchMap.has_key(i):
					continue
				refRes = refMatchMap[refUngapped]
				res = matchMap[i]
				for keyAtom in ["CA", "C4'", "P"]:
					if refRes.atomsMap.has_key(keyAtom) \
					and res.atomsMap.has_key(keyAtom):
						key = keyAtom
						break
				else:
					continue
				refAtom = refRes.atomsMap[keyAtom][0]
				atom = res.atomsMap[keyAtom][0]
				setattr(res, attrName, refAtom.xformCoord()
						.distance(atom.xformCoord()))

	def associate(self, models, seq=None, force=True, minLength=10,
					showMatches=None, showErrors=None, reassoc=False):
		"""associate models with sequences

		   'models' is normally a list of models, but it can be
		   a Sequence instance or None.  If it's a Sequence, it
		   should be a Sequence of a particular chain of a model.
		   If None, then some or all of the alignment sequences
		   have 'residues' attributes indicating their corresponding
		   model; set up the proper associations.

		   if 'seq' is given, associate only with that sequence,
		   otherwise consider all sequences in alignment.  If a
		   non-empty list of models is provided and 'force' is
		   False, then it is assumed that the seq has just been
		   added to the alignment and that associations are being
		   re-evaluated.

		   If force is True, then if no association meets the
		   built-in association criteria, then use Needleman-
		   Wunsch to force an association with at least one
		   sequence.

		   If a chain is less than 'minLength' residues,
		   ignore it.

		   'showMatches' and 'showErrors' control whether
		   regions will be created indicating matches and errors.
		   A complete, error-free matchup will not have
		   regions created regardless. Values of None indicate
		   that the user preference should be used.
		"""
		from structAssoc import tryAssoc, nwAssoc, estimateAssocParams
		from chimera.Sequence import Sequence, StructureSequence
		from prefs import ASSOC_ERROR_RATE
		reeval = False
		if isinstance(models, Sequence):
			molecules = [models]
		elif models is None:
			for seq in self.seqs:
				if isinstance(seq, StructureSequence) \
				and seq.molecule not in self.associations:
					self.associate([], seq=seq, reassoc=reassoc)
			return
		else:
			molecules = [m for m in models if isinstance(m, chimera.Molecule)
				and getattr(m, "isRealMolecule", True)]
			if molecules and seq and not force:
				reeval = True
		# sort alignment sequences from shortest to longest;
		# a match against a shorter sequence is better than a
		# match against a longer sequence for the same number
		# of errors (except for structure sequences _longer_
		# than alignment sequences, handled later)
		newMatchMaps = []
		if seq:
			if isinstance(seq, StructureSequence) \
			and not isinstance(models, Sequence):
				# if the sequence we're being asked to set up
				# an association for is a StructureSequence
				# then we already know what molecule
				# it associates with and how...
				molecules = []
				matchMap = {}
				for res, index in seq.resMap.items():
					matchMap[res] = index
					matchMap[index] = res
				self.prematchedAssocStructure(seq, seq, matchMap, 0,
						showMatches, showErrors, reassoc)
				newMatchMaps.append(matchMap)
			else:
				aseqs = [seq]
		else:
			aseqs = self.seqs[:]
			aseqs.sort(lambda a, b:
				cmp(len(a.ungapped()), len(b.ungapped())))
		if molecules:
			forwAseqs = aseqs
			revAseqs = aseqs[:]
			revAseqs.reverse()
		for mol in molecules:
			if isinstance(mol, Sequence):
				mseqs = [mol]
				mol = mol.molecule
			else:
				mseqs = mol.sequences()
				# sort sequences so that longest is tried
				# first
				mseqs.sort(lambda a, b: 0 - cmp(len(a),len(b)))
			assocInfo = None
			molName = os.path.split(mol.name)[-1]
			if '.' in mol.oslIdent():
				# ensemble
				molName += " (" + mol.oslIdent() + ")"
			for mseq in mseqs:
				if len(mseq) < minLength:
					continue

				# find the apparent gaps in the structure,
				# and estimate total length of structure
				# sequence given these gaps;
				# make a list of the continuous segments
				estLen, segments, gaps = estimateAssocParams(mseq)
				if not force:
					if len(segments) > 10 and len(segments[0]) == 1 \
					and segments.count(segments[0]) == len(segments):
						# some kind of bogus structure (e.g. from SAXS)
						return

				if estLen >= len(forwAseqs[-1].ungapped()):
					# structure sequence longer than
					# alignment sequence; match against
					# longest alignment sequences first
					aseqs = revAseqs
				elif estLen > len(forwAseqs[0].ungapped()):
					# mixture of longer and shorter
					# alignment seqs; do special sorting
					mixed = aseqs[:]
					mixed.sort(lambda a, b:
							_mixSort(a, b, estLen))
					aseqs = mixed
				else:
					aseqs = forwAseqs
				bestSeq = bestErrors = None
				maxErrors = len(mseq) / self.prefs[
							ASSOC_ERROR_RATE]
				if reeval:
					if mol in self.associations:
						aseqs = [self.associations[mol],
									seq]
					else:
						aseqs = [seq]
				for aseq in aseqs:
					if bestErrors:
						tryErrors = bestErrors - 1
					else:
						tryErrors = maxErrors
					try:
						matchMap, errors = tryAssoc(
							aseq, mseq, segments,
							gaps, estLen,
							maxErrors=tryErrors)
					except ValueError:
						# maybe the sequence is
						# derived from the structure...
						if gaps:
							try:
								matchMap, \
								errors = \
								tryAssoc(aseq,
								mseq, [mseq[:]],
								[], len(mseq),
								maxErrors=
								tryErrors)
							except ValueError:
								continue
						else:
							continue
					else:
						# if the above worked but
						# had errors, see if just
						# smooshing sequence together
						# works better
						if errors and gaps:
							try:
								matchMap, \
								errors = \
								tryAssoc(aseq,
								mseq, [mseq[:]],
								[], len(mseq),
								maxErrors=
								errors-1)
							except ValueError:
								pass

					bestMatchMap = matchMap
					bestErrors = errors
					bestSeq = aseq
					if errors == 0:
						break

				if bestSeq:
					if assocInfo \
					and bestErrors >= assocInfo[-1]:
						continue
					assocInfo = (bestSeq, mseq,
						bestMatchMap, bestErrors)
			if not assocInfo and force:
				# nothing matched built-in criteria
				# use Needleman-Wunsch
				bestSeq = bestMseq = bestErrors = None
				maxErrors = len(mseq) / self.prefs[
							ASSOC_ERROR_RATE]
				for mseq in mseqs:

					# aseqs are already sorted by length...
					for aseq in aseqs:
						self.status(
		"Using Needleman-Wunsch to test-associate %s %s with %s\n"
							% (molName,
							mseq.name, aseq.name))
						matchMap, errors = nwAssoc(
								aseq, mseq)
						if not bestSeq \
						or errors < bestErrors:
							bestMatchMap = matchMap
							bestErrors = errors
							bestSeq = aseq
							bestMseq = mseq
				if bestMatchMap:
					assocInfo = (bestSeq, bestMseq,
						bestMatchMap, bestErrors)
				else:
					self.status("No reasonable association"
						" found for %s %s\n" % (molName,
						mseq.name))

			if assocInfo:
				bestSeq, mseq, bestMatchMap, bestErrors = \
								assocInfo
				if reeval \
				and mseq.molecule in self.associations:
					oldAseq = self.associations[
								mseq.molecule]
					if oldAseq == bestSeq:
						continue
					self.disassociate(mseq.molecule)
				msg = "Associated %s %s to %s with %d error(s)"\
						"\n" % (molName, mseq.name,
						bestSeq.name, bestErrors)
				self.status(msg, log=1, followWith=
					"Right-click to focus on residue\n"
					"Right-shift-click to focus on region",
					followLog=False, blankAfter=10)
				self.prematchedAssocStructure(bestSeq, mseq,
						bestMatchMap, bestErrors,
						showMatches, showErrors, reassoc)
				newMatchMaps.append(bestMatchMap)
		if self.intrinsicStructure and len(self.seqs) == 1:
			self.showSS()
			self.status("Helices/strands depicted in gold/green")
		if newMatchMaps:
			if reassoc:
				trigName = MOD_ASSOC
				trigData = (ADD_ASSOC, newMatchMaps)
			else:
				trigName = ADD_ASSOC
				trigData = newMatchMaps
			self.triggers.activateTrigger(trigName, trigData)
			if self.prefs[SHOW_SEL]:
				self.regionBrowser.showChimeraSelection()

	def blast(self, seq):
		from blastpdb.gui import BlastDialog, BlastResultsDialog
		param = BlastDialog(master=self.uiMaster()).run(self.uiMaster())
		if not param:
			return
		BlastResultsDialog(seq=seq, blastData=param)

	def computeRealignment(self, serviceName, inOutFlags, options,
			destination=True, reordersSequences=False):
		# destination:
		#	True: this MAV
		#	string: new MAV with that title
		#	(False: raw sequences)
		from RealignBase import RunRealignmentWS
		from chimera.Sequence import Sequence
		inputSeqs = []
		for seq in self.seqs:
			inputSeq = Sequence(seq.name)
			inputSeq[:] = seq.ungapped()
			inputSeqs.append(inputSeq)
		if destination == True:
			destination = self
		RunRealignmentWS(self._addRealignmentJob, self._removeRealignmentJob,
			self._removeRealignmentJob, serviceName=serviceName,
			inOutFlags=inOutFlags, options=options, seqs=inputSeqs,
			mav=destination, reordersSequences=reordersSequences)

	def currentRegion(self):
		return self.regionBrowser.curRegion()

	def dehighlightName(self):
		"used to cancel highlight caused by seeSeq()"
		self.seqCanvas.dehighlightName()

	def deleteAllGaps(self):
		"delete all-gap columns"
		allGap = set()
		for i in range(len(self.seqs[0])):
			for s in self.seqs:
				if not s.isGap(i):
					break
			else:
				allGap.add(i)
		if not allGap:
			return
		from chimera.Sequence import Sequence
		newSeqs = []
		for s in self.seqs:
			ns = Sequence()
			newSeqs.append(ns)
			ns.extend([x for i, x in enumerate(s)
							if i not in allGap])

		# fix up fixed headers
		from HeaderSequence import FixedHeaderSequence
		for hdr in self.headers():
			if not isinstance(hdr, FixedHeaderSequence):
				continue
			hdr.vals = [x for i, x in enumerate(hdr.vals)
							if i not in allGap]
			if hasattr(hdr, 'colors'):
				hdr.colors = [x for i, x in enumerate(hdr.colors)
							if i not in allGap]

		# fix up markups
		for seq in self.seqs:
			for k, v in seq.markups.items():
				newMarkup = [x for i, x in enumerate(list(v))
								if i not in allGap]
				if type(v) == list:
					seq.markups[k] = newMarkup
				else:
					seq.markups[k] = "".join(newMarkup)

		# fix up regions
		ag = list(allGap)
		ag.sort()
		for reg in self.regionBrowser.regions:
			newBlocks = []
			for line1, line2, pos1, pos2 in reg.blocks:
				adjust1 = adjust2 = 0
				for gap in ag:
					if gap > pos2:
						break
					adjust2 += 1
					if gap < pos1:
						adjust1 += 1
				np1 = pos1 - adjust1
				np2 = pos2 - adjust2
				if np2 < np1:
					continue
				newBlocks.append((line1, line2, np1, np2))
			reg.blocks = newBlocks
		# realign will probably redraw the regions, so need to fix them
		# up first (so they don't hang off the end of the alignment)
		self.realign(newSeqs, offset=0, markEdited=True, handleRegions=False)
		# need redraw after realign so that the "cover gaps" property
		# of regions works properly
		self.regionBrowser.redrawRegions(cullEmpty=True)

	def deleteHeaders(self, headers):
		"""delete header sequences"""
		self.seqCanvas.deleteHeaders(headers)
		
	def deleteSeqs(self, delSeqs):
		if not delSeqs:
			return
		delSeqs = set(delSeqs)
		if len(self.seqs) - len(delSeqs) < 1:
			raise UserError("Must leave at least one sequence in"
				" alignment!")
		if len(self.seqs) - len(delSeqs) == 1:
			self.hideHeaders([hd
				for hd in self.seqCanvas.headerDisplayOrder()
					if not hd.singleSequenceRelevant])
		for seq in delSeqs:
			if seq in self._blastAnnotationServices:
				self._blastAnnotationServices[seq][0].task.cancel()
				# cancel will cause callback that updates _blastAnn... dict
			if not hasattr(seq, 'matchMaps'):
				continue
			for mol in seq.matchMaps.keys():
				self.disassociate(mol)

		self.triggers.activateTrigger(PRE_DEL_SEQS, delSeqs)
		self.seqs[:] = [s for s in self.seqs if s not in delSeqs]
		self.seqCanvas._reformat(cullEmpty=True)
		self.triggers.activateTrigger(DEL_SEQS, delSeqs)
		self.setResidueAttrs()
		for seq in delSeqs:
			seq.triggers.deleteHandler(seq.TRIG_RENAME,
				self._seqRenameHandlers[seq])
			del self._seqRenameHandlers[seq]
		self._edited = True

	def destroy(self, *args):
		if self._modAssocHandlerID is None:
			# previously destroyed
			return
		self._inDestroy = True
		self.triggers.deleteHandler(MOD_ASSOC, self._modAssocHandlerID)
		self.triggers.deleteHandler(ADD_SEQS, self._predSSHandler)
		chimera.triggers.deleteHandler(CLOSE_SESSION,
						self._closeSessionHandlerID)
		chimera.triggers.deleteHandler("Residue", self._resChangeHandler)
		self.sessionSave = False
		if self._monitorChangesHandlerID:
			chimera.triggers.deleteHandler('monitor changes',
						self._monitorChangesHandlerID)
		chimera.openModels.deleteAddHandler(self._addHandlerID)
		chimera.openModels.deleteRemoveHandler(self._removeHandlerID)

		self._modAssocHandlerID = None
		self.regionBrowser.destroy()
		self.prefDialog.destroy()
		self.seqCanvas.destroy()
		for dialog in [self.alignDialog, self.assessDialog,
				self.associationsDialog, self.findDialog,
				self.prositeDialog, self.saveHeaderDialog,
				self.alignAttrDialog, self.epsDialog,
				self.assocInfoDialog, self.loadHeaderDialog,
				self.identityDialog, self.colorSchemeDialog,
				self.treeDialog, self.reorderDialog,
				self.delSeqsGapsDialog, self.insertGapDialog,
				self.addSeqDialog, self.numberingsDialog,
				self.editKeysDialog, self.copySeqDialog,
				self.modellerHomologyDialog, self.blastPdbDialog,
				self.fetchAnnotationsDialog, self.modellerLoopsDialog,
				self.seqNameEditDialog, self.regexDialog,
				self.realignDialog, self.findSeqNameDialog]:
			if dialog:
				dialog.destroy()
		chimera.extension.manager.deregisterInstance(self)
		for mol, seq in self.associations.items():
			matchMap = seq.matchMaps[mol]
			mseq = matchMap["mseq"]
			mseq.triggers.deleteHandler(mseq.TRIG_DELETE,
						matchMap["mavDelHandler"])
			mseq.triggers.deleteHandler(mseq.TRIG_MODIFY,
						matchMap["mavModHandler"])
		for blast, cbKw in self._blastAnnotationServices.values():
			blast.task.cancel()
		ModelessDialog.destroy(self)

	def disassociate(self, mol, reassoc=False):
		beingDestroyed = getattr(self, '_inDestroy', False)
		if mol not in self.associations or beingDestroyed:
			return
		seq = self.associations[mol]
		if not (mol.__destroyed__ or reassoc):
			self.status("Disassociating %s from %s" % (mol.name,seq.name))
		matchMap = seq.matchMaps[mol]
		del seq.matchMaps[mol]
		del self.associations[mol]
		self.seqCanvas.assocSeq(seq)
		if not seq.matchMaps:
			delattr(seq, 'matchMaps')
		mseq = matchMap["mseq"]
		mseq.triggers.deleteHandler(mseq.TRIG_DELETE,
						matchMap["mavDelHandler"])
		mseq.triggers.deleteHandler(mseq.TRIG_MODIFY,
						matchMap["mavModHandler"])
		if reassoc:
			return
		if self._monitorChangesHandlerID:
			self._monitorChangesData.append(matchMap)
		elif chimera.update.inTriggerProcessing:
			# need to slide DEL_ASSOC trigger to after checkForChanges
			self._monitorChangesData = [matchMap]
			self._monitorChangesHandlerID = chimera.triggers.addHandler(
							'monitor changes', self._monitorChangesCB,
							self._monitorChangesData)
		else:
			# should process DEL_ASSOC immediately (to preserve order
			# of ADD/DEL which is important for residue attributes)
			self._monitorChangesCB(DEL_ASSOC, [matchMap], None)
		if self.prefs[SHOW_SEL]:
			self.regionBrowser.showChimeraSelection()
		if not mol.__destroyed__:
			self.status("Disassociated %s from %s\n"
					% (mol.name, seq.name), log=True)
			
	def emHide(self):
		"""Extension manager method"""
		self.regionBrowser.Cancel()
		self.prefDialog.Cancel()
		for dialog in [self.alignDialog, self.assessDialog,
				self.associationsDialog, self.findDialog,
				self.prositeDialog, self.saveHeaderDialog,
				self.alignAttrDialog, self.epsDialog,
				self.assocInfoDialog, self.loadHeaderDialog,
				self.identityDialog, self.colorSchemeDialog,
				self.treeDialog, self.reorderDialog,
				self.delSeqsGapsDialog, self.insertGapDialog,
				self.addSeqDialog, self.numberingsDialog,
				self.editKeysDialog, self.copySeqDialog,
				self.modellerHomologyDialog, self.blastPdbDialog,
				self.fetchAnnotationsDialog, self.modellerLoopsDialog,
				self.seqNameEditDialog, self.regexDialog,
				self.realignDialog, self.findSeqNameDialog]:
			if dialog:
				dialog.Cancel()
		ModelessDialog.Cancel(self)

	def emName(self):
		"""Extension manager method"""
		return "MAV - " + self.title

	def emQuit(self):
		"""Extension manager method"""
		if self._runModellerWSList + self._runModellerLocalList:
			from chimera.baseDialog import AskYesNoDialog
			if AskYesNoDialog("Quitting will cancel running Modeller jobs.\n"
					"Quit anyway?", default="No").run(self.uiMaster()) == "no":
				return
			# this is here instead of destroy() since destroy() gets called on APPQUIT
			for modjob in self._runModellerWSList + self._runModellerLocalList:
				# use try/except to avoid possible race condition
				try:
					modjob.terminate()
				except AttributeError:
					pass
		if self._realignmentWSJobs['self']:
			from chimera.baseDialog import AskYesNoDialog
			if AskYesNoDialog("Quitting will cancel running sequence"
					" realignment job.\n"
					"Quit anyway?", default="No").run(self.uiMaster()) == "no":
				return
			# this is here instead of destroy() since destroy() gets called on APPQUIT
			for job in self._realignmentWSJobs['self']:
				# use try/except to avoid possible race condition
				try:
					job.ws.task.cancel()
				except AttributeError:
					pass
		if self.quitCB and self.quitCB(self) != None:
			return
		self.quitCB = None
		self.destroy()

	def emRaise(self):
		"""Extension manager method"""
		self.enter()

	def expandSelectionByColumns(self):
		selResidues = chimera.selection.currentResidues(asDict=True)
		if not selResidues:
			raise UserError("No selection to expand")
		selColumns = set()
		for aseq in self.seqs:
			try:
				matchMaps = aseq.matchMaps.values()
			except AttributeError:
				continue
			for mm in matchMaps:
				for sr in selResidues.keys():
					try:
						ungapped = mm[sr]
					except KeyError:
						continue
					selColumns.add(
						aseq.ungapped2gapped(ungapped))
		expansion = []
		for aseq in self.seqs:
			try:
				matchMaps = aseq.matchMaps.values()
			except AttributeError:
				continue
			for mm in matchMaps:
				for sc in selColumns:
					ungapped = aseq.gapped2ungapped(sc)
					if ungapped is None:
						continue
					try:
						sr = mm[ungapped]
					except KeyError:
						continue
					if sr not in selResidues:
						expansion.append(sr)
		if not expansion:
			self.status("No extra residues selected by"
					" expanding columns", color="red")
		chimera.selection.addCurrent(expansion)

	def exportActiveRegion(self):
		cr = self.currentRegion()
		if not cr:
			self.status("No active region", color="red")
			return
		if len(cr.blocks) == 0:
			self.status("Active region is empty", color="red")
			return
		if len(cr.blocks) > 1:
			self.status("Cannot export multi-block region", color="red")
			return
		line1, line2, col1, col2 = cr.blocks[0]
		if line2 not in self.seqs:
			self.status("Current region does not include any sequences",
				color="red")
			return
		if line1 not in self.seqs:
			index1 = 0
		else:
			index1 = self.seqs.index(line1)
		index2 = self.seqs.index(line2)
		from chimera.Sequence import Sequence
		newSeqs = []
		associationInfos = []
		for seq in self.seqs[index1:self.seqs.index(line2)+1]:
			ns = Sequence(seq.name)
			newSeqs.append(ns)
			ns.extend(seq[col1:col2+1])
			seqAssociationInfos = []
			associationInfos.append(seqAssociationInfos)
			if not ns.ungapped():
				continue
			for i in range(len(ns)):
				nsStart = ns.gapped2ungapped(i)
				if nsStart is not None:
					seqStart = seq.gapped2ungapped(col1+i)
					break
			for i in range(len(ns), -1, -1):
				nsEnd = ns.gapped2ungapped(i)
				if nsEnd is not None:
					seqEnd = seq.gapped2ungapped(col1+i)
					break
			for mol, mm in getattr(seq, 'matchMaps', {}).items():
				smm = {}
				seqAssociationInfos.append((ns, mm['mseq'], smm))
				for k, v in mm.items():
					if not isinstance(k, chimera.Residue):
						continue
					if not (seqStart <= v <= seqEnd):
						continue
					smm[k] = v - seqStart
					smm[v - seqStart] = k

		numberings = (self.leftNumberingVar.get(),
					self.rightNumberingVar.get())
		newMav = MAViewer(newSeqs, title="%s (partial)" % (self.title,),
			autoAssociate=False, numberingDisplay=numberings)
		newMMs = []
		for ns, infos in zip(newSeqs, associationInfos):
			for aseq, mseq, mm in infos:
				newMav.prematchedAssocStructure(aseq, mseq, mm,
					False, False, False, False)
				newMMs.append(mm)
		newMav.numberingsStripped = self.numberingsStripped
		newMav.autoAssociate = True
		regionInfos = []
		for region in self.regionBrowser.regions:
			if region == cr:
				continue
			# only regions that at least partially cover the new
			# alignment without fully covering it...
			newBlocks = []
			for block in region.blocks:
				rl1, rl2, rc1, rc2 = block
				if rl2 not in self.seqs:
					continue
				if rl1 in self.seqs:
					i1 = self.seqs.index(rl1)
				else:
					i1 = 0
				i2 = self.seqs.index(rl2)
				if (index1 <= i1 <= index2 or index1 <= i2 <= index2) \
				and (i1 > index1 or i2 < index2):
					if (col1 <= rc1 <= col2 or col1 <= rc2 <= col2) \
					and (rc1 > col1 or rc2 < col2):
						newBlocks.append((i1 - index1, i2 - index1,
							rc1 - col1, rc2 - col1))
			if newBlocks:
				if region.sequence:
					seq = newSeqs[self.seqs.index(region.sequence)]
				else:
					seq = None
				regionInfos.append({ 'name': region.name, 'blocks': newBlocks,
					'fill': region.interiorRGBA, 'outline': region.borderRGBA,
					'assocWith': region.associatedWith, 'shown': region.shown,
					'coverGaps': region.coverGaps, 'sequence': seq,
					'source': region.source})
		for i, kw in enumerate(regionInfos):
			kw['rebuildTable'] = i == len(regionInfos)-1
			newMav.newRegion(**kw)
		if newMMs:
			newMav.triggers.activateTrigger(ADD_ASSOC, newMMs)

	def extractSubalignment(self):
		newRoot = self.seqCanvas.activeNode()
		indices = newRoot.assignedIndices()
		indices.sort()
		from copy import copy
		newSeqs = [copy(self.seqs[i]) for i in indices]
		if newRoot.label:
			subtext = newRoot.label
		else:
			subtext = "partial"
		title = "%s (%s)" % (self.title, subtext)
		numberings = (self.leftNumberingVar.get(),
					self.rightNumberingVar.get())
		newMav = MAViewer(newSeqs, title=title, autoAssociate=False,
						numberingDisplay=numberings)
		newMav.numberingsStripped = self.numberingsStripped
		for newIndex, oldIndex in enumerate(indices):
			newSeq = newSeqs[newIndex]
			oldSeq = self.seqs[oldIndex]
			mols = getattr(oldSeq, 'matchMaps', {}).keys()
			if mols:
				newMav.associate(mols, seq=newSeq)
		newMav.useTree(newRoot.freshCopy())
		newMav.autoAssociate = True

	def gapChar(self):
		"""best guess as to what gap character is for this alignment"""
		counts = {}
		for seq in self.seqs:
			for c in seq:
				counts[c] = counts.get(c, 0) + 1
		from string import punctuation
		gappables = set(punctuation)
		keys = counts.keys()
		keys.sort(lambda c1, c2: cmp(counts[c2], counts[c1]))
		for c in keys:
			if c in gappables:
				return c
		return '.'

	def getRegion(self, name=None, **kw):
		"""if 'name' is None, return the active region"""
		if name is None:
			return self.regionBrowser.curRegion()
		return self.regionBrowser.getRegion(name, **kw)

	def headers(self, shownOnly=False):
		if shownOnly:
			return self.seqCanvas.headerDisplayOrder()
		return self.seqCanvas.headers

	def Hide(self):
		self.emHide()

	def hideHeaders(self, headers, fromMenu=False):
		"""hide header sequences"""
		self.seqCanvas.hideHeaders(headers, fromMenu=fromMenu)
		
	def insertGap(self, amount, column, gapChar='.'):
		"""insert a gap into the alignment

		   'amount' is the size of the gap
		   'column' is the column _after_ which the gap is inserted
		   (so zero would put it in front of the alignment)
		   'gapChar' is what to fill the gap with
		"""
		column = max(0, column)
		column = min(len(self.seqs[0]), column)
		insert = gapChar * amount
		from chimera.Sequence import Sequence
		newSeqs = []
		for seq in self.seqs:
			newSeq = Sequence(seq.name)
			newSeqs.append(newSeq)
			newSeq.extend(seq[:column])
			newSeq.extend(insert)
			newSeq.extend(seq[column:])

		# fix up fixed headers
		from HeaderSequence import FixedHeaderSequence
		for hdr in self.headers():
			if not isinstance(hdr, FixedHeaderSequence):
				continue
			hdr.vals[column:column] = [None] * amount
			if hasattr(hdr, 'colors'):
				hdr.colors[column:column] = ['black'] * amount

		self.realign(newSeqs, offset=amount, startOffset=column,
							markEdited=True, handleRegions=False)

	def _gapFixedHeaders(self, gaps):
		from HeaderSequence import FixedHeaderSequence
		for hdr in self.headers():
			if not isinstance(hdr, FixedHeaderSequence):
				continue
			offset = 0
			hdrVal = list(hdr.vals)
			for amount, column in gaps:
				hdrVal[column+offset:column+offset] = [None] * amount
				offset += amount
			hdr.vals = hdrVal
			
	def _gapMarkups(self, seq, gaps):
		for k, v in seq.markups.items():
			lv = list(v)
			offset = 0
			for amount, column in gaps:
				lv[column+offset:column+offset] = [" "] * amount
				offset += amount
			if type(v) == list:
				seq.markups[k] = lv
			else:
				seq.markups[k] = "".join(lv)

	def _getIntrinsicStructure(self):
		return getattr(self, "_intrinsicStructure", False)

	def _setIntrinsicStructure(self, isVal):
		if isVal == self.intrinsicStructure:
			return
		self._intrinsicStructure = isVal
		if isVal:
			self.autoAssociate = False
			if not self.associations:
				self.associate(None)
			self.structureMenu.entryconfigure("Load Structures",
												state='disabled')
		else:
			self.structureMenu.entryconfigure("Load Structures",
												state='normal')
			if self.quitCB:
				# tell Sequence monitor that we're no longer acting
				# as the Sequence GUI for this sequence
				self.quitCB(self)
				self.quitCB = None
				self.sessionSave = True
			self.autoAssociate = True
			self.uiMaster().winfo_toplevel().title(
				"Alignment based on " + self.title)

	intrinsicStructure = property(_getIntrinsicStructure,
									_setIntrinsicStructure)

	def loadScfFile(self, path, colorStructures=True):
		self.regionBrowser.loadScfFile(path, colorStructures)

	def match(self, refMol, matchMols, createRegion=False,
			makePseudobonds=False, matchConserved=False,
			matchActive=False, iterate=False, iterateCutoff=5.0):
		"""match models to a reference model

		   'refMol' is the reference model
		   'matchMols' is a list of models to match
		   'createRegion' indicates if a region on the alignment
		   	should be created to indicate which residues were
			involved in matching
		   'makePseudobonds' indicates if pseudobonds should be
		   	created between matched atoms
		   'matchConserved' restricts matching to "highly" conserved
		   	(capitalized) residues only
		   'matchActive' restricts matching to the currently active
		   	region
		   'iterate' indicates if the matching should iterate,
		   	pruning poorly-matching residues at each pass
		   'iterateCutoff' controls when iteration stops:  it stops
		   	when no pair exceeds the cutoff
		"""
		from chimera.colorTable import getColorByName
		if refMol.__destroyed__:
			raise ValueError("Reference model no longer exists!")
		if refMol not in self.associations:
			raise ValueError("%s not associated with any sequence"
						% refMol.name)
		reference = self.associations[refMol].matchMaps[refMol]
		colorList = [ "dark green", "dodger blue", "sienna", "yellow",
				"spring green", "purple", "gray", "coral"]
		colors = colorList[:]
		alignedResidues = {}
		returnVals = []
		for matchMol in matchMols:
			if refMol == matchMol:
				continue
			if matchMol not in self.associations:
				raise ValueError, "%s not associated" \
					" with any sequence" % matchMol.name
			if makePseudobonds:
				from chimera.misc import getPseudoBondGroup
				pbg = getPseudoBondGroup("matches of %s to %s"
						% (self.molName(matchMol),
						self.molName(refMol)))
				if pbg.pseudoBonds:
					pbg.deleteAll()
				else:
					if not colors:
						colors = colorList[:]
					color = colors[0]
					colors = colors[1:]
					pbg.color = getColorByName(color)
			else:
				pbg = None
			mobile = self.associations[matchMol].matchMaps[matchMol]
			refAtoms, mobileAtoms, rmsd = self._align(reference,
					mobile, matchConserved, matchActive,
					iterate, iterateCutoff, pbg)
			returnVals.append((refAtoms, mobileAtoms, rmsd))
			if not createRegion or refAtoms is None:
				continue
			refAseqAligned = alignedResidues.setdefault(
						reference['aseq'], {})
			refAligned = refAseqAligned.setdefault(refMol, {})
			mobileAseqAligned = alignedResidues.setdefault(
						mobile['aseq'], {})
			mobileAligned = mobileAseqAligned.setdefault(
								matchMol, {})
			for atoms, resMap in ((refAtoms, refAligned),
						(mobileAtoms, mobileAligned)):
				for a in atoms:
					resMap[a.residue] = True
		if not createRegion:
			return returnVals
		blocks = []
		for aseq, molDict in alignedResidues.items():
			gapped = {}
			for mol, resDict in molDict.items():
				matchMap = aseq.matchMaps[mol]
				for res in resDict.keys():
					gapped[aseq.ungapped2gapped(
							matchMap[res])] = True
			matches = gapped.keys()
			matches.sort()
			while matches:
				begin = matches.pop(0)
				end = begin
				while matches and matches[0] == end+1:
					end = matches.pop(0)
				blocks.append((aseq, aseq, begin, end))

		name, fill, outline = MATCHED_REGION_INFO
		reg = self.regionBrowser.getRegion(name, fill=fill,
						outline=outline, create=True)
		reg.clear()
		reg.addBlocks(blocks)
		return returnVals

	def molName(self, mol):
		return "%s (%s), %s" % (mol.name, mol.oslIdent(),
			self.associations[mol].matchMaps[mol]['mseq'].name)

	def newRegion(self, **kw):
		if 'blocks' in kw:
			# interpret numeric values as indices into sequences
			blocks = kw['blocks']
			if blocks and isinstance(blocks[0][0], int):
				blocks = [(self.seqs[i1], self.seqs[i2], i3, i4)
						for i1, i2, i3, i4 in blocks]
				kw['blocks'] = blocks
		if 'columns' in kw:
			# in lieu of specifying blocks, allow list of columns
			# (implicitly all rows); list should already be in order
			left = right = None
			blocks = []
			for col in kw['columns']:
				if left is None:
					left = right = col
				elif col > right + 1:
					blocks.append((self.seqs[0],
						self.seqs[-1], left, right))
					left = right = col
				else:
					right = col
			if left is not None:
				blocks.append((self.seqs[0], self.seqs[-1],
								left, right))
			kw['blocks'] = blocks
			del kw['columns']
		return self.regionBrowser.newRegion(**kw)

	def Quit(self):
		self.emQuit()

	def realign(self, input, fileType=None, offset=None, startOffset=0,
							markEdited=False, handleRegions=True):
		"""Switch to a different alignment of the same sequences
		
		   'input' is list of Sequences or file name
		"""
		# since structure associations are mapped via ungapped
		# sequences, don't need to disassociate/reassociate
		if isinstance(input, list):
			seqs = input
			for seq in seqs[1:]:
				if len(seq) != len(seqs[0]):
					replyobj.error("Switching to sequences"
						" of unequal length\n")
					return
			self.fileMarkups = {}
		else:
			from common import readFile
			seqs, self.fileAttrs, self.fileMarkups = readFile(input, fileType)
			name = os.path.split(input)[1]
			self._toplevel.title(name)
		
		if len(seqs) != len(self.seqs):
			replyobj.error("Number of new sequences (%d) not"
				" equal to number of old sequences (%d)\n" %
				(len(seqs), len(self.seqs)))
			return
		lengthChange = len(self.seqs[0]) != len(seqs[0])

		# self.seqs updated as side effect of ...
		self.seqCanvas.realign(seqs, handleRegions=handleRegions)

		if offset is not None:
			self.regionBrowser.moveRegions(offset,
						startOffset=startOffset)
		elif lengthChange:
			# don't know what to do with regions when sequences
			# change length, so...
			self.regionBrowser.clearRegions(doSingleSeqRegions=False)
			if self.prefs[SHOW_SEL]:
				self.regionBrowser.showChimeraSelection()
		if markEdited:
			self._edited = True

	def refreshHeader(self, header, **kw):
		self.seqCanvas.refresh(header, **kw)

	def reorder(self, seqs):
		self.regionBrowser.clearRegions(doSingleSeqRegions=False)
		self.seqs[:] = seqs
		tree = self.seqCanvas.tree
		if tree:
			ordered, ordering = tree.assignSeqIndices(self.seqs)
			tree.assignYpositions()
			tree.assignXpositions(branchStyle="weighted")
			tree.assignXdeltas()
		self.seqCanvas._reformat()
		if self.prefs[SHOW_SEL]:
			self.regionBrowser.showChimeraSelection()
		self.triggers.activateTrigger(MOD_ALIGN, seqs)
		self._edited = True

	def readHeaderFile(self, fileName):
		from CGLutil.annotatedDataFile import readDataFile
		from LineItem import LineItem
		from OpenSave import osOpen
		f = osOpen(fileName, "r")
		try:
			fileData = readDataFile(f)
		except SyntaxError, v:
			raise UserError(v)
		f.close()

		control = {}
		for newControl, data in fileData:
			control.update(newControl)
			if "name" not in control:
				control["name"] = ""
			identifiers = ["name", "style"]
			for ident in control.keys():
				if ident in identifiers:
					continue
				replyobj.warning("Ignoring unknown identifier"
					" (%s) in control line.\nKnown"
					" identifiers are: %s." % (ident,
					", ".join(identifiers)))
			if "style" in control:
				style = control["style"].lower()
				styles = ["character", "numeric", "symbol"]
				if style not in styles:
					raise UserError("Unknown style (%s)."
						"Legal styles are: %s." % (
						style, ", ".join(styles)))
			else:
				style = None
			vals = [None] * len(self.seqs[0])
			colors = [None] * len(self.seqs[0])
			from chimera.colorTable import getTkColorByName
			from CGLtk.color import rgba2tk
			for ln, d in enumerate(data):
				try:
					pos, val = d
					color = None
				except ValueError:
					try:
						pos, val, color = d
					except ValueError:
						raise UserError("Data line %d"
							" is neither position/"
							"value nor position/"
							"value/color" % (ln+1))
				if val.strip() == "None":
					continue
				if style is None:
					# guess from value
					if val in LineItem.supportedSymbols:
						style = "symbol"
					elif len(val) == 1:
						style = "character"
					else:
						style = "numeric"
				if color is not None:
					color = color.strip()
				if not color:
					if style == "numeric":
						color = 'dark gray'
					elif style == "symbol":
						color = "white"
					else:
						color = 'black'
				else:
					# convert color to Tk
					if color[0].isalpha():
						try:
							color = getTkColorByName(color)
						except KeyError:
							raise UserError(
								"Unknown color"
								" name (%s) on"
								" data line %d"
								% (color, ln+1))
					else:
						try:
							rgb = [float(x) for x in
								color.split()]
						except ValueError:
							raise UserError(
								"Non-numeric"
								" color RGB"
								" color value"
								" given on data"
								" line %d"
								% (ln+1))
						if len(rgb) != 3:
							raise UserError(
								"RGB color on"
								" data line %d"
								" is not 3"
								" numbers" % (
								ln +1))
						if min(rgb) < 0 or max(rgb) > 1:
							raise UserError("RGB"
								" color values"
								" on data line"
								" %d not in the"
								" range zero to"
								" one" % (ln+1))
						color = rgba2tk(rgb)
				try:
					pos = int(pos)
				except ValueError:
					raise UserError("Non-integer position"
						" (%s) on data line %d" % (
						pos, ln+1))
				if pos < 1 or pos > len(vals):
					raise UserError("Position (%d) is less"
						" than one or greater than"
						" alignment length on data line"
						" %d" % (pos, ln+1))
				if style == "numeric":
					val = val.strip()
					try:
						val = float(val)
					except ValueError:
						raise UserError("Non-floating"
							" point value (%s)"
							" given on data line %d"
							% (val, ln+1))
				elif style == "symbol":
					if val not in LineItem.supportedSymbols:
						raise UserError("Value on data line %d ('%s') is not a"
							" known symbol.\nThe known symbols are: %s" % (
							ln+1, val, ", ".join(LineItem.supportedSymbols)))
				else:
					if len(val) != 1:
						raise UserError("Value on data"
							" line %d is not a"
							" single character"
							" ('%s')" % (ln+1, val))
				vals[pos-1] = val
				colors[pos-1] = color

			header = CustomFixedHeader(control["name"], self, vals, colors, style)
			self.addHeaders([header])

	def seeRegion(self, region):
		self.regionBrowser.seeRegion(region)

	def seeSeq(self, seq, highlightName=False):
		"""scroll to show given sequence and possibly briefly
		   highlight sequence name"""
		self.seqCanvas.seeSeq(seq, highlightName)
		self.status(self.seqCanvas.seqInfoText(seq))

	def _addRealignmentJob(self, ws, mav):
		if mav:
			self._realignmentWSJobs['self'].append(ws)
		else:
			self._realignmentWSJobs['new'].append(ws)

	def _removeRealignmentJob(self, ws, mav, results):
		try:
			if mav:
				self._realignmentWSJobs['self'].remove(ws)
			else:
				self._realignmentWSJobs['new'].remove(ws)
		except ValueError:
			# Just in case item gets removed twice
			# Really should not happen
			pass

	def _addRunModellerLocal(self, job):
		self._runModellerLocalList.append(job)

	def _addRunModellerWS(self, job):
		self._runModellerWSList.append(job)

	def _removeRunModellerLocal(self, job):
		try:
			self._runModellerLocalList.remove(job)
		except ValueError:
			# Just in case item gets removed twice
			# Really should not happen
			pass

	def _removeRunModellerWS(self, rmws):
		try:
			self._runModellerWSList.remove(rmws)
		except ValueError:
			# Just in case item gets removed twice
			# Really should not happen
			pass

	def save(self, modal=False):
		from output import saveFile
		saveFile(self, modal=modal)
	
	def saveAssocInfo(self, fileName, namingStyle="simple"):
		from chimera.misc import chimeraLabel
		from OpenSave import osOpen
		f = osOpen(fileName, "w")
		for mol, aseq in self.associations.items():
			print>>f, mol.name, "associates with", aseq.name
			pairs = []
			for k, v in aseq.matchMaps[mol].items():
				if not isinstance(k, chimera.Residue):
					continue
				pairs.append((aseq.ungapped2gapped(v) + 1,
					chimeraLabel(k, showModel=False,
					style=namingStyle)))
				pairs.sort()
			for info in pairs:
				print>>f, "  %d - %s" % info
		f.close()

	def saveEPS(self, fileName, colorMode="color", rotate=False,
						extent="all", hideNodes=True):
		self.seqCanvas.saveEPS(fileName, colorMode, rotate, extent,
								hideNodes)

	def saveHeader(self, fileName, header, omitNoValue=True):
		from OpenSave import osOpen
		f = osOpen(fileName, "w")
		if header == self.seqCanvas.conservation:
			self._outputConservationPreamble(f)
		elif header == self.seqCanvas.consensus:
			self._outputConsensusPreamble(f)

		print>>f, "name:", header.name
		style = "numeric"
		defaultColor = 'dark gray'
		for i, c in enumerate(header):
			if omitNoValue and c is None:
				continue
			# use f.write to suppress extraneous spaces
			f.write("\t%d\t" % (i+1))
			if type(c) in (float, int):
				f.write("%g" % c)
			else:
				f.write(unicode(c))
				if c is not None:
					if len(c) > 1:
						style = "symbol"
						defaultColor = 'white'
					else:
						style = "character"
						defaultColor = 'black'
			if c is None or not hasattr(header, 'colorFunc'):
				print>>f
				continue
			color = header.colorFunc(header, i)
			if color == defaultColor or color is None:
				print>>f
				continue
			if color[0] != '#':
				f.write("\t%s" % color)
				continue
			# Tk color; decipher into RGB
			fieldLen = int((len(color)-1)/3)
			f.write("\t")
			maxCval = float(16 ** fieldLen - 1)
			rgb = []
			for ci in range(1, len(color), fieldLen):
				rgb.append(eval("0x"+color[ci:ci+fieldLen])/maxCval)
			print>>f, " ".join(["%g" % x for x in rgb])
		print>>f, "style:", style
		f.close()

	def saveInfo(self):
		"""returns a string that can be used by restoreMAV()"""
		info = {}
		info['title'] = self.title
		info['autoAssociate'] = self.autoAssociate
		info['intrinsic'] = self.intrinsicStructure
		info['sessionSave'] = self.sessionSave
		info['runModellerWS'] = [ rmws.sessionData()
					for rmws in self._runModellerWSList ]
		info['realignmentWS'] = {
			'self': [(ws.sessionData(), ws.mavReordersSequences)
				for ws in self._realignmentWSJobs['self']],
			'new': [(ws.sessionData(), ws.mavReordersSequences)
				for ws in self._realignmentWSJobs['new']]
		}
		info['versionedModSesData'] = True
		rb = self.regionBrowser
		info['regions'] = []
		regToSeq = {}
		for seq, regions in rb.sequenceRegions.items():
			for reg in regions:
				regToSeq[reg] = seq
		for region in rb.regions:
			regInfo = {}
			regInfo['name'] = region.name
			regInfo['blocks'] = []
			for block in region.blocks:
				line1, line2, pos1, pos2 = block
				if line1 in self.seqs:
					index1 = self.seqs.index(line1)
				else:
					index1 = -1 - self.seqCanvas.headers\
								.index(line1)
				if line2 in self.seqs:
					index2 = self.seqs.index(line2)
				else:
					index2 = -1 - self.seqCanvas.headers\
								.index(line2)
				regInfo['blocks'].append([index1, index2,
								pos1, pos2])
			regInfo['fill'] = region.interiorRGBA
			regInfo['outline'] = region.borderRGBA
			regInfo['shown'] = region.shown
			regInfo['select'] = region == rb.curRegion()
			regInfo['coverGaps'] = region.coverGaps
			regInfo['source'] = region.source
			seq = regToSeq[region]
			if seq:
				regInfo['sequence'] = self.seqs.index(seq)
			info['regions'].append(regInfo)
		info['specials'] = []
		info['ruler shown'] = self.showRulerVar.get()
		info['numberings'] = (self.leftNumberingVar.get(),
					self.rightNumberingVar.get())
		info['numberingsStripped'] = self.numberingsStripped
		info['header shown'] = shown = []
		for header in self.seqCanvas.headers:
			shown.append(self.seqCanvas.displayHeader[header])
			if header in [self.seqCanvas.consensus,
						self.seqCanvas.conservation]:
				continue
			specInfo = {}
			specInfo['class'] = header.__class__.__name__
			specInfo['name'] = header.name
			if isinstance(header, FixedHeaderSequence):
				specInfo['restore info'] = (header.__class__.__name__,) + header.saveInfo()
			info['specials'].append(specInfo)
		info['header display order'] = [self.seqCanvas.headers.index(h)
				for h in self.seqCanvas.headerDisplayOrder()]
		if self.seqCanvas.tree:
			info['tree'] = str(self.seqCanvas.tree)
			info['show tree'] = self.showTreeVar.get()
		assocs = []
		info['associations'] = assocs
		mseqs = []
		mseqLookup = {}
		for seq in self.seqs:
			if not hasattr(seq, 'matchMaps'):
				continue
			for matchMap in seq.matchMaps.values():
				mseq = matchMap['mseq']
				try:
					mseqIndex = mseqLookup[mseq]
				except KeyError:
					mseqIndex = len(mseqs)
					mseqs.append(mseq)
					mseqLookup[mseq] = mseqIndex
				assocs.append((self.seqs.index(seq), mseqIndex))
		assocRegions = {}
		info['region associations'] = assocRegions
		for key, regions in rb.associatedRegions.items():
			mseq, aseq = key
			assocRegions[(mseqs.index(mseq), self.seqs.index(aseq))
				] = [rb.regions.index(rg) for rg in regions]
		info['mseqs'] = [mseq.saveInfo() for mseq in mseqs]
		info['fileAttrs'] = self.fileAttrs
		info['fileMarkups'] = self.fileMarkups
		info['showActualSS'] = self.showSSVar.get()
		info['showPredictedSS'] = self.showPredictedSSVar.get()
		info['blastAnnotationServices'] = baServiceInfo = {}
		for seq, serviceInfo in self._blastAnnotationServices.items():
			service, cbKw = serviceInfo
			baServiceInfo[self.seqs.index(seq)] = (service.sessionData(), cbKw)
		from SimpleSession import sesRepr
		return sesRepr(info)

	def seqNameToStructureID(self, seqName):
		seqName = seqName.lower()
		if self.prefs[LOAD_SCOP]:
			if len(seqName) == 7 and seqName[1].isdigit() \
			and seqName[2:5].isalnum():
				return (seqName, "SCOP")

		if self.prefs[LOAD_PDB_NAME_EXACT]:
			if len(seqName) == 4 and seqName.isalnum() \
			and seqName[0].isdigit():
				return (seqName, "PDBID")
		if self.prefs[LOAD_PDB_NAME_START]:
			if len(seqName) > 4 and seqName[:4].isalnum() \
			and seqName[0].isdigit():
				return (seqName[:4], "PDBID")
		if self.prefs[LOAD_PDB_NAME_NCBI]:
			where = seqName.find("pdb|")
			if where >= 0 and len(seqName) >= where + 8 \
			and seqName[where+4:where+8].isalnum() \
			and seqName[where+4].isdigit():
				return (seqName[where+4:where+8], "PDBID")
		if self.prefs[LOAD_PDB_NAME_VARSTART]:
			prefix = self.prefs[LOAD_PDB_NAME_VARSTART_VAL]
			if seqName.startswith(prefix):
				start = len(prefix)
				putativePDB = seqName[start:start+4]
				if len(putativePDB) == 4 \
				and putativePDB.isalnum() \
				and putativePDB[0].isdigit():
					return (putativePDB, "PDBID")
		return None

	def _getSessionSave(self):
		return getattr(self, "_sessionSave", False)

	def _setSessionSave(self, isVal):
		if isVal == self.sessionSave:
			return
		self._sessionSave = isVal
		if isVal:
			self._saveSessionHandlerID = chimera.triggers.addHandler(
					SAVE_SESSION, self._saveSession, None)
		else:
			chimera.triggers.deleteHandler(SAVE_SESSION,
						self._saveSessionHandlerID)

	sessionSave = property(_getSessionSave, _setSessionSave)

	def setLeftNumberingDisplay(self, showNumbering=None):
		if showNumbering is None:
			showNumbering = self.leftNumberingVar.get()
		else:
			self.leftNumberingVar.set(showNumbering)
		self.seqCanvas.setLeftNumberingDisplay(showNumbering)

	def setResidueAttrs(self):
		if self.intrinsicStructure and len(self.associations) < 2:
			return
		conservation = self.seqCanvas.conservation
		structInfo = []
		for mol, aseq in self.associations.items():
			structInfo.append((mol, aseq, aseq.matchMaps[mol]))
		if not structInfo:
			return
		intsOkay = len(self.seqs) <= 100
		track = chimera.TrackChanges.get()
		if len(self.seqs) > 1:
			trackReason = self.ConsAttr + " changed"
			for pos in range(len(conservation)):
				pi = 100.0 * conservation.percentIdentity(pos)
				if intsOkay:
					pi = int(pi + 0.5)
				for mol, aseq, mmap in structInfo:
					ungapped = aseq.gapped2ungapped(pos)
					if ungapped is None:
						continue
					try:
						res = mmap[ungapped]
					except KeyError:
						continue
					setattr(res, self.ConsAttr, pi)
					track.addModified(res, trackReason)

			self._resAttrs[self.ConsAttr] = intsOkay
		headerAttrs = {}
		from types import StringTypes
		from chimera.misc import stringToAttr
		for header in self.seqCanvas.headers:
			if not header.visible and not header.evalWhileHidden:
				continue
			if len(self.seqs) == 1 and not header.singleSequenceRelevant:
				continue
			attrName = stringToAttr(header.name, prefix="mav",
								style="caps")
			if attrName == self.ConsAttr:
				continue
			self._resAttrs[attrName] = True
			intAttr = True
			for c in header:
				if not isinstance(c, StringTypes):
					intAttr = False
					break
				try:
					int(c)
				except ValueError:
					intAttr = False
					break
			headerAttrs[attrName] = (header, intAttr)
		for pos in range(len(conservation)):
			for mol, aseq, mmap in structInfo:
				ungapped = aseq.gapped2ungapped(pos)
				if ungapped is None:
					continue
				try:
					res = mmap[ungapped]
				except KeyError:
					continue
				for attrName, info in headerAttrs.items():
					header, intAttr = info
					if intAttr:
						val = int(header[pos])
					else:
						val = header[pos]
					setattr(res, attrName, val)
					track.addModified(res, "attribute set")
		self._resAttrs.update(headerAttrs)

	def setRightNumberingDisplay(self, showNumbering=None):
		if showNumbering is None:
			showNumbering = self.rightNumberingVar.get()
		else:
			self.rightNumberingVar.set(showNumbering)
		self.seqCanvas.setRightNumberingDisplay(showNumbering)

	def setRulerDisplay(self, showRuler=None):
		if showRuler is None:
			showRuler = self.showRulerVar.get()
		else:
			self.showRulerVar.set(showRuler)
		self.seqCanvas.setRulerDisplay(showRuler)

	def showHeaders(self, headers, fromMenu=False):
		"""show previously-added header sequences"""
		self.seqCanvas.showHeaders(headers, fromMenu=fromMenu)
		
	def showSS(self, show=True, ssType="actual"):
		if ssType == "actual":
			var = self.showSSVar
		else:
			var = self.showPredictedSSVar
		if show == None:
			show = bool(var.get())
		elif show == var.get():
			return
		else:
			var.set(show)
		if ssType == "actual":
			self.regionBrowser.showSS(show)
		else:
			self.regionBrowser.showPredictedSS(show)

	def uniprotInfo(self, seq, method, methodInfo=None, ignoreCache=False,
			annotate=True, showPage=False):
		if hasattr(seq, 'fullName'):
			seqName = seq.fullName()
		else:
			seqName = seq.name
		if method == "pdb":
			pdbID, chainID = methodInfo
			from SeqAnnotations import uniprotIDs as getUniprotIDs
			try:
				uniprotIDs = getUniprotIDs(pdbID, chainID)
			except CancelOperation:
				self.status("Fetch of %s, chain %s cancelled" % (pdbID, chainID),
					color="red")
				return
			replyobj.info("%s has UniProt ID(s): %s\n" % (seqName, ", ".join(uniprotIDs)))
		elif method == "uniprot":
			from SeqAnnotations import mapUniprotNameID
			uniprotIDs = [mapUniprotNameID(methodInfo)]
		else: # blast
			from blastpdb.ParserBlastP import BlastpService
			if seq in self._blastAnnotationServices:
				raise UserError("Blast annotation already running for %s" % seqName)
			cbKw = {
				'ignoreCache': ignoreCache,
				'annotate': annotate,
				'showPage': showPage
			}
			# the fail/cancel callbacks are also used in the session-restore
			# code, so if you change them here then change them there too
			self._blastAnnotationServices[seq] = (BlastpService(
				lambda params, results, f=self._blastFinished, seq=seq, cbKw=cbKw: f(seq,
				results=results, **cbKw), params=("blast", "uniref100",
				seqName.replace(' ', '_'), seq.ungapped(), 3, "BLOSUM90", 1),
				failCB=lambda f=self._blastFinished, seq=seq: f(seq, failed=True),
				cancelCB=lambda f=self._blastFinished, seq=seq:
				f(seq, cancelled=True)), cbKw)
			self.status("Blasting %s (see main status line)" % seqName)
			return

		for uniprotID in uniprotIDs:
			if annotate:
				from SeqAnnotations import uniprotFetch, showUniprotFeatures
				try:
					uniprotSeq, fullName, features = uniprotFetch(uniprotID)
				except CancelOperation:
					self.status("Fetch of %s UniProt info cancelled" % (pdbID, chainID),
						color="red")
					return
				self.status("Matching alignment sequence to UniProt sequence")
				ungapped = seq.ungapped()
				from NeedlemanWunsch import nw
				score, matches = nw(uniprotSeq, ungapped)
				self.status("")
				if score < len(ungapped):
					replyobj.error("Alignment sequence doesn't seem to correspond"
						" with UniProt sequence.\n")
				mapping = {}
				for i1, i2 in matches:
					mapping[i1] = i2
				if len(uniprotIDs) > 1:
					sourceID = uniprotID
				else:
					sourceID = None
				showUniprotFeatures(self, features, seqIndex=self.seqs.index(
					seq), mapping=mapping, sourceID=sourceID)
				self.regionBrowser.enter()
			if showPage:
				import webbrowser
				webbrowser.open("http://www.uniprot.org/uniprot/" + uniprotID)

	def updateNumberings(self):
		self.seqCanvas.updateNumberings()

	def useColoringFile(self, colorFileName, makeDefault=False):
		from prefs import RC_CLUSTALX, RC_BLACK
		if colorFileName == None:
			self.seqCanvas.setColorFunc(RC_BLACK)
			return
		from clustalX import clustalInfo
		self.seqCanvas.setClustalParams(*clustalInfo(colorFileName))
		self.seqCanvas.setColorFunc(RC_CLUSTALX)
		self.prefDialog.addColorScheme(colorFileName, makeDefault)

	def usePhylogenyFile(self, phylogenyFile, askReorder=True):
		from parsePhylo import parseNewick
		from OpenSave import osOpen
		from chimera import UserError
		f = osOpen(phylogenyFile)
		try:
			try:
				fileTrees = parseNewick(f.readlines(),
				numberingsStripped=self.numberingsStripped)
			except SyntaxError, v:
				raise UserError(v)
		finally:
			f.close()
		trees = [t for t in fileTrees
			if t.countNodes(nodeType="leaf") == len(self.seqs)]
		if not trees:
			raise UserError("No trees in '%s' have the same number"
				" of leaf nodes as the number of sequences"
				" in the alignment\n(tree: %s; alignment: %d)"
				% (phylogenyFile, ",".join([str(t.countNodes(
				"leaf")) for t in fileTrees]), len(self.seqs)))
		if len(trees) > 1:
			from chimera.baseDialog import ModalDialog
			import Tkinter, Pmw
			items = []
			for i, t in enumerate(trees):
				if t.label:
					items.append("#%d: %s" % (i+1, t.label))
				else:
					if t.maxLength():
						weightInfo = "weighted branches"
					else:
						weightInfo = "no branch weights"
					items.append("#%d: (no label, %s)"
							% (i+1, weightInfo))
			class ResolveTree(ModalDialog):
				oneshot = True
				title = "Multiple Trees"
				buttons = ('Cancel', 'OK')
				def fillInUI(self, parent):
					labelText = "%s contains multiple" \
						" trees.\nChoose one:" % (
						os.path.basename(phylogenyFile))
					self.listbox = Pmw.ScrolledListBox(
						parent, items=items,
						dblclickcommand=self.OK,
						labelpos='n',
						label_text=labelText)
					self.listbox.grid(sticky="nsew")
				def OK(self):
					ModalDialog.Cancel(self, value=
						self.listbox.curselection())
			sels = ResolveTree().run(self.uiMaster())
			if not sels:
				raise UserError("No tree chosen")
			elif len(sels) > 1:
				raise UserError("Must choose only one tree")
			tree = trees[int(sels[0])]
		else:
			tree = trees[0]

		self.useTree(tree, askReorder=askReorder)
		self.status("Click on tree to select nodes for Tree menu"
								" actions")

	def useTree(self, tree, askReorder=True):
		ordered, ordering = tree.assignSeqIndices(self.seqs)
		if not ordered:
			from chimera.baseDialog import AskYesNoDialog
			if (not askReorder) or AskYesNoDialog("With the current"
			" sequence ordering, tree branches will cross.\nReorder"
			" sequences to avoid branch crossings?",
			title="Reorder Sequences?", default="Yes").run(
			self.uiMaster().winfo_toplevel()) == 'yes':
				self.reorder([self.seqs[i] for i in ordering])
				tree.assignSeqIndices(self.seqs)

		self.seqCanvas.usePhyloTree(tree, callback=self._treeCB)
		self.treeMenu.entryconfigure("Extract*", state='normal')
		self.treeMenu.entryconfigure("Show Tree", state='normal')

	def _align(self, refMatchMap, mobileMatchMap, matchConserved,
				matchActive, iterate, iterateCutoff, pbg):
		from chimera.match import matchAtoms
		refAtoms = []
		mobileAtoms = []

		refMseq = refMatchMap['mseq']
		refAseq = refMatchMap['aseq']
		refMol = refMseq.molecule
		refName = "%s %s" % (refMol.name, refMseq.name)
		mobileMseq = mobileMatchMap['mseq']
		mobileAseq = mobileMatchMap['aseq']
		mobileMol = mobileMseq.molecule
		mobileName = "%s %s" % (mobileMol.name, mobileMseq.name)

		if matchActive:
			curRegion = self.currentRegion()
			if curRegion is None:
				replyobj.error("No active region.\n")
				return None, None, None

		self.status('Matching %s to %s' % (mobileName, refName),
								blankAfter=0)

		consensus = self.seqCanvas.consensus
		for key in refMatchMap.keys():
			if not isinstance(key, int):
				continue
			gapped = refAseq.ungapped2gapped(key)
			ungappedMobile = mobileAseq.gapped2ungapped(gapped)
			if ungappedMobile is None:
				continue
			if not mobileMatchMap.has_key(ungappedMobile):
				continue
			if matchConserved and not consensus[gapped].isupper():
				continue
			if matchActive:
				for block in curRegion.blocks:
					line1, line2, pos1, pos2 = block
					if gapped >= pos1 and gapped <= pos2:
						break
				else:
					continue
			refRes = refMatchMap[key]
			mobileRes = mobileMatchMap[ungappedMobile]

			for matchable in ["CA", "C4'", "P"]:
				if refRes.atomsMap.has_key(matchable) \
				and mobileRes.atomsMap.has_key(matchable):
					break
			else:
				continue

			refAtoms.append(refRes.atomsMap[matchable][0])
			mobileAtoms.append(mobileRes.atomsMap[matchable][0])

		from Midas import match, TooFewAtomsError
		if iterate:
			ival = iterateCutoff
		else:
			ival = None
		numFullRef = len(refAtoms)
		try:
			mobileAtoms, refAtoms, rmsd, fullRmsd = match(
					mobileAtoms, refAtoms, iterate=ival)
		except TooFewAtomsError:
			replyobj.error('Too few corresponding atoms (<4) to '
				'match %s and %s\n' % (mobileName, refName))
			self.status("")
			return None, None, None

		if pbg:
			for i in range(len(refAtoms)):
				ref = refAtoms[i]
				mobile= mobileAtoms[i]
				pb = pbg.newPseudoBond(ref, mobile)
				pb.drawMode = chimera.Bond.Stick

		if iterate:
			msg = "Matched %s to %s with %.3f RMSD (%d pruned atom pairs;" \
				" RMSD %.3f across all %d atom pairs)\n" % (
					mobileName, refName, rmsd, len(refAtoms), fullRmsd, numFullRef)
		else:
			msg = "Matched %s to %s with %.3f RMSD (%d atom pairs)\n" % (
					mobileName, refName, rmsd, len(refAtoms))
		self.status(msg, log=1, blankAfter=120)
		return refAtoms, mobileAtoms, rmsd

	def prematchedAssocStructure(self, aseq, mseq, matchMap, errors,
						createMatches, createErrors, reassoc):
		"""If somehow you had obtained a matchMap for the aseq<->mseq
		   correspondence, you would use this call instead of the more
		   usual associate() call
		"""
		newRegionInfo = []
		delRegions = []
		if getattr(aseq, 'circular', False):
			offset = len(aseq.ungapped())/2
			for k, v in matchMap.items():
				if type(k) == chimera.Residue:
					matchMap[v + offset] = k
		if createMatches == None:
			createMatches = True
			showMatches = self.prefs[MATCH_REG_ACTIVE]
		else:
			showMatches = createMatches
		if createErrors == None:
			showMismatches = self.prefs[ERROR_REG_ACTIVE]
			showGaps = self.prefs[GAP_REG_ACTIVE]
			createErrors = True
		else:
			showGaps = showMismatches = createErrors
		mol = mseq.molecule
		# can have several 'chains' of the same sequence match to
		# one alignment sequence if there is an erroneous chain break
		matchMap['mseq'] = mseq
		matchMap['aseq'] = aseq
		try:
			aseq.matchMaps[mol] = matchMap
		except AttributeError:
			aseq.matchMaps = { mol: matchMap }
		self.associations[mol] = aseq

		self.seqCanvas.assocSeq(aseq)
		if hasattr(aseq, 'residueSequence'):
			aref = aseq.residueSequence
			errors = True
		else:
			aref = aseq.ungapped()
		if createErrors and errors or createMatches:
			stretches = []
			gaps = []
			mismatches = []
			curStretch = None
			for i, res in enumerate(mseq.residues):
				try:
					if not res:
						raise KeyError("gap")
					aIndex = matchMap[res]
				except KeyError:
					# forced to gap structure sequence;
					# stop current stretch
					if curStretch != None:
						stretches.append(curStretch)
						curStretch = None
					continue
				if curStretch == None:
					curStretch = [aIndex, aIndex]
					if stretches:
						gaps.append((stretches[-1][1]+1, aIndex-1))
					# now that showMatches defaults False...
					# (could possibly be len(self.seqs) == 1 to
					# allow UniProt fetches to show frequently
					# large initial/trailing gaps)
					#elif self.intrinsicStructure and aIndex > 0:
					elif aIndex > 0:
						# show initial gap
						gaps.append((0, aIndex-1))
				elif aIndex == curStretch[1] + 1:
					curStretch[1] = aIndex
				else:
					gaps.append((curStretch[1]+1, aIndex-1))
					stretches.append(curStretch)
					curStretch = [aIndex, aIndex]

				if mseq.ungapped()[i] != aref[aIndex].upper():
					mismatches.append(aIndex)
			if curStretch == None:
				# now that showMatches defaults False...
				# (could possibly be len(self.seqs) == 1 to
				# allow UniProt fetches to show frequently
				# large initial/trailing gaps)
				#if self.intrinsicStructure:
				if True:
					# show trailing gap
					if stretches:
						gapStart = stretches[-1][1]+1
					else:
						gapStart = 0
					gapEnd = len(aseq.ungapped()) - 1
					if gapStart <= gapEnd:
						gaps.append((gapStart, gapEnd))
			else:
				stretches.append(curStretch)
				if aIndex < len(aseq.ungapped()) - 1:
					# deletion at end of structure seq
					# (therefore show trailing gap)
					gaps.append((aIndex+1, len(aseq.ungapped())-1))

			def _findDelRegion(regKey, regNameStart):
				for region in self.regionBrowser.associatedRegions.get(regKey, []):
					if region.name.startswith(regNameStart):
						return [region]
				return []
			regionKey = (mseq, aseq)
			mol = mseq.molecule
			molName = mol.name
			molName = os.path.split(molName)[-1]
			if stretches and createMatches:
				blocks = []
				for start, end in stretches:
					start = aseq.ungapped2gapped(start)
					end = aseq.ungapped2gapped(end)
					blocks.append([aseq, aseq, start, end])
				allMatched = 0
				if len(matchMap) - 2 == 2*len(aseq.ungapped()):
					allMatched = 1
				if not allMatched:
					newRegionInfo.append((
						("%s of %s" % (self.MATCH_REG_NAME_START,
						mseq.fullName()), blocks),
						{'fill': self.prefs[MATCH_REG_FILL],
						'outline': self.prefs[MATCH_REG_EDGE],
						'assocWith': regionKey, 'coverGaps': False,
						'shown': showMatches, 'sequence': aseq}))
				if reassoc:
					delRegions.extend(_findDelRegion(regionKey, self.MATCH_REG_NAME_START))
			if gaps and createErrors:
				blocks = []
				for start, end in gaps:
					start = aseq.ungapped2gapped(start)
					end = aseq.ungapped2gapped(end)
					blocks.append([aseq, aseq, start, end])
				if len(gaps):
					gapText = str(len(gaps)) + " gaps"
				else:
					gapText = "none"
				newRegionInfo.append((
					("%s (%s) of %s" % (self.GAP_REG_NAME_START,
					gapText, mseq.fullName()), blocks),
					{'fill': self.prefs[GAP_REG_FILL],
					'outline': self.prefs[GAP_REG_EDGE],
					'assocWith': regionKey, 'sequence': aseq,
					'coverGaps': False, 'shown': showGaps}))
				if reassoc:
					delRegions.extend(_findDelRegion(regionKey, self.GAP_REG_NAME_START))
			if mismatches and createErrors:
				blocks = []
				for pos in mismatches:
					pos = aseq.ungapped2gapped(pos)
					blocks.append([aseq, aseq, pos, pos])
				newRegionInfo.append((
					("%s (%d) of %s" % (self.ERROR_REG_NAME_START,
					len(mismatches), mseq.fullName()), blocks),
					{'fill': self.prefs[ERROR_REG_FILL],
					'outline': self.prefs[ERROR_REG_EDGE],
					'assocWith': regionKey, 'sequence': aseq,
					'coverGaps': False, 'shown': showMismatches}))
				if reassoc:
					delRegions.extend(_findDelRegion(regionKey, self.ERROR_REG_NAME_START))
		# set up callbacks for structure changes
		matchMap["mavDelHandler"] = mseq.triggers.addHandler(
				mseq.TRIG_DELETE, self._mseqDelCB, matchMap)
		matchMap["mavModHandler"] = mseq.triggers.addHandler(
				mseq.TRIG_MODIFY, self._mseqModCB, matchMap)
		if reassoc:
			blockingTrigger = MOD_ASSOC
		else:
			blockingTrigger = ADD_ASSOC
		if self.triggers.isTriggerBlocked(blockingTrigger):
			# delay new regions until all associations made
			# so that rebuilt region browser doesn't prematurely
			# try to calculate RMSD
			if delRegions or newRegionInfo:
				if not hasattr(self, "_pendingRegionChanges"):
					self._pendingRegionChanges = ([], [])
				if not self._pendingRegionChanges[0] and not self._pendingRegionChanges[1]:
					def makeNewRegions(trigName, regData, trigData):
						delRegions, newRegionInfo = self._pendingRegionChanges
						self._pendingRegionChanges = ([], [])
						for args, kw in newRegionInfo:
							self.regionBrowser.newRegion(*args, **kw)
						# delete regions second so that sequence-region
						# menu doesn't become temporarily empty, causing
						# it to switch to "entire alignment"
						for region in set(delRegions) & set(self.regionBrowser.regions):
							self.regionBrowser.deleteRegion(region)
						from chimera.triggerSet import ONESHOT
						return ONESHOT
					self.triggers.addHandler(blockingTrigger, makeNewRegions, None)
				for dr in delRegions:
					if dr not in self._pendingRegionChanges[0]:
						self._pendingRegionChanges[0].append(dr)
				for nr in newRegionInfo:
					if nr not in self._pendingRegionChanges[1]:
						self._pendingRegionChanges[1].append(nr)
		else:
			for args, kw in newRegionInfo:
				self.regionBrowser.newRegion(*args, **kw)
			# delete regions second so that sequence-region
			# menu doesn't become temporarily empty, causing
			# it to switch to "entire alignment"
			for region in delRegions:
				self.regionBrowser.deleteRegion(region)

	def _blastFinished(self, seq, results=None, failed=False, cancelled=False,
			**infoKw):
		try:
			del self._blastAnnotationServices[seq]
		except KeyError:
			# seq no longer in alignment
			return
		if failed or cancelled:
			return
		foundHit = False
		for line in results.split('\n'):
			words = line.split()
			if words and words[0].startswith("<Hit_def>UniRef") \
			and len(words[0].split('_')) == 3:
				if foundHit:
					# didn't find the E-value?!?
					self.uniprotInfo(seq, "uniprot", methodInfo=uniprotID, **infoKw)
					replyobj.info("Mapping annotations to %s from top BLAST hit in UniRef100: %s"
						% (seq.name, uniprotID))
					break
				prefix1, prefix2, uniprotID = words[0].split('_')
				self.uniprotInfo(seq, "uniprot", methodInfo=uniprotID, **infoKw)
				foundHit = True
				continue
			if foundHit and words and words[0].startswith("<Hsp_evalue>"):
				evalue = words[0].replace("<Hsp_evalue>", "").replace("</Hsp_evalue>", "")
				msgLines = [
					"Mapping annotations to %s from top BLAST hit in UniRef100:"
					% seq.name,
					"UniProt ID %s (E-value: %s)" % (uniprotID, evalue)
				]
				self.status("\n".join(msgLines))
				replyobj.info(" ".join(msgLines) + "\n")
				from chimera import dialogs
				dialogs.display("reply")
				break
		else:
			replyobj.error("Blast of UniProt yielded no hits for %s\n" % seq.name)

	def _closeModelsCB(self, trigName, myData, models):
		self._modelChangeCB(models)

	def _disableAlignDialog(self):
		self.alignDialog.Cancel()
		self.alignDialog.destroy()
		self.alignDialog = None

	def _disableAssessDialog(self):
		self.assessDialog.Cancel()
		self.assessDialog.destroy()
		self.assessDialog = None

	def _disableAssociationsDialog(self):
		self.associationsDialog.Cancel()
		self.associationsDialog.destroy()
		self.associationsDialog = None

	def _doByConsCB(self, mode):
		from chimera.dialogs import display, find
		import ShowAttr
		dialogName = ShowAttr.ShowAttrDialog.name
		if isinstance(self.seqCanvas.conservation[0], basestring):
			attrName = self.ConsAttr
		else:
			attrName = "mavConservation"
			d = find(dialogName)
			if d:
				d.refreshAttrs()
		d = display(dialogName)
		d.configure(models=self.associations.keys(), mode=mode,
			attrsOf="residues", attrName=attrName)

	def _editSeqName(self, seq):
		self._showSeqNameEditDialog()
		self.seqNameEditDialog.seqMenu.invoke(seq.name)
		
	def _fireAddDelSeq(self, trigName, myData, trigData):
		self.triggers.activateTrigger(ADDDEL_SEQS, (trigName, trigData))

	def _fireModAlign(self, trigName, myData, trigData):
		if len(self.seqs) == 1:
			state = "disabled"
		else:
			state = "normal"
		self.infoMenu.entryconfig("Percent Identity...", state=state)
		self.structureMenu.entryconfig("Modeller (homology)...", state=state)
		if len(self.associations) == 0:
			state = "disabled"
		self.structureMenu.entryconfigure("Render*", state=state)
		self.structureMenu.entryconfigure("Select*", state=state)
		self.triggers.activateTrigger(MOD_ALIGN, self.seqs)

	def _fireModAssoc(self, trigName, myData, trigData):
		self.triggers.activateTrigger(MOD_ASSOC, (trigName, trigData))

	def _getStartNumber(self, matchMap):
		for i in range(len(matchMap['aseq'].ungapped())):
			if i in matchMap:
				r = matchMap[i]
				return r.id.position - i
		return None

	def _loadStructures(self, auto=0):
		if self.intrinsicStructure:
			return
		structures = []
		for seq in self.seqs:
			if hasattr(seq, 'matchMaps') and seq.matchMaps:
				continue

			idInfo = self.seqNameToStructureID(seq.name)
			if not idInfo:
				continue
			structures.append(idInfo + (seq,))

		if auto and self.prefs[LOAD_PDB_DO_LIMIT] \
		and len(structures) > self.prefs[LOAD_PDB_LIMIT]:
			replyobj.warning("Number of structures to autoload "
				"(%d) exceeds user-specified threshold (%d)\n"
				% (len(structures), self.prefs[LOAD_PDB_LIMIT]))
			return
		prevAA = self.autoAssociate
		self.autoAssociate = False
		for identifier, structureType, seq in structures:
			try:
				models = chimera.openModels.open(identifier,
							type=structureType)
			except:
				replyobj.reportException("Problem opening %s"
								% identifier)
				continue
			self.associate(models, seq=seq, force=True)
		self.autoAssociate = prevAA
		if not structures:
			if auto:
				f = replyobj.warning
			else:
				f = replyobj.error
			f("Could not determine any PDBs/SCOPs"
						" from sequence names\n")

	def _makeSequenceRegions(self):
		regionCategories = {}
		for seq in self.seqs:
			for cat in seq.markups.keys():
				regionCategories.setdefault(cat, []).append(seq)
		if not regionCategories:
			return
		regionInfo = {}
		consideredBlank = " ._"
		def add2regionInfo(cat, c, seq, start, end):
			if not c or c in consideredBlank:
				return
			regName = "%s (%s)" % (cat, c)
			regionInfo.setdefault(regName, []).append((seq, seq,
								start, end))
		for cat, seqs in regionCategories.items():
			for seq in seqs:
				curChar = None
				for i, c in enumerate(seq.markups[cat]):
					if c == curChar:
						continue
					if curChar:
						add2regionInfo(cat, curChar,
								seq, start, i-1)
					curChar = c
					start = i
				add2regionInfo(cat, curChar, seq, start, i-1)
		from CGLtk.color import colorRange
		# sort regionInfo so that related regions are consecutive
		# in the region browser...
		riItems = regionInfo.items()
		riItems.sort()
		for ri, color in zip(riItems, colorRange(len(regionInfo))):
			regName, blocks = ri
			self.newRegion(name=regName, blocks=blocks, fill=color,
								shown=False)
		self.status("Alignment has per-sequence markups "
			"and corresponding regions have been created\n"
			"The regions can be displayed with "
			u"Info\u2192Region Browser", color="blue")

	def _modAssocCB(self, trigName, myData, trigData):
		if len(self.associations) > 1:
			self.structureMenu.entryconfigure("Match*",
							state='normal')
			self.structureMenu.entryconfigure("Assess*",
							state='normal')
		else:
			self.structureMenu.entryconfigure("Match*",
							state='disabled')
			self.structureMenu.entryconfigure("Assess*",
							state='disabled')
		if len(self.associations) > 0:
			if len(self.seqs) > 1:
				self.structureMenu.entryconfigure("Render*",
								state='normal')
				self.structureMenu.entryconfigure("Select*",
								state='normal')
			self.fileMenu.entryconfigure("Save Association Info...",
							state='normal')
			self.structureMenu.entryconfigure("Expand Selection to Columns",
							state='normal')
			self.structureMenu.entryconfigure("Modeller (loops/refinement)...",
							state='normal')
		else:
			self.structureMenu.entryconfigure("Render*",
							state='disabled')
			self.structureMenu.entryconfigure("Select*",
							state='disabled')
			self.fileMenu.entryconfigure("Save Association Info...",
							state='disabled')
			self.structureMenu.entryconfigure("Expand Selection to Columns",
							state='disabled')
			self.structureMenu.entryconfigure("Modeller (loops/refinement)...",
							state='disabled')
		mols = []
		delAdd, matchMaps = trigData
		for matchMap in matchMaps:
			# if molecule closed, this callback could be after
			# sequence's 'molecule' attribute is deleted and
			# before match map is updated
			try:
				mol = matchMap['mseq'].molecule
			except AttributeError:
				continue
			if delAdd == DEL_ASSOC:
				track = chimera.TrackChanges.get()
				attrNames = self._resAttrs.keys()
				for r in mol.residues:
					# newly-added residues may not have
					# the attribute...
					for attrName in attrNames:
						if hasattr(r, attrName):
							delattr(r, attrName)
							track.addModified(r,
							"attribute deleted")
			else:
				mols.append(mol)
		if mols:
			self.setResidueAttrs()
		self.showSS(show=None)
		self.showSS(show=None, ssType="predicted")

		# adjust sequence numberings if appropriate
		if not self.intrinsicStructure:
			aseqs = [mm['aseq'] for mm in matchMaps]
			changed = False
			for aseq in aseqs:
				if hasattr(aseq, 'matchMaps'):
					# as per comment above, 'molecule' attr could be missing...
					starts = set([self._getStartNumber(mm)
						for mm in aseq.matchMaps.values()
							if hasattr(mm['mseq'], "molecule")])
					starts.discard(None)
					if len(starts) == 1:
						start = starts.pop()
						if start != aseq.numberingStart:
							aseq.numberingStart = start
							changed = True
					else:
						if aseq.numberingStart != 1:
							aseq.numberingStart = 1
							changed = True
			if changed:
				self.updateNumberings()

	def _modelChangeCB(self, models):
		if len(filter(lambda m: isinstance(m, chimera.Molecule),
					chimera.openModels.list())) > 0:
			self.structureMenu.entryconfigure("Assoc*",
							state='normal')
		else:
			self.structureMenu.entryconfigure("Assoc*",
							state='disabled')

	def _monitorChangesCB(self, trigName, matchMaps, trigData):
		self.triggers.activateTrigger(DEL_ASSOC, matchMaps)
		self._monitorChangesData = []
		self._monitorChangesHandlerID = None
		from chimera.triggerSet import ONESHOT
		return ONESHOT

	def _mseqDelCB(self, trigName, matchMap, mseq):
		self.disassociate(mseq.molecule)

	def _mseqModCB(self, trigName, matchMap, mseq):
		# delay processing in case multiple sequences are
		# modified at once -- they will be in a consistent
		# state once the processing happens (which can cause
		# header updates)
		if not hasattr(self, '_pendingMseqModData'):
			self._pendingMseqModData = []
		if not self._pendingMseqModData:
			def _reassoc(trigName, myData, trigData, self=self):
				self.triggers.blockTrigger(ADD_ASSOC)
				self.triggers.blockTrigger(DEL_ASSOC)
				self.triggers.blockTrigger(MOD_ASSOC)
				while self._pendingMseqModData:
					matchMap, mseq = self._pendingMseqModData.pop()
					try:
						aseq = matchMap["aseq"]
						self.disassociate(mseq.molecule, reassoc=True)
						if self.intrinsicStructure:
							# show possible residue type changes for
							# non-multiple alignments only
							self.seqCanvas.refresh(aseq)
						if isinstance(mseq, StaticStructureSequence):
							self.associate(None, seq=aseq, reassoc=True)
						else:
							self.associate(mseq, seq=aseq, force=True, reassoc=True)
					except:
						replyobj.reportException(description="MAV Error")
				self.triggers.releaseTrigger(ADD_ASSOC)
				self.triggers.releaseTrigger(DEL_ASSOC)
				self.triggers.releaseTrigger(MOD_ASSOC)
				from chimera.triggerSet import ONESHOT
				return ONESHOT
			chimera.triggers.addHandler('monitor changes', _reassoc, None)
		self._pendingMseqModData.append((matchMap, mseq))
		
	def _newModelsCB(self, trigName=None, myData=None, models=None):
		self._modelChangeCB(models)
		if not self.autoAssociate:
			return
		self.associate(models, force=False)

	def _outputConsensusPreamble(self, f):
		from prefs import CONSENSUS_STYLE
		print>>f, "# Consensus for", self.title
		print>>f, "#"
		print>>f, "# consensus settings"
		print>>f, "# ---------------------"
		print>>f, "#   style: ", self.prefs[CONSENSUS_STYLE]

	def _outputConservationPreamble(self, f):
		from prefs import CONSERVATION_STYLE, CSV_AL2CO
		print>>f, "# Conservation for", self.title
		print>>f, "#"
		print>>f, "# conservation settings"
		print>>f, "# ---------------------"
		print>>f, "#   style: ", self.prefs[CONSERVATION_STYLE]
		if self.prefs[CONSERVATION_STYLE] == CSV_AL2CO:
			from prefs import al2coFrequencies, AL2CO_FREQ, \
				al2coConservations, AL2CO_CONS, AL2CO_WINDOW, \
				AL2CO_GAP, AL2CO_MATRIX, al2coTransforms, \
				AL2CO_TRANSFORM
			print>>f, "#   AL2CO frequency estimation:", \
				al2coFrequencies[self.prefs[AL2CO_FREQ]]
			print>>f, "#   AL2CO conservation measure:", \
				al2coConservations[self.prefs[AL2CO_CONS]]
			print>>f, "#   AL2CO averaging window:", \
				self.prefs[AL2CO_WINDOW]
			print>>f, "#   AL2CO gap fraction: %g" % (
				self.prefs[AL2CO_GAP])
			if self.prefs[AL2CO_CONS] == 2:
				print>>f, "#   AL2CO similarity matrix:", \
							self.prefs[AL2CO_MATRIX]
				print>>f, "#   AL2CO matrix transformation:", \
					al2coTransforms[self.prefs[AL2CO_TRANSFORM]]
			print>>f, "#"
			print>>f, "# Published work using AL2CO" \
				" conservation measures should cite:"
			print>>f, "#    Pei, J. and Grishin, N.V. (2001)"
			print>>f, "#    AL2CO: calculation of positional" \
								" conservation"
			print>>f, "#            in a protein sequence alignment"
			print>>f, "#    Bioinformatics, 17, 700-712."

	def _rebuildHeadersMenu(self, *args):
		# find last separator
		hm = self.headersMenu
		end = hm.index('end')
		for lastSep in range(end, 0, -1):
			if hm.type(lastSep) == "separator":
				break
		if lastSep < end:
			hm.delete(lastSep+1, end)
		shown = self.seqCanvas.headerDisplayOrder()
		self._headerVars = [] # have to hold a reference apparently...
		hmState = 'disabled'
		for hd in shown:
			if hd.singleSequenceRelevant or len(self.seqs) > 1:
				state = 'normal'
				hmState = 'normal'
			else:
				state = 'disabled'
			var = Tkinter.IntVar(hm)
			var.set(True)
			self._headerVars.append(var)
			hm.add_checkbutton(label=hd.name or "(no name)", variable=var,
				selectcolor="black", state=state,
				command=lambda hd=hd: self.hideHeaders([hd], fromMenu=True))
		hm.entryconfig("Save...", state=hmState)
		unshown = []
		for hd in self.seqCanvas.headers:
			if hd not in shown:
				unshown.append(hd)
		unshown.sort(lambda h1, h2:
					cmp(h1.name.lower(), h2.name.lower()))
		for hd in unshown:
			var = Tkinter.IntVar(hm)
			var.set(False)
			self._headerVars.append(var)
			if hd.singleSequenceRelevant or len(self.seqs) > 1:
				state = 'normal'
			else:
				state = 'disabled'
			hm.add_checkbutton(label=hd.name or "(no name)", variable=var,
				selectcolor="black", state=state,
				command=lambda hd=hd: self.showHeaders([hd], fromMenu=True))

	def _resChangeCB(self, triggerName, myData, trigData):
		if not trigData.modified:
			return
		if "isHelix changed" in trigData.reasons \
		or "isStrand changed" in trigData.reasons:
			self.showSS(show=None)

	def _saveSession(self, triggerName, myData, sessionFile):
		print>>sessionFile, "try:"
		print>>sessionFile, "\tseqInfo = [",
		from SimpleSession import sesRepr
		for seq in self.seqs:
			print>>sessionFile, sesRepr(seq.saveInfo()), ","
		print>>sessionFile, "\t]"
		print>>sessionFile, "\tfrom chimera.Sequence import restoreSequence"
		print>>sessionFile, "\tseqs = [restoreSequence(s) for s in seqInfo]"
		print>>sessionFile, "\tfrom MultAlignViewer.MAViewer import restoreMAV"
		print>>sessionFile, "\tregisterAfterModelsCB(lambda rm=restoreMAV, s=seqs: rm(s, %s))" % (self.saveInfo())
		print>>sessionFile, "\tdel seqInfo, restoreSequence, s, seqs, restoreMAV"
		print>>sessionFile, "except:"
		print>>sessionFile, "\treportRestoreError('Error restoring MultAlignViewer instance [' +",  repr(self.title), "+ '] in session')"
		self._edited = False
		
	def _seqRenameCB(self, trigName, myData, trigInfo):
		self.triggers.activateTrigger(SEQ_RENAMED, trigInfo)

	def _showAddSeqDialog(self):
		if self.addSeqDialog:
			self.addSeqDialog.enter()
		else:
			from AddSeqDialog import AddSeqDialog
			self.addSeqDialog = AddSeqDialog(self)

	def _showAlignDialog(self):
		if self.alignDialog:
			self.alignDialog.enter()
		else:
			from AlignDialog import AlignDialog
			self.alignDialog = AlignDialog(self)

	def _showCopySeqDialog(self):
		if self.copySeqDialog:
			self.copySeqDialog.enter()
		else:
			from CopySeqDialog import CopySeqDialog
			self.copySeqDialog = CopySeqDialog(self)

	def _showNumberingsDialog(self):
		if self.numberingsDialog:
			self.numberingsDialog.enter()
		else:
			from NumberingsDialog import NumberingsDialog
			self.numberingsDialog = NumberingsDialog(self)

	def _showAlignAttrDialog(self):
		if self.alignAttrDialog:
			self.alignAttrDialog.enter()
		else:
			from AttrDialog import AlignmentAttrDialog
			self.alignAttrDialog = AlignmentAttrDialog(
						self.fileAttrs, self.status)

	def _showSeqNameEditDialog(self):
		if self.seqNameEditDialog:
			self.seqNameEditDialog.enter()
		else:
			from EditSeqNameDialog import EditSeqNameDialog
			self.seqNameEditDialog = EditSeqNameDialog(self)

	def _showAssessDialog(self):
		if self.assessDialog:
			self.assessDialog.enter()
		else:
			from AssessDialog import AssessDialog
			self.assessDialog = AssessDialog(self)

	def _showModellerHomologyDialog(self):
		if self.modellerHomologyDialog:
			self.modellerHomologyDialog.enter()
		else:
			from ModellerDialog import ModellerDialog
			self.modellerHomologyDialog = ModellerDialog(self)

	def _showModellerLoopsDialog(self):
		if self.modellerLoopsDialog:
			self.modellerLoopsDialog.enter()
		else:
			from LoopsDialog import LoopsDialog
			self.modellerLoopsDialog = LoopsDialog(self)

	def _showAssociationsDialog(self):
		if self.associationsDialog:
			self.associationsDialog.enter()
		else:
			from AssociationsDialog import AssociationsDialog
			self.associationsDialog = AssociationsDialog(self)

	def _showAssocInfoDialog(self):
		if self.assocInfoDialog:
			self.assocInfoDialog.enter()
		else:
			from AssocInfoDialog import AssocInfoDialog
			self.assocInfoDialog = AssocInfoDialog(self)

	def _showEditKeysDialog(self):
		if self.editKeysDialog:
			self.editKeysDialog.enter()
		else:
			from EditKeysDialog import EditKeysDialog
			self.editKeysDialog = EditKeysDialog()

	def _showSaveHeaderDialog(self):
		if self.saveHeaderDialog:
			self.saveHeaderDialog.enter()
		else:
			from SaveHeaderDialog import SaveHeaderDialog
			self.saveHeaderDialog = SaveHeaderDialog(self)

	def _showBlastPdbDialog(self):
		if self.blastPdbDialog:
			self.blastPdbDialog.enter()
		else:
			from BlastPdbDialog import BlastPdbDialog
			self.blastPdbDialog = BlastPdbDialog(self)

	def _showColorSchemeDialog(self):
		if self.colorSchemeDialog:
			self.colorSchemeDialog.enter()
		else:
			from clustalX import ColorSchemeDialog
			self.colorSchemeDialog = ColorSchemeDialog(self)

	def _showDelSeqsGapsDialog(self):
		if self.delSeqsGapsDialog:
			self.delSeqsGapsDialog.enter()
		else:
			from DelSeqsGapsDialog import DelSeqsGapsDialog
			self.delSeqsGapsDialog = DelSeqsGapsDialog(self)

	def _showEpsDialog(self):
		if self.epsDialog:
			self.epsDialog.enter()
		else:
			from EpsDialog import EpsDialog
			self.epsDialog = EpsDialog(self)

	def _showFetchAnnotationsDialog(self):
		if self.fetchAnnotationsDialog:
			self.fetchAnnotationsDialog.enter()
		else:
			from FetchAnnotationsDialog import FetchAnnotationsDialog
			self.fetchAnnotationsDialog = FetchAnnotationsDialog(self)

	def _showFindDialog(self):
		if self.findDialog:
			self.findDialog.enter()
		else:
			from FindDialog import FindDialog
			self.findDialog = FindDialog(self)

	def _showFindSeqNameDialog(self):
		if self.findSeqNameDialog:
			self.findSeqNameDialog.enter()
		else:
			from FindDialog import FindSeqNameDialog
			self.findSeqNameDialog = FindSeqNameDialog(self)

	def _showIdentityDialog(self):
		if self.identityDialog:
			self.identityDialog.enter()
		else:
			from IdentityDialog import IdentityDialog
			self.identityDialog = IdentityDialog(self)

	def _showInsertGapDialog(self):
		if self.insertGapDialog:
			self.insertGapDialog.enter()
		else:
			from InsertGapDialog import InsertGapDialog
			self.insertGapDialog = InsertGapDialog(self)

	def _showLoadHeaderDialog(self):
		if self.loadHeaderDialog:
			self.loadHeaderDialog.enter()
		else:
			from LoadHeaderDialog import LoadHeaderDialog
			self.loadHeaderDialog = LoadHeaderDialog(self)

	def _showPrositeDialog(self):
		if self.prositeDialog:
			self.prositeDialog.enter()
		else:
			from FindDialog import PrositeDialog
			self.prositeDialog = PrositeDialog(self)

	def _showRealignmentDialog(self):
		if self.realignDialog:
			self.realignDialog.enter()
		else:
			from RealignDialog import RealignDialog
			self.realignDialog = RealignDialog(self)

	def _showRegexDialog(self):
		if self.regexDialog:
			self.regexDialog.enter()
		else:
			from FindDialog import RegexDialog
			self.regexDialog = RegexDialog(self)

	def _showReorderDialog(self):
		if self.reorderDialog:
			self.reorderDialog.enter()
		else:
			from ReorderDialog import ReorderDialog
			self.reorderDialog = ReorderDialog(self)

	def _showTreeCB(self):
		self.seqCanvas.showTree(self.showTreeVar.get())
		
	def _showTreeDialog(self):
		if self.treeDialog:
			self.treeDialog.enter()
		else:
			from parsePhylo import PhylogenyDialog
			self.treeDialog = PhylogenyDialog(self)

	def _treeCB(self, node):
		pass

def restoreMAV(seqs, mavInfo, quitCB=None, frame=None, ownSeqs=None):
	"""restore MAV from session"""
	# ownSeqs keyword needed for backwards compatibility
	from chimera.Sequence import restoreSequence
	if isinstance(mavInfo, basestring):
		mavInfo = eval(mavInfo)
	mavKw = {}
	if 'numberings' in mavInfo:
		mavKw['numberingDisplay'] = mavInfo['numberings']
	if 'sessionSave' in mavInfo:
		mavKw['sessionSave'] = mavInfo['sessionSave']

	mav = MAViewer(seqs, autoAssociate=False, title=mavInfo['title'],
		quitCB=quitCB, frame=frame, **mavKw)
	seqs = mav.seqs # some may now be StaticStructureSequences
	if 'specials' in mavInfo:
		headerInfo = mavInfo['specials']
		addHeaders = []
		for si in headerInfo:
			try:
				ri = si['restore info']
			except KeyError:
				continue
			try:
				className, initArgs, initKw = ri
				if not isinstance(initKw, dict):
					raise ValueError("3-letter sequence!")
			except ValueError:
				from HeaderSequence import FixedHeaderSequence
				addHeaders.append(FixedHeaderSequence(si['name'], mav, ri))
			else:
				if className == "FixedHeaderSequence":
					from HeaderSequence import FixedHeaderSequence
					classObj = FixedHeaderSequence
				elif className == "CustomFixedHeader":
					classObj = CustomFixedHeader
				else:
					raise ValueError("Don't know how to restore %s header type" % className)
				addHeaders.append(classObj(si['name'], mav, *initArgs, **initKw))
		if addHeaders:
			mav.addHeaders(addHeaders)

		if 'header shown' in mavInfo:
			shown = mavInfo['header shown']
		else:
			shown = [True] * (len(headerInfo)+2)
		show = []
		hide = []
		for i, builtin in enumerate(mav.seqCanvas.headers[:2]):
			if shown[i]:
				show.append(builtin)
			else:
				hide.append(builtin)
		for i, si in enumerate(headerInfo):
			name, klass = si['name'], si['class']
			if name == "RMSD" and klass == "DistanceSeq":
				# old RMSD header
				from MAVHeader.ChimeraExtension import CaDistanceSeq
				name, klass = CaDistanceSeq.name, CaDistanceSeq.__name__
			for seq in mav.seqCanvas.headers[2:]:
				if seq.name == name and seq.__class__.__name__ == klass:
					if shown[i+2]:
						show.append(seq)
					else:
						hide.append(seq)
					break
		if 'header display order' in mavInfo \
		and len(mav.seqCanvas.headers) == len(shown) \
		and len(mavInfo['header display order']) == len(show):
			mav.hideHeaders(mav.seqCanvas.headers)
			mav.showHeaders([mav.seqCanvas.headers[i] for i in mavInfo['header display order']])
		else:
			mav.showHeaders(show)
			mav.hideHeaders(hide)

	if 'ruler shown' in mavInfo:
		mav.setRulerDisplay(showRuler=mavInfo['ruler shown'])

	regionInfo = mavInfo['regions']
	# newRegion() inserts at head, so reverse order before calling...
	regionInfo.reverse()
	rb = mav.regionBrowser
	rb.clearRegions() # get rid of selection region
	helixReg = strandReg = None
	for ri in regionInfo:
		blocks = []
		for block in ri['blocks']:
			i1, i2, pos1, pos2 = block
			if i1 >= 0:
				seq1 = seqs[i1]
			else:
				seq1 = mav.seqCanvas.headers[-1 - i1]
			if i2 >= 0:
				seq2 = seqs[i2]
			else:
				seq2 = mav.seqCanvas.headers[-1 - i2]
			blocks.append([seq1, seq2, pos1, pos2])
			ri['blocks'] = blocks
		if 'coverGaps' not in ri and ri['name'] \
		and ri['name'] in rb.SS_REG_NAMES:
			ri['coverGaps'] = False
		if 'sequence' in ri:
			ri['sequence'] = seqs[ri['sequence']]
		nr = rb.newRegion(sessionRestore=True,
				rebuildTable=(ri == regionInfo[-1] or ri.get('select', False)), **ri)
		if nr.name == rb.ACTUAL_HELICES_REG_NAME:
			helixReg = nr
			helixShown = nr.shown
		if nr.name == rb.ACTUAL_STRANDS_REG_NAME:
			strandReg = nr
			strandShown = nr.shown
	associations = mavInfo['associations']
	if 'mseqs' in mavInfo:
		mseqs = [restoreSequence(ms) for ms in mavInfo['mseqs']]
		for seqIndex, mseqIndex in associations:
			seq = seqs[seqIndex]
			mseq = mseqs[mseqIndex]
			if isinstance(seq, StructureSequence) \
			and mseq.residues == seq.residues:
				# circular permutations problematic otherwise
				mav.associate([], seq=seq, showMatches=False, showErrors=False)
				mseqs[mseqIndex] = seq # otherwise region association wrong
			else:
				mav.associate(mseq, seq=seq,
					showMatches=False, showErrors=False)
		for keyInfo, regionIndices in mavInfo['region associations'].items():
			mseqIndex, aseqIndex = keyInfo
			key = (mseqs[mseqIndex], seqs[aseqIndex])
			regions = [rb.regions[i] for i in regionIndices]
			rb.associatedRegions[key] = regions
			for region in regions:
				region.associatedWith = key
	else:
		for index, mseqInfo in associations:
			mav.associate(restoreSequence(mseqInfo),
					seq=seqs[index], showMatches=False,
					showErrors=False)
	# turning these on needs to happen after associate to avoid
	# re-creating SS regions that may have been deleted explicitly
	if 'showActualSS' in mavInfo:
		mav.showSSVar.set(mavInfo['showActualSS'])
		mav.showPredictedSSVar.set(mavInfo['showPredictedSS'])

	# there is a small chance that 'shown' attr of secondary structure
	# regions are changed by association (would have to differ from menu
	# settings, prob by using region browser), so sync up again...
	if helixReg is not None:
		helixReg.shown = helixShown
	if strandReg is not None:
		strandReg.shown = strandShown
	mav.autoAssociate = mavInfo['autoAssociate']
	if 'intrinsic' in mavInfo:
		mav._intrinsicStructure = mavInfo['intrinsic']
	mav.fileAttrs = mavInfo.get('fileAttrs', {})
	mav.fileMarkups = mavInfo.get('fileMarkups', {})
	if 'numberingsStripped' in mavInfo:
		mav.numberingsStripped = mavInfo['numberingsStripped']
	if mavInfo.get('tree', None):
		from parsePhylo import parseNewick
		mav.useTree(parseNewick(mavInfo['tree'],
			numberingsStripped=mav.numberingsStripped)[0], askReorder=False)
		if not mavInfo.get('show tree', True):
			mav.showTreeVar.set(False)
			mav.seqCanvas.showTree(False)

	try:
		rmwsList = mavInfo['runModellerWS']
	except KeyError:
		# Probably saved by an older version of Chimera
		pass
	else:
		from ModellerBase import restoreRunModellerWS
		for sesData in rmwsList:
			restoreRunModellerWS(mav, sesData,
					versioned=mavInfo.get('versionedModSesData', False))

	try:
		realignmentInfo = mavInfo['realignmentWS']
	except KeyError:
		pass
	else:
		from RealignBase import RunRealignmentWS
		for sesData, reordersSequences in realignmentInfo['self']:
			RunRealignmentWS(mav._addRealignmentJob, mav._removeRealignmentJob,
				mav._removeRealignmentJob, mav=mav, sessionData=sesData,
				reordersSequences=reordersSequences)
		for sesData, reordersSequences in realignmentInfo['new']:
			RunRealignmentWS(mav._addRealignmentJob, mav._removeRealignmentJob,
				mav._removeRealignmentJob, mav=None, sessionData=sesData,
				reordersSequences=reordersSequences)

	if 'blastAnnotationServices' in mavInfo:
		from blastpdb.ParserBlastP import BlastpService
		for seqIndex, serviceInfo in mavInfo['blastAnnotationServices'].items():
			seq = mav.seqs[seqIndex]
			serviceData, cbKw = serviceInfo
			mav._blastAnnotationServices[seq] =  (BlastpService(
				lambda params, results, f=mav._blastFinished, seq=seq, cbKw=cbKw: f(seq,
				results=results, **cbKw), sessionData=serviceData,
				failCB=lambda f=mav._blastFinished, seq=seq: f(seq, failed=True),
				cancelCB=lambda f=mav._blastFinished, seq=seq:
				f(seq, cancelled=True)), cbKw)
	return mav

class SeqMenu(Pmw.OptionMenu):
	NoneOptionText = "none"
		# getvalue() == None (or [] if includeAllOption == True)
	AllOptionText = "all sequences"
		# getvalue() == list of all seqs or list of one seq
		# (or possibly [] if includeNoneOption == True)

	def __init__(self, parent, mav, includeNoneOption=False,
			includeAllOption=False, **kw):
		assert('items' not in kw)
		self.__mav = mav
		self.__includeNoneOption = includeNoneOption
		self.__includeAllOption = includeAllOption
		items = self.__makeItems()
		if 'command' in kw:
			kw['command'] = lambda txt, cb=kw['command']: cb(self.getvalue())
		Pmw.OptionMenu.__init__(self, parent, items=items, **kw)
		self.__handlerIDs = {}
		for trig, cb in [(SEQ_RENAMED, self.__seqRenamedCB),
				(PRE_DEL_SEQS, self.__preDelCB),
				(ADD_SEQS, self.__addSeqsCB), (DEL_SEQS, self.__delSeqsCB)]:
			self.__handlerIDs[trig] = mav.triggers.addHandler(trig, cb, None)

	def destroy(self):
		for trig, handlerID in self.__handlerIDs.items():
			self.__mav.triggers.deleteHandler(trig, handlerID)
		self.__mav = None
		Pmw.OptionMenu.destroy(self)

	def getvalue(self):
		index = Pmw.OptionMenu.index(self, Pmw.SELECT)
		if self.__includeNoneOption:
			if index == 0:
				if self.__includeAllOption:
					return []
				return None
			index -= 1
		if self.__includeAllOption:
			if index == 0:
				return self.__mav.seqs
			index -= 1
		seq = self.__mav.seqs[index]
		if self.__includeAllOption:
			return [seq]
		return seq

	def setvalue(self, seq):
		if isinstance(seq, basestring):
			return Pmw.OptionMenu.setvalue(self, seq)
		if isinstance(seq, Sequence):
			index = self.__mav.seqs.index(seq) + self.__includeNoneOption \
				+ self.__includeAllOption
		elif not seq:
			index = 0
		else:
			index = int(self.__includeNoneOption)
		self.invoke(index)

	def __addSeqsCB(self, trigName, myData, addSeqs):
		curSel = self.getvalue()
		items = self.__makeItems()
		if isinstance(curSel, Sequence):
			index = self.__mav.seqs.index(curSel) + self.__includeNoneOption \
				+ self.__includeAllOption
		elif not curSel:
			index = 0
		else:
			index = int(self.__includeNoneOption)
		self.setitems(items, index=index)

	def __delSeqsCB(self, trigName, myData, delSeqs):
		preDelVal = self.__preDeletionVal
		self.__preDeletionVal = None
		if type(preDelVal) == list and len(preDelVal) == 1:
			preDelVal = preDelVal[0]
		if type(preDelVal) != list and preDelVal in delSeqs:
			self.setitems(self.__makeItems())
			self.invoke(0)
		else:
			if isinstance(preDelVal, Sequence):
				index = self.__mav.seqs.index(preDelVal) \
					+ self.__includeNoneOption + self.__includeAllOption
			elif not preDelVal:
				index = 0
			else:
				index = int(self.__includeNoneOption)
			self.setitems(self.__makeItems(), index=index)

	def __makeItems(self):
		items = []
		if self.__includeNoneOption:
			items.append(self.NoneOptionText)
		if self.__includeAllOption:
			items.append(self.AllOptionText)
		items.extend([s.name for s in self.__mav.seqs])
		return items

	def __preDelCB(self, trigName, myData, delSeqs):
		self.__preDeletionVal = self.getvalue()

	def __seqRenamedCB(self, trigName, myData, trigData):
		seq, oldName = trigData
		curSeq = self.getvalue()
		if self.__includeAllOption and curSeq:
			curSeq = curSeq[0]
		items = self.__makeItems()
		if seq == curSeq:
			kw = {'index': self.__mav.seqs.index(seq) \
				+ self.__includeNoneOption + self.__includeAllOption}
		else:
			kw = {}
		self.setitems(items, **kw)

class SeqList(Pmw.ScrolledListBox):
	def __init__(self, parent, mav, **kw):
		assert('items' not in kw)
		self.__mav = mav
		items = self.__makeItems()
		Pmw.ScrolledListBox.__init__(self, parent, items=items, **kw)
		self.__handlerIDs = {}
		for trig, cb in [(SEQ_RENAMED, self.__addOrRenameSeqsCB),
				(PRE_DEL_SEQS, self.__preDelCB),
				(ADD_SEQS, self.__addOrRenameSeqsCB),
				(DEL_SEQS, self.__delSeqsCB)]:
			self.__handlerIDs[trig] = mav.triggers.addHandler(trig, cb, None)

	def destroy(self):
		for trig, handlerID in self.__handlerIDs.items():
			self.__mav.triggers.deleteHandler(trig, handlerID)
		self.__mav = None
		Pmw.ScrolledListBox.destroy(self)

	def getvalue(self):
		indices = [int(s) for s in self.curselection()]
		return [self.__mav.seqs[i] for i in indices]

	def setvalue(self, seqs):
		if isinstance(seqs, basestring) \
		or (seqs and isinstance(seqs[0], basestring)):
			Pmw.ScrolledListBox.setvalue(self, seqs)
		else:
			Pmw.ScrolledListBox.setvalue(self, [s.name for s in seqs])

	def __addOrRenameSeqsCB(self, trigName, myData, trigData):
		curSel = self.getvalue()
		self.setlist(self.__makeItems())
		self.setvalue(curSel)

	def __delSeqsCB(self, trigName, myData, delSeqs):
		preDelVal = self.__preDeletionVal
		self.__preDeletionVal = None
		seqSet = set(self.__mav.seqs)
		remSel = [pdv for pdv in preDelVal if pdv in seqSet]
		self.setlist(self.__makeItems())
		if remSel:
			self.setvalue(remSel)

	def __makeItems(self):
		return [s.name for s in self.__mav.seqs]

	def __preDelCB(self, trigName, myData, delSeqs):
		self.__preDeletionVal = self.getvalue()

from HeaderSequence import FixedHeaderSequence
class CustomFixedHeader(FixedHeaderSequence):
	colorFunc = lambda self, seq, pos: seq.__colors[pos]

	def __init__(self, name, mav, vals, colors, style):
		self.__colors = colors
		self.__style = style
		if style == "numeric":
			numVals = [v for v in vals if v is not None]
			if numVals:
				if min(numVals) < 0:
					self.depictionVal = self.histInfinity
				elif max(numVals) > 1:
					self.depictionVal = self.positiveHistInfinity
		FixedHeaderSequence.__init__(self, name, mav, vals)

	def saveInfo(self):
		return (self.vals, self.__colors, self.__style), {}

# used in sorting sequences for comparsion against structure sequence
# could have been inline, but moved here due reduce indentation nightmares
def _mixSort(a, b, lm):
	la = len(a.ungapped())
	lb = len(b.ungapped())
	if la >= lm:
		if lb >= lm:
			return cmp(la, lb)
		else:
			return -1
	else:
		if lb >= lm:
			return 1
		else:
			return cmp(lb, la)
