# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

PRINCIPAL = "principal chain"
CHAIN_FMT = "chain %s"

clustalStrongGroups = ["STA", "NEQK", "NHQK", "NDEQ", "QHRK",
						"MILV", "MILF", "HY", "FYW"]
clustalWeakGroups = ["CSA", "ATV", "SAG", "STNK", "STPA", "SGND",
				"SNDEQK", "NDEQHK", "NEQHRK", "FVLIM", "HFY"]

defHelixColor = "goldenrod"
defStrandColor = "lime green"

# this is imported by chimera.__init__, so minimize global imports
import string

class Sequence(object):
	"""
	Sequence is a single sequence

	internally a list of characters (available in the 'sequence' attribute)
	external interface as a string
	"""

	_name = "sequence"

	SS_HELIX = 'H'
	SS_OTHER = 'O'
	SS_STRAND = 'S'

	TRIG_RENAME = "rename"

	def __init__(self, name=None):
		self.sequence = []
		if name is not None:
			self._name = name
		self.attrs = {} # miscellaneous attributes
		self.markups = {} # per-residue (strings or lists)
		self.numberingStart = None
		self._cache = {}
		from chimera.triggerSet import TriggerSet
		self.triggers = TriggerSet()
		self.triggers.addTrigger(self.TRIG_RENAME)

	def append(self, item):
		self._cache = {}
		try:
			itemList = list(item)
		except TypeError:
			itemList = [item]
		self.sequence.extend(itemList)

	def __copy__(self, copySeq=None):
		from copy import copy
		if copySeq is None:
			copySeq = Sequence(self.name)
		copySeq.attrs = copy(self.attrs)
		copySeq.markups = copy(self.markups)
		copySeq.sequence = copy(self.sequence)
		copySeq.numberingStart = self.numberingStart
		return copySeq

	def __del__(self):
		if hasattr(self, '_removeHandlerID'):
			try:
				from chimera import openModels
			except ImportError:
				return
			openModels.deleteRemoveHandler(self._removeHandlerID)

	def __delitem__(self, key):
		self._cache = {}
		del self.sequence[key]

	def __delslice__(self, i, j):
		self._cache = {}
		del self.sequence[i:j]

	extend = append

	def fullName(self):
		return self.name

	def gapped2ungapped(self, index):
		try:
			g2u = self._cache["g2u"]
		except KeyError:
			self.ungapped()
			g2u = self._cache["g2u"]
		try:
			return g2u[index]
		except KeyError:
			return None

	def __getitem__(self, key):
		return self.sequence[key]

	def __getslice__(self, i, j):
		return "".join(self.sequence[i:j])

	def __hash__(self):
		return id(self)

	def inGap(self, pos):
		return not self.sequence[pos].isalpha()
	isGap = inGap

	def insert(self, pos, insertion):
		self._cache = {}
		self.sequence.insert(pos, insertion)

	def __len__(self):
		return len(self.sequence)
	
	def _getName(self):
		return self._name

	def _setName(self, name):
		if name == self._name:
			return
		oldName = self._name
		self._name = name
		self.triggers.activateTrigger(self.TRIG_RENAME, (self, oldName))

	name = property(_getName, _setName)

	def patternMatch(self, expr):
		"""expr is a pattern compiled with re.compile()"""
		matches = []
		target = self.ungapped()
		startPos = 0
		while startPos < len(target):
			match = expr.search(target, startPos)
			if not match:
				break
			matches.append([self.ungapped2gapped(i)
				for i in [match.start(), match.end()-1]])
			startPos = match.start() + 1
		return matches

	def regexMatch(self, regex):
		"""regex is regular expression compilable with re.compile()"""
		import re
		return self.patternMatch(re.compile(regex))

	def prositeMatch(self, pattern):
		"""PROSITE matching

		   Return a list of start/end tuple for matches to the
		   given PROSITE pattern (see http://us.expasy.org/tools/
		   scanprosite/scanprosite-doc.html)
		"""
		if len(pattern) > 1 and pattern[0] in string.ascii_uppercase \
		and pattern[1] in string.ascii_uppercase and '-' not in pattern:
			pattern = '-'.join(pattern)
		elements = pattern.split('-')
		if not elements:
			return []

		elements = [e.strip() for e in elements]
		try:
			target = self._cache["prositeTarget"]
		except KeyError:
			target = self.ungapped().upper()
			self._cache["prositeTarget"] = target

		matches = []
		for start in range(len(target)):
			matches.extend(self._prositeMatch(target, elements,
								start))
		# due to ranges, there may be multiple different matches 
		# to the exact same characters, so eliminate duplicates
		# while remapping indices into gapped sequence...
		gapped = {}
		for start, end in matches:
			gapped[(self.ungapped2gapped(start),
				self.ungapped2gapped(end))] = 1
		return gapped.keys()

	def _prositeMatch(self, target, elements, start):
		from chimera import UserError
		try:
			partials = self._prositeMatchElement(target,
							elements[0], start)
		except _PrositePatternError:
			raise UserError("Unrecognized PROSITE pattern element:"
							" %s" % elements[0])
		if partials is None:
			return []
		tailElements = elements[1:]
		matches = []
		for end in partials:
			# handle the rare case of '>' inside brackets...
			if (end == len(target)-1 
			and len(tailElements) == 1 
			and tailElements[0][0] == '['
			and tailElements[0][-1] == ']'
			and '>' in tailElements[0]) or not tailElements:
				matches.append((start, end))
			else:
				if end >= len(target)-1:
					continue
				tailMatches = self._prositeMatch(target,
							tailElements, end+1)
				if not tailMatches:
					continue
				matches.extend([ (start, tEnd)
					for tStart, tEnd in tailMatches])
		return matches
				
	def _prositeMatchElement(self, target, element, start):
		if element and element[0] == '<':
			if start > 0:
				return None
			element = element[1:]
		if not element:
			from chimera import UserError
			raise UserError(
			     "Element of PROSITE pattern is empty or lone '<'")
		try:
			simple, minTimes, maxTimes = self._prositeParseRange(
									element)
		except ValueError:
			simple = element
			minTimes = maxTimes = 1

		return self._prositeMatchRange(target, simple, start,
							minTimes, maxTimes)

	def _prositeParseRange(self, element):
		lp = element.rindex('(')
		try:
			comma = element.rindex(',')
		except ValueError:
			comma = None
		rp = element.rindex(')')
		if lp == 0:
			raise ValueError, "No element to repeat"
		if comma is None:
			if not lp < rp:
				raise ValueError, "Range elements disordered"
			minTimes = maxTimes = int(element[lp+1:rp])
		else:
			if not lp < comma < rp:
				raise ValueError, "Range elements disordered"
			minTimes = int(element[lp+1:comma])
			maxTimes = int(element[comma+1:rp])
			if minTimes > maxTimes:
				raise ValueError, \
				   "Minimum range greater than maximum range"
		return element[:lp], minTimes, maxTimes

	def _prositeMatchRange(self, target, element, start,
							minTimes, maxTimes):
		for i in range(minTimes):
			if start+i >= len(target):
				return None
			if not self._prositeMatchSimple(target, element,
								start+i):
				return None

		matches = [start+minTimes-1]

		for i in range(minTimes, maxTimes):
			if start+i >= len(target):
				break
			if not self._prositeMatchSimple(target, element,
								start+i):
				break
			matches.append(start+i)
		return matches

	def _prositeMatchSimple(self, target, element, pos):
		char = target[pos]
		if len(element) == 1:
			if element == 'x' or element == char:
				return [(pos, pos)]
			return None
				
		if element[0] == '[' and element[-1] == ']':
			for matchable in element[1:-1]:
				if matchable == char:
					return [(pos, pos)]
			return None
		if element[0] == '{' and element[-1] == '}':
			for avoid in element[1:-1]:
				if avoid == char:
					return None
			return [(pos, pos)]
				
		raise _PrositePatternError

	def saveInfo(self):
		"""info that can be used with restoreSequence()"""
		saveInfo = {
			'name': self.name,
			'sequence': self.sequence,
			'attrs': self.attrs,
			'markups': self.markups,
			'numberingStart': self.numberingStart
		}
		if hasattr(self, 'circular'):
			saveInfo['circular'] = self.circular
		return saveInfo

	def __setitem__(self, key, val):
		self._cache = {}
		self.sequence[key] = val

	def __setslice__(self, i, j, seq):
		self._cache = {}
		self.sequence[i:j] = list(seq)

	def ssType(self, loc, locIsUngapped=False):
		try:
			ssMarkup = self.markups['SS']
		except KeyError:
			return None
		if not locIsUngapped:
			loc = self.gapped2ungapped(loc)
		if loc is None:
			return None
		ss = ssMarkup[loc]
		if ss in "HGI":
			return self.SS_HELIX
		if ss == "E":
			return self.SS_STRAND
		return self.SS_OTHER

	def __str__(self):
		try:
			return "".join(self.sequence)
		except TypeError:
			return "non-ASCII sequence (%s)" % self.name

	def ungapped(self, _raw=False):
		try:
			return self._cache["ungapped"]
		except KeyError:
			pass
		self._cache["ungapped"] = "".join([c for c in self.sequence
							if c.isalpha() or c == '?'])
		if _raw:
			return self._cache["ungapped"]
		uI = 0
		g2u = {}
		u2g = {}
		seq = self.sequence
		for i, char in enumerate(seq):
			if char.isalpha() or char == '?':
				g2u[i] = uI
				u2g[uI] = i
				uI += 1
		self._cache["g2u"] = g2u
		self._cache["u2g"] = u2g
				
		return self._cache["ungapped"]

	def ungapped2gapped(self, index):
		try:
			return self._cache["u2g"][index]
		except KeyError:
			self.ungapped()
			return self._cache["u2g"][index]

