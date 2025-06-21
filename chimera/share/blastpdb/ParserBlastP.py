_GapChars = "-. "

import re
REPdbId = re.compile(r"\S*pdb\|(?P<id>\w{4})\|(?P<chain>\w*)\s*(?P<desc>.*)")

class Parser:
	"""Parser for XML output from blastp (tested against
	version 2.2.29+."""

	def __init__(self, trueName, params, output, fromPsiblast=False):
		# Bookkeeping data
		self.trueName = trueName
		self.matches = []
		self.matchDict = {}
		self._gapCount = None

		# Data from results
		self.database = None
		self.query = None
		self.queryLength = None
		self.reference = None
		self.version = None

		self.gapExistence = None
		self.gapExtension = None
		self.matrix = None

		self.dbSizeSequences = None
		self.dbSizeLetters = None

		# Extract information from results
		#import xml.etree.ElementTree as ET
		#tree = ET.fromstring(output)
		#if tree.tag != "BlastOutput":
		#	raise ValueError("Text is not BLAST XML output")
		#self._extractRoot(tree)
		try:
			outputs = output["BlastOutput2"]
		except (KeyError, IndexError):
			raise ValueError("Output is not BLAST JSON output")
		if len(outputs) != 1:
			raise ValueError("Unexpected number of items in blast output (%d)" % len(outputs))
		report = outputs[0]["report"]
		#e = tree.find("./BlastOutput_param/Parameters")
		e = report.get("params", None)
		if e is not None:
			self._extractParams(e)
		self._extractRoot(report)
		#el = tree.findall("BlastOutput_iterations/Iteration")
		#if len(el) > 1:
		#	raise ValueError("Multi-iteration BLAST output unsupported")
		#elif len(el) == 0:
		#	raise ValueError("No iteration data in BLAST OUTPUT")
		#iteration = el[0]
		#for he in iteration.findall("./Iteration_hits/Hit"):
		#	self._extractHit(he)
		search = report["results"]["search"]
		for he in search["hits"]:
			self._extractHit(he)
		#self._extractStats(iteration.find("./Iteration_stat/Statistics"))
		self._extractStats(search["stat"])

		# Insert the query as match[0]
		seq = params[0]
		m = Match(self.trueName, None, "user_input",
				0.0, 0.0, 1, len(seq), seq, seq) #SH
		self.matches.insert(0, m)
		self.matchDict[self.query] = m

		# Go back and fix up hit sequences so that they all align
		# with the query sequence
		self._alignSequences()

	def _text(self, parent, tag):
		e = parent.find(tag)
		return e is not None and e.text.strip() or None

	def _extractRoot(self, re):
		#self.database = self._text(oe, "BlastOutput_db")
		self.database = re["search_target"]["db"]
		#self.query = self._text(oe, "BlastOutput_query-ID")
		self.query = re["results"]["search"]["query_id"]
		#self.queryLength = int(self._text(oe, "BlastOutput_query-len"))
		self.queryLength = re["results"]["search"]["query_len"]
		self._gapCount = [ 0 ] * self.queryLength
		#self.reference = self._text(oe, "BlastOutput_reference")
		self.reference = re["reference"]
		#self.version = self._text(oe, "BlastOutput_version")
		self.version = re["version"]

	def _extractParams(self, pe):
		#self.gapExistence = self._text(pe, "Parameters_gap-open")
		#self.gapExtension = self._text(pe, "Parameters_gap-extend")
		#self.matrix = self._text(pe, "Parameters_matrix")
		self.gapExistence = pe.get("gap_open", None)
		self.gapExtension = pe.get("gap_extend", None)
		self.matrix = pe.get("matrix", None)

	def _extractStats(self, se):
		#self.dbSizeSequences = self._text(se, "Statistics_db-num")
		#self.dbSizeLetters = self._text(se, "Statistics_db-len")
		self.dbSizeSequences = se.get("dn_num", None)
		self.dbSizeLetters = se.get("db_len", None)

	def _extractHit(self, he):
		#hid = self._text(he, "Hit_id")
		hid = he["description"][0]["id"]
		m = REPdbId.match(hid)
		if m:
			# PDB hit, create list of PDB hits
			idList = []
			#for defline in (hid + ' ' + self._text(he, "Hit_def")).split(">"):
			for defline in he["description"]:
				m = REPdbId.match(defline["id"] + ' ' + defline["title"])
				if m:
					idList.append(m.groups())
			pdbid, chain, desc = idList.pop(0)
			name = pdb = pdbid + '_' + chain if chain else pdbid
		else:
			name = hid
			pdb = None
			desc = self._text(he, "Hit_def").split(">")[0]
			# An nr hit can have many more ids on the defline, but
			# we only keep pdb ones
			idList = []
			#for defline in (hid + ' ' + self._text(he, "Hit_def")).split(">"):
			for defline in he["description"]:
				m = REPdbId.match(defline["id"] + ' ' + defline["title"])
				if m:
					idList.append(m.groups())
		mList = []
		#for hspe in he.findall("./Hit_hsps/Hsp"):
		for hspe in he["hsps"]:
			mList.append(self._extractHSP(hspe, name, pdb, desc))
		for pdbid, chain, desc in idList:
			name = pdb = pdbid + '_' + chain if chain else pdbid
			for m in mList:
				self._copyMatch(m, name, pdb, desc)

	def _extractHSP(self, hspe, name, pdb, desc):
		#score = int(float(self._text(hspe, "Hsp_bit-score"))) #SH
		score = int(hspe["bit_score"])
		#evalue = float(self._text(hspe, "Hsp_evalue"))
		evalue = hspe["evalue"]
		#qSeq = self._text(hspe, "Hsp_qseq")
		qSeq = hspe["qseq"]
		#qStart = int(self._text(hspe, "Hsp_query-from"))
		qStart = hspe["query_from"]
		#qEnd = int(self._text(hspe, "Hsp_query-to"))
		qEnd = hspe["query_to"]
		self._updateGapCounts(qSeq, qStart, qEnd)
		#hSeq = self._text(hspe, "Hsp_hseq")
		hSeq = hspe["hseq"]
		#hStart = int(self._text(hspe, "Hsp_hit-from"))
		hStart = hspe["hit_from"]
		#hEnd = int(self._text(hspe, "Hsp_hit-to"))
		hEnd = hspe["hit_to"]
		m = Match(name, pdb, desc, score, evalue, qStart, qEnd, qSeq, hSeq) #SH
		self.matches.append(m)
		self.matchDict[name] = m
		return m

	def _copyMatch(self, m, name, pdb, desc):
		nm = Match(name, pdb, desc, m.score, m.evalue,
				m.qStart + 1, m.qEnd + 1, # switch back to 1-base indexing
				m.qSeq, m.hSeq)
		self.matches.append(nm)
		self.matchDict[name] = nm

	def _updateGapCounts(self, seq, start, end):
		start -= 1	# Switch to 0-based indexing
		count = 0
		for c in seq:
			if c in _GapChars:
				count += 1
			else:
				oldCount = self._gapCount[start]
				self._gapCount[start] = max(oldCount, count)
				start += 1
				count = 0

	def _alignSequences(self):
		for m in self.matches:
			m.matchSequenceGaps(self._gapCount)

	def writeMSF(self, f, perLine=60, block=10, matches=None):
		if (matches is not None and len(matches) == 1
				and matches[0] is self.matches[0]):
			# if user selected only the query sequence,
			# we treat it as if he selected nothing at all
			matches = None
		if matches is None:
			matches = self.matches
		if self.matches[0] not in matches:
			matches.insert(0, self.matches[0])
		length = len(matches[0].sequence)
		# Assumes that all sequence lengths are equal

		f.write("Query: %s\n" % self.query)
		f.write("BLAST Version: %s\n" % self.version)
		f.write("Reference: %s\n" % self.reference)
		f.write("Database: %s\n" % self.database)
		f.write("Database size: %s sequences, %s letters\n" %
			(self.dbSizeSequences, self.dbSizeLetters))
		f.write("Matrix: %s\n" % self.matrix)
		f.write("Gap penalties: existence: %s, extension: %s\n" %
			(self.gapExistence, self.gapExtension))
		f.write("\n")
		label = {}
		for m in matches:
			label[m] = m.name
		if len(matches) > 1:
			width = max(map(lambda m: len(label[m]), matches[1:]))
			for m in matches[1:]:
				f.write("%*s %4d %g" %
					(width, label[m], m.score, m.evalue))
				if m.description:
					f.write(" %s\n" % m.description)
				else:
					f.write("\n")
		f.write("\n")

		import time
		now = time.strftime("%B %d, %Y %H:%M",
					time.localtime(time.time()))
		f.write(" %s  MSF: %d  Type: %s  %s  Check: %d ..\n\n"
				% ("BLAST", length, 'P', now , 0))

		nameWidth = max(map(lambda m: len(label[m]), matches))
		nameFmt = " Name: %-*s  Len: %5d  Check: %4d  Weight: %5.2f\n"
		for m in matches:
			f.write(nameFmt % (nameWidth, label[m], length, 0, 1.0))
		f.write("\n//\n\n")

		for i in range(0, length, perLine):
			start = i + 1
			end = start + perLine - 1
			if end > length:
				end = length
			seqLen = end - start + 1
			startLabel = str(start)
			endLabel = str(end)
			separators = (seqLen + block - 1) / block - 1
			blanks = (seqLen + separators
					- len(startLabel) - len(endLabel))
			if blanks < 0:
				f.write("%*s  %s\n" %
					(nameWidth, ' ', startLabel))
			else:
				f.write("%*s  %s%*s%s\n" %
					(nameWidth, ' ', startLabel,
					blanks, ' ', endLabel))
			for m in matches:
				f.write("%-*s " % (nameWidth, label[m]))
				for n in range(0, perLine, block):
					front = i + n
					back = front + block
					f.write(" %s" % m.sequence[front:back])
				f.write("\n")
			f.write("\n")

	def sessionData(self):
		try:
			from cPickle import dumps
		except ImportError:
			from pickle import dumps
		return dumps(self)

	def dump(self, f=None):
		if f is None:
			from sys import stderr as f
		for a in dir(self):
			if a.startswith("_"):
				continue
			attr = getattr(self, a)
			if callable(attr):
				continue
			if isinstance(attr, basestring):
				print >> f, "  %s: %s" % (a, attr)
			elif isinstance(attr, list):
				for o in attr:
					o.dump(f)
			elif attr is None:
				print >> f, "  %s: _uninitialized_" % a

