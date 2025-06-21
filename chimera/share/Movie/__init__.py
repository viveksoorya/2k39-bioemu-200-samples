#!/usr/bin/env python

# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import sys, os

def Movie(movieFile=None):
	from Movie.gui import MovieDialog
	from Trajectory import EnsembleLoader
        EnsembleLoader.loadEnsemble(MovieDialog, movieFile=movieFile)

def restoreSession(info, mdDialog=None, **kw):
	if 'model' in info:
		from Trajectory import Ensemble
		from chimera import CancelOperation
		try:
			ensemble = Ensemble(None, sesInfo=info['model'])
		except CancelOperation:
			from chimera import replyobj
			replyobj.info("MD Movie interface restore cancelled by user.\n")
			return
	else:
		from SimpleSession import idLookup
		mol = idLookup(info['molecule'])
		class FakeEnsemble:
			molecule = mol
			startFrame = info['startFrame']
			endFrame = info['endFrame']
			name = info['name']
			_length = info['length']
			def __len__(self):
				return self._length
		ensemble = FakeEnsemble()
	
	if mdDialog is None:
		from Movie.gui import MovieDialog as mdDialog
	mdDialog(ensemble, fromSession=True, **kw)
