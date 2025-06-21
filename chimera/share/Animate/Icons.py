# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---


from PIL import Image
import os.path as osPath

# Animation icons
path2icons = osPath.join(osPath.dirname(__file__), 'icons')

def LoadImage(filename):
	"Return animation icon as a PIL Image (or None)"
	filepath = osPath.join(path2icons, filename)
	if osPath.exists(filepath):
		image = Image.open(filepath)
	else:
		image = None
	return image
