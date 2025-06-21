# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id:$

import chimera
from chimera.baseDialog import ModalDialog, ModelessDialog
from chimera import replyobj
from chimera import Molecule
from chimera.Sequence import StructureSequence, Sequence

class BlastParameters(object):

	def addParametersUI(self, master):
		import Tkinter
		import Pmw
		f = Tkinter.Frame(master)
		f.grid(row=1, column=0, sticky="nsew")
		f.columnconfigure(1, weight=1)
		row = 0

		self.wDb = Pmw.OptionMenu(f,
					labelpos="w",
					label_text="Database:",
					initialitem="pdb",
					items=[ "pdb", "nr" ])
		self.wDb.grid(column=0, row=row, sticky="ew")
		row += 1

		self.wEvalue = Pmw.EntryField(f,
					labelpos="w",
					label_text="E-value (1e-X):",
					value=3,
					validate = {'validator':'integer',
							'min':-10,
							'max':200})
		self.wEvalue.grid(column=0, row=row, sticky="ew")
		row += 1

		self.wMatrix = Pmw.OptionMenu(f,
					labelpos="w",
					label_text="Matrix:",
					initialitem="BLOSUM62",
					items=[ "BLOSUM45",
						"BLOSUM62",
						"BLOSUM80",
						"PAM30",
						"PAM70", ])
		self.wMatrix.grid(column=0, row=row, sticky="ew")
		row += 1

		Pmw.alignlabels([ self.wDb, self.wEvalue, self.wMatrix, ],
                                sticky="e")

		self.showOneVar = Tkinter.IntVar(master)
		self.showOneVar.set(1)
		self.showOne = Tkinter.Checkbutton(f,
						text="List only best-matching "
						"chain per PDB entry",
						variable=self.showOneVar)
		self.showOne.grid(column=0, row=row, sticky="w")
		row += 1

	def checkParameters(self):
		if not self.wEvalue.valid():
			replyobj.error("Blast: invalid e-value\n")
			return None
		prog = "blastp"
		db = self.wDb.getcurselection()
                eval = -int(self.wEvalue.get())
		evalue = "1e%d" % eval 
		matrix = self.wMatrix.getcurselection()
		passes = 1
		showOne = self.showOneVar.get()
		return (prog, db, evalue, matrix, passes, showOne)

class BlastChainDialog(ModelessDialog, BlastParameters):

	name = "blast chain"
	title = "Blast Protein"
	buttons = ("OK", "Apply", "Cancel")
	help = "UsersGuide/blast.html"

	def fillInUI(self, master):
		import Pmw
		self.notebook = nb = Pmw.NoteBook(master)
		nb.grid(column=0, row=0, sticky="ew")

		chainPage = nb.add("From Structure")
		from chimera.widgets import MoleculeChainOptionMenu
		def proteinOnly(s):
			return s.hasProtein()
		self.chainOptionMenu = MoleculeChainOptionMenu(chainPage,
						filtFunc=proteinOnly)
		self.chainOptionMenu.grid(row=0, column=0)

		textPage = nb.add("Plain Text")
		self.seqText = Pmw.ScrolledText(textPage, labelpos="nw",
					label_text="Sequence")
		self.seqText.grid(row=0, column=0, sticky="nsew")
		textPage.rowconfigure(0, weight=1)
		textPage.columnconfigure(0, weight=1)

		self.addParametersUI(master)

	def Apply(self):
		args = self.checkParameters()
		if args is None:
			return
		if self.notebook.getcurselection() == "Plain Text":
			bases = [ c for c in self.seqText.getvalue().upper()
					if c.isalpha() ]
			if not bases:
				replyobj.error(
					"Must supply contents of sequence\n")
				return
			seq = ''.join(bases)
			BlastResultsDialog(seq=seq, blastData=args)
		else:
			chain = self.chainOptionMenu.getvalue()
			if chain is None:
				replyobj.error("No molecule chain selected\n")
				return
			BlastResultsDialog(mol=chain, blastData=args)

class BlastDialog(ModalDialog, BlastParameters):

	name = "blast parameters"
	title = "Blast Parameters"
	buttons = ("OK", "Cancel")
	help = "UsersGuide/blast.html"

	def fillInUI(self, master):
		self.addParametersUI(master)

	def OK(self):
		args = self.checkParameters()
		if args is None:
			return
		self.Cancel(value=args)

