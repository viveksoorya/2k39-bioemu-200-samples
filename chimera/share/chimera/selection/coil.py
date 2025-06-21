# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: ss.py 30865 2010-07-02 00:01:29Z pett $

from manager import selMgr

# register some element type selectors
ssSelCategory = "secondary structure"
selectorTemplate = """\
from chimera.misc import principalAtom
selAdd = []
for mol in molecules:
	for res in mol.residues:
		if (getattr(principalAtom(res), "name", None) == "CA"
		and not res.isHelix and not res.isStrand):
			selAdd.append(res)
sel.add(selAdd)
sel.addImplied(vertices=0)
"""
selMgr.addSelector("secondary structure",
	[selMgr.STRUCTURE, ssSelCategory, "coil"], selectorTemplate)
selMgr.makeCallbacks()

