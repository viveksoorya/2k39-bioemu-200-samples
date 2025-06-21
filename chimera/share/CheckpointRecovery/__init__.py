# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

def recover():
	import chimera
	if chimera.nogui:
		return
	from chimera.preferences import preferences
	mainPrefFile = preferences.filename()
	if not mainPrefFile:
		return
	from chimera.printer import ImageSaveDialog
	import os
	imageRecoveryFile = os.path.join(os.path.dirname(mainPrefFile),
		ImageSaveDialog.crashRecoveryName)
	if not os.path.exists(imageRecoveryFile):
		return
	from gui import RecoveryDialog
	RecoveryDialog(imageRecoveryFile)
