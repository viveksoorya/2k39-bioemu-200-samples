# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: Smiles.py 42114 2020-01-24 23:48:37Z pett $

import chimera

def openSmiles(smiles, resName="UNK"):
	m = smiles2mol(smiles, resName=resName)
	chimera.openModels.add([m])
	return m

class SmilesTranslationError(ValueError):
	pass

def smiles2mol(smiles, resName="UNK", identifyAs=None, retry=False):
	if not identifyAs:
		if len(smiles) <= 14:
			identifyAs = "smiles:" + smiles
		else:
			identifyAs = "smiles:" + smiles[:14] + "..."
	# triple-bond characters (#) get mangled by http protocol, so switch to
	# http-friendly equivalent
	webSmiles = smiles.replace('#', '%23')
	from chimera import replyobj
	from string import printable
	printables = []
	for char in webSmiles:
		if char in printable:
			printables.append(char)
	diff = len(webSmiles) - len(printables)
	if diff > 0:
		replyobj.warning("Removed %d non-printable characters from SMILES string" % diff)
		webSmiles = "".join(printables)
	for fetcher, moniker in [(_cactusFetch, "NCI"), (_indianaFetch, "Indiana University")]:
		try:
			path = fetcher(webSmiles, identifyAs)
		except SmilesTranslationError:
			pass
		else:
			from ReadSDF import readSDF
			mols = readSDF(path, identifyAs=identifyAs)
			if mols:
				break
		replyobj.info("Failed to translate SMILES to 3D structure via %s web service (SMILES: %s)\n" % (moniker, smiles))
	else:
		raise SmilesTranslationError("Web services failed to translate SMILES"
				" string to 3D structure.")
	replyobj.info("Translated SMILES to 3D structure via %s web service (SMILES: %s)\n"
		% (moniker, smiles))
	m = mols[0]
	m.residues[0].type = resName
	return m

def _indianaFetch(smiles, identifyAs):
	from chimera.fetch import fetch_file
	# can't cache due to case-independent file systems
	path, headers = fetch_file("http://cheminfov.informatics.indiana.edu/rest/thread/d3.py/SMILES/%s" % smiles, identifyAs)
	return path

def _cactusFetch(smiles, identifyAs):
	cactusSite = "cactus.nci.nih.gov"
	import urllib2
	try:
		reply = urllib2.urlopen("http://%s/cgi-bin/translate.tcl?smiles=%s&format=sdf&astyle=kekule&dim=3D&file=" % (cactusSite, smiles.strip()))
	except urllib2.URLError, v:
		pass
	else:
		for line in reply:
			if "Click here" in line and line.count('"') == 2 and 'href="' in line:
				pre, url, post = line.split('"')
				return "http://%s%s" % (cactusSite, url)
	raise SmilesTranslationError("Cactus could not translate %s" % smiles)
