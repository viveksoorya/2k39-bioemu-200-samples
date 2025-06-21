# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42121 2020-02-26 21:27:17Z pett $

import chimera
from chimera import replyobj
from chimera.baseDialog import ModelessDialog
from chimera.widgets import MoleculeChainScrolledListBox, \
					MoleculeChainOptionMenu
from chimera.tkoptions import FloatOption, SymbolicEnumOption
import Tkinter, Pmw
from prefs import prefs, defaults, DIST_CUTOFF, CIRCULAR, ANYALL, GAPCHAR, \
	ITERATE, ITER_CONVERGE, ITER_AMOUNT, ITER_ALL_COLS, ITER_CONSECUTIVE_COLS

class Match2Align(ModelessDialog):
	title = "Create Alignment from Superposition"
	help = "ContributedSoftware/matchalign/matchalign.html"

	def fillInUI(self, parent):
		row = 0
		f = Tkinter.Frame(parent, bd=4, relief="raised")
		f.grid(row=row, column=0, sticky='nsew')
		parent.columnconfigure(0, weight=1)
		parent.rowconfigure(row, weight=1)
		row += 1
		self.chainList = MoleculeChainScrolledListBox(f,
					selectioncommand=self._updateIterRef,
					listbox_selectmode='multiple')
		self.chainList.grid(row=0, column=0, columnspan=2, sticky='nsew')
		f.rowconfigure(0, weight=1)
		Tkinter.Button(f, text="Choose all", command=lambda s=self:
			s.chainList.setvalue(s.chainList.get())).grid(row=1, column=0)
		Tkinter.Button(f, text="Clear choices", command=lambda s=self:
			s.chainList.setvalue([])).grid(row=1, column=1)
		f.columnconfigure(0, weight=1)
		f.columnconfigure(1, weight=1)
		mols = {}
		for chain in self.chainList.get():
			mol = chain.molecule
			if mol in mols:
				continue
			mols[mol] = chain
		self.chainList.setvalue(mols.values())

		f = Tkinter.Frame(parent)
		f.grid(row=row, column=0, sticky='w')
		row += 1
		self.distCutoff = FloatOption(f, 0,
			"Residue-residue distance cutoff (angstroms)",
			prefs[DIST_CUTOFF], None, balloon="""\
residues whose principal atoms are further apart
than this distance will not be aligned in the
generated sequence alignment""")
		self.distCutoff.min = 0.0

		class MatchTypeOption(SymbolicEnumOption):
			values = ["any", "all"]
			labels = ["at least one other", "all others"]
		f = Tkinter.Frame(parent)
		f.grid(row=row, column=0, sticky='w')
		row += 1
		self.matchType = MatchTypeOption(f, 0,
			"Residue aligned in column if within cutoff of",
			prefs[ANYALL], None, balloon="""\
whether a residue needs to match the distance cutoff to all other
residues in its column, or just to one residue in the column""")

		class GapCharOption(SymbolicEnumOption):
			values = [".", "-", "~"]
			labels = [". (period)", "- (dash)", "~ (tilde)"]
		f = Tkinter.Frame(parent)
		f.grid(row=row, column=0, sticky='w')
		row += 1
		self.gapChar = GapCharOption(f, 0, "Gap character",
			prefs[GAPCHAR], None, balloon="""\
character used to depict gaps in alignment""")

		self.circularVar = Tkinter.IntVar(parent)
		self.circularVar.set(prefs[CIRCULAR])
		Tkinter.Checkbutton(parent, variable=self.circularVar, text=
				"Allow for circular permutation").grid(row=row,
				column=0, sticky='w')
		row += 1

		self.iterateVar = Tkinter.IntVar(parent)
		self.iterateVar.set(prefs[ITERATE])
		Tkinter.Checkbutton(parent, command=self._iterParamsDisplay,
				text="Iterate superposition/alignment...",
				variable=self.iterateVar).grid(
				row=row, column=0, columnspan=2, sticky='w')
		row += 1
		self.iterParams = Pmw.Group(parent, hull_padx=2,
					tag_text="Iteration Parameters")
		self.iterParams.grid(row=row, column=0, columnspan=2)
		row += 1
		inside = self.iterParams.interior()
		Tkinter.Label(inside, text="Iterate alignment:").grid(
					row=0, column=0, rowspan=2, sticky='e')
		self.iterConvergeVar = Tkinter.IntVar(parent)
		self.iterConvergeVar.set(prefs[ITER_CONVERGE])
		f = Tkinter.Frame(inside)
		f.grid(row=0, column=1, sticky='w')
		Tkinter.Radiobutton(f, value=False, text="at most",
			variable=self.iterConvergeVar).grid(row=0, column=0)
		self.iterLimit = Pmw.EntryField(f, labelpos='e',
			label_text="times", validate={'min': 1,
			'validator': 'numeric'}, value=str(prefs[ITER_AMOUNT]),
			entry_width=2, entry_justify="center")
		self.iterLimit.grid(row=0, column=1)
		Tkinter.Radiobutton(inside, text="until convergence",
			value=True, variable=self.iterConvergeVar).grid(
			row=1, column=1, sticky='w')
		inside.rowconfigure(2, minsize="0.1i")
		Tkinter.Label(inside, text="Superimpose full columns:"
			).grid(row=3, rowspan=2, column=0, sticky='e')
		self.iterAllColsVar = Tkinter.IntVar(parent)
		self.iterAllColsVar.set(prefs[ITER_ALL_COLS])
		Tkinter.Radiobutton(inside, text="across entire alignment",
			value=True, variable=self.iterAllColsVar).grid(
			row=3, column=1, sticky='w')
		f = Tkinter.Frame(inside)
		f.grid(row=4, column=1, sticky='w')
		Tkinter.Radiobutton(f, text="in stretches of at least",
					variable=self.iterAllColsVar,
					value=False).grid(row=0, column=0)
		self.stretchLen = Pmw.EntryField(f, labelpos='e',
				label_text="consecutive columns",
				validate={'min': 2, 'validator': 'numeric'},
				value=str(prefs[ITER_CONSECUTIVE_COLS]),
				entry_width=1, entry_justify="center")
		self.stretchLen.grid(row=0, column=1)
		self.referenceMenu = Pmw.OptionMenu(inside, labelpos='w',
			items=Pmw.ScrolledListBox.get(self.chainList),
			label_text="Reference chain for matching:")
		self.referenceMenu.grid(row=5, column=0, columnspan=2)

		self._iterParamsDisplay()

		f = Tkinter.Frame(parent)
		f.grid(row=row, column=0, columnspan=2, sticky='ew')
		row += 1
		from chimera import help
		b = Tkinter.Button(f, text="Save settings", pady=0,
					command=self._saveSettings)
		b.grid(row=0, column=0)
		help.register(b, balloon="Save current settings")
		b = Tkinter.Button(f, text="Reset to defaults", pady=0,
					command=self._restoreSettings)
		b.grid(row=0, column=1)
		help.register(b, balloon="Reset dialog to factory defaults")
		f.columnconfigure(0, weight=1)
		f.columnconfigure(1, weight=1)

	def Apply(self):
		chains = self.chainList.getvalue()
		if len(chains) < 2:
			replyobj.error("Must choose at least two chains\n")
			self.enter()
			return

		iterate = self.iterateVar.get()
		ref = self.referenceMenu.getvalue()
		for name, refChain in self.chainList.itemMap.items():
			if name.decode('utf-8') == ref:
				break
		else:
			raise ValueError("Reference chain not in chain list?!?")

		if iterate and refChain not in chains:
			replyobj.error("Reference chain must be involved in alignment!\n")
			self.enter()
			return

		mols = {}
		for chain in chains:
			if chain.molecule in mols:
				replyobj.error(
				  "Please choose only one chain per model\n")
				self.enter()
				return
			mols[chain.molecule] = 1

		if self.iterConvergeVar.get():
			iterLimit = None
		else:
			self.iterLimit.invoke()
			iterLimit = int(self.iterLimit.getvalue())
		if self.iterAllColsVar.get():
			stretchLen = 1
		else:
			self.stretchLen.invoke()
			stretchLen = int(self.stretchLen.getvalue())
		makeAlignment(chains, cutoff=float(self.distCutoff.get()),
			matchType=self.matchType.get(), gapChar=self.gapChar.get(),
			circular=self.circularVar.get(), iterate=iterate,
			iterLimit=iterLimit, makeMAV=True, stretchLen=stretchLen,
			refChain=refChain)
		self.destroy()

	def _iterParamsDisplay(self):
		if self.iterateVar.get():
			self.iterParams.grid()
		else:
			self.iterParams.grid_remove()

	def _restoreSettings(self):
		from prefs import defaults
		self.distCutoff.set(defaults[DIST_CUTOFF])
		self.matchType.set(defaults[ANYALL])
		self.gapChar.set(defaults[GAPCHAR])
		self.circularVar.set(defaults[CIRCULAR])
		self.iterateVar.set(defaults[ITERATE])
		self._iterParamsDisplay()
		self.iterConvergeVar.set(defaults[ITER_CONVERGE])
		self.iterLimit.setvalue(str(defaults[ITER_AMOUNT]))
		self.iterAllColsVar.set(defaults[ITER_ALL_COLS])
		self.stretchLen.setvalue(str(defaults[ITER_CONSECUTIVE_COLS]))

	def _saveSettings(self):
		prefs[DIST_CUTOFF] = float(self.distCutoff.get())
		prefs[ANYALL] = self.matchType.get()
		prefs[GAPCHAR] = self.gapChar.get()
		prefs[CIRCULAR] = self.circularVar.get()
		prefs[ITERATE] = self.iterateVar.get()
		prefs[ITER_CONVERGE] = self.iterConvergeVar.get()
		self.iterLimit.invoke()
		prefs[ITER_AMOUNT] = int(self.iterLimit.getvalue())
		prefs[ITER_ALL_COLS] = self.iterAllColsVar.get()
		self.stretchLen.invoke()
		prefs[ITER_CONSECUTIVE_COLS] = int(self.stretchLen.getvalue())

	def _updateIterRef(self, *args):
		self.referenceMenu.setitems([self.chainList.valueMap[chain]
				for chain in self.chainList.getvalue()])

