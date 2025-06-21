# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: v10.py 39155 2013-10-15 17:38:41Z pett $

from v9 import reportRestoreError, restoreWindowSize, init, \
	restoreOpenModelsAttrs, RemapDialog, beginRestore, endRestore, \
	sessionID, registerAfterModelsCB, makeAfterModelsCBs, findFile, \
	idLookup, getColor, restoreMiscAttrs, restoreSurfaces, \
	restoreOpenStates, restoreColors, restoreVdw, \
	restoreDrawModes, restoreDispChanged, restoreSelections, \
	restorePseudoBondGroups, restoreCamera, restoreMolecules, \
	noAutoRestore, autoRestorable, restoreModelClip

import globals # so that various version files can easily access same variables
import chimera

def restoreLabels(labels):
	from chimera.initprefs import PREF_LABEL, LABEL_FONT
	from chimera import preferences
	preferences.getOption(PREF_LABEL, LABEL_FONT).set(labels.pop('labelInfo'))
	for itemID, label in labels.items():
		item = idLookup(itemID)
		item.label = label
