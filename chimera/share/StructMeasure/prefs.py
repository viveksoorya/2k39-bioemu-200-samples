# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 39506 2014-01-30 00:31:54Z pett $

from chimera import preferences

ROT_LABEL = "rot label"
ROT_DIAL_SIZE = "dial size"
ANGLE_PRECISION = "angle precision"
TORSION_PRECISION = "torsion precision"
SHOW_DEGREE_SYMBOL = "show degree symbol"
AXIS_RADIUS = "axis radius"
AXIS_SEL_OBJ = "axis sel obj"
AXIS_SEL_ATOMS = "axis sel atoms"
OBJ_SEL_AXIS = "obj sel axis"
ATOMS_SEL_AXIS = "atoms sel axis"
PLANE_THICKNESS = "plane thickness"
CENTROID_RADIUS = "centroid radius"
DIST_COLOR = "distance color"
DIST_LINE_TYPE = "distance line type"
DIST_LINE_WIDTH = "distance line width"

import chimera
defaults = {
	ROT_LABEL: 'None',
	ROT_DIAL_SIZE: 1,
	ANGLE_PRECISION: 3,
	TORSION_PRECISION: 3,
	SHOW_DEGREE_SYMBOL: True,
	AXIS_RADIUS: 1,
	AXIS_SEL_OBJ: True,
	AXIS_SEL_ATOMS: False,
	OBJ_SEL_AXIS: True,
	ATOMS_SEL_AXIS: False,
	PLANE_THICKNESS: 0.1,
	CENTROID_RADIUS: 2.0,
	DIST_COLOR: "yellow",
	DIST_LINE_TYPE: chimera.Dash,
	DIST_LINE_WIDTH: 1.0
}

# so the defaults above can be used elsewhere, send a copy of the dictionary...
prefs = preferences.addCategory("Struct Measure", preferences.HiddenCategory,
						optDict=defaults.copy())
