def segmentSieve(rList0, rList1, fraction=0.5):
	"""MolMovDB style segmenting.  Use sieve fit to find core.
	Everything else is in the second segment."""
	# SieveFit checks that the two molecule have equivalent residues
	import SieveFit
	coreList0, coreList1 = SieveFit.fitResidues(rList0, rList1, fraction)
	def splitCore(rList, coreSet):
		core = []
		others = []
		for r in rList:
			if r in coreSet:
				core.append(r)
			else:
				others.append(r)
		return core, others

	# First we split our residue list by chain identifier
	# For each chain, we split into a core segment and an other segment
	coreSet0 = set(coreList0)
	coreSet1 = set(coreList1)
	segments = list()
	start = 0
	chain = rList0[0].id.chainId
	for i in range(1, len(rList0)):
		r0 = rList0[i]
		if r0.id.chainId != chain:
			core0, others0 = splitCore(rList0[start:i], coreSet0)
			core1, others1 = splitCore(rList1[start:i], coreSet1)
			segments.append((core0, core1))
			segments.append((others0, others1))
			start = i
	if start < len(rList0):
		core0, others0 = splitCore(rList0[start:], coreSet0)
		core1, others1 = splitCore(rList1[start:], coreSet1)
		segments.append((core0, core1))
		segments.append((others0, others1))
	return segments

def segmentHingeExact(m0, m1, fraction=0.5):

        # Split by chain
        cr0, cr1 = residuesByChain(m0.residues), residuesByChain(m1.residues)
        if len(cr0) != len(cr1):
		raise ValueError("models have different number of chains")

        # If chain ids all match then pair same ids, otherwise use order from file.
        if set(cid for cid, rlist in cr0) == set(cid for cid, rlist in cr1):
                cr0.sort()
                cr1.sort()

        parts = []
	atomMap = {}
	unusedAtoms = []
        for (cid0,r0list), (cid1,r1list) in zip(cr0, cr1):
                if len(r0list) != len(r1list):
                        raise ValueError("Chains %s and %s have different number of residues" % (cid0, cid1))
                curCat = None
                curRList0 = None
                curRList1 = None
                for r0, r1 in zip(r0list, r1list):
                        if not shareAtoms(r0, r1, atomMap, unusedAtoms):
                                raise ValueError("residues do not share atoms")
                        #
                        # Split residues based on surface category (in m0)
                        #
                        if r0.atoms[0].surfaceCategory == curCat:
                                curRList0.append(r0)
                                curRList1.append(r1)
                        else:
                                curRList0 = [ r0 ]
                                curRList1 = [ r1 ]
                                parts.append((curRList0, curRList1))
                                curCat = r0.atoms[0].surfaceCategory

	#
	# Split each part on hinges and collate results
	#
	segments = []
	for rList0, rList1 in parts:
		segments.extend(segmentHingeResidues(rList0, rList1, fraction))
	return segments, atomMap, [], unusedAtoms

def residuesByChain(residues):
        cres = {}
        cids = []
        for r in residues:
                cid = r.id.chainId
                if cid in cres:
                        cres[cid].append(r)
                else:
                        cres[cid] = [r]
                        cids.append(cid)
        return [(cid, cres[cid]) for cid in cids]

