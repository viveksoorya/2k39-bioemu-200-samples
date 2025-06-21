from Rotamers import NoResidueRotamersError, RotamerParams

citeName = displayName = "Dunbrack 2010"
description = "Dunbrack 2010 backbone-dependent rotamer library -- 5% stepdown"
citation = """Shapovalov, M.S., and Dunbrack, R.L., Jr. (2011)
A Smoothed Backbone-Dependent Rotamer Library for Proteins
    Derived from Adaptive Kernel Density Estimates and Regressions
Structure, 19, 844-858."""
citePubmedID = 21645855
residueTypes = ["ALA", "ARG", "ASN", "ASP", "CPR", "CYD", "CYH", "CYS", "GLN", "GLU", "GLY",
	"HIS", "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TPR", "TRP", "TYR", "VAL"]
resTypeMapping = { "CPR": "PRO", "CYD": "CYS", "CYH": "CYS", "TPR": "PRO" }

_dependentCache = {}
def dependentRotamerParams(resName, phi, psi):
	from math import floor
	phi = floor((phi + 5) / 10.0) * 10
	psi = floor((psi + 5) / 10.0) * 10
	fileName = "%s%d%d" % (resName, phi, psi)
	return _getParams(resName, fileName, _dependentCache,
						"dependentRotamerData.zip")

_independentCache = {}
def independentRotamerParams(resName):
	return _getParams(resName, resName, _independentCache,
						"independentRotamerData2002.zip")

def _getParams(resName, fileName, cache, archive):
	try:
		return cache[fileName]
	except KeyError:
		pass
	import os.path
	myDir = os.path.split(__file__)[0]
	from zipfile import ZipFile
	zf = ZipFile(os.path.join(myDir, archive), "r")
	try:
		data = zf.read(fileName)
	except KeyError:
		raise NoResidueRotamersError("No rotamers for %s" % resName)
	from struct import unpack, calcsize
	sz1 = calcsize("!ii")
	numRotamers, numParams = unpack("!ii", data[:sz1])
	sz2 = calcsize("!%df" % numParams)
	rotamers = []
	for i in range(numRotamers):
		params = unpack("!%df" % numParams,
						data[sz1+i*sz2:sz1+(i+1)*sz2])
		p = params[0]
		chis = params[1:]
		rotamers.append(RotamerParams(p, chis))
	cache[fileName] = rotamers
	return rotamers