class StructureSequence(Sequence):
	"""
	Sequence of a structure chain (subclass of Sequence)
	"""

	TRIG_DELETE = "delete"
	TRIG_MODIFY = "modify"

	def __init__(self, molecule, *args, **kw):
		Sequence.__init__(self, *args, **kw)
		self.residues = []
		self.resMap = {}
		self.molecule = molecule
		# allow numberingStart to be dynamic
		self._numberingStart = self.numberingStart
		delattr(self, 'numberingStart')
		self.descriptiveName = None

		# since bound methods are "first class" objects, using
		# proxies to them doesn't work as you would expect
		# (the proxy immediately becomes invalid), so...
		from chimera import triggers, update, triggerSet
		from weakref import proxy
		def wrapper1(a1, a2, a3, s=proxy(self)):
			s._delMoleculeCB(a1, a2, a3)
		self._removeHandlerID = triggers.addHandler("Molecule",
					wrapper1, None)
		def wrapper2(a1, a2, a3, s=proxy(self)):
			s._residueCB(a1, a2, a3)
		if update.inTriggerProcessing:
			# avoid handling expensive and redundant pending
			# Residue trigger callback
			def mcCB(*args):
				self._residueHandlerID = triggers.addHandler("Residue",
					wrapper2, None)
				return triggerSet.ONESHOT
			self._delayedResHandlerID = triggers.addHandler(
				"monitor changes", mcCB, None)
		else:
			self._residueHandlerID = triggers.addHandler("Residue",
					wrapper2, None)
		self.triggers.addTrigger(self.TRIG_DELETE)
		self.triggers.addTrigger(self.TRIG_MODIFY)

	def __getattr__(self, attrName):
		if attrName == 'numberingStart':
			if self._numberingStart == None:
				for i, r in enumerate(self.residues):
					if r is None:
						continue
					if r.__destroyed__:
						return getattr(self, '_prevNumberingStart', 1)
					break
				else:
					return getattr(self, '_prevNumberingStart', 1)
				pns = self._prevNumberingStart = r.id.position - i
				return pns
			return self._numberingStart
		if attrName == 'chainID':
			ids = set([r.id.chainId for r in self.residues if r])
			if len(ids) == 1:
				return ids.pop()
			if len(ids) == 0:
				raise ValueError("No residues in chain")
			raise ValueError("Multiple chain IDs in chain")
		raise AttributeError("%s instance has no attribute '%s'"
				% (self.__class__.__name__, attrName))

	def append(self, item):
		try:
			itemList = list(item)
		except TypeError:
			itemList = [item]
		if itemList and isinstance(itemList[0], basestring):
			return Sequence.extend(self, itemList)
		base = len(self.residues)
		for i, res in enumerate(itemList):
			self.resMap[res] = base + i
		self.residues.extend(itemList)
		from resCode import res3to1
		Sequence.extend(self, [res3to1(r.type) for r in itemList])

	def _bestUngapped(self, i):
		end = len(self)
		while i < end:
			un = self.gapped2ungapped(i)
			if un is not None:
				return un
			i += 1
		return end

	def _cleanup(self):
		if not hasattr(self, 'molecule'):
			return
		# invalidate first since TRIG_DELETE will remove
		# sequence from _SequenceSequences
		if not self.molecule.__destroyed__ \
		and hasattr(self.molecule, '_SequenceSequences') \
		and self in self.molecule._SequenceSequences[0]: # not a copy
			invalidate(self.molecule)
		self.triggers.activateTrigger(self.TRIG_DELETE, self)
		delattr(self, 'molecule')
		delattr(self, 'residues')
		delattr(self, 'resMap')
		from chimera import triggers
		triggers.deleteHandler("Molecule", self._removeHandlerID)
		delattr(self, '_removeHandlerID')
		if hasattr(self, '_residueHandlerID'):
			triggers.deleteHandler("Residue", self._residueHandlerID)
			delattr(self, '_residueHandlerID')
		else:
			triggers.deleteHandler("monitor changes", self._delayedResHandlerID)

	def __copy__(self, copySeq=None):
		from copy import copy
		if copySeq is None:
			copySeq = StructureSequence(self.molecule, self.name)
		copySeq = Sequence.__copy__(self, copySeq=copySeq)
		copySeq._numberingStart = self._numberingStart
		delattr(copySeq, 'numberingStart')
		copySeq.residues.extend(self.residues)
		copySeq.resMap.update(self.resMap)
		if hasattr(self, 'circular'):
			copySeq.circular = self.circular
		copySeq.fromSeqres = self.fromSeqres
		copySeq.descriptiveName = self.descriptiveName
		if hasattr(self, 'residueSequence'):
			copySeq.residueSequence = self.residueSequence
		return copySeq

	def __del__(self):
		try:
			from chimera import openModels, triggers
		except ImportError:
			return
		self.destroy()

	def __delitem__(self, key):
		ungappedKey = self.gapped2ungapped(key)
		if ungappedKey is not None:
			res = self.residues[ungappedKey]
			del self.residues[ungappedKey]
			if res:
				del self.resMap[res]
			for res, i in self.resMap.items():
				if i > ungappedKey:
					self.resMap[res] = i-1
		Sequence.__delitem__(self, key)
		self.triggers.activateTrigger(self.TRIG_MODIFY, self)

	def _delMoleculeCB(self, trigName, myData, trigData):
		if self.molecule in trigData.deleted:
			self.demoteToSequence()

	def __delslice__(self, i, j):
		ungappedI = self._bestUngapped(i)
		ungappedJ = self._bestUngapped(j)
		for res in self.residues[ungappedI:ungappedJ]:
			if res:
				del self.resMap[res]
		del self.residues[ungappedI:ungappedJ]
		for res, k in self.resMap.items():
			if k >= j:
				self.resMap[res] = k - (j-i)
		Sequence.__delslice__(self, i, j)
		self.triggers.activateTrigger(self.TRIG_MODIFY, self)

	def demoteToSequence(self):
		numberingStart = self.numberingStart
		self._cleanup()
		self.__class__ = Sequence
		self.numberingStart = numberingStart

	def destroy(self):
		self._cleanup()

	extend = append

	def _getFromSeqres(self):
		return getattr(self, "_fromSeqres", None)

	def _setFromSeqres(self, fsVal):
		if fsVal == self.fromSeqres:
			return
		if self.fromSeqres:
			for pos in range(len(self)-1, -1, -1):
				if not self.residues[pos]:
					Sequence.__delitem__(self, self.ungapped2gapped(pos))
					del self.residues[pos]
		self._fromSeqres = fsVal

	fromSeqres = property(_getFromSeqres, _setFromSeqres)

	def fullName(self):
		rem = self.name
		for part in (self.molecule.name, "(%s)" % self.molecule):
			rem = rem.strip()
			if rem:
				rem = rem.strip()
				if rem.startswith(part):
					rem = rem[len(part):]
					continue
			break
		if rem and not rem.isspace():
			namePart = " " + rem.strip()
		else:
			namePart = ""
		return "%s (%s)%s" % (self.molecule.name, self.molecule, namePart)

	def hasProtein(self):
		"""contains some protein residues"""
		from resCode import protein3to1
		for r in self.residues:
			if r and r.type in protein3to1:
				return True
		return False

	def insert(self, pos, insertion):
		if type(insertion) == str:
			return Sequence.insert(self, pos, insertion)
		for r, i in self.resMap.items():
			if i >= pos:
				self.resMap[r] = i+1
		self.residues.insert(pos, insertion)
		self.resMap[insertion] = pos
		from resCode import res3to1
		Sequence.insert(self, pos, res3to1(insertion.type))
		self.triggers.activateTrigger(self.TRIG_MODIFY, self)

	def _residueCB(self, trigName, ignore, resChanges):
		deletions = [dr for dr in resChanges.deleted
							if dr in self.resMap]
		if len(deletions) == len([r for r in self.residues if r]):
			self.demoteToSequence()
			return
		# sort deletions into descending order so we can easily
		# delete from our residue list
		deletions.sort(lambda r1, r2:
					cmp(self.resMap[r2], self.resMap[r1]))
		for dr in deletions:
			pos = self.resMap[dr]
			del self.resMap[dr]
			if self.fromSeqres:
				self.residues[pos] = None
			else:
				Sequence.__delitem__(self, self.ungapped2gapped(pos))
				del self.residues[pos]

		typesChanged = False
		if "type changed" in resChanges.reasons:
			from resCode import res3to1
			ungapped = self.ungapped()
			for res, pos in self.resMap.items():
				if res3to1(res.type) != ungapped[pos]:
					typesChanged = True
					self[self.ungapped2gapped(pos)
							] = res3to1(res.type)
		if typesChanged and self.fromSeqres:
			self.fromSeqres = False

		# identify new residues that should be added to the sequence
		candidates = {}.fromkeys([cr for cr in resChanges.created
					if cr.molecule == self.molecule
					and cr not in self.resMap])
		addedSome = False
		if candidates:
			# find cross-residue bonds that connect candidates/
			# current residues
			allRes = self.resMap.copy()
			allRes.update(candidates)
			resConn = dict((r, [rb for rb in r.bondedResidues()
					    if rb in allRes]) for r in allRes)
			while True:
				addThese = {}
				for ar in candidates.keys():
					for jr in resConn.get(ar, []):
						if jr not in self.resMap:
							continue
						if len(resConn.get(jr, [])) > 2:
							# throw up hands
							continue
						addThese[ar] = jr
				if addThese:
					addedSome = True
					from resCode import res3to1
					for add, prev in addThese.items():
						after = cmp(add.id,
								prev.id) > 0
						where = self.residues.index(
								prev) + after
						if where == len(self.residues):
							seqWhere = len(self)
						else:
							seqWhere = self.\
							ungapped2gapped(where)
						oneLet = res3to1(add.type)
						if self.fromSeqres:
							if where == 0 or where == len(self.residues) \
							or self.residues[where-1+after] != None \
							or self[seqWhere] != oneLet:
								self.fromSeqres = False
						if self.fromSeqres:
							self.residues[where-1+after] = add
						else:
							self.residues.insert(where, add)
							Sequence.insert(self, seqWhere, oneLet)
						self.resMap[add] = None
						del candidates[add]
				else:
					break
		if deletions or typesChanged or addedSome:
			self.resMap.clear()
			for i, r in enumerate(self.residues):
				if r:
					self.resMap[r] = i
			self.triggers.activateTrigger(self.TRIG_MODIFY, self)

	def saveInfo(self, molEncodeFunc=None):
		"""info that can be used with restoreSequence()"""
		saveInfo = Sequence.saveInfo(self)
		if molEncodeFunc is None:
			from SimpleSession import sessionID as molEncodeFunc
		saveInfo['molecule'] = molEncodeFunc(self.molecule)
		def resSes(r):
			if r is None:
				return None
			return molEncodeFunc(r)
		saveInfo['residues'] = [resSes(r) for r in self.residues]
		saveMap = {}
		for residue, pos in self.resMap.items():
			saveMap[molEncodeFunc(residue)] = pos
		saveInfo['resMap'] = saveMap
		saveInfo['fromSeqres'] = self.fromSeqres
		saveInfo['descriptiveName'] = self.descriptiveName
		return saveInfo

	def __setitem__(self, key, val):
		if isinstance(val, basestring):
			return Sequence.__setitem__(self, key, val)
		ungapped = self.gapped2ungapped(key)
		if ungapped is None:
			raise KeyError("Cannot set gap to non-gap")
		oldRes = self.residues[ungapped]
		if oldRes:
			del self.resMap[oldRes]
		self.resMap[val] = ungapped
		self.residues[ungapped] = val
		from resCode import res3to1
		Sequence.__setitem__(self, key, res3to1(val.type))
		self.triggers.activateTrigger(self.TRIG_MODIFY, self)

	def __setslice__(self, i, j, seq):
		if not isinstance(seq, self.__class__):
			return Sequence.__setslice__(self, i, j, seq)
		ungappedI = self._bestUngapped(i)
		ungappedJ = self._bestUngapped(j)
		for r in self.residues[ungappedI:ungappedJ]:
			del self.resMap[r]
		size = ungappedJ - ungappedI
		for r, ri in self.resMap.items():
			if ri >= ungappedI:
				self.resMap[r] = ri + len(seq) - max(size, 0)
		self.residues[ungappedI:ungappedJ] = seq.residues
		from resCode import res3to1
		Sequence.__setslice__(self, i, j,
						[res3to1(r.type) for r in seq])
		self.triggers.activateTrigger(self.TRIG_MODIFY, self)

	def ssType(self, loc, locIsUngapped=False):
		if not locIsUngapped:
			loc = self.gapped2ungapped(loc)
		if loc is None:
			return None
		r = self.residues[loc]
		if r is None:
			return None
		if r.isHelix:
			return self.SS_HELIX
		if r.isStrand:
			return self.SS_STRAND
		return self.SS_OTHER

	def static(self, start=0, end=-1):
		if end < 0:
			end += len(self)
		return StaticStructureSequence(self, start, end)

