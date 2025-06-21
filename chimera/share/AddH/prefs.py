# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 30830 2010-06-30 18:19:39Z pett $

from chimera import preferences

HBOND_GUIDED = "hbond guided"
MEMORIZED_SETTINGS = "memorized settings"

options = {
	HBOND_GUIDED: True,
	MEMORIZED_SETTINGS: {}
}

prefs = preferences.addCategory("AddH", preferences.HiddenCategory,
							optDict=options)
