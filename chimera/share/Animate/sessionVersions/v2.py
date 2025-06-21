'''Version specific functions for expanding selected attributes from saved
session files for restoration of Animation scene states.'''

import chimera

# the following lists control which attributes get compressed
atomColor = [
	'color'
	, 'labelColor'
	, 'surfaceColor'
]
atomAttr = [
	'display'
	, 'label'
	, 'radius'
	, 'surfaceDisplay'
	, 'surfaceOpacity'
	, 'drawMode'
]

bondColor = [
	'color'
	, 'labelColor'
]
bondAttr = [
	'display'
	, 'label'
	, 'radius'
	, 'drawMode'
]

resColor = [
	'fillColor'
	, 'labelColor'
	, 'ribbonColor'
]
resAttr = [
	'fillDisplay'
	, 'label'
	, 'labelOffset'
	, 'ribbonDisplay'
	, 'fillMode'
	, 'ribbonDrawMode'
#	,'ribbonStyle'
]

def atomsCompress(atomDict):
	return vCompress(atomDict, atomColor, atomAttr)

def atomsExpand(atomDict):
	return vExpand(atomDict, atomColor, atomAttr)

def bondsCompress(bondDict):
	return vCompress(bondDict, bondColor, bondAttr)

def bondsExpand(bondDict):
	return vExpand(bondDict, bondColor, bondAttr)

def residuesCompress(resDict):
	return vCompress(resDict, resColor, resAttr)

def residuesExpand(resDict):
	return vExpand(resDict, resColor, resAttr)


'''Convert an older version to the current version of session saving.'''
def vConvert(vDict, vColors, oldver):
	'''Only the way colors are saved varies between versions.'''
	from Animate.SceneState import SceneState

	if oldver == 1:
		colorDict = {} # ensure dupes use the same MaterialColor instance
		for colattr in vColors:
			colorList = []
			colors = vDict[colattr]
			for color in colors:
				if color is None:
					colorList.append(None)
					continue
				try:
					rgba = color['rgba']
				except:
					print "uh, oh"
				if not colorDict.has_key(rgba):
					colorDict[rgba] = SceneState.MaterialColorRestore(color)
				colorList.append(colorDict[rgba])
			vDict[colattr] = colorList

	return vDict

def atomsConvert(atomDict, oldver):
	return vConvert(atomDict, atomColor, oldver)

def bondsConvert(bondDict, oldver):
	return vConvert(bondDict, bondColor, oldver)

def residuesConvert(resDict, oldver):
	return vConvert(resDict, resColor, oldver)


def vCompress(vDict, vColors, vAttrs):
	vvDict = {} # return a copy of vDict
	for colors in vColors:
		colorList = colors_to_ids(vDict[colors])
		vvDict[colors] = listSummary(colorList)
	for attr in vAttrs:
		attrList = vDict[attr]
		vvDict[attr] = listSummary(attrList)
	for k in vDict.keys():
		if not vvDict.has_key(k):
			vvDict[k] = vDict[k]
	return vvDict

def vExpand(vDict, vColors, vAttrs):
	for colors in vColors:
		color_id_list = listExpand(vDict[colors])
		vDict[colors] = ids_to_colors(color_id_list)
	for attr in vAttrs:
		vDict[attr] = listExpand(vDict[attr])
	return vDict

def colors_to_ids(colorList):
	from SimpleSession import colorID
	newColorList = []
	for i, color in enumerate(colorList):
		if color is None:
			newColorList.append(None)
			continue
		try:
			assert isinstance(color, chimera.MaterialColor)
		except:
			errstr = "color wrong type: %s" % (str(type(color)),)
			print errstr
		newColorList.append(colorID(color))
	return newColorList

def ids_to_colors(idTuple):
	from SimpleSession import getColor
	colorList = []
	for i, cid in enumerate(idTuple):
		if isinstance(cid, dict):
			print "this has to be caught"

		colorList.append(getColor(cid))
	return colorList

def materialColorExpand(mc_id):
	from SimpleSession import getColor
	return getColor(mc_id)

def materialColorID(mc):
	from SimpleSession import colorID
	return colorID(mc)

#
# BEGIN SimpleSession code.
#

def listExpand(summary, hashable=True):
	numVals, default, exceptions = summary
	if hashable:
		vals = [default] * numVals
		for value, indices in exceptions.items():
			if indices[0] == None:
				indices = sequenceExpand(indices[1])
			for i in indices:
				vals[i] = value
	else:
		try:
			vals = [eval(v) for v in exceptions]
		except NameError:
			# numpy?
			import numpy
			evalLocals = locals()
			evalLocals.update(vars(numpy))
			vals = [eval(v, evalLocals) for v in exceptions]
	return vals

def listSummary(vals, consecutiveExceptions=False, hashable=True):
	if not hashable:
		if vals.count(None) == len(vals):
			return len(vals), None, []
		return len(vals), None, [repr(v) for v in vals]
	sorted = {}
	for i, val in enumerate(vals):
		sorted.setdefault(val, []).append(i)
	mostCount = None
	for val, indices in sorted.items():
		if mostCount is None or len(indices) > mostCount:
			mostVal = val
			mostCount = len(indices)
	if mostCount is None:
		return len(vals), None, {}
	del sorted[mostVal]
	if consecutiveExceptions:
		for k, v in sorted.items():
			sorted[k] = (None, sequenceSummary(v))
	return len(vals), mostVal, sorted

def sequenceSummary(vals):
	summary = []
	first = True
	start = prev = None
	numNone = 0
	for v in vals:
		if first:
			first = False
			if v == None:
				numNone += 1
			start = prev = v
		elif v == None:
			numNone += 1
			if start != None:
				length = prev - start + 1
				summary.append((start, length))
			start = prev = v
		elif prev == None:
			summary.append((None, numNone))
			numNone = 0
			start = prev = v
		elif v == prev + 1:
			prev = v
		else:
			length = prev - start + 1
			summary.append((start, length))
			start = prev = v
	if numNone > 0:
		summary.append((None, numNone))
	elif start != None:
		length = prev - start + 1
		summary.append((start, length))
	return summary

def sequenceExpand(summary):
	expanded = []
	for start, length in summary:
		if start == None:
			seq = [None] * length
		else:
			seq = range(start, start + length)
		expanded.extend(seq)
	return expanded

#
# END SimpleSession code
#
