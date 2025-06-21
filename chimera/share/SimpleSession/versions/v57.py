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

from v56 import *
from v23 import alignModels, lowestIdXform

import globals # so that various version files can easily access same variables
import chimera

def endRestore(sesKw):
	import SimpleSession
	alignModels(SimpleSession.preexistingModels)
	del SimpleSession.registerAfterModelsCB
	del SimpleSession.reportRestoreError
	del SimpleSession.findFile
	del SimpleSession.getColor
	del SimpleSession.idLookup
	del SimpleSession.modelMap
        del SimpleSession.modelOffset
        del SimpleSession.preexistingModels
	del globals.colorMap
	del globals.colorInfo
	del globals.dirRemappings
	del globals.afterModelsCBs
	del globals.sessionMap
	from SimpleSession import END_RESTORE_SESSION
	chimera.triggers.activateTrigger(END_RESTORE_SESSION, (1, sesKw))
	del SimpleSession.mergedSession
