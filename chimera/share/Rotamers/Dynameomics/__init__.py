from Rotamers import NoResidueRotamersError, RotamerParams

citeName = displayName = "Dynameomics"
description = "Dynameomics backbone-independent rotamer library -- March '12"
citation = """A.D. Scouras and V. Daggett (2011)
The dynameomics rotamer library:
  Amino acid side chain conformations and dynamics from
  comprehensive molecular dynamics simulations in water
Protein Science 20, 341-352."""
citePubmedID = 21280126
residueTypes = ["ALA", "ARG", "ASN", "ASP", "CYS", "CYH", "GLN", "GLU", "GLY", "HID",
	"HIE", "HIP", "HIS", "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"]
resTypeMapping = { "CYH": "CYS", "HID": "HIS", "HIE": "HIS", "HIP": "HIS" }

_independentCache = {}
def independentRotamerParams(resName):
	return _getParams(resName, resName, _independentCache, "rotamerData.zip")

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