def segmentHingeApproximate(m0, m1, fraction=0.5, matrix="BLOSUM-62"):
	#
	# Get the chains from each model.  If they do not have the
	# same number of chains, we give up.  Otherwise, we assume
	# that the chains should be matched in the same order.
	#
	m0seqs = m0.sequences()
	m1seqs = m1.sequences()
	if len(m0seqs) != len(m1seqs):
		raise ValueError("models have different number of chains")
	resCount0 = len(m0.residues)
	matchCount0 = 0
	for seq0 in m0seqs:
		matchCount0 += len(seq0.residues)
	print "Aligning %d of %d residues from molecule %s" % (
			matchCount0, resCount0, m0.name)
	resCount1 = len(m1.residues)
	matchCount1 = 0
	for seq1 in m1seqs:
		matchCount1 += len(seq1.residues)
	print "Aligning %d of %d residues from molecule %s" % (
			matchCount1, resCount1, m1.name)

	#
	# Any residue that does not appear in chains are unused
	#
	maybe = set()
	for seq0 in m0seqs:
		maybe.update(seq0.residues)
	unusedResidues = [ r0 for r0 in m0.residues if r0 not in maybe ]

	#
	# Try to find the best matches for sequences.
	# If both models have chains with the same ids, assume that
	# chains with the same ids match.  Otherwise, assume the chains
	# match in input order.
	#
	m0map = dict((s.chain, s) for s in m0seqs)
	m1map = dict((s.chain, s) for s in m1seqs)
	if set(m0map.keys()) == set(m1map.keys()):
		seqPairs = [ (m0map[k], m1map[k]) for k in m0map.keys() ]
	else:
		seqPairs = zip(m0seqs, m1seqs)

	#
	# For each chain pair, we align them using MatchMaker to get
	# the residue correspondences.
	#
	import MatchMaker
	ksdsspCache = set([m0, m1])
	parts = []
	atomMap = {}
	unusedAtoms = []
	matched = 0
	matrices = [
		MatchMaker.defaults[MatchMaker.MATRIX],
		"Nucleic",
	]
	for seq0, seq1 in seqPairs:
		for matrix in matrices:
			if (MatchMaker.matrixCompatible(seq0, matrix)
			and MatchMaker.matrixCompatible(seq1, matrix)):
				break
		else:
			continue
		score, gapped0, gapped1 = MatchMaker.align(seq0, seq1,
				matrix, "nw",
				MatchMaker.defaults[MatchMaker.GAP_OPEN],
				MatchMaker.defaults[MatchMaker.GAP_EXTEND],
				ksdsspCache)
		rList0 = []
		rList1 = []
		for pos in range(len(gapped0)):
			i0 = gapped0.gapped2ungapped(pos)
			if i0 is None:
				continue
			r0 = gapped0.residues[i0]
			if r0 is None:
				continue
			i1 = gapped1.gapped2ungapped(pos)
			if i1 is None:
				unusedResidues.append(r0)
				continue
			r1 = gapped1.residues[i1]
			if r1 is None:
				unusedResidues.append(r0)
				continue
			if not shareAtoms(r0, r1, atomMap, unusedAtoms):
				unusedResidues.append(r0)
				continue
			rList0.append(r0)
			rList1.append(r1)
			matched += 1
		if rList0:
			parts.append((rList0, rList1))

	#
	# Split each part on hinges and collate results
	#
	segments = []
	for rList0, rList1 in parts:
		segments.extend(segmentHingeResidues(rList0, rList1, fraction))

	#
	# Identify any residues that were not in sequences but have
	# similar connectivity (e.g., metals and ligands) and share
	# some common atoms
	#
	segmentMap = dict()
	residueMap = dict()
	for sIndex, s in enumerate(segments):
		for r0, r1 in zip(s[0], s[1]):
			residueMap[r1] = r0
			segmentMap[r0] = sIndex
	used = set()
	for seq0 in m0seqs:
		used.update(seq0.residues)
	m0candidates = [ r0 for r0 in m0.residues if r0 not in used ]
	keyMap = dict()
	for r0 in m0candidates:
		neighbors = _getConnectedResidues(r0)
		if not neighbors:
			continue
		nlist = list(neighbors)
		nlist.sort()
		keyMap[tuple(nlist)] = r0
	used = set()
	for seq1 in m1seqs:
		used.update(seq1.residues)
	m1candidates = [ r1 for r1 in m1.residues if r1 not in used ]
	for r1 in m1candidates:
		neighbors = _getConnectedResidues(r1)
		if not neighbors:
			continue
		try:
			nlist = [ residueMap[r] for r in neighbors ]
		except KeyError:
			pass
		else:
			nlist.sort()
			key = tuple(nlist)
			try:
				r0 = keyMap[key]
				sIndex = segmentMap[nlist[0]]
			except KeyError:
				pass
			else:
				if shareAtoms(r0, r1, atomMap, unusedAtoms):
					s0, s1 = segments[sIndex]
					segments[sIndex] = (s0 + (r0,),
								s1 + (r1,))
					unusedResidues.remove(r0)
					matched += 1

	#
	# Finally, finished
	#
	print "Matched %d residues in %d segments" % (matched, len(segments))
	return segments, atomMap, unusedResidues, unusedAtoms

