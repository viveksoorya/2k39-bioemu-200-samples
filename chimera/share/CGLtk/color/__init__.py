# need this file for package importing.

from ColorWell import rgba2tk

def colorRange(n):
	"Generate a set of 'n' distinguishable RGB colors"

	from colorsys import hls_to_rgb
	lValues = [ 0.5, 0.25, 0.75 ]
	layers = min(int(n / 6) + 1, len(lValues))
	remainder = n % layers
	perLayer = (n - remainder) / layers
	colorList = []
	for i in range(layers):
		numColors = perLayer
		if i < remainder:
			numColors += 1
		l = lValues[i]
		s = 1.0
		nc = float(numColors)
		for count in range(numColors):
			h = count / nc
			colorList.append(hls_to_rgb(h, l, s))
	return colorList


_dfState = {}
def distinguishFrom(rgbs, numCandidates=3, seed=None, saveState=True):
	if rgbs and len(rgbs[0]) > 3:
		rgbs = [rgba[:3] for rgba in rgbs]

	maxDiff = None
	import random
	global _dfState
	if seed is not None:
		if saveState and seed in _dfState:
			random.setstate(_dfState[seed])
		else:
			random.seed(seed)
	for i in range(numCandidates):
		candidate = tuple([random.random() for i in range(3)])
		if not rgbs:
			if saveState and seed is not None:
				_dfState[seed] = random.getstate()
			return candidate
		minDiff = None
		for rgb in rgbs:
			diff = abs(rgb[0]-candidate[0]) + abs(rgb[1]-candidate[1]) \
				+ 0.5 * (abs(rgb[2]-candidate[2]))
			if minDiff is None or diff < minDiff:
				minDiff = diff
		if maxDiff is None or minDiff > maxDiff:
			maxDiff = minDiff
			bestCandidate = candidate
	if saveState and seed is not None:
		_dfState[seed] = random.getstate()
	return bestCandidate