class StaticStructureSequence(StructureSequence):
	"""static structure sequence
	   (doesn't change as residues added/deleted)
	"""
	def __init__(self, sseq, start=None, end=None):
		StructureSequence.__init__(self, sseq.molecule, name=sseq.name)
		StructureSequence.__copy__(sseq, copySeq=self)
		if end is not None and end < len(self) - 1:
			del self[end+1:]
		if start is not None and start > 0:
			del self[:start]
		# stop dynamic numbering...
		self.numberingStart = self.numberingStart

	def saveInfo(self, molEncodeFunc=None):
		"""info that can be used with restoreSequence()"""
		saveInfo = StructureSequence.saveInfo(self)
		saveInfo['static'] = True
		return saveInfo

	def _residueCB(self, trigName, ignore, resChanges):
		deletions = [dr for dr in resChanges.deleted
							if dr in self.resMap]
		if len(deletions) == len(self.resMap):
			self.demoteToSequence()
			return

		# sort deletions into descending order so we can easily
		# delete from our residue list
		deletions.sort(lambda r1, r2:
					cmp(self.resMap[r2], self.resMap[r1]))
		for dr in deletions:
			pos = self.resMap[dr]
			del self.resMap[dr]
			self.residues[pos] = None

		typesChanged = False
		if "type changed" in resChanges.reasons:
			from resCode import res3to1
			ungapped = self.ungapped()
			for res, pos in self.resMap.items():
				if res3to1(res.type) != ungapped[pos]:
					typesChanged = True
					self[self.ungapped2gapped(pos)
							] = res3to1(res.type)
		if deletions or typesChanged:
			self.triggers.activateTrigger(self.TRIG_MODIFY, self)

