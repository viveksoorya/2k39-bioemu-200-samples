# also check out comments and definitions in MultAlignViewer.HeaderSequence

from MultAlignViewer.HeaderSequence import registerHeaderSequence, \
			DynamicHeaderSequence, DynamicStructureHeaderSequence
class ChargeSeq(DynamicHeaderSequence):
	name = "Charge variation"
	positive = "RHK"
	negative = "DE"
	def evaluate(self, pos):
		if not hasattr(self, "colors") \
		or len(self.colors) != len(self.mav.seqs[0]):
			self.colors = ["gray"] * len(self.mav.seqs[0])
		minCharge = maxCharge = lastCharge = None
		for seq in self.mav.seqs:
			let = seq[pos].upper()
			if not let.isupper():
				continue
			if let in self.negative:
				charge = -1
			elif let in self.positive:
				charge = 1
			else:
				charge = 0
			if minCharge is None:
				firstCharge = charge
				minCharge = maxCharge = charge
			else:
				lastCharge = charge
				maxCharge = max(maxCharge, charge)
				minCharge = min(minCharge, charge)
		if minCharge == None:
			val = 0
		else:
			val = (maxCharge - minCharge)
		color = "gray"
		if len(self.mav.seqs) == 2 and lastCharge != None:
			if firstCharge > lastCharge:
				color = "red"
			elif lastCharge > firstCharge:
				color = "blue"
		self.colors[pos] = color
		return val

	def colorFunc(self, line, pos):
		return self.colors[pos]

	def depictionVal(self, pos):
		return self[pos] / 2.0

registerHeaderSequence(ChargeSeq, defaultOn=False)

class DistanceSeq(DynamicStructureHeaderSequence):
	def __init__(self, *args, **kw):
		from math import log
		self.scaling = log(0.5) / (-3.0)
		# the global DynamicStructureHeaderSequence points to None by the
		# time this method gets called, so...
		from MultAlignViewer.HeaderSequence import \
					DynamicStructureHeaderSequence
		DynamicStructureHeaderSequence.__init__(self, *args, **kw)
		self._motionHandler = None

	def show(self):
		from MultAlignViewer.HeaderSequence import \
					DynamicStructureHeaderSequence
		DynamicStructureHeaderSequence.show(self)
		if self._motionHandler == None:
			from chimera import triggers, MOTION_STOP
			self._motionHandler = triggers.addHandler(MOTION_STOP,
						self.refresh, None)
		if len(self.mav.associations) < 2:
			self.mav.status("Need at least two associated"
						" structures", color="red")

	def hide(self):
		from MultAlignViewer.HeaderSequence import \
					DynamicStructureHeaderSequence
		DynamicStructureHeaderSequence.hide(self)
		if self._motionHandler != None:
			from chimera import triggers, MOTION_STOP
			triggers.deleteHandler(MOTION_STOP, self._motionHandler)
			self._motionHandler = None
			
	def destroy(self):
		if self._motionHandler != None:
			from chimera import triggers, MOTION_STOP
			triggers.deleteHandler(MOTION_STOP, self._motionHandler)
			self._motionHandler = None
		from MultAlignViewer.HeaderSequence import \
					DynamicStructureHeaderSequence
		DynamicStructureHeaderSequence.destroy(self)
		
	def evaluate(self, pos):
		sum = 0.0
		n = 0
		for coords in self.gatherCoords(pos):
			for i , crd1 in enumerate(coords):
				for crd2 in coords[i+1:]:
					sum += crd1.sqdistance(crd2)
			n += (len(coords) * (len(coords)-1)) / 2
		if n == 0:
			return None
		from math import sqrt
		return sqrt(sum / n)

	def colorFunc(self, line, pos):
		return "dark gray"

	def depictionVal(self, pos):
		val = self[pos]
		if val == None:
			return ' '
		else:
			from math import exp
			return 1.0 - exp(0.0 - self.scaling * val)

from CGLutil.SortString import SortString
class CaDistanceSeq(DistanceSeq):
	name = SortString("RMSD: ca", cmpVal=1)

	def gatherCoords(self, pos):
		coords = []
		from chimera.misc import principalAtom
		for mol, seq in self.mav.associations.items():
			ungapped = seq.gapped2ungapped(pos)
			matchMap = seq.matchMaps[mol]
			if ungapped == None or ungapped not in matchMap:
				continue
			pa = principalAtom(matchMap[ungapped])
			if not pa:
				continue
			coords.append(pa.xformCoord())

		return [coords]

registerHeaderSequence(CaDistanceSeq, defaultOn=False)

class BackboneDistanceSeq(DistanceSeq):
	name = SortString("RMSD: backbone", cmpVal=2)

	def gatherBackboneCoords(self, pos):
		residues = []
		for mol, seq in self.mav.associations.items():
			ungapped = seq.gapped2ungapped(pos)
			matchMap = seq.matchMaps[mol]
			if ungapped == None or ungapped not in matchMap:
				continue
			res = matchMap[ungapped]
			if res:
				residues.append(res)
		if not residues:
			return []

		backboneNames = None
		for res in residues:
			if "C4'" in res.atomsMap:
				backboneNames = ["P", "O5'", "C5'", "C4'", "C3'", "O3'"]
				break
			if "CA" in res.atomsMap:
				backboneNames = ["N", "CA", "C", "O", "OXT"]
				break
		if not backboneNames:
			return []

		coordLists = []
		for bbName in backboneNames:
			coords = []
			for res in residues:
				a = res.findAtom(bbName)
				if a:
					coords.append(a.xformCoord())
			if len(coords) > 1:
				coordLists.append(coords)
		return coordLists

	gatherCoords = gatherBackboneCoords

registerHeaderSequence(BackboneDistanceSeq, defaultOn=False)

class FullDistanceSeq(BackboneDistanceSeq):
	name = SortString("RMSD: full", cmpVal=3)

	def gatherCoords(self, pos):
		residues = []
		for mol, seq in self.mav.associations.items():
			ungapped = seq.gapped2ungapped(pos)
			matchMap = seq.matchMaps[mol]
			if ungapped == None or ungapped not in matchMap:
				continue
			res = matchMap[ungapped]
			if res:
				residues.append(res)
				if res.type != residues[0].type:
					return self.gatherBackboneCoords(pos)
		if not residues:
			return []

		coordsByName = {}
		for res in residues:
			for a in res.atoms:
				if a.element.number < 2:
					continue
				coordsByName.setdefault(a.name, []).append(a.xformCoord())
		coordLists = []
		for coords in coordsByName.values():
			if len(coords) > 1:
				coordLists.append(coords)
		return coordLists

registerHeaderSequence(FullDistanceSeq, defaultOn=False)