def blastprotein(mol, *args):
	BlastResultsDialog(mol=mol, blastData=args)

class BlastResultsDialog(ModelessDialog):

	buttons = ( "Show in MAV", "Load Structure", "PDB Web Site", "Columns", "Export...", "Hide", "Quit" )
	help = "UsersGuide/blast.html#results"

	factoryDefaultColumns = ('Name', 'Evalue', 'Score', 'Description')
	factoryDefaultWrap = 40

	def __init__(self, mol=None, seq=None, blastData=None, sessionData=None):
		import os.path
		self.loaded = {}
		self.mavMap = {}
		self.reference = mol or seq
		blast_columns = (
			("Name", 'name', {'entryPadX':5, 'anchor':"nw"},
			 'Sequence identifier'),
			("Evalue", 'evalue', {'anchor':"nw"},
			 'BLAST E-value, probability that random sequences\n'
			 'would match as well as query and target'),
			("Score", 'score', {'anchor':"nw"},
			 'BLAST alignment score'),
			("Description", 'description',
			 {'entryPadX':5, 'anchor':"w"}, 'Sequence description'),
			)
		import pdbinfo as PI
		self.columns = blast_columns + fetchedColumns(PI.columns)
		self.columnNames = tuple(c[0] for c in self.columns)
		self.columnFetch = True

		if isinstance(self.reference, StructureSequence):
			self.molecule = self.reference.molecule
			base = "%s.%s" % (os.path.basename(self.molecule.name),
						self.reference.name)
		elif isinstance(self.reference, Molecule):
			self.molecule = self.reference
			base = os.path.basename(self.molecule.name)
		else:
			self.reference = None
			self.molecule = None
			base = "query"
		self.basename = base.replace(' ', '_')
		self.sequence = seq	# for session data only
		if seq is None:
			self.seq, self.refResList = self._makeSeq(mol)
		else:
			self.seq = seq
			if self.reference:
				tseq, resList = self._makeSeq(self.molecule)
				self.refResList = self._getResidues(self.seq,
								tseq, resList)
		if blastData:
			self.initBlast(*blastData)
		else:
			self.initSession(*sessionData)
		self.title = "Blast: %s" % self.basename
		ModelessDialog.__init__(self)
		if not blastData:
			self._updateLoadButton()
		if self.molecule:
			self.closeHandler = chimera.openModels.addRemoveHandler(
						self._modelClosedCB, None)
		else:
			self.closeHandler = None
		from SimpleSession import SAVE_SESSION
		self.saveSesHandler = chimera.triggers.addHandler(
						SAVE_SESSION,
						self._saveSessionCB, None)
		from chimera import CLOSE_SESSION
		self.closeSesHandler = chimera.triggers.addHandler(
						CLOSE_SESSION,
						self._closeSessionCB, None)
		chimera.extension.manager.registerInstance(self)

	def _makeSeq(self, mol):
		if isinstance(mol, StructureSequence):
			if not mol.hasProtein():
				from chimera import UserError
				raise UserError("No protein sequence found "
						"in %s %s\n" % (
							mol.molecule.name,
							mol.name))
			return ''.join(mol.sequence), mol.residues
		elif isinstance(mol, Molecule):
			from chimera import resCode
			seq = []
			refResList = []
			for r in mol.residues:
				try:
					seq.append(resCode.protein3to1[r.type])
				except KeyError:
					pass
				else:
					refResList.append(r)
			if len(seq) == 0:
				from chimera import UserError
				raise UserError("No protein sequence "
						"found in %s\n" % mol.name)
			return ''.join(seq), refResList
		elif mol is None:
			# This can happen if the data came from a session
			# where the reference model for blast was closed
			return None, None
		else:
			raise ValueError("Blast Protein not called with "
						"molecule or chain\n")
	
	def initBlast(self, prog, db, evalue, matrix, passes, showOne):
		self.program = prog
		self.showOne = showOne
		self.parser = None
		from ParserBlastP import BlastpService, _GapChars
                seq = str(self.seq).translate(None, _GapChars)
		self.service = BlastpService(self._finish, params=(
							prog, db,
							self.basename,
							seq, evalue,
							matrix, passes))
		self.tableData = None

	def initSession(self, program, name, showOne, parserData,
				serviceData, tableData, mavData, loadedData):
		self.basename = name
		self.program = program
		self.showOne = showOne
		if parserData:
			from ParserBlastP import restoreParser
			self.parser = restoreParser(parserData)
		else:
			self.parser = None
		if serviceData:
			from ParserBlastP import BlastpService
			self.service = BlastpService(self._finish,
							sessionData=serviceData)
		else:
			self.service = None
		self.tableData = tableData
		if mavData:
			from MultAlignViewer.MAViewer import restoreMAV
			from chimera.Sequence import restoreSequence
			for seqData, mavInfo, matchSeqData in mavData:
				seqList = [ restoreSequence(seqInfo)
						for seqInfo in seqData ]
				mav = restoreMAV(seqList, mavInfo)
				matchSeqMap = {}
				for matchIndex, seqIndex in matchSeqData:
					match = self.parser.matches[matchIndex]
					seq = seqList[seqIndex]
					matchSeqMap[match] = seq
				self.mavMap[mav] = matchSeqMap
		if loadedData:
			from chimera.Sequence import restoreSequence
			from SimpleSession import idLookup
			for matchIndex, molId, seqInfo in loadedData:
				match = self.parser.matches[matchIndex]
				mol = idLookup(molId)
				if seqInfo == molId:
					mseq = mol
				else:
					mseq = restoreSequence(seqInfo)
				self.loaded[match] = (mol, mseq)

	def fillInUI(self, parent):
		import Tkinter
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(0, weight=1)

		from CGLtk import Hybrid
		cp = Hybrid.Popup_Panel(parent, resize_dialog=False)
		cf = cp.frame
		cf.grid(row=1, column=0, sticky='news')
		cf.grid_remove()
		controlsArea = Tkinter.Frame(cf)
		controlsArea.grid(row=0, column=0)
		self.columnButtonsShown = cp.panel_shown_variable
		cb = cp.make_close_button(cf)
		cb.grid(row=0, column=1, sticky = 'ne')
		cf.columnconfigure(1, weight=1)

		from CGLtk.Table import SortableTable
		standardCols = dict.fromkeys(self.factoryDefaultColumns, True)
		sortablePrefs = prefs.get(SortableTable.PREF_KEY, None)
		conversion = sortablePrefs is None \
				and prefs.get(DEFAULT_COLUMNS, None) is not None
		# Replace "GI" and "PDB" with "Name" in default displayed column
		try:
			defCols = sortablePrefs[SortableTable.PREF_SUBKEY_COL_DISP]
		except (TypeError, KeyError):
			pass
		else:
			if "GI" in defCols or "PDB" in defCols:
				if "GI" in defCols:
					del defCols["GI"]
				if "PDB" in defCols:
					del defCols["PDB"]
				defCols["Name"] = True
		self.blastTable = SortableTable(parent, allowCopy=True,
			menuInfo=(controlsArea, prefs, standardCols, False, self.fetchColumnValue, 4, None),
			automultilineHeaders=False)
		for colName, fetch, kw, balloon in self.columns:
			self.blastTable.addColumn(colName, fetch, balloon=balloon, **kw)
		if self.parser:
			if not self.tableData:
				self.fetchColumnValues()
			self.blastTable.setData(self.parser.matches)
		else:
			self.blastTable.setData([])
		self.blastTable.launch(browseCmd=self._selectHitCB,
				       restoreInfo=self.tableData)
		if conversion:
			# convert from old-style preferences;
			# namely switch to the saved default
			oldDefault = set(prefs.get(DEFAULT_COLUMNS))
			needRefresh = False
			for col in self.blastTable.columns:
				needRefresh = self.blastTable.columnUpdate(col, display=col.title in oldDefault,
						immediateRefresh=False) or needRefresh
			if needRefresh:
				self.blastTable.refresh(rebuild=True)
		self.blastTable.grid(row=0, column=0, sticky='news')
		bw = self.buttonWidgets
		bw["Show in MAV"].config(state="disabled")
		bw["Load Structure"].config(state="disabled")
		bw["PDB Web Site"].config(state="disabled")
		bw["Export..."].config(state="disabled")
		bw["Quit"].config(state="disabled")

	def Columns(self):
		self.columnButtonsShown.set(not self.columnButtonsShown.get())

	def Export(self):
		from OpenSave import SaveModeless
		SaveModeless(title="Export Comma Separated Values",
			     command=self.exportTable)

	def exportTable(self, okay, d):
		if not okay:
			return
		fileList = d.getPaths()
		if len(fileList) == 0:
			return
		t = self.blastTable
		tvs = t.tableValuesString(selectedOnly = bool(t.selected()))
		f = open(fileList[0],'w')
		f.write(tvs)
		f.close()

	def _finish(self, params, output):
		if self.blastTable is None:
			# We already quit, so UI is gone
			return
		from ParserBlastP import Parser
		try:
			self.parser = Parser(self.basename, params, output,
						self.program == "psiblast")
		except SyntaxError, s:
			replyobj.error("BLAST error: %s\n" % s)
			return
		except:
			replyobj.reportException("BLAST error")
			return
		self.service = None
		if self.showOne:
			matches = []
			seen = set()
			for m in self.parser.matches:
				if m.pdb is not None:
					parts = m.pdb.split('_')
					pdb = parts[0]
					if pdb in seen:
						continue
					seen.add(pdb)
				matches.append(m)
			self.parser.matches = matches
		self.fetchColumnValues()
		self.blastTable.setData(self.parser.matches)
		self._updateLoadButton()

	def fetchColumnValue(self, col):
		'''Fetch additional PDB info for each match.'''
		if self.parser is None:
			return
		if not col.display:
			return
		if not self.columnFetch:
			return
		self.fetchColumnValues()
		self.blastTable.refresh()

	def fetchColumnValues(self):
		'''Fetch additional PDB info for each match.'''
		if self.parser is None:
			return
		if not self.columnFetch:
			return
		pdb_ids = tuple(m.pdb for m in self.parser.matches if m.pdb)
		if len(pdb_ids) == 0:
			return
		from pdbinfo import fetch_pdb_info
		info = fetch_pdb_info(pdb_ids)
		for m in self.parser.matches:
			for k, v in info.get(m.pdb,{}).items():
				val = ", ".join([str(x) for x in v]) if isinstance(v, list) else v
				setattr(m.fetchedValues, k, val)
		self.columnFetch = False

	def _updateLoadButton(self):
		bw = self.buttonWidgets
		if self.parser is None:
			bw["Quit"].config(state="disabled")
			bw["Load Structure"].config(state="disabled")
			bw["Show in MAV"].config(state="disabled")
			bw["PDB Web Site"].config(state="disabled")
			bw["Export..."].config(state="disabled")
			return
		sel = self.blastTable.selected()
		if not sel:
			sel = self.parser.matches
		state = "disabled"
		for m in sel:
			if m.pdb is not None:
				state = "normal"
		bw["Load Structure"].config(state=state)
		bw["Show in MAV"].config(state="normal")
		bw["PDB Web Site"].config(state=state)
		bw["Export..."].config(state="normal")
		bw["Quit"].config(state="normal")

	def _selectHitCB(self, tableSel):
		self._updateLoadButton()

	def _modelClosedCB(self, trigger, closure, mols):
		loaded = {}
		for match, (mol, mseq) in self.loaded.iteritems():
			if mol not in mols:
				loaded[match] = (mol, mseq)
		self.loaded = loaded
		if self.molecule not in mols:
			return
		if not self.loaded:
			self.reference = None
			self.molecule = None
			self.seq = None
			self.refResList = None
		else:
			match, (mol, mseq) = self.loaded.popitem()
			self._setReference(match, mol, mseq)

	def _saveSessionCB(self, trigger, myData, sesFile):
		from SimpleSession import sessionID, sesRepr
		# Structure and sequence data
		if self.reference:
			if isinstance(self.reference, StructureSequence):
				mid = None
				ss = self.reference.saveInfo()
			elif isinstance(self.reference, Molecule):
				mid = sessionID(self.reference)
				ss = None
			else:
				raise ValueError("unexpected type for "
					"BlastResultsDialog.reference: %s" %
					repr(self.reference))
		else:
			mid = None
			ss = None
		if isinstance(self.sequence, Sequence):
			isChimeraSequence = True
			sequence = self.sequence.saveInfo()
		else:
			isChimeraSequence = False
			sequence = self.sequence

		# Blast results data
		if self.parser:
			parserData = self.parser.sessionData()
		else:
			parserData = None
		if self.service:
			serviceData = self.service.sessionData()
		else:
			serviceData = None

		# MAV data
		mavData = []
		for mav, matchSeqMap in self.mavMap.iteritems():
			seqData = [ seq.saveInfo() for seq in mav.seqs ]
			matchSeqData = []
			for m, s in matchSeqMap.iteritems():
				try:
					mavIndex = mav.seqs.index(s)
					matchIndex = self.parser.matches.index(m)
				except ValueError:
					continue
				matchSeqData.append((matchIndex, mavIndex))
			mavData.append((seqData, mav.saveInfo(), matchSeqData))

		# Loaded molecule data
		loadedData = []
		for m, (mol, mseq) in self.loaded.iteritems():
			matchIndex = self.parser.matches.index(m)
			molId = sessionID(mol)
			if mseq is mol:
				seqInfo = molId
			else:
				seqInfo = mseq.saveInfo()
			loadedData.append((matchIndex, molId, seqInfo))

		# Complete session data
		data = (5,					# version
			mid,					# molecule
			ss,					# StructureSeq
			isChimeraSequence,			# is input Seq
			sequence,				# input seq
			self.program,				# program
			self.basename,				# name
			self.showOne,				# one hit per PDB
			parserData,				# parser
			serviceData,				# service
			self.blastTable.getRestoreInfo(),	# GUI
			mavData,				# MAV info
			loadedData)				# Loaded info
		print >> sesFile, """
try:
	from blastpdb.gui import sessionRestore
	sessionRestore(%s)
except:
	reportRestoreError("Error restoring Blast dialog")
""" % sesRepr(data)

	def _closeSessionCB(self, trigger, myData, data):
		self.exit()

	def exit(self):
		for mav in self.mavMap.iterkeys():
			mav.sessionSave = True
		if self.closeHandler:
			chimera.openModels.deleteRemoveHandler(
							self.closeHandler)
			self.closeHandler = None
		if self.saveSesHandler:
			from SimpleSession import SAVE_SESSION
			chimera.triggers.deleteHandler(SAVE_SESSION,
							self.saveSesHandler)
			self.saveSesHandler = None
		if self.closeSesHandler:
			from chimera import CLOSE_SESSION
			chimera.triggers.deleteHandler(CLOSE_SESSION,
							self.closeSesHandler)
			self.closeSesHandler = None
		chimera.extension.manager.deregisterInstance(self)
		self.destroy()
		self.blastTable = None

	def ShowinMAV(self):
		from cStringIO import StringIO
		s = StringIO()
		sel = self.blastTable.selected()
		if not sel:
			sel = self.parser.matches
		self.parser.writeMSF(s, matches=sel)
		s.seek(0)
		from MultAlignViewer.parsers import readMSF
		seqs, fileType, markups = readMSF.parse(s)
		from MultAlignViewer import MAViewer
		mav = MAViewer.MAViewer(seqs, fileType=fileType,
						quitCB=self._mavQuit,
						sessionSave=False)
		mav.deleteAllGaps()
		mav._edited = False	# don't bother user with question
					# about alignment being edited
		matchSeqMap = dict(zip(sel, seqs))
		for m in sel:
			try:
				mol, mseq = self.loaded[m]
			except KeyError:
				pass
			else:
				if mseq.molecule in mav.associations:
					if mav.associations[mseq.molecule] == matchSeqMap[m]:
						continue
					mav.disassociate(mseq.molecule)
				mav.associate(mseq, matchSeqMap[m])
		self.mavMap[mav] = matchSeqMap

	def _mavQuit(self, mav):
		try:
			del self.mavMap[mav]
		except KeyError:
			pass

	def LoadStructure(self):
		sel = self.blastTable.selected()
		if not sel:
			sel = self.parser.matches
		sel = [ m for m in sel if m.pdb ]
		if len(sel) > 5:
			from chimera.baseDialog import AskYesNoDialog
			from chimera import tkgui
			d = AskYesNoDialog("This will load %d models."
					"  Proceed?" % len(sel),
					default="Yes")
			if d.run(self.uiMaster().winfo_toplevel()) != "yes":
				return
		mList = []
		autoSave = {}
		for mav in self.mavMap.iterkeys():
			autoSave[mav] = mav.autoAssociate
			mav.autoAssociate = False
		for m in sel:
			if not m.pdb:
				continue
			parts = m.pdb.split('_')
			pdbid = parts[0]
			for mol in chimera.openModels.open(pdbid, type="PDBID"):
				if len(parts) == 1:
					mseq = mol
				else:
					mseq = mol.sequence(parts[1])
				self._mavAssociate(m, mseq)
				mList.append((m, mol, mseq))
		for mav in self.mavMap.iterkeys():
			mav.autoAssociate = autoSave[mav]
		if self.reference is None:
			# Make the first model loaded the reference model
			# so others align to it.
			m, mol, mseq = mList[0]
			self._setReference(m, mol, mseq)
		for m, mol, mseq in mList:
			if mol is self.molecule:
				continue
			resList = self._getMatchResidues(m, mol, mseq)
			if resList:
				self._match(mol, m, resList)

	def PDBWebSite(self):
		sel = self.blastTable.selected()
		top_only = False
		if not sel:
			from chimera import replyobj
			replyobj.status("No entries selected in table; showing page for top hit")
			sel = self.parser.matches
			top_only = True

		sel = [ m for m in sel if m.pdb ]
		if top_only:
			sel = sel[:1]
		pdb_ids = [m.pdb.split('_')[0].upper() for m in sel]
		from chimera import help
		for pdb_id in pdb_ids:
			url = 'http://www.rcsb.org/structure/' + pdb_id 
			help.display(url)

	def _mavAssociate(self, m, mseq):
		for mav, matchMap in self.mavMap.iteritems():
			try:
				seq = matchMap[m]
			except KeyError:
				pass
			else:
				mav.associate(mseq, seq)

	def _setReference(self, match, mol, mseq):
		# refMatch and match are already aligned
		refMatch = self.parser.matches[0]
		if len(refMatch.sequence) != len(match.sequence):
			raise ValueError("Blast: alignment length mismatch\n")
		resList = self._getMatchResidues(match, mol, mseq)
		rIndex = 0
		self.reference = mseq
		self.molecule = mol
		if not self.closeHandler:
			self.closeHandler = chimera.openModels.addRemoveHandler(
						self._modelClosedCB, None)
		self.refResList = []
		for i, ms in enumerate(match.sequence):
			rs = refMatch.sequence[i]
			if rs == '-':
				if ms != '-':
					rIndex += 1
			else:
				if ms == '-':
					self.refResList.append(None)
				else:
					self.refResList.append(resList[rIndex])
					rIndex += 1

	def _getMatchResidues(self, match, mol, mseq):
		# Since the match sequence may be a subset of the
		# entire PDB structure, we cannot do the same thing
		# as for the reference model where we created the
		# match sequence from the structure.  Instead, we
		# find the best match of match sequence to
		# structure sequence, and then pull the residues
		# corresponding to the match sequence.
		matchSeq = [ s for s in match.sequence if s != '-' ]
		mseq = self._getChain(mol, match.pdb)
		self.loaded[match] = (mol, mseq)

		# Try MAV association first, then fail back to N&W if needed
		try:
			from MultAlignViewer.structAssoc \
				import estimateAssocParams, tryAssoc
			estLen, segments, gaps = estimateAssocParams(mseq)
			from chimera.Sequence import Sequence
			aseq = Sequence()
			aseq.append(matchSeq)
			matchMap, errors = tryAssoc(aseq, mseq, segments,
							gaps, estLen,
							maxErrors=len(mseq))
			resList = [ matchMap.get(i, None)
					for i in range(len(matchSeq)) ]
		except ValueError:
			resList = self._getResidues(matchSeq, mseq.sequence,
								mseq.residues)
		return resList

	def _getChain(self, mol, pdb):
		parts = pdb.split('_')
		try:
			chain = parts[1]
		except IndexError:
			chain = ' '
		for s in mol.sequences():
			if s.chain == chain or s.chain is None:
				return s
		else:
			replyobj.error("%s: chain '%s' not found\n"
					% (pdb, chain))
			return mol

	def _getResidues(self, matchSeq, molSeq, molRes):
		from NeedlemanWunsch import nw
		score, matchList = nw(matchSeq, molSeq)
		matchMap = dict(matchList)
		resList = []
		for mi in range(len(matchSeq)):
			try:
				si = matchMap[mi]
			except KeyError:
				r = None
			else:
				r = molRes[si]
			resList.append(r)
		return resList

	def _match(self, tmol, tm, tres):
		rmol = self.molecule
		rm = self.parser.matches[0]
		rres = self.refResList

		rs = rm.sequence	# reference sequence
		ri = 0			# reference residue index
		rAtoms = []		# reference atom list
		ts = tm.sequence	# t = target
		ti = 0
		tAtoms = []
		# Find corresponding residue pairs and add
		# CA to each atom list
		if len(rm.sequence) != len(tm.sequence):
			replyobj.error("sequence length mismatch: %s and %s\n"
					% (rm.pdb, tm.pdb))
			return
		for si in range(len(rm.sequence)):
			if rs[si] == '-':
				rr = None
			else:
				rr = rres[ri]
				ri += 1
			if ts[si] == '-':
				tr = None
			else:
				tr = tres[ti]
				ti += 1
			if rr is None or tr is None:
				continue
			ra = rr.findAtom("CA")
			ta = tr.findAtom("CA")
			if ra is not None and ta is not None:
				rAtoms.append(ra)
				tAtoms.append(ta)

		if len(rAtoms) == 0:
			replyobj.info("No matching residues to align %s to %s\n"
				      % (tm.name, rmol.name))
			return
			
		from chimera import match
		xform, rmsd = match.matchAtoms(rAtoms, tAtoms)
		xf = rmol.openState.xform
		xf.multiply(xform)
		tmol.openState.xform = xf
		replyobj.info("RMSD between %s and %s over %d residues "
				"is %.3f angstroms\n"
				% (rmol.name, tm.name, len(rAtoms), rmsd))

	def emName(self):
		return self.title

	def emRaise(self):
		self.enter()

	def emHide(self):
		self.Close()
	Hide = emHide

	def emQuit(self):
		self.exit()
	Quit = emQuit