def getSequence(molecule, chainID, **kw):
	"""Get the Sequence of the specified chain

	   Uses the getSequences function (below) and accepts the same
	   keywords.  Throws KeyError if the specified chain isn't found,
	   and AssertionError if there are multiple chains with the
	   specified ID.
	"""
	
	kw['asDict'] = True
	return getSequences(molecule, **kw)[chainID]

def getSequences(molecule, asDict=False):
	"""return all non-trivial sequences in a molecule

	   This function is also available as molecule.sequences(...)

	   returns a list of sequences for the given molecule, one sequence per
	   multi-residue chain.  The sequence name is "Chain X" where X is
	   the chain ID, or "Principal chain" if there is no chain ID.

	   The 'residues' attribute of each sequence is a list of the
	   residues for that sequence, and the attribute 'resmap' is a
	   dictionary that maps residue to sequence position (zero-based).
	   The 'residues' attribute will self-delete if the corresponding
	   model is closed.

	   If 'asDict' is true, return a dictionary of Sequences keyed on
	   chain ID (can throw AssertionError if multiple chains have same ID),
	   otherwise return a list.
	"""
	from chimera import bondsBetween, openModels, triggers
	from copy import copy

	def connected(res1, res2):
		if res1.id.chainId != ' ' \
		and res1.id.chainId == res2.id.chainId \
		and not res1.isHet and not res2.isHet:
			return True
		return bondsBetween(res1, res2, onlyOne=True)

	if hasattr(molecule, '_SequenceSequences'):
		seqList, seqDict, trigIDs = molecule._SequenceSequences
		if asDict:
			if seqDict is not None:
				return copy(seqDict)
			# known to be non-unique chain IDs...
			raise AssertionError("Non-unique chain IDs")
		else:
			return copy(seqList)

	chain = None
	prevRes = None
	firstRes = molecule.residues[0]
	seqs = []
	# don't start a sequence until we've seen two residues in the chain
	for res in molecule.residues:
		# if a residue has only one heavy atom, and that is connected
		# to only one other heavy atom, then don't put the residue
		# in the sequence
		# 
		# if heavy is connected to no other heavy atom (presumably
		# metal or ion), end the chain
		nheavys = res.heavyAtomCount
		chainBreak = prevRes == None
		if nheavys == 0:
			continue
		# heavys more reliably connected than hydrogens
		if prevRes and not connected(prevRes, res):
			didMod = 0
			if seq:
				for sr in seq.residues:
					if connected(sr, res):
						didMod = 1
			if didMod:
				continue
			chainBreak = 1
		elif prevRes and prevRes.id == res.id and nheavys == 1:
			continue
		elif chain is not None:
			# avoid adding a ligand that joins two side chains to
			# the sequence (DTT in 1fvg)...
			if prevRes and res.isHet and prevRes.id.chainId == res.id.chainId \
			and prevRes.id.position < res.id.position - 1:
				btw = bondsBetween(prevRes, res)
				if len(btw) == 1 and set([a.element.name for a in
				btw[0].atoms]) not in [set(['N', 'C']), set(['P', 'O'])]:
					continue
			# HET residues in named chains get the chain name,
			# but in blank chains they get 'het' -- allow for this
			truePrevID = chain
			trueResID = res.id.chainId
			if truePrevID != trueResID:
				if truePrevID in (" ", "het"):
					prevID = " "
				else:
					prevID = truePrevID
				if trueResID in (" ", "het"):
					resID = " "
				else:
					resID = trueResID
				if resID != prevID:
					chainBreak = 1

		if chainBreak or res == firstRes:
			# if chain ID changes in middle of connected chain
			# need to remember new chain ID...
			chain = res.id.chainId
			startRes = res
			prevRes = res
			seq = None
			continue # to avoid starting single-residues chains

		if not seq:
			if not chain or chain == " ":
				name = PRINCIPAL
				chain = " "
			else:
				name = CHAIN_FMT % chain
			seq = StructureSequence(startRes.molecule, name)
			seq.chain = chain
			seqs.append(seq)
			seq.append(startRes)
		seq.append(res)
		prevRes = res
	chain2desc = {}
	pdbHeaders = getattr(molecule, "pdbHeaders", {})
	compndRecs = pdbHeaders.get("COMPND", None)
	if compndRecs and molecule.pdbVersion > 1:
		compndChainIDs = None
		description = ""
		continued = False
		for rec in compndRecs:
			if continued:
				v += " " + rec[10:].strip()
			else:
				try:
					k, v = rec[10:].strip().split(": ", 1)
				except ValueError:
					# bad PDB file
					break
			if v.endswith(';'):
				v = v[:-1]
				continued = False
			elif rec == compndRecs[-1]:
				continued = False
			else:
				continued = True
				continue
			if k == "MOL_ID":
				if compndChainIDs and description:
					for chainID in compndChainIDs:
						chain2desc[chainID] = (description, synonym)
				compndChainIDs = None
				description = ""
			elif k == "MOLECULE":
				if v.startswith("PROTEIN (") and v.endswith(")"):
					description = v[9:-1]
				else:
					description = v
				synonym = False
			elif k == "SYNONYM":
				if ',' not in v:
					# not a long list of synonyms
					description = v
					synonym = True
			elif k == "CHAIN":
				compndChainIDs = v.split(", ")
		if compndChainIDs and description:
			for chainID in compndChainIDs:
				chain2desc[chainID] = (description, synonym)
	mmcifHeaders = getattr(molecule, "mmCIFHeaders", {})
	if not chain2desc and mmcifHeaders:
		scheme = mmcifHeaders.get('pdbx_poly_seq_scheme', [])
		id2index = {}
		for sch in scheme:
			id2index[sch['pdb_strand_id']] = int(sch['entity_id']) - 1
		entity = mmcifHeaders.get('entity', [])
		entity_name_com = mmcifHeaders.get('entity_name_com', [])
		name_com_lookup = {}
		for enc in entity_name_com:
			name_com_lookup[int(enc['entity_id'])-1] = enc['name']
		for chainID, index in id2index.items():
			description = None
			if len(entity) > index:
				try:
					description = entity[index]['pdbx_description']
				except KeyError:
					description = "chain " + chainID
				synonym = False
			if not description and index in name_com_lookup:
				# fall back to SYNONYM equivalent
				syn = name_com_lookup[index]
				if syn != '?':
					description = syn
					synonym = True
			if description:
				chain2desc[chainID] = (description, synonym)
	if chain2desc:
		from misc import processPdbChemName
		for k, v in chain2desc.items():
			description, synonym = v
			chain2desc[k] = processPdbChemName(description,
								probableAbbrs=synonym)
		seqChainIDs = set()
		for seq in seqs:
			try:
				chainID = seq.chainID
			except ValueError:
				continue
			seqChainIDs.add(chainID)
			seq.descriptiveName = chain2desc.get(chainID, None)
		if not getattr(molecule, '_chainDescriptionsLogged', False):
			for chainID in sorted(list(seqChainIDs)):
				descriptiveName = chain2desc.get(chainID, None)
				if descriptiveName:
					import replyobj
					replyobj.info("%s, chain %s: %s\n" % (molecule, chainID,
						descriptiveName))
			molecule._chainDescriptionsLogged = True
	sd = {}
	for seq in seqs[:]:
		# set 'fromSeqres' in this loop so that all sequences have it
		seq.fromSeqres = None
		if seq.chain in sd:
			# a sequence of all 'X' residues or all het (against non-X/non-het) loses
			source = sd[seq.chain]
			sourceX = str(source).count('?') == len(source)
			seqX = str(seq).count('?') == len(seq)
			sourceHet = len([r for r in source.residues if not r.isHet]) == 0
			seqHet = len([r for r in seq.residues if not r.isHet]) == 0
			if (seqX and not sourceX) or (seqHet and not sourceHet):
				seqs.remove(seq)
				continue
			elif (sourceX and not seqX) or (sourceHet and not seqHet):
				seqs.remove(sd[seq.chain])
				sd[seq.chain] = seq
				continue
			# Used to raise AssertionError here; by not raising the error
			# we can cache the fact that there are non-unique chain IDs 
			# and short-circuit multiple calls to this routine
			sd = None
			break
		sd[seq.chain] = seq

	# use full sequence if available...
	if sd:
		seqresSeqs = seqresSequences(molecule, asDict=True)
		for chain, seq in sd.items():
			try:
				srSeq = seqresSeqs[chain]
			except (KeyError, TypeError):
				continue
			seq.fromSeqres = True
			if len(srSeq) == len(seq):
				# no adjustment needed
				continue
			if len(srSeq) < len(seq):
				seq.fromSeqres = False
				import replyobj
				replyobj.warning("SEQRES record for chain %s of %s is "
					"incomplete.\n" "Ignoring record as basis for sequence."
					% (chain, molecule))
				continue
			# skip PDBs where the standard residues have been removed
			# but the SEQRES records haven't been...
			if str(seq).count('?') == len(seq) and str(seq) not in str(srSeq):
				seq.fromSeqres = False
				import replyobj
				replyobj.warning("Residues corresponding to SEQRES record for"
					" chain %s of %s are missing.\n"
					"Ignoring record as basis for sequence."
					% (chain, molecule))
				continue

			from MultAlignViewer.structAssoc import estimateAssocParams, \
													tryAssoc
			estLen, segments, gaps = estimateAssocParams(seq)
			# UNK residues may be jammed up against the regular sequence
			# in SEQRES records (3dh4, 4gns) despite missing intervening 
			# residues; compensate...
			# can't test aginst estLen since there can be other missing structure
			#
			# leading Xs...
			additionalXs = 0
			xs = ""
			for i, seg in enumerate(segments[:-1]):
				if seg.replace('?', ' ').isspace():
					xs += seg
					additionalXs += gaps[i]
				else:
					break
			if xs and srSeq[:len(xs)] == xs:
				srSeq[:0] =  '?' * additionalXs
			# trailing Xs...
			additionalXs = 0
			xs = ""
			for i, seg in enumerate(list(reversed(segments[1:]))):
				if seg.replace('?', ' ').isspace():
					xs += seg
					additionalXs += gaps[-(i+1)]
				else:
					break
			if xs and srSeq[-len(xs):] == xs:
				srSeq.extend('?' * additionalXs)
			# if a jump in numbering is in an unresolved part of the
			# structure, the estimated length can be too long...
			estLen = min(estLen, len(srSeq))
			# since gapping a structure sequence is considered an
			# "error", need to allow a lot more errors than normal...
			# However, allowing a _lot_ of errors can make it take a very
			# long time to find the answer, so limit the maximum...
			# (1vqn, chain 0 is > 2700 residues)
			seqLen = len(seq)
			maxErrs = int(min(seqLen/2, max(seqLen/10, sum(gaps))))
			try:
				matchMap, numErrors = tryAssoc(srSeq, seq, segments, gaps,
									estLen, maxErrors=maxErrs)
			except ValueError:
				seq.fromSeqres = False
				continue

			for i in range(len(srSeq)):
				if i in matchMap:
					del matchMap[i]
				else:
					seq.residues.insert(i, None)
			seq.resMap = matchMap
			seq[:] = srSeq[:]

	# try to avoid identical names
	baseNames = {}
	for seq in seqs:
		baseNames.setdefault(seq.name, []).append(seq)
	for baseName, sameNamedSeqs in baseNames.items():
		if len(sameNamedSeqs) > 1:
			def fmtID(r):
				if r.id.insertionCode != " ":
					return str(r.id.position) + r.id.insertionCode
				return str(r.id.position)
			for seq in sameNamedSeqs:
				actualResidues = [r for r in seq.residues if r]
				seq.name += " (%s-%s)" % (fmtID(actualResidues[0]),
					fmtID(actualResidues[-1]))

	if hasattr(molecule, '_SequenceSequences'):
		# deregister from previous sequence's triggers...
		# (don't destroy the old sequences, may be in use elsewhere)
		seqList, seqDict, trigIDs = molecule._SequenceSequences
		for i, seq in enumerate(seqList):
			seq.triggers.deleteHandler(seq.TRIG_DELETE, trigIDs[i])
	else:
		# invalidate the sequences cache if residues added/deleted
		molecule.__cacheHandlerID = triggers.addHandler('Residue',
					_invalidateCacheCB, molecule)
		molecule.__removeHandlerID = openModels.addRemoveHandler(
							_removeMolCB, molecule)
	# register for current sequence's triggers
	trigIDs = []
	for seq in seqs:
		trigIDs.append(
			seq.triggers.addHandler(seq.TRIG_DELETE, _delSeq, None))
	molecule._SequenceSequences = (seqs, sd, trigIDs)
	if asDict:
		if sd is not None:
			return copy(sd)
		raise AssertionError("Non-unique chain IDs")
	return copy(seqs)