def restoreParser(data):
	try:
		from cPickle import loads
	except ImportError:
		from pickle import loads
	return loads(data)

class Match:
	"""Data from a single BLAST hit."""

	def __init__(self, name, pdb, desc, score, evalue, qStart, qEnd, qSeq, hSeq): #SH
		self.name = name
		self.pdb = pdb
		self.description = desc.strip()
		self.score = score
		self.evalue = evalue
		self.qStart = qStart - 1	# switch to 0-base indexing
		self.qEnd = qEnd - 1 # switch to 0-base indexing #SH
		self.qSeq = qSeq
		self.hSeq = hSeq
		if len(qSeq) != len(hSeq):
			raise ValueError("sequence alignment length mismatch")
		self.sequence = ""
		self.fetchedValues = FetchedValues()

	def __repr__(self):
		return "<Match %s (pdb=%s)>" % (self.name, self.pdb)

	def printSequence(self, f, prefix, perLine=60):
		for i in range(0, len(self.sequence), perLine):
			f.write("%s%s\n" % (prefix, self.sequence[i:i+perLine]))

	def matchSequenceGaps(self, gapCount):
		seq = []
		# Insert gap for head of query sequence that did not match
		for i in range(self.qStart):
			seq.append('.' * (gapCount[i] + 1))
		start = self.qStart
		count = 0
		# Add all the sequence data from this HSP
		for i in range(len(self.qSeq)):
			if self.qSeq[i] in _GapChars:
				# If this is a gap in the query sequence,
				# then the hit sequence must be an insertion.
				# Add the insertion to the final sequence
				# and increment number of gaps we have added
				# thus far.
				seq.append(self.hSeq[i])
				count += 1
			else:
				# If this is not a gap, then we have to make
				# sure that we have inserted enough gaps for
				# the longest insertion by any sequence (as
				# computed in "gapCount").  Then we add the
				# hit sequence character that matches this
				# query sequence character, and increment
				# out query sequence index ("start").
				if count > gapCount[start]:
					print "start", start
					print "count", count, ">", gapCount[start]
					raise ValueError("cannot align sequences")
				if count < gapCount[start]:
					seq.append('-' * (gapCount[start] - count))
				seq.append(self.hSeq[i])
				count = 0
				start += 1
		# Append gap for tail of query sequence that did not match
		while start < len(gapCount):
			seq.append('.' * (gapCount[start] + 1))
			start += 1
		self.sequence = ''.join(seq)

	def dump(self, f):
		print >> f, self
		self.printSequence(f, '')

