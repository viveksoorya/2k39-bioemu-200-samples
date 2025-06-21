# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 29861 2010-01-26 18:48:43Z pett $

from chimera import preferences

LIG_POS = "ligand position param"
LIG_SEP = "ligand separation param"

defaults = {
	LIG_POS: "mid",
	LIG_SEP: 2.8,
}

# so the defaults above can be used elsewhere, send a copy of the dictionary...
prefs = preferences.addCategory("Metal Geometry", preferences.HiddenCategory,
						optDict=defaults.copy())
