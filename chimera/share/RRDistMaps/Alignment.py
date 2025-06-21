# --- UCSF Chimera Copyright ---
# Copyright (c) 2014 Regents of the University of California.
# All rights reserved. This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use. This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

class Alignment:
	def __init__(self, ui, seqs, info, nw):
		"""Alignment Object for Needleman-Wunsch and MUSCLE output

		MUSCLE:
			seqs - list of aligned Sequence instances
			info - list of maps from indices to residues
		NW:
			seqs - list of StructureSequence instances
			info - list of indices for matching residues
		nw: bool, NW y/n
		"""

		# Main attributes: resListList - holds the aligned residues
		# coordListList - holds the aligned coordinates
		if nw:
			self.resListList = self._nwConvert(ui, seqs, info)
		else:
			self.resListList = self._muscConvert(ui, seqs, info)
		self.coordListList = self._coordAcquire(ui, self.resListList)

	def _muscConvert(self, ui, sequences, mapList):
		"""Turn MUSCLE output into a list of lists of residues"""
		# Compute a set of n-tuples of columns where no
		# sequence has a gap and corresponding residues have
		# atomic coordinates
		numSeq = len(sequences)
		numCol = len(sequences[0])
		counters = [ 0 ] * numSeq
		resListList = [ [] for s in sequences ]
		for col in range(numCol):
			indexList = []
			for n in range(numSeq):
				if sequences[n][col] == '-':
					# Gap character, skip
					continue
				else:
					# Non-gap, store residue index
					# and advance
					indexList.append(counters[n])
					counters[n] += 1
			if len(indexList) < numSeq:
				# This column has gaps, skip
				continue
			residues = []
			for n, m in enumerate(mapList):
				try:
					r = m[indexList[n]]
					a = ui._atomOf(r)
				except (AttributeError, KeyError):
					break
				residues.append(r)
			else:
				for n, r in enumerate(residues):
					resListList[n].append(r)
		return resListList

	def _nwConvert(self, ui, seqs, matchList):
		"""For NW - Remove sets of residues aligned to gaps.
		Return a list of list of residues (no None's)"""

		matchCount = len(matchList)
		resListList = [ [], [] ]
		for indexPair in sorted(matchList):
			resList = []
			for i in range(2):
				ri = indexPair[i]
				try:
					r = seqs[i].residues[ri]
					a = ui._atomOf(r)
				except (AttributeError, KeyError):
					break
				else:
					resList.append(r)
			else:
				for i in range(2):
					resListList[i].append(resList[i])
		return resListList

	def _coordAcquire(self, ui, resListList):
		"""Given list of list of residues,
		return list of list of coordinates"""

		# Loop through list, create new list with coordinates
		coordListList = []
		for l in resListList:
			coordList = [ ui._coordOf(r) for r in l ]
			coordListList.append(coordList)
		return coordListList

	def statsMessage(self):
		return "Aligned %d residues" % len(self.resListList[0])