class FetchedValues:
	pass

class BlastpService:

	ServiceName = "blast"
	OutputFile = "blast.out"

	def __init__(self, finishCB, params=None, sessionData=None,
			failCB=None, cancelCB=None):
		self.finishCB = finishCB
		self.failCB, self.cancelCB = failCB, cancelCB
		if params is not None:
			self._initBlast(*params)
		else:
			self._initSession(*sessionData)

	def makeArgList(self, db, name, outputFile, evalue, matrix, querySeq):
		return "-d %s -i %s -o %s -e %s -M %s -seq %s" % (
				db, name, outputFile, evalue, matrix, querySeq.replace(' ', '-'))

	def _initBlast(self, program, db, queryName, querySeq,
			evalue, matrix, passes):
		self.program = "blastp"		# "program" is an anachronism
		self.db = db
		self.queryName = queryName
		self.params = (querySeq, evalue, matrix, passes)
		#from WebServices.opal_client import makeInputFileWithContents
		#name = "query.fa"
		#inputFile = makeInputFileWithContents(name, self.makeFasta(queryName, querySeq))
		argList = self.makeArgList(db, queryName, self.OutputFile, evalue, matrix, querySeq)
		#from WebServices.opal_client import OpalService
		from WebServices.cx_client import CxService
		try:
			#self.opal = OpalService(self.ServiceName)
			self.cx = CxService(self.ServiceName)
		except:
			import traceback, sys
			print "Traceback from Blastp request:"
			traceback.print_exc(file=sys.stdout)
			print """
Typically, if you get a TypeError, it's a problem on the remote server
and it should be fixed shortly.  If you get a different error or
get TypeError consistently for more than a day, please report the
problem using the Report a Bug... entry in the Help menu.  Please
include the traceback printed above as part of the problem description."""
			from chimera import NonChimeraError
			raise NonChimeraError("Blast web service appears "
						"to be down.  See Reply Log "
						"for more details.")
		#self.opal.launchJob(argList, _inputFile=[inputFile])
		self.cx.launchJob(argList, _inputFile=[])
		from chimera.tasks import Task
		self.task = Task(self._title(), self._cancelCB, self._statusCB)

	def _initSession(self, program, db, queryName,
				params, running, jobData,
				startTime=None):
		self.program = program
		self.db = db
		self.queryName = queryName
		self.params = params
		#from WebServices.opal_client import OpalService
		#self.opal = OpalService(sessionData=opalData)
		from WebServices.cx_client import CxService
		self.cx = CxService(self.ServiceName, sessionData=jobData)
		if not running:
			self.task = None
		else:
			from chimera.tasks import Task
			self.task = Task(self._title(), self._cancelCB, self._statusCB)
			if startTime:
				self.task.setStartTime(startTime)

	def _title(self):
		return "%s %s: %s" % (self.program, self.db, self.queryName)

	def sessionData(self):
		if self.task:
			# Use int so that sesRepr keeps the exact value
			startTime = int(self.task.getStartTime())
		else:
			startTime = None
		return (self.program, self.db, self.queryName, self.params,
				self.task is not None,
				self.cx.sessionData(),
				startTime)

	def _cancelCB(self):
		self.task.finished()
		self.task = None
		if self.cancelCB:
			self.cancelCB()

	def _statusCB(self):
		self.task.updateStatus(self.cx.currentStatus())
		if not self.cx.isFinished():
			self.cx.queryStatus()
			return
		self.cx.getJobStatistics()
		if self.cx.times[0]:
			self.task.setStartTime(self.cx.times[0])
		if self.cx.times[1]:
			self.task.setEndTime(self.cx.times[1])
		self.task.finished()
		self.task = None
		#fileMap = self.cx.getOutputs()
		if self.cx.isFinished() > 0:
			# Successful completion
			#output = self.getURLContent(fileMap[self.OutputFile])
			#self.finishCB(self.params, output)
			self.finishCB(self.params, self.cx.get_results())
		else:
			# Failed
			from chimera import replyobj
			replyobj.error("blast %s failed; "
					"see Reply Log for more information\n"
					% self.queryName)
			#self.showURLContent("blast stderr", fileMap["stderr.txt"])
			#self.showURLContent("blast stdout", fileMap["stdout.txt"])
			self.showURLContent("blast stderr", self.cx.get_stderr())
			self.showURLContent("blast stdout", self.cx.get_stdout())
			if self.failCB:
				self.failCB()

	def makeFasta(self, name, seq):
		output = [ ">QUERY\n" ]
		maxLine = 60
		for i in range(0, len(seq), maxLine):
			end = min(i + maxLine, len(seq))
			output.append("%s\n" % seq[i:end])
		return ''.join(output)

	def getURLContent(self, url):
		import urllib2
		f = urllib2.urlopen(url)
		data = f.read()
		f.close()
		return data

	def showURLContent(self, title, url):
		from chimera import replyobj
		#data = self.getURLContent(url)
		data = url
		replyobj.message("%s\n-----\n%s-----\n" % (title, data))

if __name__ == "__main__":
	with open("testdata/query.fa") as f:
	    f.readline()    # skip defline
	    seq = f.read().replace('\n', '')
	params = (seq,)

	with open("testdata/out.nrpreformatted") as f:
	    data = f.read()
	from ParserBlastP import Parser
	p = Parser("query", params, data, False)
	import sys
	p.writeMSF(sys.stdout)

	with open("testdata/out.nrfasta") as f:
	    data = f.read()
	from ParserBlastP import Parser
	p = Parser("query", params, data, False)
	import sys
	p.writeMSF(sys.stdout)
