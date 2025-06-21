# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 41090 2016-06-07 21:05:40Z pett $

"""management functions for bond rotations"""

import chimera
from chimera import BondRot
from chimera.triggerSet import TriggerSet

class BondRotManager:
	CREATED, MODIFIED, REVERSED, DELETED = triggerNames = ("created",
					"modified", "reversed", "deleted")

	def __init__(self):
		self.rotations = {}
		self.triggers = TriggerSet()
		for trigName in self.triggerNames:
			self.triggers.addTrigger(trigName)
		chimera.triggers.addHandler('BondRot', self._rotChangeCB, None)
		chimera.triggers.addHandler('Model', self._modelChangeCB, None)
		from SimpleSession import SAVE_SESSION
		chimera.triggers.addHandler(SAVE_SESSION, self._sessionSave, None)

	def rotationForBond(self, bond, create=True, requestedID=None):
		for br in self.rotations.values():
			if br.bond == bond:
				if requestedID != None and requestedID != br.id:
					raise chimera.UserError("Rotation"
						" already exists with different"
						" ID (%d) than requested (%d)"
						% (br.id, requestedID))
				return br
		if create:
			return BondRotation(bond, requestedID=requestedID)
		return None

	def _modelChangeCB(self, trigName, myData, trigData):
		if not trigData.modified:
			return
		if 'atoms moved' not in trigData.reasons \
		and 'activeCoordSet changed' not in trigData.reasons:
			return
		for br in self.rotations.values():
			if br.bondRot.__destroyed__:
				continue
			if br.anchorSide.molecule in trigData.modified:
				self.triggers.activateTrigger(bondRotMgr.MODIFIED, br)

	def _newRot(self, rotation, requestedID):
		if requestedID is None:
			if self.rotations:
				requestedID = max(self.rotations.keys()) + 1
			else:
				requestedID = 1
		rotation.id = requestedID
		self.rotations[rotation.id] = rotation
		self.triggers.activateTrigger(self.CREATED, rotation)

	def _rotChangeCB(self, trigName, myData, trigData):
		delRots = [br for br in self.rotations.values()
					if br.bondRot in trigData.deleted]
		if delRots:
			for br in delRots:
				del self.rotations[br.id]
			self.triggers.activateTrigger(self.DELETED, delRots)

	def _sessionRestore(self, info, version=1):
		if version == 1 and not chimera.nogui:
			# torsion gui moved from StructMeasure to BuildStructure
			# and the latter isn't "always awake".  Wake it up so
			# that it gets the upcoming triggers
			from BuildStructure.gui import BuildStructureDialog
			from chimera import dialogs
			dialogs.display(BuildStructureDialog.name)

		from SimpleSession import idLookup
		for bondID, anchorID, delta, rotID in info:
			bond = idLookup(bondID)
			dup = False
			for br in self.rotations.values():
				if br.bond == bond:
					from chimera import replyobj
					replyobj.error("Active torsion in session file same as"
						" existing active torsion; skipping")
					dup = True
					break
			if dup:
				continue

			anchorSide = idLookup(anchorID)
			if delta:
				# need to make rotation have same delta as original
				bondRot = BondRot(bond)
				bondRot.angle = (-delta, anchorSide)
				bondRot.destroy()

			if rotID in self.rotations:
				rotID = None
			br = self.rotationForBond(bond, requestedID=rotID)
			br.anchorSide = anchorSide

			if delta:
				br.set(delta)

	def _sessionSave(self, trigger, myData, session):
		if not self.rotations:
			return

		from SimpleSession import sesRepr, sessionID
		print>>session, """info = %s
try:
	from BondRotMgr import bondRotMgr
	bondRotMgr._sessionRestore(info, version=2)
except:
	reportRestoreError("Error restoring bond rotations")
""" % sesRepr([(sessionID(br.bond), sessionID(br.anchorSide),
				br.get(), br.id) for br in self.rotations.values()])

class BondRotation(object):
	SMALLER, BIGGER = range(2)

	def __init__(self, bond, anchorSide=BIGGER, requestedID=None):
		try:
			self.bondRot = BondRot(bond)
		except (chimera.error, ValueError), v:
			if "cycle" in str(v):
				raise chimera.UserError("Cannot rotate a bond"
					" that is part of a closed cycle")
			raise
		self.bond = bond
		self.__anchorSide = self._sideToAtom(anchorSide)
		if requestedID is not None \
		and requestedID in bondRotMgr.rotations:
			raise chimera.UserError("Requested bond-rotation ID already"
								" in use")
		bondRotMgr._newRot(self, requestedID)

	def destroy(self):
		if not self.bondRot.__destroyed__:
			self.bondRot.destroy()

	def get(self):
		return self.bondRot.angle

	def increment(self, increment):
		self.bondRot.angle = (self.get() + increment, self.__anchorSide)
		bondRotMgr.triggers.activateTrigger(bondRotMgr.MODIFIED, self)

	def set(self, totalDelta):
		self.bondRot.angle = (totalDelta, self.__anchorSide)
		bondRotMgr.triggers.activateTrigger(bondRotMgr.MODIFIED, self)

	def _getAnchorSide(self):
		return self.__anchorSide

	def _setAnchorSide(self, side):
		atom = self._sideToAtom(side)
		if atom == self.__anchorSide:
			return
		self.__anchorSide = atom
		bondRotMgr.triggers.activateTrigger(bondRotMgr.REVERSED, self)

	anchorSide = property(_getAnchorSide, _setAnchorSide)

	def _getAtoms(self):
		atoms = self.bond.atoms
		if atoms[0] == self.__anchorSide:
			return atoms
		return atoms[1], atoms[0]

	atoms = property(_getAtoms)

	def _sideToAtom(self, side):
		if side == self.BIGGER:
			return self.bondRot.biggerSide()
		if side == self.SMALLER:
			return self.bond.otherAtom(self.bondRot.biggerSide())
		return side

bondRotMgr = BondRotManager()