def invalidate(molecule):
	try:
		seqList, seqDict, trigIDs = molecule._SequenceSequences
	except AttributeError:
		pass
	else:
		for i, seq in enumerate(seqList):
			seq.triggers.deleteHandler(seq.TRIG_DELETE, trigIDs[i])
		del molecule._SequenceSequences

class _PrositePatternError(ValueError):
	pass

def _delSeq(trigName, myData, seq):
	seqList, seqDict, trigIDs = seq.molecule._SequenceSequences
	i = seqList.index(seq)
	del seqList[i]
	del trigIDs[i]
	if seqDict is not None and seq in seqDict:
		del seqDict[seq]
	from chimera.triggerSet import ONESHOT
	return ONESHOT

def _invalidateCacheCB(trigName, molecule, resChanges):
	# we need to wait for the sequences to update themselves, so...
	additions = [r for r in resChanges.created if r.molecule == molecule]
	if additions:
		from chimera import triggers
		triggers.addHandler("monitor changes", _cacheCheck,
						(molecule, additions))

def _removeMolCB(trigName, molecule, removed):
	if molecule in removed:
		_delMolHandlers(molecule)

def _cacheCheck(trigName, info, trigData):
	from chimera.triggerSet import ONESHOT
	molecule, additions = info
	try:
		seqList, seqDict, trigIDs = molecule._SequenceSequences
	except AttributeError:
		# didn't have a cache anyway!
		return ONESHOT
	try:
		resList = molecule.residues
	except:
		# we must be in molecule destructor
		_delMolHandlers(molecule)
		return ONESHOT
	
	# modifications and deletions "take care of themselves", so we
	# only care about additions that are in chains that haven't added
	# themselves into current sequences
	for r in additions:
		if r.isIsolated:
			continue
		incorporated = False
		for seq in seqList:
			if r in seq.resMap:
				incorporated = True
				break
		if not incorporated:
			delattr(molecule, '_SequenceSequences')
			for i, seq in enumerate(seqList):
				seq.triggers.deleteHandler(seq.TRIG_DELETE, trigIDs[i])
			_delMolHandlers(molecule)
			break
	return ONESHOT

