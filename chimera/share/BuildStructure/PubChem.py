# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: PubChem.py 42160 2020-07-09 16:05:51Z pett $

import chimera

def openPubChem(pcID, resName="UNK", ignore_cache=False):
	m = pubChem2mol(pcID, resName=resName, ignore_cache=ignore_cache)
	chimera.openModels.add([m])
	return m

class InvalidPub3dID(ValueError):
	def __init__(self, pcID):
		if pcID.isdigit():
			msg = "Either no such PubChem ID (%s) or structure cannot be handled by Pub3D service (typically inorganic, metal-containing or unstable structures)" % pcID
		else:
			msg = "No such PubChem ID (%s)" % pcID
		ValueError.__init__(self, msg)

def pubChem2mol(pcID, resName="UNK", ignore_cache=False):
	from chimera import fetch
	def file_check(path):
		from OpenSave import osOpen
		f = osOpen(path)
		data = f.read()
		f.close()
		if data.startswith("Status: 404"):
			raise IOError("No 3D structure available")
		elif data.startswith("Status: 400"):
			raise IOError("No such entry")
	from chimera import replyobj
	from string import printable
	pcID = pcID.strip()
	printables = []
	for char in pcID:
		if char in printable:
			printables.append(char)
	diff = len(pcID) - len(printables)
	if diff > 0:
		replyobj.warning("Removed %d non-printable characters from PubChem CID" % diff)
		pcID = "".join(printables)
	path, headers = fetch.fetch_file(
		"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/%s/SDF?record_type=3d" % pcID,
		pcID, save_dir="Pub3D", save_name="%s.sdf" % pcID,
		ignore_cache=ignore_cache, file_check=file_check)
	from ReadSDF import readSDF
	result = readSDF(path, identifyAs="CID %s" % pcID)
	if not result:
		raise InvalidPub3dID(pcID)
	m = result[0]
	m.residues[0].type = resName
	return m
