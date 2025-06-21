# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 38963 2013-07-23 23:32:40Z pett $

from chimera import preferences

SCRIPT_PYTHON = "Python"
SCRIPT_CHIMERA = "Chimera commands"

SCRIPT_TYPE = "script type"
DICT_NAME = "substitution dictionary name"
FRAME_TEXT = "frame # substitution text"
ZERO_PAD = "zero pad frame numbers"

RMSD_MIN = "rmsd min"
RMSD_MAX = "rmsd max"
RMSD_AUTOCOLOR = "rmsd autocolor"

VOLUME_CUTOFF = "volume cutoff"
VOLUME_RESOLUTION = "volume resolution"
VOLUME_ATOM_RADII_TREATMENT = "volume atom radii handling"

RECORDER_RECORD_ARGS = "record args"
RECORDER_ENCODE_ARGS = "encode args"
RECORDER_ROUNDTRIP = "roundtrip"

PLOTS_LAST_USE = "plots last use"

RES_NET_WEIGHTING = "weight res interactions by #contacts"
RES_NET_IGNORE_BONDED = "ignore bonded residues in network"
RES_NET_SOLVENT_NODE = "treat solvent as one node"
RES_NET_IONS_NODE = "treat ions as one node"
RES_NET_EDGE_DISCARD_FRAC = "value edge-discard threshold"
RES_NET_EDGE_DISCARD_WEIGHT = "weight edge-discard threshold"
RES_NET_EDGE_HIST_MARKERS = "res net edge coloring histogram markers"
RES_NET_EDGE_WIDTH = "res net edge width"
RES_NET_INTERACTION_TYPE = "res net interaction type"

options = {
	SCRIPT_TYPE: SCRIPT_CHIMERA,
	DICT_NAME: "mdInfo",
	FRAME_TEXT: "<FRAME>",
	ZERO_PAD: True,
	RMSD_MIN: 0.5,
	RMSD_MAX: 3.0,
	RMSD_AUTOCOLOR: True,
	VOLUME_CUTOFF: 10.0,
	VOLUME_RESOLUTION: 1.0,
	VOLUME_ATOM_RADII_TREATMENT: "ignored",
	RECORDER_RECORD_ARGS: "",
	RECORDER_ENCODE_ARGS: "",
	RECORDER_ROUNDTRIP: False,
	PLOTS_LAST_USE: None,
	RES_NET_WEIGHTING: True,
	RES_NET_IGNORE_BONDED: True,
	RES_NET_SOLVENT_NODE: True,
	RES_NET_IONS_NODE: True,
	RES_NET_EDGE_DISCARD_FRAC: 0.25,
	RES_NET_EDGE_DISCARD_WEIGHT: 0.5,
	RES_NET_EDGE_HIST_MARKERS: (
		# non-difference network; unweighted
		([((0.25, 0.0), "light gray"), ((0.5, 0.0), "dark gray"), ((0.75, 0.0), "black")],
		# non-difference network; weighted
		[((1.0, 0.0), "light gray"), ((3.0, 0.0), "dark gray"), ((5.0, 0.0), "black")]),
		# difference network; unweighted
		([((-0.75, 0.0), "magenta"), ((0.00, 0.0), "black"), ((0.75, 0.0), "cyan")],
		# difference network; weighted
		[((-2.0, 0.0), "magenta"), ((0.0, 0.0), "black"), ((2.0, 0.0), "cyan")]),
	),
	RES_NET_EDGE_WIDTH: 5,
	RES_NET_INTERACTION_TYPE: "H-bonds"
}
prefs = preferences.addCategory("MD Movie", preferences.HiddenCategory,
							optDict=options)
