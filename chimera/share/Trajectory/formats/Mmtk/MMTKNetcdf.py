# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: MMTKNetcdf.py 40321 2014-11-18 21:10:40Z pett $

# much of this code is based on sample code provided by Walter Scott

import chimera
from chimera import replyobj
import os

class MMTKNetcdf:

	def __init__(self, netcdfPath, startFrame, endFrame, sesInfo=None):
		from MMTK.Trajectory import Trajectory
		if sesInfo:
			# prev version of sesInfo used 'trajFile' instead of 'trajFiles'
			if 'trajFiles' in sesInfo:
				netcdfPath = sesInfo['trajFiles'][0]
			else:
				netcdfPath = sesInfo['trajFile']
			if not os.path.exists(netcdfPath):
				from Trajectory import findTrajFile
				netcdfPath = findTrajFile(netcdfPath)
		replyobj.status("Reading NetCDF file", blankAfter=0)
		try:
			self.trajectory = Trajectory(None, netcdfPath)
		finally:
			replyobj.status("Done reading NetCDF file")

		if sesInfo:
			self.atomNames = sesInfo["atomNames"]
			self.bonds = sesInfo["bonds"]
			from chimera import Element
			self.elements = [Element(n) for n in sesInfo["elements"]]
			self.endFrame = sesInfo["endFrame"]
			self.ipres = sesInfo["ipres"]
			self.resNames = sesInfo["resNames"]
			self.startFrame = sesInfo["startFrame"]
			return
		replyobj.status("Processing trajectory", blankAfter=0)

		self.atomNames = []
		self.elements = []
		self.resNames = []
		self.atomIndices = {}
		self.bonds = []
		self.ipres = [1]

		from chimera import Element
		univ = self.trajectory.universe
		self.coordLookupOrder = univ.atomList()
		for i, a in enumerate(self.coordLookupOrder):
			self.atomIndices[a] = i
			self.atomNames.append(mmtkName2Chimera(a.name))
			self.elements.append(Element(a.getAtomProperty(a,
								"symbol")))
		groupData = []
		for obj in univ:
			self._processObj(obj, groupData)
		if groupData:
			# process data we collated in the above loop
			atomIndex = 0
			sortInfo = []
			for resIndex, rtype, g in groupData:
				sortInfo.append((resIndex, rtype, g, atomIndex))
				atomIndex += len(g.atoms)
			sortInfo.sort()
			residues = [si[2] for si in sortInfo]
			resNames = [si[1] for si in sortInfo]
			newAtomOrdering = []
			for si in sortInfo:
				resIndex, resType, group, atomIndex = si
				newAtomOrdering.extend(
					range(atomIndex, atomIndex + len(group.atoms)))
			self.atomNames = [self.atomNames[i] for i in newAtomOrdering]
			self.elements = [self.elements[i] for i in newAtomOrdering]
			numAtoms = len(self.atomNames)
			newAtomIndices = {}
			indexTranslation = dict(zip(newAtomOrdering, range(numAtoms)))
			for a, oldIndex in self.atomIndices.items():
				newAtomIndices[a] = indexTranslation[oldIndex]
			self.atomIndices = newAtomIndices
			lookupTranslation = dict(zip(range(numAtoms), newAtomOrdering))
			self.coordLookupOrder = [self.coordLookupOrder[lookupTranslation[i]]
				for i in range(numAtoms)]
			self.resNames = resNames
			for obj in univ:
				self.bonds.extend([(self.atomIndices[b.a1],
					self.atomIndices[b.a2]) for b in obj.bonds])
			for res in residues:
				self.ipres.append(self.ipres[-1] + len(res.atoms))

		delattr(self, "atomIndices")
		self.ipres.pop()
		
		self.startFrame = startFrame
		self.endFrame = endFrame

		self.name = os.path.basename(netcdfPath)

		replyobj.status("Done processing trajectory")

	def _processObj(self, obj, groupData):
		if not hasattr(obj, 'bonds'):
			subobjs = obj.bondedUnits()
			if subobjs == [obj]:
				if hasattr(obj, "atoms") and obj.atoms:
					raise ValueError("Don't know how to"
						" handle MMTK object %s"
						% str(obj))
				replyobj.warning("Skipping unknown MMTK object:"
					" %s\n" % str(obj))
				return
			for so in subobjs:
				self._processObj(so)
			return

		if hasattr(obj, 'residues'):
			residues = obj.residues()
			resNames = [r.name[:3] for r in residues]
		elif hasattr(obj, 'groups'):
			sortInfo = []
			for g in obj.groups:
				rtype, index, rem = g.name.split('_', 2)
				groupData.append((int(index), rtype, g))
			return
		else:
			residues = [obj]
			resNames = ["UNK"]

		self.resNames.extend(resNames)
		self.bonds.extend([(self.atomIndices[b.a1],
				self.atomIndices[b.a2]) for b in obj.bonds])
		for res in residues:
			self.ipres.append(self.ipres[-1] + len(res.atoms))

	def GetDict(self, key):
		if key == "atomnames":
			return self.atomNames
		if key == "elements":
			return self.elements
		if key == "resnames":
			return self.resNames
		if key == "bonds":
			return self.bonds
		if key == "ipres":
			return self.ipres
		raise KeyError, "Unknown GetDict() value: '%s'" % key

	def __getitem__(self, i):
		cnf = self.trajectory[i-1]['configuration']
		cnf = self.trajectory.universe.contiguousObjectConfiguration(conf=cnf)
		cnf.scaleBy(10)
		import numpy
		return numpy.array([a.position(cnf)
				for a in self.coordLookupOrder], numpy.float)

	def __len__(self):
		return len(self.trajectory)

	def sesSave_gatherData(self):
		return {
			"atomNames": self.atomNames,
			"bonds": self.bonds,
			"elements": [e.number for e in self.elements],
			"endFrame": self.endFrame,
			"ipres": self.ipres,
			"resNames": self.resNames,
			"startFrame": self.startFrame,
			"trajFiles": [self.trajectory.filename]
		}

greek2letter = {
	'alpha': 'A',
	'beta': 'B',
	'gamma': 'C',
	'delta': 'D',
	'epsilon': 'E',
	'eta': 'H',
	'zeta': 'Z'
}
def mmtkName2Chimera(mmtkName):
	numUnderscores = mmtkName.count('_')
	if numUnderscores == 0:
		return mmtkName
	if numUnderscores == 1:
		element, remoteness = mmtkName.split('_')
		num = ""
	else:
		element, remoteness, num = mmtkName.split('_', 2)

	try:
		let = greek2letter[remoteness]
	except KeyError:
		return mmtkName
	return element + let + num.replace('_', '')


