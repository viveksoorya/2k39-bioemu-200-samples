from MMMD.MMTKinter import *
from chimera import Point
import chimera

class energyMMTKinter(MMTKinter):
	def __init__(self, mols, col1, col2, *args, **kw):
		self.col1 = col1
		self.col2 = col2
		MMTKinter.__init__(self, mols, *args, **kw)

	def _makeUniverse(self):
		MMTKinter._makeUniverse(self)
		
	def energyEvaluator(self, cs):
		from MMTK import Collection
		for a in self.mols[0].atoms:
			p = Point(a.coord(cs))
			self.atomMap[a].setPosition(p)
		frag1 = [self.atomMap[a] for a in self.col1]
		frag2 = [self.atomMap[a] for a in self.col2]
		col1 = Collection()
		col2 = Collection()
		col1.addObject(frag1)
		col2.addObject(frag2)
		evaluator = self.universe.energyEvaluator(col1,col2)
		energy = evaluator()
		return energy
		
	