def _delMolHandlers(mol):
	from chimera import triggers, openModels
	if hasattr(mol, "__cacheHandlerID"):
		triggers.deleteHandler('Residue', mol.__cacheHandlerID)
		openModels.deleteRemoveHandler(mol.__removeHandlerID)
		delattr(mol, "__cacheHandlerID")
		delattr(mol, "__removeHandlerID")

def seqresSequences(molecule, singletons=False, asDict=False):
	"""return the sequences found in PDB SEQRES records for molecule

	   Returns None if there are no SEQRES records.
	   By default, singleton chains are ignored to match
	   getSequences() behavior.
	"""

	try:
		seqs = molecule.cifPolySeq
	except AttributeError:
		pass
	else:
		return _retSeqres(seqs, singletons, asDict)

	from resCode import res3to1
	try:
		srRecords = molecule.pdbHeaders["SEQRES"]
	except (AttributeError, KeyError):
		return None
	curChain = None
	seqs = {}
	for rec in srRecords:
		chain = rec[11]
		if chain != curChain:
			if chain == " ":
				name = PRINCIPAL
			else:
				name = CHAIN_FMT % chain
			seq = Sequence(name)
			seqs[chain] = seq
			curChain = chain
		seq.extend(map(res3to1, rec[19:70].split()))
	return _retSeqres(seqs, singletons, asDict)

