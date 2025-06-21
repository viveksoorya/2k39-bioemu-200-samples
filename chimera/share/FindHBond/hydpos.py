# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: hydpos.py 39593 2014-03-10 18:54:50Z pett $

from chimera.idatm import *
from chimera import Element
from chimera.bondGeom import bondPositions

def hydPositions(heavy, includeLonePairs=False):
	"""Return list of positions for hydrogens attached to this atom.
	   If a hydrogen could be in one of several positions, don't
	   return any of those.
	"""

	# first, find known attached atoms
	bondedHeavys = []
	hyds = []
	for atom in heavy.primaryNeighbors():
		if atom.element.number > 1:
			bondedHeavys.append(atom)
		else:
			hyds.append(atom)
	
	# convert to Points
	hydLocs = []
	for hyd in hyds:
		hydLocs.append(hyd.xformCoord())
	
	if hydLocs and not includeLonePairs:
		# explicit hydrogens "win" over atom types
		return hydLocs

	if typeInfo.has_key(heavy.idatmType):
		info = typeInfo[heavy.idatmType]
		geom = info.geometry
		if includeLonePairs:
			subs = geom
		else:
			subs = info.substituents
		bondedLocs = hydLocs[:]
		for bHeavy in bondedHeavys:
			bondedLocs.append(bHeavy.xformCoord())
	else:
		return hydLocs
	
	knownSubs = len(bondedLocs)
	if knownSubs >= subs or knownSubs == 0:
		return hydLocs
	# above eliminates 'single' geometry
	
	if knownSubs == 1 and geom == tetrahedral:
		# rotamer
		return hydLocs
	
	maxSubs = geom
	if maxSubs - subs > 0:
		# the "empty" bond could be anywhere
		return hydLocs

	heavyLoc = heavy.xformCoord()
	bondLen = Element.bondLength(heavy.element, Element(1))

	if geom == planar:
		coPlanar = []
		for bHeavy in bondedHeavys:
			try:
				bhGeom = typeInfo[bHeavy.idatmType].geometry
			except KeyError:
				bhGeom = None
			if bhGeom != planar:
				continue
			if heavy.altLoc == bHeavy.altLoc or not heavy.altLoc:
				for atom in bHeavy.primaryNeighbors():
					if atom != heavy:
						coPlanar.append(atom.xformCoord())
			else:
				# heavy has altloc and neighbor doesn't;
				# make sure to use only atoms with no altloc
				# or same altloc
				for atom in bHeavy.neighbors:
					if not atom.altLoc or atom.altLoc == heavy.altLoc:
						if atom != heavy:
							coPlanar.append(atom.xformCoord())

	else:
		coPlanar = None

	hydLocs = hydLocs + bondPositions(heavyLoc, geom, bondLen, bondedLocs,
							coPlanar=coPlanar)
	return hydLocs
	
