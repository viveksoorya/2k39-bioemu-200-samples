# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 32300 2011-01-12 01:07:29Z pett $

from chimera import preferences

CHARGE_METHOD = "charge method"
MEMORIZED_SETTINGS = "memorized settings"

options = {
	CHARGE_METHOD: "AM1-BCC",
	MEMORIZED_SETTINGS: {}
}
prefs = preferences.addCategory("AddCharge", preferences.HiddenCategory,
							optDict=options)
