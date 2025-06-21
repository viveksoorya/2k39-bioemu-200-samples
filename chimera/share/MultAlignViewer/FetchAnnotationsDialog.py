# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: AddSeqDialog.py 27358 2009-04-21 00:32:47Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj, UserError, help
from MAViewer import SeqMenu

class FetchAnnotationsDialog(ModelessDialog):
	"""Fetch UniProt/CDD annotations"""

	buttons = ("OK", "Apply", "Close")
	default = "OK"
	title = "Get UniProt Info"
	help = "ContributedSoftware/multalignviewer/multalignviewer.html#unifetch"
	
	def __init__(self, mav, *args, **kw):
		self.mav = mav
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		import itertools
		row = itertools.count()
		self.menu = SeqMenu(parent, self.mav, labelpos='w',
			label_text="Fetch annotations for", command=self._seqCB)
		self.menu.grid(row=row.next(), column=0, sticky='w')

		nb = self.notebook = Pmw.NoteBook(parent)
		upPage = nb.add("UniProt")
		#cddPage = nb.add("CDD")
		nb.selectpage("UniProt")
		nb.grid(row=row.next(), column=0, sticky="nsew")

		row = itertools.count()
		f = Tkinter.LabelFrame(upPage, text="Identify UniProt Entry")
		f.grid(row=row.next(), column=0, sticky='nsew')

		self.methodVar = Tkinter.StringVar(upPage)

		uniprotf = Tkinter.Frame(f)
		uniprotf.grid(row=0, column=0, sticky='w')
		Tkinter.Radiobutton(uniprotf, variable=self.methodVar, value="uniprot",
			text="from UniProt ID:").grid(row=0, column=0)
		self.uniprotEntry = Pmw.EntryField(uniprotf, entry_width=15,
			modifiedcommand=lambda v=self.methodVar: v.set("uniprot"))
		self.uniprotEntry.grid(row=0, column=1)

		pdbf = Tkinter.Frame(f)
		pdbf.grid(row=1, column=0, sticky='w')
		Tkinter.Radiobutton(pdbf, variable=self.methodVar, value="pdb",
			text="from PDB code:").grid(row=0, column=0)
		self.pdbEntry = Pmw.EntryField(pdbf, entry_width=4, command=self.OK,
			modifiedcommand=lambda v=self.methodVar: v.set("pdb"))
		self.pdbEntry.grid(row=0, column=1)
		self.chainEntry = Pmw.EntryField(pdbf, labelpos='w', entry_width=1,
			label_text="and chain ID:")
		self.chainEntry.grid(row=0, column=2)

		blastf = Tkinter.Frame(f)
		blastf.grid(row=2, column=0, sticky='w')
		Tkinter.Radiobutton(blastf, variable=self.methodVar, value="blast", text=
			"by Blast search of UniProt (may take minutes)").grid(row=0, column=0)

		f = Tkinter.Frame(upPage)
		f.grid(row=row.next(), column=0)
		self.annotateVar = Tkinter.IntVar(upPage)
		self.annotateVar.set(True)
		Tkinter.Checkbutton(f, text="Annotate sequence", variable=self.annotateVar
			).grid(row=0, column=0, sticky='w')
		self.showPageVar = Tkinter.IntVar(upPage)
		self.showPageVar.set(False)
		Tkinter.Checkbutton(f, text="Show UniProt page(s)", variable=self.showPageVar
			).grid(row=1, column=0, sticky='w')

		self.ignoreCachesVar = Tkinter.IntVar(upPage)
		self.ignoreCachesVar.set(False)
		cacheBut = Tkinter.Checkbutton(upPage, text="Ignore any cached data",
			variable=self.ignoreCachesVar)
		from CGLtk.Font import shrinkFont
		shrinkFont(cacheBut)
		cacheBut.grid(row=row.next(), column=0)

		self.menu.invoke()

		"""
		Tkinter.Label(cddPage, text="Query sequence against NCBI Conserved"
			" Domain Database (CDD)").grid(row=0, column=0)
		Tkinter.Button(cddPage, text="CDD info",
			command=lambda: help.display("https://www.ncbi.nlm.nih.gov/"
				"Structure/cdd/cdd_help.shtml")).grid(row=1, column=0)
		self.cddShowPagesVar = Tkinter.IntVar(cddPage)
		self.cddShowPagesVar.set(True)
		Tkinter.Checkbutton(cddPage, text="Also show corresponding web page(s)",
			variable=self.cddShowPagesVar).grid(row=2, column=0)
		"""
		nb.setnaturalsize()

	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		seq = self.menu.getvalue()
		if self.notebook.getcurselection() == "UniProt":
			method = self.methodVar.get()
			if method == "pdb":
				pdbID = self.pdbEntry.getvalue().strip()
				if len(pdbID) != 4:
					self.enter()
					raise UserError("PDB ID code must be exactly 4"
						" characters long!")
				pdbID = pdbID.upper()
				chainID = self.chainEntry.getvalue().strip()
				if not chainID:
					self.enter()
					raise UserError("No chains ID supplied!")
				if len(chainID) != 1 or not chainID.isalnum():
					self.enter()
					raise UserError("Chain ID must be 1 letter or digit!")
				methodInfo = (pdbID, chainID)
			elif method == "uniprot":
				uniprotID = self.uniprotEntry.getvalue()
				if not uniprotID:
					self.enter()
					raise UserError("No UniProt ID supplied!")
				methodInfo = uniprotID
			else: # blast
				methodInfo = None
			self.mav.uniprotInfo(seq, method, methodInfo,
				annotate=self.annotateVar.get(),
				showPage=self.showPageVar.get(),
				ignoreCache=self.ignoreCachesVar.get())
		else:
			# CDD
			from SeqAnnotations import showCddFeatures
			pssmIDs = showCddFeatures(self.mav,
				seqIndex=self.mav.seqs.index(seq))
			replyobj.info("CDD annotations for %s came from the following CDD"
				" PSSM-IDs: %s" % (seq.fullName(), ", ".join(list(pssmIDs))
				if pssmIDs else "(no features found)"))
			if self.cddShowPagesVar.get():
				for pssmID in pssmIDs:
					help.display("https://www.ncbi.nlm.nih.gov/Structure/cdd/"
						"cddsrv.cgi?uid=" + pssmID)

	def _seqCB(self, *args):
		if self.methodVar.get() != "uniprot":
			self.methodVar.set("blast")
		seq = self.menu.getvalue()
		if len(getattr(seq, 'matchMaps', {})) == 1:
			mseq = seq.matchMaps.values()[0]['mseq']
			from SeqAnnotations import chain2pdbID
			pdbID = chain2pdbID(mseq)
			if pdbID:
				self.methodVar.set("pdb")
				self.pdbEntry.setvalue(pdbID)
				self.chainEntry.setvalue(mseq.chainID)
