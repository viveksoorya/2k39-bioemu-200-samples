# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

class ClusterError(ValueError):
	pass

def cluster(mol, atoms, frameNums, testAbort=None, status=None):
	numFrames = len(frameNums)
	if status:
		status("Fetching %d coordinate arrays" % numFrames)
	from chimera import CancelOperation
	from chimera.match import matchPositions
	from chimera import numpyArrayFromAtoms
	numpyArrays = {}
	from time import time
	t0 = time()
	for i, fn in enumerate(frameNums):
		numpyArrays[fn] = numpyArrayFromAtoms(atoms, mol.findCoordSet(fn))
		if testAbort and testAbort():
			raise CancelOperation("clustering aborted")
		if status:
			if i == numFrames - 1:
				status("Fetched %d coordinate arrays" % (i+1))
			else:
				elapsed = time() - t0
				perSec = elapsed / (i+1)
				remaining = perSec * (numFrames - (i+1))
				status("Fetched %d of %d coordinate arrays"
					"\nAbout %.1f minutes remaining" %
					(i+1, numFrames, remaining / 60.0))
	t0 = time()
	totalRMSDs = numFrames * (numFrames - 1) / 2
	if status:
		status("Computing %d RMSDs" % totalRMSDs)
	from EnsembleMatch.distmat import DistanceMatrix
	fullDM = DistanceMatrix(numFrames)
	sameAs = {}
	for i, frame1 in enumerate(frameNums):
		na1 = numpyArrays[frame1]
		for j, frame2 in enumerate(frameNums[i+1:]):
			na2 = numpyArrays[frame2]
			rmsd = matchPositions(na1, na2)[1]
			fullDM.set(i, i+j+1, rmsd)
			if rmsd == 0.0:
				sameAs[frame2] = frame1
		if testAbort and testAbort():
			raise CancelOperation("clustering aborted")
		numComputed = totalRMSDs - ((numFrames - (i+1)) *
						(numFrames - (i+2))) / 2
		if status:
			if numComputed == totalRMSDs:
				status("Computed %d RMSDs" % totalRMSDs)
			else:
				elapsed = time() - t0
				perSec = elapsed / numComputed
				remaining = perSec * (totalRMSDs - numComputed)
				if remaining < 50:
					timeEst = "%d seconds" % int(
							remaining + 0.5)
				else:
					timeEst = "%.1f minutes" % (
							remaining / 60.0)
				status("Computed %d of %d RMSDs\n"
					"About %s remaining" % (numComputed,
					totalRMSDs, timeEst))
	if status:
		status("Generating clusters")
	if not sameAs:
		dm = fullDM
		reducedFrameNums = frameNums
		indexMap = range(len(frameNums))
	elif len(sameAs) == numFrames - 1:
		raise ClusterError("All frames to cluster are identical!")
	else:
		dm = DistanceMatrix(numFrames - len(sameAs))
		reducedFrameNums = []
		indexMap = []
		for i, fn in enumerate(frameNums):
			if fn in sameAs:
				continue
			reducedFrameNums.append(fn)
			indexMap.append(i)
		for i in range(len(reducedFrameNums)):
			mapi = indexMap[i]
			for j in range(i+1, len(reducedFrameNums)):
				mapj = indexMap[j]
				dm.set(i, j, fullDM.get(mapi, mapj))
	from EnsembleMatch.nmrclust import NMRClust
	return NMRClust(dm), reducedFrameNums, sameAs
