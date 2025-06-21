# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: AssociationsDialog.py 40014 2014-08-05 21:26:35Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
from chimera.misc import oslModelCmp
import Pmw, Tkinter
from MAViewer import ADD_ASSOC, DEL_ASSOC, SeqMenu

class AssociationsDialog(ModelessDialog):
	"""Allow the user to change structure/sequence associations"""

	provideStatus = True
	statusPosition = "left"
	buttons = ("OK", "Apply", "Close")
	help = "ContributedSoftware/multalignviewer/multalignviewer.html" \
							"#assocpanel"

	def __init__(self, mav, *args, **kw):
		self.mav = mav
		self.title = "Structure/Sequence Associations for %s" % (
								mav.title,)
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		self.scrolledFrame = sf = Pmw.ScrolledFrame(parent)
		sf.grid(sticky="nsew")
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(0, weight=1)
		self.parent = sf.interior()
		self.assocInfo = {}
		col1 = Tkinter.Label(self.parent, text="Model")
		col1.grid(row=0, column=0)
		col2 = Tkinter.Label(self.parent, text="Chain")
		col2.grid(row=0, column=1)
		col3 = Tkinter.Label(self.parent, text="Association")
		col3.grid(row=0, column=2)
		self._postDeletionID = None
		self._newModelsCB()
		for aseq in self.mav.seqs:
			try:
				mapDict = aseq.matchMaps
			except AttributeError:
				continue
			self._addAssocCB(newAssocs=mapDict.values())
		self.addAssocHandlerID = self.mav.triggers.addHandler(ADD_ASSOC,
							self._addAssocCB, None)
		self.delAssocHandlerID = self.mav.triggers.addHandler(DEL_ASSOC,
							self._delAssocCB, None)
		self.addHandlerID = chimera.openModels.addAddHandler(
			self._newModelsCB, None)
		self.removeHandlerID = chimera.openModels.addRemoveHandler(
			self._closeModelsCB, None)

	def _addAssocCB(self, trigName=None, myData=None, newAssocs=[]):
		for matchMap in newAssocs:
			mseq = matchMap['mseq']
			mol = mseq.molecule
			try:
				assocInfo = self.assocInfo[mol]
			except KeyError:
				continue
			widgets = assocInfo['widgets']
			if widgets[1]:
				# MatchMaker can pass in an mseq not in
				# mol.sequences 
				try:
					chains = mol.sequences(asDict=True)
				except:
					pass
				else:
					if mseq not in chains.values():
						mseq = chains[mseq.chainID]
				widgets[1].setvalue(mseq.name)
			widgets[2].setvalue(matchMap['aseq'])
			widgets[3].variable.set(False)
			widgets[3].button.grid_remove()

	def _assocMenuCB(self, val, widgets):
		if val is None:
			widgets[3].button.grid()
		else:
			widgets[3].button.grid_remove()

	def _chainDeletionCB(self, *args):
		from chimera.triggerSet import ONESHOT
		if self._postDeletionID:
			return ONESHOT
		self._postDeletionID = self.uiMaster().after_idle(
							self._newModelsCB)
		return ONESHOT

	def _closeModelsCB(self, trigName=None, myData=None, models=[]):
		if not self.mav:
			# already destroyed
			return
		for mol in models:
			if mol not in self.assocInfo:
				continue
			for widget in self.assocInfo[mol]['widgets']:
				if not widget:
					continue
				widget.grid_forget()
				widget.destroy()
			del self.assocInfo[mol]
		mols = filter(lambda m: isinstance(m, chimera.Molecule),
						chimera.openModels.list())
		mols.sort(lambda a, b: oslModelCmp(a.oslIdent(), b.oslIdent()))
		seenIDs = set()
		for mol in mols:
			if mol.subid > 0:
				if mol.id not in seenIDs:
					seenIDs.add(mol.id)
					self.assocInfo[mol]['widgets'][4].grid()
		if not chimera.openModels.list(modelTypes=[chimera.Molecule]):
			self.mav._disableAssociationsDialog()

	def _configureLike(self, id1, id2):
		ensemble = []
		for mol, info in self.assocInfo.items():
			widgets = info['widgets']
			if mol.id == id1:
				ensemble.append(mol)
				if mol.subid == id2:
					if widgets[1]:
						chainName = widgets[1].getvalue()
					else:
						chainName = None
					seq = widgets[2].getvalue()
					checked = widgets[3].variable.get()
		for mol in ensemble:
			widgets = self.assocInfo[mol]['widgets']
			chainMenu = widgets[1]
			assocMenu = widgets[2]
			bestMatch = widgets[3]
			if chainName is None:
				if chainMenu is not None:
					continue
			else:
				if chainMenu is None:
					continue
				try:
					chainMenu.index(chainName)
				except ValueError:
					continue
				chainMenu.setvalue(chainName)
			assocMenu.setvalue(seq)
			bestMatch.variable.set(checked)
			if seq:
				bestMatch.button.grid_remove()
			else:
				bestMatch.button.grid()

		self.status("Click Ok or Apply to have changes take effect",
			color="blue")

	def _delAssocCB(self, trigName=None, myData=None, delAssocs=[]):
		for matchMap in delAssocs:
			mseq = matchMap['mseq']
			from chimera.Sequence import StructureSequence
			if not isinstance(mseq, StructureSequence):
				# model has closed and sequence updated;
				# model-close trigger should have cleaned things up
				continue
			mol = mseq.molecule
			if mol not in self.assocInfo:
				continue
			assocWidget, matchWidget = self.assocInfo[mol][
								'widgets'][2:4]
			assocWidget.setvalue(None)
			matchWidget.button.grid()

	def destroy(self):
		self.mav.triggers.deleteHandler(ADD_ASSOC,
							self.addAssocHandlerID)
		self.mav.triggers.deleteHandler(DEL_ASSOC,
							self.delAssocHandlerID)
		self.mav = None
		chimera.openModels.deleteAddHandler(self.addHandlerID)
		chimera.openModels.deleteRemoveHandler(self.removeHandlerID)
		ModelessDialog.destroy(self)

	def _newModelsCB(self, trigName=None, myData=None, models=None):
		if self.mav == None:
			# dialog already destroyed
			return
		mols = filter(lambda m: isinstance(m, chimera.Molecule),
						chimera.openModels.list())
		mols.sort(lambda a, b: oslModelCmp(a.oslIdent(), b.oslIdent()))
		seenIDs = set()
		for i in range(len(mols)):
			mol = mols[i]
			chains = mol.sequences()
			if mol in self.assocInfo:
				col = -1
				for widget in self.assocInfo[mol]['widgets']:
					col += 1
					if not widget:
						continue
					widget.grid_remove()
					if len(chains) == 0:
						widget.destroy()
					else:
						widget.grid(row=i+1, column=col, sticky='w')
						if col == 4:
							if mol.id in seenIDs:
								widget.grid_remove()
							else:
								seenIDs.add(mol.id)
				if len(chains) == 0:
					del self.assocInfo[mol]
				continue
			if len(chains) == 0:
				continue
			for chain in chains:
				chain.triggers.addHandler(chain.TRIG_DELETE,
						self._chainDeletionCB, None)
			assocInfo = {}
			self.assocInfo[mol] = assocInfo
			widgets = []
			assocInfo['widgets'] = widgets
			w = Tkinter.Label(self.parent,
				text="%s (%s)" % (mol.name, mol.oslIdent()))
			widgets.append(w)
			w.grid(row=i+1, column=0, sticky='w')

			if len(chains) > 1:
				w = Pmw.OptionMenu(self.parent,
					items=map(lambda s: s.name, chains))
				w.grid(row=i+1, column=1, sticky='w')
			else:
				w = None
			widgets.append(w)

			w = SeqMenu(self.parent, self.mav, includeNoneOption=True,
				command=lambda v, w=widgets: self._assocMenuCB(v,w))
			widgets.append(w)
			w.grid(row=i+1, column=2, sticky='w')

			w = Tkinter.Frame(self.parent)
			widgets.append(w)
			w.grid(row=i+1, column=3, sticky='w')
			w.variable = Tkinter.IntVar(w)
			w.variable.set(False)
			w.button = Tkinter.Checkbutton(w, variable=w.variable,
				text="associate with best match")
			w.button.grid()

			if mol.subid > 0:
				w = Tkinter.Frame(self.parent)
				Tkinter.Button(w, text="Propagate",
					command=lambda s=self, id1=mol.id, id2=mol.subid:
					s._configureLike(id1, id2)).grid(row=0, column=0)
				Tkinter.Label(w, text="setting to rest of ensemble"
					).grid(row=0, column=1)
				w.grid(row=i+1, column=4, sticky='w')
				if mol.id in seenIDs:
					w.grid_remove()
				else:
					seenIDs.add(mol.id)
			else:
				w = None
			widgets.append(w)
		self.parent.after(100, lambda sf=self.scrolledFrame: sf.component(
			'clipper').configure(width=sf.component('frame').winfo_reqwidth()))


	def Apply(self):
		# block triggers to avoid having handlers prematurely
		# reset widgets...
		trigs = [DEL_ASSOC, ADD_ASSOC]
		for trig in trigs:
			self.mav.triggers.blockTrigger(trig)
		assocs = self.mav.associations
		for mol, info in self.assocInfo.items():
			widgets = info['widgets']
			if assocs.has_key(mol):
				aseq = assocs[mol]
				mseq = aseq.matchMaps[mol]['mseq']
				# sequences _could_ have the same name...
				if widgets[1] and widgets[1].getvalue() != mseq.name \
				or widgets[2].getvalue() != aseq:
					if self.mav.intrinsicStructure and aseq.molecule == mol:
						self.mav.status("Cannot disassociate structure"
							" that sequence derives from", color="red")
						if widgets[1]:
							widgets[1].setvalue(mseq.name)
						widgets[2].setvalue(aseq)
						continue
					self.mav.disassociate(mol)
			if not assocs.has_key(mol):
				aseq = widgets[2].getvalue()
				if widgets[1]:
					mseq = mol.sequences()[
						widgets[1].index(Pmw.SELECT)]
				else:
					mseq = mol.sequences()[0]
				if aseq == None:
					if widgets[3].variable.get():
						self.mav.associate(mseq, force=True)
				else:
					self.mav.associate(mseq, seq=aseq, force=True)
		for trig in trigs:
			self.mav.triggers.releaseTrigger(trig)