def _retSeqres(seqs, singletons, asDict):
	if asDict:
		if singletons:
			return seqs
		else:
			pruned = {}
			for k, v in seqs.items():
				if len(v) > 1:
					pruned[k] = v
			return pruned
	else:
		if singletons:
			return seqs.values()
		return [s for s in seqs.values() if len(s) > 1]

def restoreSequence(seqInfo, molDecodeFunc=None):
	"""restore a sequence from the string returned by seq.saveString()"""
	if isinstance(seqInfo, basestring):
		seqInfo = eval(seqInfo)
	if 'molecule' in seqInfo:
		if isinstance(seqInfo['molecule'], basestring):
			# backwards compatibility with old sessions
			from SimpleSession import oslLookup as molDecodeFunc
		elif molDecodeFunc is None:
			from SimpleSession import idLookup as molDecodeFunc
		molecule = molDecodeFunc(seqInfo['molecule'])
		seq = StructureSequence(molecule, seqInfo['name'])
		def resDecode(info):
			if info is None:
				return None
			return molDecodeFunc(info)
		seq.residues.extend([resDecode(info)
				for info in seqInfo['residues']])
		for sesID, pos in seqInfo['resMap'].items():
			seq.resMap[molDecodeFunc(sesID)] = pos
		if seqInfo.get('static', False):
			seq = StaticStructureSequence(seq)
		seq.descriptiveName = seqInfo.get('descriptiveName', None)
	else:
		seq = Sequence(seqInfo['name'])
		if 'numberingStart' in seqInfo:
			seq.numberingStart = seqInfo['numberingStart']
	if 'attrs' in seqInfo:
		seq.attrs = seqInfo['attrs']
		seq.markups = seqInfo['markups']
	else:
		seq.attrs = seqInfo['miscAttrs']
		seq.markups = {}
	if 'circular' in seqInfo:
		seq.circular = seqInfo['circular']
	seq.fromSeqres = seqInfo.get('fromSeqres', None)
	seq.sequence.extend(seqInfo['sequence'])
	return seq

def percentIdentity(seq1, seq2, denominator="shorter"):
	"""Compute the percent identity between two gapped sequences

	   'denominator' control what the number of matches is divided by:
	     "shorter":  the ungapped length of the shorter of the two sequences
	     "longer":  converse of "shorter"
	     "in common":  the number of non-gap columns in common
	"""
	if len(seq1) != len(seq2):
		raise ValueError("Cannot compute percent identity for"
					" different-length sequences")

	matches = inCommon = 0

	for i, c1 in enumerate(seq1):
		if not c1.isalnum():
			continue
		c2 = seq2[i]
		if not c2.isalnum():
			continue
		inCommon += 1
		if c1.lower() == c2.lower():
			matches += 1
	try:
		if denominator == "shorter":
			return matches * 100.0 / min(len(seq1.ungapped()),
								len(seq2.ungapped()))
		elif denominator == "longer":
			return matches * 100.0 / max(len(seq1.ungapped()),
								len(seq2.ungapped()))
		return matches * 100.0 / inCommon
	except ZeroDivisionError:
		return 0.0

