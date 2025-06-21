# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import Tkinter
import Pmw

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
from chimera import tkoptions
from CGLutil import vrml

import base

class Interface(ModelessDialog):

	title = 'Pipes and Planks'
	help = "ContributedSoftware/pipesandplanks/pipesandplanks.html"

	def fillInUI(self, parent):
		self.molecules = Pmw.ComboBox(parent, label_text=self.title,
						labelpos='nw')
		self.molecules.pack(side=Tkinter.TOP, fill=Tkinter.X)
		self.frame = Tkinter.Frame(parent)
		self.frame.pack(expand=Tkinter.TRUE, fill=Tkinter.BOTH)

		import itertools
		row = itertools.count()

		#
		# Helix options
		#
		self.helixColor = tkoptions.ColorOption(
						self.frame, row.next(),
						'Helix color', None, None,
						noneOkay=True)
		self.helixEdgeColor = tkoptions.ColorOption(
						self.frame, row.next(),
						'Helix edge color', None, None,
						noneOkay=True)
		self.helixArrow = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Show arrow on helix', 1, None)
		self.helixFixedRadius = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Fixed helix radius', 1, None)
		self.helixRadius = tkoptions.FloatOption(
						self.frame, row.next(),
						'Helix radius', 1.25, None)
		self.helixSplit = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Split curved helices', 0, None)
		self.helixSplitRatio = tkoptions.FloatOption(
						self.frame, row.next(),
						'Helix split threshold',
						2.5, None)

		#
		# Strand options
		#
		self.strandColor = tkoptions.ColorOption(
						self.frame, row.next(),
						'Strand color', None, None,
						noneOkay=True)
		self.strandEdgeColor = tkoptions.ColorOption(
						self.frame, row.next(),
						'Strand edge color', None, None,
						noneOkay=True)
		self.strandArrow = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Show arrow on strand', 1, None)
		self.strandFixedWidth = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Fixed strand width', 1, None)
		self.strandWidth = tkoptions.FloatOption(
						self.frame, row.next(),
						'Strand width', 2.5, None)
		self.strandFixedThickness = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Fixed strand thickness',
						1, None)
		self.strandThickness = tkoptions.FloatOption(
						self.frame, row.next(),
						'Strand thickness', 1.0, None)
		self.strandSplit = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Split curved strands', 0, None)
		self.strandSplitRatio = tkoptions.FloatOption(
						self.frame, row.next(),
						'Strand split threshold',
						2.5, None)

		#
		# Coil options
		#
		self.displayTurns = tkoptions.BooleanOption(
						self.frame, row.next(),
						'Display coil', True, None)
		self.turnColor = tkoptions.ColorOption(
						self.frame, row.next(),
						'Coil color', None, None,
						noneOkay=True)
		self.turnEdgeColor = tkoptions.ColorOption(
						self.frame, row.next(),
						'Coil edge color', None, None,
						noneOkay=True)
		self.turnResolution = tkoptions.IntOption(
						self.frame, row.next(),
						'Coil subdivision', 10, None)
		self.turnWidth = tkoptions.FloatOption(
						self.frame, row.next(),
						'Coil width', 0.25, None)
		self.turnThickness = tkoptions.FloatOption(
						self.frame, row.next(),
						'Coil thickness', 0.25, None)

		self.openModels = {}
		self.molTrigger = chimera.triggers.addHandler('Molecule',
						self._setMolList, None)
		self.vrmlTrigger = chimera.triggers.addHandler('VRMLModel',
						self._setVRMLList, None)
		self.molList = []
		self._setMolList()

	def _setMolList(self, triggerName=None, closure=None, m=None):
		if m and not m.created and not m.deleted:
			return
		molList = chimera.openModels.list(modelTypes=[chimera.Molecule])
		self.molList = map(lambda m: (m.name, m.id, m.subid), molList)
		self.molList.sort()
		nameList = map(lambda t: t[0], self.molList)
		self.molecules.setlist(nameList)
		if len(nameList) == 1:
			self.molecules.selectitem(0)

		if m:
			for mol in m.deleted:
				try:
					del self.openModels[mol]
				except KeyError:
					pass

	def _setVRMLList(self, triggerName=None, closure=None, m=None):
		if not m.deleted:
			return
		for mol, vrml in self.openModels.items():
			if vrml in m.deleted:
				del self.openModels[mol]

	def Apply(self):
		molList = chimera.openModels.list(modelTypes=[chimera.Molecule])
		selList = self.molecules.curselection() 
		if len(selList) != 1:
			return
		molName, molId, molSubid = self.molList[int(selList[0])]
		for m in molList:
			if m.id == molId and m.subid == molSubid:
				mol = m
				break
		else:
			replyobj.error('No selected molecule')
			return
		try:
			chimera.openModels.close(self.openModels[mol])
		except KeyError:
			pass
		m = base.makePandP(mol,
			self.helixColor.get(),
			self.helixEdgeColor.get(),
			self.helixArrow.get(),
			self.helixFixedRadius.get(),
			self.helixRadius.get(),
			self.helixSplit.get(),
			self.helixSplitRatio.get(),
			self.strandColor.get(),
			self.strandEdgeColor.get(),
			self.strandArrow.get(),
			self.strandFixedWidth.get(),
			self.strandWidth.get(),
			self.strandFixedThickness.get(),
			self.strandThickness.get(),
			self.strandSplit.get(),
			self.strandSplitRatio.get(),
			self.displayTurns.get(),
			self.turnColor.get(),
			self.turnEdgeColor.get(),
			int(self.turnResolution.get()),
			self.turnWidth.get(),
			self.turnThickness.get())
		if m:
			self.openModels[mol] = m
			self.openModels[m] = None

singleton = None

def gui():
	global singleton
	if not singleton:
		singleton = Interface()
	singleton.enter()
