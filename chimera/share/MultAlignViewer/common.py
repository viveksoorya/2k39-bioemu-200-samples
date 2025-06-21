# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

"""routines common to both MAV and ProfileGrids"""

def getStaticSeqs(fileNameOrSeqs, fileType=None):
	if isinstance(fileNameOrSeqs, basestring):
		fileName = fileNameOrSeqs
		seqs, fileAttrs, fileMarkups = readFile(fileName, fileType)
	else:
		seqs = fileNameOrSeqs
		fileMarkups = {}
		fileAttrs = {}
	seqs = list(seqs)
	from chimera.Sequence import StructureSequence, StaticStructureSequence
	for i, seq in enumerate(seqs):
		if isinstance(seq, StructureSequence) \
		and not isinstance(seq, StaticStructureSequence):
			seqs[i] = seq.static()
	return seqs, fileMarkups, fileAttrs

def readFile(fileName, fileType):
	from parse import parseFile
	seqs, fileAttrs, fileMarkups = parseFile(fileName, fileType, minSeqs=1)
	if not seqs:
		from chimera import UserError
		raise UserError("Found no sequences in file %s" % fileName)
	return seqs, fileAttrs, fileMarkups
