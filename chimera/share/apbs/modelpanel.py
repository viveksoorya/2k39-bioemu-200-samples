# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

def callback(molecules):
	from gui import ApbsDialog
	from chimera import dialogs
	d = dialogs.find(ApbsDialog.name, create=True)
	d.setMolecules(molecules)
	d.enter()
