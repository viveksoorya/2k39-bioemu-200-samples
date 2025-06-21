# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: v38.py,v 1.1 2008-11-11 01:04:35 goddard Exp $

from v57 import *

import globals # so that various version files can easily access same variables
import chimera

def restoreSelections(curSelIds, savedSels):
	from chimera import selection
	sel = []
	surfSel = selection.ItemizedSelection()
	for csid in curSelIds:
		if type(csid) == list:
			if len(csid) == 2:
				# chain trace pseudobond
				a1, a2 = [idLookup(x) for x in csid]
				for pb in a1.pseudoBonds:
					if pb.category.startswith("chain-trace-") and pb.otherAtom(a1) == a2:
						sel.append(pb)
						break
			else:
				# MSMS surface
				m = idLookup(csid[0])
				surfMap = dict([(s.molecule, s) for s in chimera.openModels.list(
					modelTypes=[chimera.MSMSModel])])
				# surface could possibly fail if different platform
				if m in surfMap:
					surfSel.add(surfMap[m])
		else:
			sel.append(idLookup(csid))
	selection.setCurrent(sel)
	if not surfSel.empty():
		# sidestep auto-selection of atoms/bonds when surface added
		surfSel.remove([a for a in surfSel.atoms()] + surfSel.edges())
		selection.mergeCurrent(selection.EXTEND, surfSel)

	for selInfo in savedSels:
		selName, ids = selInfo
		sel = selection.ItemizedSelection()
		sel.add(map(idLookup, ids))
		chimera.selection.saveSel(selName, sel)
