# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 39985 2014-07-15 18:35:35Z pett $

import os.path
import Tkinter
import chimera
from chimera.tkoptions import InputFileOption, OrderedFileListOption

class ParamGUI:
	"""subclass expected to provide self.formatName"""

	def __init__(self, parent):
		from Trajectory.prefs import prefs, INPUT_FILES
		inputPrefs = prefs[INPUT_FILES].setdefault(self.formatName, {})
		self.psfOption = InputFileOption(parent, 0, "PSF",
				inputPrefs.get("PSF", True), None,
				title="Choose PSF File", filters=[("PSF", ["*.psf"])],
				historyID="%s PSF" % self.formatName)
		defaultDCDs = inputPrefs.get('DCDs', None)
		if defaultDCDs is None and 'DCD' in inputPrefs:
			defaultDCDs = [inputPrefs['DCD']]
		self.addTrajKw = {'filters': [("DCD", ["*.dcd"])],
			'title': "Choose DCD File",
			'historyID': "%s DCD" % self.formatName}
		self.dcdsOption = OrderedFileListOption(parent, 1, "DCD",
			defaultDCDs, None, addKw=self.addTrajKw)
		parent.columnconfigure(1, weight=1)
		parent.rowconfigure(1, weight=1)
		f = Tkinter.Frame(parent)
		f.grid(row=2, column=0, columnspan=2)
		Tkinter.Label(f, text="PSF/DCD support courtesy of"
				).grid(row=0, column=0, sticky='e')
		from chimera import help
		if chimera.tkgui.windowSystem == "aqua":
			kw = {}
		else:
			kw = {'padx': 0}
		Tkinter.Button(f, text="MDTools", command=lambda:
			help.display("http://www.ks.uiuc.edu/~jim/mdtools/"), **kw
			).grid(row=0, column=1, sticky='w')

	def loadEnsemble(self, startFrame, endFrame, callback):
		psf = self.psfOption.get()
		dcds = self.dcdsOption.get()
		from chimera import UserError
		if not os.path.exists(psf):
			raise UserError("PSF file does not exist!")
		if not dcds:
			raise UserError("No DCD files specified")
		for dcd in dcds:
			if not os.path.exists(dcd):
				raise UserError("DCD file (%s) does not exist!" % dcd)
		from Trajectory.prefs import prefs, INPUT_FILES
		# need to change a _copy_ of the dictionary, otherwise
		# when we try to save the "original" dictionary will also
		# have our changes and no save will occur
		from copy import deepcopy
		inputPrefs = deepcopy(prefs[INPUT_FILES])
		inputPrefs[self.formatName]['PSF'] = psf
		inputPrefs[self.formatName]['DCDs'] = dcds
		prefs[INPUT_FILES] = inputPrefs

		loadEnsemble([psf] + dcds, startFrame, endFrame, callback,
			addTrajKw=self.addTrajKw)

def loadEnsemble(inputs, startFrame, endFrame, callback, relativeTo=None,
		addTrajKw={'filters': [("DCD", ["*.dcd"])], 'title': "Choose DCD File"}
		):
	from DCD import PSF_DCD
	if relativeTo:
		import os.path
		for i, f in enumerate(inputs):
			if os.path.isabs(f):
				continue
			inputs[i] = os.path.join(relativeTo, f)
	psf, dcd = inputs[:2]
	ensemble = PSF_DCD(psf, dcd, startFrame, endFrame)
	ensemble.AddTrajKw = addTrajKw
	for dcd in inputs[2:]:
		ensemble.addTraj(dcd)
	from chimera import replyobj
	replyobj.status("Creating interface", blankAfter=0)
	try:
		callback(ensemble, keepLongBonds=True)
	finally:
		replyobj.status("Interface created")
