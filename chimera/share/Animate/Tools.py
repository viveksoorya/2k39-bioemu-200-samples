# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

pbAttrNames = ['drawMode', 'display', 'halfbond', 'label', 'color', 'labelColor']

from Scenes import scenes
sceneID = scenes.get_id_by_obj
idLookup = scenes.get_obj_by_id

def colorID(v):
	if v is None:
		return None
	return v.rgba()

def getColor(v):
	if v is None:
		return v
	from chimera import MaterialColor
	return MaterialColor(*v)

def get_saveable_pb_info(pbg):
	saveable = { 'version': 1 }
	pbs = pbg.pseudoBonds
	if not pbs:
		return saveable
	saveable['atoms'] = [[sceneID(a) for a in pb.atoms] for pb in pbg.pseudoBonds]
	for attrName in pbAttrNames:
		vals = [getattr(pb, attrName) for pb in pbs]
		if attrName.lower().endswith("color"):
			vals = [colorID(v) for v in vals]
		if vals.count(vals[0]) == len(vals):
			saveable[attrName] = vals[0]
		else:
			saveable[attrName] = vals
	return saveable

def restore_pbs(pbg, info):
	pbg.deleteAll()
	if not info or 'atoms' not in info:
		return
	atomPairs = [[idLookup(atomID) for atomID in (id1, id2)] for id1, id2 in info['atoms']]
	pbs = [pbg.newPseudoBond(a1, a2) for a1, a2 in atomPairs]
	for attrName in pbAttrNames:
		vals = info[attrName]
		singleton = False
		if not isinstance(vals, list):
			singleton = True
			vals = [vals] * len(pbs)
		if attrName.lower().endswith("color"):
			if singleton:
				vals = [getColor(vals[0])] * len(pbs)
			else:
				vals = [getColor(v) for v in vals]
		for pb, val in zip(pbs, vals):
			setattr(pb, attrName, val)
	return pbs
