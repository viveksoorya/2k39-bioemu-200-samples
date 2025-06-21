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
from chimera import UserError, triggers

class FetchAnnotationsDialog(ModelessDialog):

	title = "PDB/UniProt Info"
	buttons = ('Close',)
	provideStatus = True
	name = "sequence annotations"
	help = "ContributedSoftware/uniprot/uniprot.html"

	def fillInUI(self, parent):
		from weakref import WeakKeyDictionary
		self._mol2pdb = WeakKeyDictionary()
		import Tkinter
		
		parent.columnconfigure(0, weight=1)
		row = 0

		from chimera.widgets import MoleculeChainScrolledListBox
		self.chainListbox = MoleculeChainScrolledListBox(parent,
			selectioncommand=self._chainCB, listbox_selectmode='extended')
		self.chainListbox.grid(row=row, column=0, sticky="nsew")
		parent.rowconfigure(row, weight=1)
		row += 1

		self.ignoreCachesVar = Tkinter.IntVar(parent)
		self.ignoreCachesVar.set(False)
		f = Tkinter.Frame(parent)
		f.grid(row=row, column=0, sticky='ew')
		cacheBut = Tkinter.Checkbutton(f, text="Ignore any cached data",
			variable=self.ignoreCachesVar)
		from CGLtk.Font import shrinkFont
		shrinkFont(cacheBut)
		cacheBut.grid(row=0, column=0)
		Tkinter.Button(f, text="Show UniProt page(s)", pady=0,
			command=self._uniprot).grid(row=0, column=1)
		f.columnconfigure(1, weight=1)
		row += 1

		from CGLtk.Table import SortableTable
		self.pdbTable = SortableTable(parent)
		self.pdbTable.addColumn("PDB ID", "id")
		self.pdbInfos = []
		self.uniprotMavs = {}
		self.pdbCols = set()
		self.pdbTable.setData(self.pdbInfos)
		self.pdbTable.launch(browseCmd=None, title="Structure Info")
		self.pdbTable.grid(row=row, column=0, sticky="nsew")
		parent.rowconfigure(row, weight=1)
		triggers.addHandler('Molecule', self._molChangeCB, None)
		row += 1

		Tkinter.Button(parent, text="Show PubMed page", pady=0,
			command=self._pubmed).grid(row=row, column=0)
		row += 1

		self.status("Choose a structure chain to populate Structure Info table",
			color="tan")

	def _chainCB(self):
		self.status("")
		chains = self.chainListbox.getvalue()
		for chain in chains:
			pdbID = self._wranglePdbID(chain)
			if not pdbID:
				return
			chainID = chain.chainID
			try:
				for mav in self.uniprotMavs[(pdbID, chainID)]:
					mav.enter()
			except KeyError:
				pass
			else:
				continue
			from SeqAnnotations import pdbUniprotCorrespondences
			from chimera import CancelOperation
			try:
				alignObjs, corrs = pdbUniprotCorrespondences(chain,
					status=self.status, ignoreCache=self.ignoreCachesVar.get(),
					pdbID=pdbID)
			except CancelOperation:
				self.status("Fetch of %s, chain %s cancelled"
							% (pdbID, chainID), color="red")
				return
			if pdbID not in [i.id for i in self.pdbInfos]:
				pi = PdbInfo(pdbID)
				self.pdbInfos.append(pi)
				from CGLtk.Table import tableize
				for prop, value in alignObjs.items():
					setattr(pi, prop, tableize(str(value)))
					colName = prop.replace('_', ' ').capitalize()
					if colName.endswith(" id"):
						colName = colName[:-2] + "ID"
					if colName not in self.pdbCols:
						self.pdbCols.add(colName)
						self.pdbTable.addColumn(colName, prop)
				self.pdbTable.setData(self.pdbInfos)
			if corrs:
				for uniprotID, uniCorrs in corrs.items():
					from SeqAnnotations import uniprotFetch, showUniprotFeatures
					try:
						seq, fullName, features = uniprotFetch(uniprotID)
					except CancelOperation:
						self.status("Fetch of %s UniProt info cancelled"
									% (uniprotID), color="red")
						return
					from chimera.Sequence import StructureSequence
					sseq = StructureSequence(chain.molecule, name=chain.name)
					sseq.extend(seq)
					lastUniprot = 0
					for pdbStart, uniprotStart, length in uniCorrs:
						if lastUniprot < uniprotStart:
							sseq.residues.extend(
								[None] * (uniprotStart - lastUniprot))
						lastUniprot = uniprotStart + length
						sseq.residues.extend(chain.residues[
										pdbStart:pdbStart+length])
					if lastUniprot < len(sseq):
						sseq.residues.extend([None] * (len(sseq) - lastUniprot))
					for i, r in enumerate(sseq.residues):
						if r:
							sseq.resMap[r] = i
					from chimera.resCode import protein3to1
					numSame = numDiffer = 0
					assert(len(sseq) == len(sseq.residues))
					resSeq = []
					for r, c in zip(sseq.residues, str(sseq)):
						resSeq.append(c)
						if not r:
							continue
						if r.type not in protein3to1:
							continue
						if protein3to1[r.type] == c:
							numSame += 1
						else:
							numDiffer += 1
							resSeq[-1] = protein3to1[r.type]
					if numDiffer * 10 > numSame:
						from chimera import replyobj
						replyobj.warning("There may be a problem with the"
							u" PDB\N{RIGHTWARDS ARROW}UniProt residue mapping"
							" (only %d%% of residues are the same type).\n"
							u"You may want to use Help\N{RIGHTWARDS ARROW}Report"
							" A Bug to inform the Chimera development team"
							" about the problem.\nPlease include the PDB ID"
							" and the chain identifier for which the problem"
							" occurred." % int(numSame*100.0/(numSame+numDiffer)))
					if numDiffer:
						# so that MAV looks for mismatches in an 'intrinisic' sequence
						sseq.residueSequence = "".join(resSeq)
					from MultAlignViewer.MAViewer import MAViewer
					mav = MAViewer([sseq], autoAssociate=None, quitCB=self._mavQuit,
						title="%s (%s)" % (fullName, chain.name))
					self.uniprotMavs.setdefault((pdbID, chainID), []).append(mav)
					showUniprotFeatures(mav, features)
				self.status("%s has UniProt ID(s): %s\n"
					% (chain.fullName(), ", ".join(chain.uniprotIDs)), log=True)
			else:
				self.status("No UniProt correspondence info found"
					" in PDB data", color="red")
		if len(self.pdbInfos) == 1:
			self.pdbTable.select(self.pdbInfos)

	def _mavQuit(self, mav):
		for k, v in self.uniprotMavs.items():
			if mav in v:
				v.remove(mav)
				if not v:
					del self.uniprotMavs[k]
				return

	def _molChangeCB(self, trigName, myData, trigData):
		delPDBs = set()
		for mol in trigData.deleted:
			if mol in self._mol2pdb:
				delPDBs.add(self._mol2pdb[mol])
		if delPDBs:
			self.pdbInfos = [pi for pi in self.pdbInfos if pi.id not in delPDBs]
			self.pdbTable.setData(self.pdbInfos)
			if len(self.pdbInfos) == 1:
				self.pdbTable.select(self.pdbInfos)

	def _pubmed(self):
		sels = self.pdbTable.selected()
		if not sels:
			raise UserError("No PubMed IDs selected")
		import webbrowser as wb
		for sel in sels:
			if getattr(sel, 'pubmed_id', None) is not None:
				wb.open("https://www.ncbi.nlm.nih.gov/pubmed/" + sel.pubmed_id)
			else:
				from chimera import replyobj
				replyobj.error("No Pubmed ID known for %s" % sel.id)

	def _wranglePdbID(self, chain):
		if chain.molecule in self._mol2pdb:
			return self._mol2pdb[chain.molecule]
		from SeqAnnotations import chain2pdbID
		pdbID = chain2pdbID(chain)
		if pdbID:
			self._mol2pdb[chain.molecule] = pdbID
			return pdbID
		from Pmw import PromptDialog
		self._promptDialog = PromptDialog(self.uiMaster(), title="PDB ID",
			label_text="Can't determine PDB ID for model %s\n"
			"Please specify the PDB ID:", entryfield_labelpos='n',
			defaultbutton=0, buttons=('OK', 'Cancel'),
			command=self._pdbPromptCB)
		result = self._promptDialog.activate()
		if result == None:
			return None
		if len(result) == 4:
			self._mol2pdb[chain.molecule] = result
		else:
			self.status("Need to input legal PDB ID", color="red")
			return self._wranglePdbID(chain)
		return self._mol2pdb[chain.molecule]

	def _pdbPromptCB(self, result):
		if result is None or result == 'Cancel':
			self._promptDialog.deactivate(None)
		else:
			self._promptDialog.deactivate(self._promptDialog.get())

	def _uniprot(self):
		chains = self.chainListbox.getvalue()
		if not chains:
			raise UserError("No chains selected")
		chains = [ch for ch in chains if hasattr(ch, 'uniprotIDs')]
		if not chains:
			raise UserError("No selected chains have UniProt pages")
		import webbrowser as wb
		for chain in chains:
			for uniprotID in chain.uniprotIDs:
				wb.open("http://www.uniprot.org/uniprot/" + uniprotID)

class PdbInfo(object):
	def __init__(self, idCode):
		self.id = idCode

	def __getattr__(self, attrName):
		return None

from chimera import dialogs
dialogs.register(FetchAnnotationsDialog.name, FetchAnnotationsDialog)
