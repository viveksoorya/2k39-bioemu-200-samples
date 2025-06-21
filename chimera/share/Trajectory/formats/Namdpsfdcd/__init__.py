# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 34710 2011-10-20 21:23:37Z pett $

formatName = "NAMD (PSF/DCD)"

from Trajectory import DCD

class ParamGUI(DCD.ParamGUI):
	formatName = formatName

loadEnsemble = DCD.loadEnsemble