def segmentHingeResidues(rList0, rList1, fraction):
	#
	# Find matching set of residues
	#
	segments = segmentSieve(rList0, rList1, fraction)

	#
	# Find hinges and split molecules at hinge residues
	# The Interpolate module wants a set of segments
	# which are 2-tuples.  Each element of the 2-tuple
	# is a tuple of residues.
	#
	from Hinge import findHinges, splitOnHinges
	hingeIndices = findHinges(rList0, rList1, segments)
	segmentsStart = [ tuple(l)
			for l in splitOnHinges(hingeIndices, rList0) ]
	segmentsEnd = [ tuple(l)
			for l in splitOnHinges(hingeIndices, rList1) ]
	segments = zip(segmentsStart, segmentsEnd)
	return segments

def shareAtoms(r0, r1, atomMap, unusedAtoms):
	# We start by finding the atom connected to the
	# previous residue.  Failing that, we want the
	# atom connected to the next residue.  Failing that,
	# we take an arbitrary atom.
	from util import residuePrimaryAtoms
	m0 = r0.molecule
	before = m0.residueBefore(r0)
	after = m0.residueAfter(r0)
	r0PrimaryAtoms = residuePrimaryAtoms(r0)
	startAtom = None
	for a0 in r0PrimaryAtoms:
		if startAtom is None:
			startAtom = a0
		for na in a0.primaryNeighbors():
			if na.residue is before:
				startAtom = a0
				break
			elif na.residue is after:
				startAtom = a0
	# From this starting atom, we do a breadth-first
	# search for an atom with a matching atom name in r1
	matched = {}
	visited = set()
	todo = [ startAtom ]
	paired = set()
	expand = []
	from util import findPrimaryAtom
	while todo:
		a0 = todo.pop(0)
		a1 = findPrimaryAtom(r1, a0.name)
		if a1 is None:
			# No match, so we put all our neighboring
			# atoms on the search list
			for na in a0.primaryNeighbors():
				if (na not in visited
				and na.residue is a0.residue):
					todo.append(na)
			visited.add(a0)
		else:
			# Found a starter atom pair
			matched[a0] = a1
			expand.append((a0, a1))
			break
	while expand:
		a0, a1 = expand.pop(0)
		if a0 in visited:
			continue
		visited.add(a0)
		# a0 and a1 are matched, now we want to see
		# if any of their neighbors match
		for na0 in a0.primaryNeighbors():
			if na0 in visited or na0.residue is not a0.residue:
				continue
			for na1 in a1.primaryNeighbors():
				if na1 in paired or na1.name != na0.name:
					continue
				matched[na0] = na1
				expand.append((na0, na1))
				paired.add(na1)
				break
	# Now we look at our results
	if not matched:
		# Note that we do not update unusedAtoms since
		# the residues do not match and will be deleted
		# as a whole.
		return False

	# Next we check for atoms we have not visited and see if
	# we can pair them
	for a0 in r0PrimaryAtoms:
		if a0 in visited:
			continue
		a1 = findPrimaryAtom(r1, a0.name)
		if a1 is not None and a1 not in paired:
			matched[a0] = a1
			paired.add(a1)

	atomMap.update(matched)
	unmatched = [ a0 for a0 in r0PrimaryAtoms if a0 not in matched ]
	unusedAtoms.extend(unmatched)
	return True

def _getConnectedResidues(r):
	neighborResidues = set()
	for a in r.atoms:
		for na in a.neighbors:
			if na.residue is not r:
				neighborResidues.add(na.residue)
		for pb in a.pseudoBonds:
			na = pb.otherAtom(a)
			if na.residue is not r:
				neighborResidues.add(na.residue)
	return neighborResidues

if __name__ == "chimeraOpenSandbox":
	import chimera
	#m0, m1 = chimera.openModels.open("testdata/1dmo.pdb")
	m0 = chimera.openModels.open("testdata/4cln-processed.pdb")[0]
	m1 = chimera.openModels.open("testdata/2bbm-matched.pdb")[0]
	segments = segmentSieve(m0.residues, m1.residues)
	print len(segments), "cores"
	for segment in segments:
		print "Core:", len(segment[0]), "residues"
