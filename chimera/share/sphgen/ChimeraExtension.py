# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import sphgen
from chimera import fileInfo, FileInfo
fileInfo.register("Sphgen spheres",			# name of file type
			sphgen.openSphgen,		# function to call
			['.sph'],			# extensions
			['sph'],			# prefixes
			category=FileInfo.GENERIC3D)	# category
