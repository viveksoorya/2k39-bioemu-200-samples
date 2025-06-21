# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 39095 2013-09-16 21:58:31Z pett $

from chimera import preferences

CLASH_THRESHOLD = "clash threshold"
ACTION_ATTR = "mark clash"
ACTION_SELECT = "select clash"
ACTION_COLOR = "color clash"
CLASH_COLOR = "clash color"
NONCLASH_COLOR = "non-clash color"
HBOND_ALLOWANCE = "h-bond allowance"
ACTION_PSEUDOBONDS = "make pseudobonds"
PB_COLOR = "pseudobond color"
PB_WIDTH = "pseudobond width"
BOND_SEPARATION = "bond separation"
ACTION_WRITEINFO = "write info"
IGNORE_INTRA_RES = "ignore intra-residue clashes"
IGNORE_INTRA_MOL = "ignore intra-molecule clashes"
ACTION_REPLYLOG = "log info"
ACTION_REVEAL_IF_HIDDEN = "reveal hidden clash atoms"

defaults = {
	CLASH_THRESHOLD: 0.6,
	ACTION_ATTR: False,
	ACTION_SELECT: False,
	ACTION_COLOR: False,
	CLASH_COLOR: "red",
	NONCLASH_COLOR: None,
	HBOND_ALLOWANCE: 0.4,
	ACTION_PSEUDOBONDS: True,
	PB_COLOR: "yellow",
	PB_WIDTH: 2.0,
	BOND_SEPARATION: 4,
	ACTION_WRITEINFO: False,
	IGNORE_INTRA_RES: True,
	IGNORE_INTRA_MOL: False,
	ACTION_REPLYLOG: False,
	ACTION_REVEAL_IF_HIDDEN: False
}
# so that defaults dict stays unmodified, send a copy...
prefs = preferences.addCategory("DetectClash", preferences.HiddenCategory,
							optDict=defaults.copy())
