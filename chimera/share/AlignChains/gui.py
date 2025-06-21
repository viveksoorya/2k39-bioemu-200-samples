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

from chimera.baseDialog import ModelessDialog

class AlignChainsDialog(ModelessDialog):
	name = "align chains"
	buttons = ('OK', 'Apply', 'Cancel')
	title = "Make Sequence Alignment from Chains"
	help = "ContributedSoftware/align/align.html"

	def fillInUI(self, parent):
		import Tkinter, Pmw

		from MultAlignViewer.RealignBase import ServiceOptions
		serviceNames = ServiceOptions.names()
		if len(serviceNames) == 1:
			serviceText = serviceNames[0]
		else:
			serviceText = " or ".join([", ".join(serviceNames[:-1]), 
				serviceNames[-1]])

		from itertools import count
		row = count()
		Tkinter.Label(parent, text="Align chains using %s web service"
			% serviceText).grid(row=row.next(), column=0, columnspan=2)
		from chimera.widgets import MoleculeChainScrolledListBox
		self.chainList = MoleculeChainScrolledListBox(parent,
			labelpos="nw", label_text="Chains to align",
			listbox_selectmode='extended')
		self.chainList.grid(row=row.next(), column=0, sticky="ew",
			columnspan=2)

		from chimera.tkoptions import BooleanOption
		self.selRestrictOpt = BooleanOption(parent, row.next(),
			"Use only selected part of chains (if any)", False,
			None)

		self.serviceOptions = ServiceOptions(parent, row)

	def Apply(self):
		chains = self.chainList.getvalue()
		if len(chains) < 2:
			self.enter()
			from chimera import UserError
			raise UserError("Must select at least two chains to align")
		if len(set([c.molecule for c in chains])) != len(chains):
			from chimera.baseDialog import AskYesNoDialog
			if AskYesNoDialog("Due to a limitation of Chimera's"
					" sequence-alignment viewer, only one chain"
					" of a model can be associated with the"
					" sequences of an alignment.  Therfore,"
					" some of the chains you have selected"
					" will not be associated with the generated"
					" alignment.  If you need to have all"
					" chains associated you will need to open"
					" multiple copies of the relevant structures"
					" and choose one chain from each.  Continue"
					" anyway?").run(self.uiMaster()) == "no":
				return
		LaunchWS(chains, self.selRestrictOpt.get(),
			self.serviceOptions.serviceOpt.get(), self.serviceOptions.get())

from chimera import dialogs
dialogs.register(AlignChainsDialog.name, AlignChainsDialog)

def processChains(chains, selRestrict):
	chainInfo = []
	if selRestrict:
		from chimera.selection import currentResidues
		selResidues = set(currentResidues())
	for chain in chains:
		if not selRestrict:
			chainInfo.append((0, len(chain.ungapped())))
			continue
		if not (set(chain.residues) & selResidues):
			chainInfo.append((0, len(chain.ungapped())))
			continue
		first = last = prevRealRes = None
		for i, res in enumerate(chain.residues):
			if res is None:
				continue
			if res in selResidues:
				if first is None:
					first = i
				elif last is not None:
					from chimera import UserError
					raise UserError("Selected parts of chain %s are"
						" not continuous" % chain.fullName())
			else:
				if first is not None and last is None:
					last = prevRealRes
			prevRealRes = i
		if first is not None and last is None:
			last = prevRealRes
		chainInfo.append((first, last+1))
	return chainInfo

class LaunchWS:
	def __init__(self, chains, selRestrict, mavTitleName, serviceInfo):
		serviceName, inOutFlags, serviceOptions, reordersSeqs = serviceInfo
		self.chainInfo = processChains(chains, selRestrict)
		self.mavTitleName = mavTitleName
		from chimera.Sequence import Sequence
		seqs = []
		for chain, info in zip(chains, self.chainInfo):
			seq = Sequence(chain.fullName())
			seq[:] = chain.ungapped()[info[0]:info[1]]
			seqs.append(seq)
		from MultAlignViewer.RealignBase import RunRealignmentWS
		RunRealignmentWS(None, None, self._serviceDone, seqs=seqs,
			mav=False, inOutFlags=inOutFlags, options=serviceOptions,
			serviceName=serviceName)

	def _serviceDone(self, ws, mav, seqs):
		# if the corresponding chain is still around, promote
		# the Sequence to a StructureSequence
		chainMap = {}
		from chimera import openModels, Molecule
		for mol in openModels.list(modelTypes=[Molecule]):
			for chain in mol.sequences():
				chainMap[chain.fullName()] = chain
		for i, seq in enumerate(seqs[:]):
			try:
				chain = chainMap[seq.name]
			except KeyError:
				continue
			info = self.chainInfo[i]
			from chimera.Sequence import StructureSequence
			sseq = StructureSequence(chain.molecule, seq.name)
			sseq[:] = seq[:]
			sseq.residues = chain.residues[info[0]:info[1]]
			seqs[i] = sseq
			for i, r in enumerate(sseq.residues):
				if r:
					sseq.resMap[r] = i
		from MultAlignViewer.MAViewer import MAViewer
		MAViewer(seqs, title="%s Alignment" % self.mavTitleName)