def fetchedColumns(clist):
	return tuple((title, 'fetchedValues.'+attr_name, kw, descrip)
		     for title, attr_name, kw, descrip in clist)

def sessionRestore(sessionData):
	from SimpleSession import idLookup
	version = sessionData[0]
	if version == 5:
		(v, mid, ss, isSeq, seq, program, name, showOne,
				parserData, serviceData, tableData,
				mavData, loadedData) = sessionData
		if mid is not None:
			mol = idLookup(mid)
		elif ss is not None:
			mol = chimera.Sequence.restoreSequence(ss)
		else:
			mol = None
		if isSeq:
			seq = chimera.Sequence.restoreSequence(seq)
	elif version == 4:
		(v, mid, ss, seq, program, name, showOne,
				parserData, serviceData, tableData,
				mavData, loadedData) = sessionData
		if mid is not None:
			mol = idLookup(mid)
		elif ss is not None:
			mol = chimera.Sequence.restoreSequence(ss)
		else:
			mol = None
	elif version == 3:
		(v, mid, ss, seq, program, name, showOne,
				parserData, serviceData, tableData) = sessionData
		if mid is not None:
			mol = idLookup(mid)
		elif ss is not None:
			mol = chimera.Sequence.restoreSequence(ss)
		else:
			mol = None
		mavData = None
		loadedData = None
	elif version == 2:
		(v, mid, seq, program, name, parserData, serviceData,
							tableData) = sessionData
		mol = idLookup(mid)
		showOne = False
		mavData = None
		loadedData = None
	elif version == 1:
		(v, mid, program, name, parserData, serviceData,
							tableData) = sessionData
		mol = idLookup(mid)
		seq = None
		showOne = False
		mavData = None
		loadedData = None
	else:
		raise ValueError("unknown blastpdb version: %s" % str(version))
	BlastResultsDialog(mol=mol, seq=seq, sessionData=(program, name,
								showOne,
								parserData,
								serviceData,
								tableData,
								mavData,
								loadedData))

from chimera.preferences import addCategory, HiddenCategory
DEFAULT_COLUMNS = 'default columns'
DEFAULT_WRAP = 'default wrap'
prefs = addCategory("BLAST", HiddenCategory)

from chimera import dialogs
dialogs.register(BlastChainDialog.name, BlastChainDialog)
dialogs.register(BlastDialog.name, BlastDialog)
