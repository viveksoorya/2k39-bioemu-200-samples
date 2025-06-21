# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 30806 2010-06-26 01:02:29Z goddard $

import chimera
from chimera import preferences

INCLUDE_THUMB = "include thumbnail"
THUMB_SIZE = "thumbnail size"

options = {
	INCLUDE_THUMB: True,
	THUMB_SIZE: "medium",
}
prefs = preferences.addCategory("SimpleSession", preferences.HiddenCategory,
							optDict=options)
