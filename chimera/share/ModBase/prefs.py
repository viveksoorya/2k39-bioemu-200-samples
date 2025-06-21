# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: prefs.py 34349 2011-08-30 02:50:52Z yz $

from chimera import preferences

SHOWN_COLS = "shown columns"

GA341_COL = "GA341"
ZDOPE_COL = "zDOPE"
TSV_RMSD_COL = "Estimated RMSD"
TSV_OVERLAP_COL = u"Estimated Overlap (3.5\N{ANGSTROM SIGN})"
COLS = (GA341_COL, ZDOPE_COL, TSV_RMSD_COL, TSV_OVERLAP_COL)

GA341_PDB = "MODEL SCORE"
ZDOPE_PDB = "zDOPE"
TSV_RMSD_PDB = "PREDICTED RMSD"
TSV_OVERLAP_PDB = "PREDICTED NO35"
PDBS = (GA341_PDB, ZDOPE_PDB, TSV_RMSD_PDB, TSV_OVERLAP_PDB)

col2pdb = {}
for col, pdb in zip(COLS, PDBS):
	col2pdb[col] = pdb

colAttr = {
	"Template PDB":		( "TEMPLATE PDB", "%s" ),
	"Template Chain":	( "TEMPLATE CHAIN", "%s" ),
	"Template Begin":	( "TEMPLATE BEGIN", "%d" ),
	"Template End":		( "TEMPLATE END", "%d" ),
	GA341_COL:		( GA341_PDB, "%.2f" ),
	ZDOPE_COL:		( ZDOPE_PDB, "%.2f" ),
	TSV_RMSD_COL:		( TSV_RMSD_PDB, "%.3f" ),
	TSV_OVERLAP_COL:		( TSV_OVERLAP_PDB, "%.3f" ),
	"ModPipe Quality Score":		( "ModPipe Quality Score", "%.2f" ),
	"E-value":		( "EVALUE", "%.2e" ),
	"Experiment Type":	( "EXPERIMENT TYPE", "%s" ),
	"Method":		( "METHOD", "%s" ),
	"ModPipe Alignment Id":	( "MODPIPE ALIGNMENT ID", "%s" ),
	"ModPipe Model Id":	( "MODPIPE MODEL ID", "%s" ),
	"ModPipe Run":		( "MODPIPE RUN", "%s" ),
	"Program":		( "PROGRAM", "%s" ),
	"Sequence Identity":	( "SEQUENCE IDENTITY", "%.1f" ),
	"Target Begin":		( "TARGET BEGIN", "%d" ),
	"Target End":		( "TARGET END", "%d" ),
	"Target Length":	( "TARGET LENGTH", "%d" ),
	"fit rotation":		( "FIT ROTATION", "%.3f %.3f %.3f %.3f"),
	"fit translation":	( "FIT TRANSLATION", "%.3f %.3f %.3"),
	"match size":		( "MATCH SIZE", "%.2f"),
	"match average distance": ("MATCH AVERAGE DISTANCE", "%d"),
	"cluster size":	("CLUSTER SIZE","%.3f"),
	"fitting score":	("FITTING SCORE","%.3f %.3f %.3f %.3f"),
	"dock rotation":	("DOCK ROTATION","%.3f %.3f %.3f"),
	"dock translation":	("DOCK TRANSLATION","%d"),
}

attrMap = {
	GA341_PDB:		"modScore_GA341",
	"GA341":	"modScore_GA341",
	"DOPE":	"modScore_DOPE",
	"molpdf":	"modScore_molpdf",
	ZDOPE_PDB:		"modScore_zDOPE",
	TSV_RMSD_PDB:		"modScore_estRMSD",
	TSV_OVERLAP_PDB:		"modScore_estOverlap",
	"ModPipe Quality Score":		"modScore_MPQS",
	"EVALUE":		"modbaseEvalue",
	"SEQUENCE IDENTITY":	"modbaseSequenceIdentity",
}

colOrder = [
	GA341_COL,
	"ModPipe Quality Score",
	ZDOPE_COL,
	TSV_RMSD_COL,
	TSV_OVERLAP_COL,
	"Sequence Identity",
	"E-value",
	"Template PDB",
	"Template Chain",
	"Template Begin",
	"Template End",
	"Target Length",
	"Target Begin",
	"Target End",
	"ModPipe Run",
	"ModPipe Model Id",
	"ModPipe Alignment Id",
	"Program",
	"Experiment Type",
	"Method",
]

colOrderModellerResults = [
	GA341_COL,
	ZDOPE_COL,
	TSV_RMSD_COL,
	TSV_OVERLAP_COL,
]

defaults = {
	"Template PDB": True,
	"GA341": True,
	"ModPipe Quality Score": True,
	"zDOPE": True,
	"E-value": True,
	"Sequence Identity": True,
	"Target Begin": True,
	"Target End": True,
}

# so the defaults above can be used elsewhere, send a copy of the dictionary...
prefs = preferences.addCategory("ModBase", preferences.HiddenCategory,
						optDict=defaults.copy())
