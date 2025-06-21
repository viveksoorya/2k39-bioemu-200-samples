# --- UCSF Chimera Copyright ---
# Copyright (c) 2014 Regents of the University of California.
# All rights reserved. This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use. This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

class RunAlignWS:
	def __init__(self, startCB, cancelCB, finishCB, seqs=None):
		self.cancelCB = cancelCB
		self.finishCB = finishCB

		from chimera import replyobj

		# Tag sequences so they can be tracked
		# if MUSCLE swaps sequence order
		n = 0
		self.nameOrder = []
		for s in seqs:
			name = "input%d" % n
			n += 1
			self.nameOrder.append((name, s.name))
			s.name = name

		# Set up FASTA File
		realignKw = {'cleanupCB' : self._cancelOrDone}
		from MultAlignViewer.formatters.saveFASTA import save
		from OpenSave import osTemporaryFile, osOpen
		inFasta = osTemporaryFile(suffix='.fa')
		names = []
		f = open(inFasta, 'w')
		save(f, None, seqs, None)
		f.close()

		# Restore sequence names
		for i, s in enumerate(seqs):
			s.name = self.nameOrder[i][1]

		# Create WS instance, prepare to call MUSCLE
		params = ("MuscleService",
				'Alignment of %d sequences' % len(seqs),
				{'input.fa': inFasta},
				'-in input.fa -out output.fa')
		from WebServices.appWebService import AppWebService
		self.ws = AppWebService(self._wsFinish, params=params,
					cleanupCB=self._cancelOrDone)
		if startCB:
			startCB(self.ws)

	def _cancelOrDone(self, backend, completed, success):
		if self.cancelCB and not completed and not success:
			self.cancelCB(self.ws)

	def _wsFinish(self, opal, fileMap):
		output = opal.getFileContent('output.fa')
		if output is None:
			from chimera import NonChimeraError
			raise NonChimeraError("alignment web service failed")

		# Save file with MUSCLE names so we can read it in
		from OpenSave import osTemporaryFile
		outputFa = osTemporaryFile(suffix='.fa')
		self.ws.file = outputFa
		f = open(outputFa, 'w')
		f.write(output)
		f.close()
		from MultAlignViewer.parsers import readFASTA
		seqs = readFASTA.parse(outputFa)[0]

		# Reorder the sequences by their tagged names
		# Preserve original order
		seqMap = dict([ (s.name, s) for s in seqs ])
		results = []
		for name, fullName in self.nameOrder:
			s = seqMap[name]
			s.name = fullName
			results.append(s)

		# Resave FASTA file with fixed up sequence names
		from MultAlignViewer.formatters.saveFASTA import save
		f = open(outputFa, 'w')
		save(f, None, results, None)
		f.close()

		# Call finish callback
		if self.finishCB:
			self.finishCB(self.ws, results)

# R. C. Edgar
# MUSCLE: multiple sequence alignment with high accuracy and high throughput.
# Nucl. Acids Res. 32 (5), 1792-1797, 2004.
# Publications using MUSCLE results should cite https://www.ncbi.nlm.nih.gov/pubmed/15034147
