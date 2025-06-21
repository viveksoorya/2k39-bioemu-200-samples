# Title and contour levels about the top500-angles files are obtained by
# examining the Kinemage files in kin/rama
ContourInfo = {
	"Alanine (no repet sec struct)":
		( "rama500-ala-nosec.data",	( "0.02", "0.002" ) ),
	"General case (no repet sec struct)":
		( "rama500-general-nosec.data",	( "0.02", "0.0005", ) ),
	"General case (not Gly, Pro or pre-Pro)":
		( "rama500-general.data",	( "0.02", "0.0005", ) ),
	"Glycine (sym, no repet sec struct)":
		( "rama500-gly-sym-nosec.data",	( "0.02", "0.002", ) ),
	"Glycine (sym)":
		( "rama500-gly-sym.data",	( "0.02", "0.002", ) ),
	"pre-Proline (not Gly or Pro)":
		( "rama500-prepro.data",	( "0.02", "0.002", ) ),
	"Proline":
		( "rama500-pro.data",		( "0.02", "0.002", ) ),
}
DefaultContour = "General case (not Gly, Pro or pre-Pro)"

def contourType(resType, beforeProline, inSS):
	"Returns name of contour for residue with given properties."
	if resType == "P":
		return "Proline"
	if beforeProline and resType != "G":
		return "pre-Proline (not Gly or Pro)"
	if inSS:
		if resType == "G":
			return "Glycine (sym)"
		else:
			return "General case (not Gly, Pro or pre-Pro)"
	else:
		if resType == "A":
			return "Alanine (no repet sec struct)"
		elif resType == "G":
			return "Glycine (sym, no repet sec struct)"
		else:
			return "General case (no repet sec struct)"

_contourCache = {}
def getContourInfo(contour):
	"Returns contour data (numpy) and recommended contour levels (tuple)."
	try:
		return _contourCache[contour]
	except KeyError:
		from contour import ContourInfo
		try:
			fn, levels = ContourInfo[contour]
		except KeyError:
			# No contour, no drawing
			return
		import os.path, numpy
		dir = os.path.dirname(__file__)
		filename = os.path.join(dir, "top500-angles",
					"pct", "rama", fn)
		xyz = numpy.loadtxt(filename)
		z = numpy.reshape(xyz[:,2], (180, 180), order='F')
		_contourCache[contour] = (z, levels)
		return (z, levels)

def _contourIndex(angle):
	if angle < -180:
		return 0
	elif angle >= 180:
		return 179
	else:
		return int((angle - -180.0) / 2.0)

def assignProb(m):
	"Assign residue probabilities in Ramachandran space."
	from contour import contourType
	from pprint import pprint
	for seq in m.sequences():
		print seq, seq.residues
		if not seq.hasProtein():
			continue
		for i, r in enumerate(seq.residues):
			if r is None or r.phi is None or r.psi is None:
				continue
			try:
				beforeProline = seq[i + 1] == 'P'
			except IndexError:
				beforeProline = False
			inSS = seq.ssType(i) in "HS"
			contour = contourType(seq[i], beforeProline, inSS)
			z, levels = getContourInfo(contour)
			nphi = _contourIndex(r.phi)
			npsi = _contourIndex(r.psi)
			r.ramaProb = z[npsi,nphi]
