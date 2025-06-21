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

class AverageError(ValueError):
	pass

def averageStructure(mol, coordIndices, alignOnCurrent, heavysOnly, metalIons, structName,
		superpositionFrame=None, status=None):

	if status:
		status("Determining atoms for superposition")
	from analysis import analysisAtoms, AnalysisError
	try:
		alignAtoms = analysisAtoms(mol, alignOnCurrent, True, heavysOnly, metalIons,
			polymericOnly=True)
	except AnalysisError, v:
		raise AverageError(unicode(v))
	from chimera import UserError
	if len(alignAtoms) < 3:
		raise AverageError("Not enough atoms for meaningful superposition")

	if superpositionFrame == None:
		if status:
			status("Clustering to determine base frame for superposition")
		from cluster import cluster, ClusterError
		try:
			clustering, indexMap, sameAsFrames = cluster(mol, alignAtoms,
				coordIndices, status=status)
		except ClusterError, v:
			raise AverageError(unicode(v))
		biggest = None
		for c in clustering.clusters:
			if biggest is None or len(c.members()) > len(biggest.members()):
				biggest = c
		superpositionFrame = indexMap[clustering.representative(biggest)]

	if status:
		status("Determining atoms to include in average")
	try:
		avgAtoms = analysisAtoms(mol, False, True, heavysOnly, metalIons,
			polymericOnly=True)
	except AnalysisError, v:
		raise AverageError(unicode(v))

	if status:
		status("Superimposing frames")
	from chimera import Point, match
	sums = dict([(a, []) for a in avgAtoms])
	refCoordSet = mol.findCoordSet(superpositionFrame)
	for ci in coordIndices:
		matchCoordSet = mol.findCoordSet(ci)
		xf, rmsd = match.matchAtoms(alignAtoms, alignAtoms, fCoordSet=refCoordSet,
			mCoordSet=matchCoordSet)
		for a, pts in sums.items():
			pts.append(xf.apply(a.coord(matchCoordSet)))

	if status:
		status("Generating average structure")
	from Combine import combine, CombineError
	try:
		atomMapping, avgMol = combine([mol], mol, returnMapping=True)
	except CombineError, v:
		raise AverageError(unicode(v))
	for a, pts in sums.items():
		atomMapping[a].setCoord(Point(pts))
	for a in mol.atoms:
		if a not in sums:
			avgA = atomMapping[a]
			r = avgA.residue
			avgMol.deleteAtom(avgA)
			del atomMapping[a]
			if len(r.atoms) == 0:
				avgMol.deleteResidue(r)
	avgMol.name = structName

	if status:
		status("Opening average structure")
	from chimera import openModels
	openModels.add([avgMol])

	if status:
		status("Average structure opened as %s" % avgMol)

	return avgMol
