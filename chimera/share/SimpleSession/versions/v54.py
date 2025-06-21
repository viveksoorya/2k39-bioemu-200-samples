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

from v53 import *

import globals # so that various version files can easily access same variables
import chimera

_restoreViewer = restoreViewer
def restoreViewer(viewerInfo):
	va = viewerInfo['viewerAttrs']
	if 'backgroundGradient' in va:
		from chimera.paletteoptions import prefToGradient
		bgg = va['backgroundGradient']
		if bgg[0]:
			bgg[0:2] = prefToGradient(bgg[0:2])
		va['backgroundGradient'] = bgg
	if 'backgroundImage' in va:
		from PIL import Image
		bgi = va['backgroundImage']
		if bgi[0]:
			mode, size, data = bgi[0]
			bgi[0] = Image.fromstring(mode, size, data)
		va['backgroundImage'] = bgi
	if 'screenWidthMM' in viewerInfo:
		if not chimera.nogui:
			from chimera import tkgui
			tkgui.setScreenMMWidth(viewerInfo['screenWidthMM'])
		
	_restoreViewer(viewerInfo)

