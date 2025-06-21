# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: DCD.py 42039 2019-05-28 21:25:24Z pett $

# much of this code is based on sample code provided by Walter Scott

import chimera
from chimera import replyobj
import os

class PSF_BASE:
	def GetDict(self, key):
		if key == "atomnames":
			return self.psf.atomNames
		if key == "elements":
			return self.psf.elements
		if key == "resnames":
			return self.psf.resNames
		if key == "resnums":
			return self.psf.resNums
		if key == "bonds":
			return self.psf.bonds
		if key == "ipres":
			return self.psf.ipres
		if key == "charges":
			if hasattr(self.psf, "charges"):
				return self.psf.charges
		if key == "segments":
			return self.psf.segments
		raise KeyError, "Unknown GetDict() value: '%s'" % key

class DCD_BASE:
	def addTraj(self, fn):
		self.dcd.addDCD(fn)

	def __getitem__(self, i):
		return self.dcd.dcd[i-1]

	def __len__(self):
		return len(self.dcd.dcd)

class PSF_DCD(PSF_BASE, DCD_BASE):
	def __init__(self, psfPath, dcdPath, startFrame, endFrame, sesInfo=None):
		if sesInfo:
			dcdPath = sesInfo['trajFiles'][0]
		else:
			self.psf = PSF(psfPath)
		self.dcd = DCD(dcdPath)
		if sesInfo:
			for dcd in sesInfo['trajFiles'][1:]:
				self.dcd.addDCD(dcd)
		else:
			numDcdAtoms = self.dcd.dcd.trajs[0].numatoms
			if numDcdAtoms != len(self.psf.atomNames):
				raise ValueError("PSF has different number of atoms (%d)"
					" than DCD (%d)!" % (len(self.psf.atomNames), numDcdAtoms))
		self.startFrame = startFrame
		self.endFrame = endFrame

		self.name = os.path.basename(dcdPath)

	def sesSave_gatherData(self):
		return {
			"trajFiles": [dcd.dcdfile for dcd in self.dcd.dcd.trajs]
		}

class PSF:
	def __init__(self, psfPath):
		from MDToolsMarch97 import md
		replyobj.status("Reading PSF file", blankAfter=0)
		try:
			mdtMol = md.Molecule(psf=psfPath)
		finally:
			replyobj.status("Done reading PSF file")
		replyobj.status("Processing PSF file", blankAfter=0)
		try:
			mdtMol.buildstructure()
		finally:
			replyobj.status("Processed PSF file")

		# atom names
		self.atomNames = map(lambda a: a.name, mdtMol.atoms)

		# elements
		from Trajectory import determineElementFromMass
		self.elements = map(lambda a: determineElementFromMass(a.mass),
								mdtMol.atoms)
		# charges
		try:
			self.charges = [a.charge for a in mdtMol.atoms]
		except AttributeError:
			pass

		# residue names
		self.resNames = []
		self.resNums = []
		self.segments = []
		for seg in mdtMol.segments:
			print repr(seg)
			for res in seg.residues:
				self.resNames.append(res.name)
				self.resNums.append(res.id)
				self.segments.append(seg.name)

		# bonds
		atomIndices = {}
		for i, a in enumerate(mdtMol.atoms):
			atomIndices[a] = i
		self.bonds = map(lambda b: (atomIndices[b[0]],
					atomIndices[b[1]]), mdtMol.bonds)

		# residue composition
		self.ipres = []
		offset = 1
		for seg in mdtMol.segments:
			for res in seg.residues:
				self.ipres.append(offset)
				offset += len(res.atoms)

class DCD:

	def __init__(self, dcdPath):
		replyobj.status("Reading DCD header", blankAfter=0)
		from Trajectory import MultiFileTrajectory
		from MDToolsMarch97 import md
		self.dcd = MultiFileTrajectory(md.DCD)
		try:
			self.dcd.addFile(dcdPath)
		finally:
			replyobj.status("Done reading DCD header")

	def addDCD(self, dcdFileName):
		replyobj.status("Reading DCD file %s" % dcdFileName, blankAfter=0)
		try:
			self.dcd.addFile(dcdFileName)
		finally:
			replyobj.status("Done reading DCD file %s" % dcdFileName)
