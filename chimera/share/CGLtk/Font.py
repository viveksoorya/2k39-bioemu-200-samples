# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: AngleCounter.py 26655 2009-01-07 22:02:30Z gregc $

"""utility font routines"""

def shrinkFont(widget, fraction=0.75, slant=None):
	from tkFont import Font
	font = Font(font=widget.cget('font'))
	kw = {}
	if slant:
		kw['slant'] = slant
	font.config(size=int(fraction * float(font.cget('size'))), **kw)
	widget.config(font=font)