def alignedCols(seqs):
	aligned = []
	for i, chars in enumerate(zip(*tuple([s[:] for s in seqs]))):
		for c in chars:
			if not c.isalpha():
				break
		else:
			aligned.append(i)
	return aligned

def columnAtoms(seq, columns):
	from chimera.misc import principalAtom
	seqColumns = [seq.gapped2ungapped(i) for i in columns]
	if getattr(seq, 'circular', False):
		numRes = len(seq.residues)
		return [principalAtom(r)
			for r in [seq.residues[i % numRes] for i in seqColumns]]
	return [principalAtom(r) for r in [seq.residues[i] for i in seqColumns]]

def showAlignment(seqs, title):
	from MultAlignViewer.MAViewer import MAViewer
	replyobj.status("Showing alignment")
	mav = MAViewer(seqs, autoAssociate=False, title=title)
	mav.associate(None)
	mav.autoAssociate = True
	if len(seqs) < 3:
		mav.hideHeaders(mav.headers(shownOnly=True))
	from MAVHeader.ChimeraExtension import CaDistanceSeq
	mav.showHeaders([h for h in mav.headers() if h.name == CaDistanceSeq.name])
	return mav

def makeAlignment(chains, cutoff=defaults[DIST_CUTOFF], matchType=defaults[ANYALL],
		gapChar=defaults[GAPCHAR], circular=defaults[CIRCULAR],
		iterate=defaults[ITERATE], iterLimit=None, makeMAV=True,
		stretchLen=defaults[ITER_CONSECUTIVE_COLS], refChain=None):
	from align import match2align
	from Midas import match, rmsd
	if int(cutoff) == cutoff:
		cutoffFmt = "%.1f"
	else:
		cutoffFmt = "%g"
	cutoffText = cutoffFmt % cutoff
	replyobj.info(u"Match\u2192Align cutoff: %s, in column"
		" if within cutoff of: %s\n" % (cutoffText, matchType))
	seqs = match2align(chains, cutoff, matchType, gapChar, circular)
	cols = alignedCols(seqs)
	replyobj.info("%d fully populated columns\n" % (len(cols)))
	if iterate:
		best = None
		iteration = 1
		if not refChain:
			refChain = chains[0]
		while True:
			refSeq = [s for s in seqs
				if s.molecule == refChain.molecule][0]
			# cull columns based on stretch len criteria
			stretch = []
			culled = []
			for col in cols:
				if not stretch or stretch[-1]+1 == col:
					stretch.append(col)
					continue
				if len(stretch) >= stretchLen:
					culled.extend(stretch)
				stretch = [col]
			if len(stretch) >= stretchLen:
				culled.extend(stretch)
			if stretchLen > 1:
				replyobj.info("%d fully populated"
					" columns in at least %d"
					" column stretches\n" % (
					len(culled), stretchLen))
			if not culled:
				break
				
			# match
			refAtoms = columnAtoms(refSeq, culled)
			for seq in seqs:
				if seq.molecule == refSeq.molecule:
					continue
				seqAtoms = columnAtoms(seq, culled)
				replyobj.info("Matching %s onto %s\n"
					% (seq.name, refSeq.name))
				match(seqAtoms, refAtoms)
			seqs = match2align(chains, cutoff, matchType,
				gapChar, circular, statusPrefix=
				"Iteration %d: " % iteration)
			cols = alignedCols(seqs)
			replyobj.info("Iteration %d: %d fully populated"
				" columns\n" % (iteration, len(cols)))
			if best == None or len(cols) > len(best):
				best = cols
			else:
				break
			if iterLimit and iteration >= iterLimit:
				break
			iteration += 1

	if cols:
		# show pairwise RMSD matrix in fully populated columns
		matchAtoms = {}
		for seq in seqs:
			matchAtoms[seq] = columnAtoms(seq, cols)
		replyobj.info("\nEvaluating superpositions across all %d fully"
			" populated columns in the final alignment:\n"
			% len(cols))
		dsqSum = 0
		for i, s1 in enumerate(seqs):
			for s2 in seqs[i+1:]:
				v = rmsd(matchAtoms[s1], matchAtoms[s2],
								log=False)
				dsqSum += v * v
				replyobj.info("RMSD of %s with %s: %.3f\n" %
						(s1.name, s2.name, v))
		from math import sqrt
		overallRMSD = sqrt(2 * dsqSum / (len(seqs) * (len(seqs)-1)))
		replyobj.info("Overall RMSD: %.3f\n" % overallRMSD)
		numAligned = len(cols)
		from chimera.misc import principalAtom
		seqLens = [len([r for r in seq.residues if r and principalAtom(r)])
					for seq in seqs]
		replyobj.info("Sequence lengths: %s\n" %
					" ".join(["%d" % sl for sl in seqLens]))
		# compute/report SMD as per:
		# 	Comparison of sequence-based and structure-based phylogenetic
		#		trees of homologous proteins: Inferences on protein
		#		evolution
		#	Balaji S, Srinivasan N.
		#	J Biosci. 2007 Jan;32(1):83-96.
		relRMSD = overallRMSD / cutoff
		srms = 1.0 - relRMSD
		pfte = numAligned / float(min(seqLens))
		w1 = 1.0 - (pfte + srms) / 2.0
		w2 = (pfte + srms) / 2.0
		from math import log
		sdm = -100.0 * log(w1*pfte + w2*srms)
		replyobj.info("SDM (cutoff %s): %.3f\n" % (cutoffText, sdm))
		# compute/report Q score as per:
		#	Secondary structure matching (SSM), a new tool for fast
		#		protein structure alignment in three dimensions
		#	Krissinel E, Henrick K.
		#	Acta Crystallogr D Biol Crystallogr. 2004 Dec;
		#		60(Pt 12 Pt 1):2256-68.
		relRMSD = overallRMSD / 3.0
		seqLenMul = 1.0
		for seqLen in seqLens:
			seqLenMul *= seqLen
		q = (numAligned ** len(seqs)) / (
						(1.0 + relRMSD * relRMSD) * seqLenMul)
		replyobj.info("Q-score: %.3f\n\n" % q)
		replyobj.status("RMSDs and structure similarity measures reported"
			" in Reply Log", color="purple")
	if not makeMAV:
		return seqs
	if len(seqs) == 2:
		mav = showAlignment(seqs, "Match of %s and %s" %
					(seqs[0].name, seqs[1].name))
	else:
		mav = showAlignment(seqs, "Match -> Align (%d models)"
							% len(seqs))
	if cols:
		mav.status("RMSDs and structure similarity measures reported in"
			" Reply Log", color="purple")
	else:
		mav.status("No fully populated columns in alignment", color="blue")
	from MultAlignViewer.MAViewer import MATCHED_REGION_INFO
	name, fill, outline = MATCHED_REGION_INFO
	mav.newRegion(name="Fully populated columns", columns=cols,
					fill=fill, outline=outline)
	return mav
