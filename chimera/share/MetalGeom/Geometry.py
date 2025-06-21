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

from geomData import minAngles, normVecs

class Geometry:
	def __init__(self, desc):
		self.description = desc

	def __str__(self):
		return self.description

	def __getattr__(self, attrName):
		if attrName == "minAngle":
			return minAngles[self.description]
		if attrName == "normVecs":
			return normVecs[self.description]
		if attrName == "coordinationNumber":
			return len(self.normVecs)
		raise AttributeError("No attribute named '%s'" % attrName)

	def angleRMSD(self, metal, ligands):
		mc = metal.coord()
		lcs = [l.coord() for l in ligands]
		angles = []
		from chimera import angle
		for i, l1 in enumerate(lcs):
			for l2 in lcs[i+1:]:
				angles.append(angle(l1, mc, l2))
		angles.sort()
		bestErrorSq = None
		from geomData import geomData
		angleSets = geomData.get(len(ligands), [])
		for testAngles, fullCoordination, description in angleSets:
			if description != self.description:
				continue
			errorSq = 0.0
			for a, ta in zip(angles, testAngles):
				d = a - ta
				errorSq += d * d
			if bestErrorSq is None or errorSq < bestErrorSq:
				bestErrorSq = errorSq
		if bestErrorSq == None:
			return None
		from math import sqrt
		return sqrt(bestErrorSq / len(angles))

	def angleSepOK(self, ligLoc, minSep, dists):
		try:
			asoCache = self.asoCache
		except AttributeError:
			asoCache = self.asoCache = {}
		key = tuple([ligLoc, minSep] + dists)
		if key not in asoCache:
			if ligLoc == "min":
				targetD = min(dists)
			elif ligLoc == "max":
				targetD = max(dists)
			else:
				targetD = sum(dists) / len(dists)
			from math import sin, radians
			asoCache[key] = minSep < targetD * 2.0 * sin(radians(
										self.minAngle/2.0))
		return asoCache[key]
