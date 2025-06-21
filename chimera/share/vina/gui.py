# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

from chimera import tkoptions, UserError

CautionMsg = """The Autodock Vina web service is hosted by the National Biomedical Computation Resource (NBCR), and is freely available to users across the Internet.  Because it is a shared resource, there is a limit to the resources permitted to run each job.  A typical Vina job may run for several minutes, to several hours, to even days.  Jobs that take more than the permitted time are terminated before any results are available.  To take best advantage of the NBCR resource, you should limit the receptor search volume (e.g., choose only the receptor site instead of the whole molecule).  Also, please do not submit identical job requests; if the first request fails, then subsequent ones will too.

Do you wish to continue?"""

# Advanced options
_AdvOpts = [
	# attribute name, title, enabled,
	#		option type, default value, additional keywords
	( "_num_modes", "Number of binding modes", True,
			tkoptions.SliderOption, 9,
			{ "min":1, "max":10, "step":1 }, int ),
	( "_exhaustiveness", "Exhaustiveness of search", True,
			tkoptions.SliderOption, 8,
			{ "min":1, "max":8, "step":1 }, int ),
	( "_energy_range", "Maximum energy difference (kcal/mol)", True,
			tkoptions.SliderOption, 3,
			{ "min":1, "max":3, "step":1 }, int ),
]

# Receptor preparation options
_ReceptorOpts = [
	# attribute name, title, enabled,
	#		option type, default value, additional keywords
	( "_addHyd", "Add hydrogens in Chimera", True,
			tkoptions.BooleanOption, True, {}, None ),
	( "_nphs", "Merge charges and remove non-polar hydrogens", True,
			tkoptions.BooleanOption, True, {}, None ),
	( "_lps", "Merge charges and remove lone pairs", True,
			tkoptions.BooleanOption, True, {}, None ),
	( "_waters", "Ignore waters", True,
			tkoptions.BooleanOption, True, {}, None ),
	( "_nonstdres", "Ignore chains of non-standard residues", True,
			tkoptions.BooleanOption, True, {}, None ),
	( "_nonstd", "Ignore all non-standard residues", True,
			tkoptions.BooleanOption, False, {}, None ),
]

#class _LigandOption(tkoptions.EnumOption):
#	values = [
#		"single ligand",
#		"screening library",
#	]
#
#class _LigandDbOption(tkoptions.SymbolicEnumOption):
#	values = [
#		"sample",
##		"NCIDS_SC",
##		"NCI_DS3",
#	]
#	labels = [
#		"Sample database (6 ligands)",
##		"NCI Diversity Set 1 with rotamers",
##		"NCI Diversity Set 3",
#	]

# Ligand preparation options
_LigandOpts = [
	# attribute name, title, enabled,
	#		option type, default value, additional keywords
	( "_ligand_nphs", "Merge charges and remove non-polar hydrogens", True,
			tkoptions.BooleanOption, True, {}, None ),
	( "_ligand_lps", "Merge charges and remove lone pairs", True,
			tkoptions.BooleanOption, True, {}, None ),
]

from chimera import preferences
options = dict()
for opt in (_AdvOpts + _ReceptorOpts + _LigandOpts):
	options[opt[0]] = opt[4]
del opt
#options["dockWith"] = _LigandOption.values[0]
#options["database"] = _LigandDbOption.values[0]
prefs = preferences.addCategory("autodock vina", preferences.HiddenCategory,
							optDict=options)

from chimera.baseDialog import ModelessDialog
class VinaDialog(ModelessDialog):
	name = "VinaDialog"
	title = "AutoDock Vina"
	help = "ContributedSoftware/vina/vina.html"
	buttons = ("OK", "Apply", "Close")
	default = "OK"
	provideStatus = True

	def __init__(self, sessionData=None, *args, **kw):
		ModelessDialog.__init__(self, *args, **kw)
		if sessionData is not None:
			self._restoreSession(sessionData)
		else:
			self._restorePreferences()
		self._updateOkay()
		from chimera.extension import manager
		manager.registerInstance(self)
		import chimera
		from SimpleSession import SAVE_SESSION
		self._saveSesHandler = chimera.triggers.addHandler(
						SAVE_SESSION,
						self._saveSessionCB, None)
		self._closeSesHandler = chimera.triggers.addHandler(
						chimera.CLOSE_SESSION,
						self.emQuit, None)
		self._confirmed = False

	def destroy(self):
		self.deleteSearchVolume()
		if self._saveSesHandler:
			import chimera
			from SimpleSession import SAVE_SESSION
			chimera.triggers.deleteHandler(SAVE_SESSION,
							self._saveSesHandler)
			self._saveSesHandler = None
		if self._closeSesHandler:
			chimera.triggers.deleteHandler(chimera.CLOSE_SESSION,
							self._closeSesHandler)
			self._closeSesHandler = None
		from chimera.extension import manager
		manager.deregisterInstance(self)
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		row = 0
		self.outputFile = None
		self.output = tkoptions.OutputFileOption(parent, row,
						"Output file",
						None, self._outputCB,
						filters=[ ("pdbqt",
								"*.pdbqt",
								".pdbqt") ])
		row += 1
		self.receptorMenu = tkoptions.MoleculeOption(parent, row,
						"Receptor", None, None,
						command=self._receptorCB)
		self.receptor = self.receptorMenu.get()
		row += 1

#		self.dockWith = _LigandOption(parent, row, "Dock with",
#						_LigandOption.values[0],
#						self._dockWithCB)
#		row += 1
#
		self.ligandMenu = tkoptions.MoleculeOption(parent, row,
							"Ligand", None, None,
							command=self._ligandCB)
		self.ligand = self.ligandMenu.get()
		row += 1

#		self.database = _LigandDbOption(parent, row, "Ligand database",
#						_LigandDbOption.values[0],
#						self._databaseCB)
#		row += 1
#		from Tkinter import Label
#		Label(parent, text="Only sample database is enabled due to\n"
#				"resource restrictions.  Please press Help\n"
#				"button below for more information.",
#		Label(parent, text="Only sample database is enabled due to\n"
#				"resource restrictions.",
#				justify="left").grid(column=1, row=row)
#		row += 1

		row = self._makeSearchVolumeOptions(parent, row)
		row = self._makeReceptorOptions(parent, row)
		row = self._makeLigandOptions(parent, row)
		row = self._makeAdvOptions(parent, row)
		row = self._makeWSLocation(parent, row)

#		self._dockWithCB()

	def _outputCB(self, opt):
		self.outputFile = opt.get()
		if self.outputFile:
			import os.path
			self.outputBase, ext = os.path.splitext(self.outputFile)
		else:
			self.outputBase = None
		self._updateOkay()

	def _receptorCB(self, ignore):
		receptor = self.receptorMenu.get()
		if receptor is self.receptor:
			return
		self.receptor = receptor
		self.deleteSearchVolume()
		self._updateOkay()

	def _addOptions(self, parent, opts, cb):
		optRow = 0
		for attr, title, enabled, opt, default, kw, cvt in opts:
			if attr.startswith('_'):
				s = title
			else:
				s = "%s (%s)" % (title, attr)
			w = opt(parent, optRow, s, default, cb, **kw)
			if not enabled:
				w.disable()
			setattr(self, attr, w)
			optRow += 1

	def _makeAdvOptions(self, parent, row):
		from chimera.widgets import DisclosureFrame
		df = DisclosureFrame(parent, text="Advanced options")
		df.grid(row=row, column=0, columnspan=2, sticky="ew")
		sf = df.frame
		self._addOptions(df.frame, _AdvOpts, self._advoptCB)
		return row + 1

	def _advoptCB(self, opt):
		for opt in _AdvOpts:
			prefs[opt[0]] = getattr(self, opt[0]).get()

	def _makeSearchVolumeOptions(self, parent, row):
		from chimera.widgets import DisclosureFrame
		df = DisclosureFrame(parent,
					text="Receptor search volume options",
					collapsed=False)
		df.grid(row=row, column=0, columnspan=2, sticky="ew")
		sf = df.frame
		self.searchVolume = None

		# Shamelessly stolen from VolumeViewer
		from CGLtk import Hybrid
		sr = Hybrid.Checkbutton(sf, "Resize search volume using ", 0)
		sr.button.grid(row=0, column=0, sticky="w")
		self.searchVolumeActive = sr.variable
		sr.callback(self._searchVolumeCB)

		srm = Hybrid.Option_Menu(sf, '',
			'button 1', 'button 2', 'button 3',
			'ctrl button 1', 'ctrl button 2', 'ctrl button 3')
		srm.variable.set('button 2')
		srm.frame.grid(row=0, column=1, sticky="w")
		srm.add_callback(self._searchVolumeButtonCB)
		self.searchVolumeButtonMenu = srm

		from Tkinter import Frame
		f = Frame(sf)
		f.grid(row=2, column=0, columnspan=2, sticky="ew")
		from chimera.tkoptions import Float3TupleOption
		self.searchVolumeCenter = Float3TupleOption(f, 0,
						"Center", None,
						self._searchVolumeTextCB,
						horizontal=True)
		self.searchVolumeSize = Float3TupleOption(f, 1,
						"Size", None,
						self._searchVolumeTextCB,
						horizontal=True)

		return row + 1

	def _searchVolumeCB(self):
		sv = self.searchVolume
		if self.searchVolumeActive.get() and self.receptor:
			sv = self.getSearchVolume()	# creates search volume
			button, modifiers = self._searchVolumeButtonSpec()
			sv.bind_mouse_button(button, modifiers)
		else:
			if sv is not None:
				sv.unbind_mouse_button()

	def _searchVolumeButtonCB(self):
		if self.searchVolumeActive.get() and self.searchVolume:
			button, modifiers = self._searchVolumeButtonSpec()
			self.searchVolume.bind_mouse_button(button, modifiers)

	def _searchVolumeChangedCB(self, initial_box):
		if not self.searchVolume.hasBounds():
			self.searchVolumeCenter.clear()
			self.searchVolumeSize.clear()
			return
		center, size = self.receptorBounds()
		self.searchVolumeCenter.set(center)
		self.searchVolumeSize.set(size)
		self._updateOkay()

	def _searchVolumeTextCB(self, widget):
		center = self.searchVolumeCenter.get()
		size = self.searchVolumeSize.get()
		self.setReceptorBounds(center, size)
		self._updateOkay()

	_ButtonNameSpecMap = {
		'button 1':('1', []),
		'button 2':('2', []),
		'button 3':('3', []),
		'ctrl button 1':('1', ['Ctrl']),
		'ctrl button 2':('2', ['Ctrl']),
		'ctrl button 3':('3', ['Ctrl'])
	}
	def _searchVolumeButtonSpec(self):
		name = self.searchVolumeButtonMenu.variable.get()
		return self._ButtonNameSpecMap[name]

	def _makeReceptorOptions(self, parent, row):
		from chimera.widgets import DisclosureFrame
		df = DisclosureFrame(parent, text="Receptor options")
		df.grid(row=row, column=0, columnspan=2, sticky="ew")
		self._addOptions(df.frame, _ReceptorOpts, self._recoptCB)
		return row + 1

	def _recoptCB(self, opt):
		for opt in _ReceptorOpts:
			prefs[opt[0]] = getattr(self, opt[0]).get()

#	def _dockWithCB(self, ignore=None):
#		prefs["dockWith"] = self.dockWith.get()
#		if self.dockWith.get() == "single ligand":
#			self.ligandMenu.enable()
#			self.ligandOptionFrame.enable()
#			for opt in _LigandOpts:
#				getattr(self, opt[0]).enable()
#			self.database.disable()
#		else:
#			self.ligandMenu.disable()
#			self.ligandOptionFrame.disable()
#			for opt in _LigandOpts:
#				getattr(self, opt[0]).disable()
#			self.database.enable()

	def _ligandCB(self, ignore):
		ligand = self.ligandMenu.get()
		if ligand is self.ligand:
			return
		self.ligand = ligand
		self._updateOkay()

#	def _databaseCB(self, ignore):
#		prefs["database"] = self.database.get()

	def _makeLigandOptions(self, parent, row):
		from chimera.widgets import DisclosureFrame
		df = DisclosureFrame(parent, text="Ligand options")
		df.grid(row=row, column=0, columnspan=2, sticky="ew")
		self._addOptions(df.frame, _LigandOpts, self._ligoptCB)
		self.ligandOptionFrame = df
		return row + 1

	def _ligoptCB(self, opt):
		for opt in _LigandOpts:
			prefs[opt[0]] = getattr(self, opt[0]).get()

	def _makeWSLocation(self, parent, row):
		from WebServices.gui import addServiceSelector
		from ws import VinaDocking
		backends = (
			# No replacement available for NBCR service
			#( "opal", ( VinaDocking.ServiceName,
			#		VinaDocking.ServiceURL ) ),
			( "local", ( "", None ) ),
		)
		df, self.serviceLocation = addServiceSelector(parent, self.name,
								backends)
		df.grid(row=row, column=0, columnspan=2, sticky="ew")
		return row + 1

	def deleteSearchVolume(self):
		sv = self.searchVolume
		if not sv:
			return
		sv.unbind_mouse_button()
		sv.delete_box()
		sv.last_subregion = ( None, None )
		self.searchVolume = None
		self.searchVolumeActive.set(False)

	def getSearchVolume(self):
		if self.searchVolume is None:
			from SearchVolume import SearchVolume
			self.searchVolume = SearchVolume(self.receptor,
						self._searchVolumeChangedCB,
						"AutoDock Vina Search Volume")
		return self.searchVolume

	def _updateOkay(self):
		msg = ""
		if not self.output.get():
			msg = "no output file selected"
		elif not self.receptor:
			msg = "no receptor selected"
		elif not self.searchVolume or not self.searchVolume.hasBounds():
			msg = "no search volume selected"
		elif not self.ligand:
			msg = "no ligand selected"
#		elif self.dockWith.get() == "single ligand":
#			if not self.ligand:
#				msg = "no ligand selected"
#			elif self.ligand is self.receptor:
#				msg = "ligand and receptor are the same"
		s = msg and "disabled" or "normal"
		self.status(msg, blankAfter=0)
		for buttonName in [ "OK", "Apply" ]:
			self.buttonWidgets[buttonName].config(state=s)

	def pathForExtension(self, ext):
		if not self.outputBase:
			raise UserError("output file not set")
		from OpenSave import tildeExpand
		return tildeExpand(self.outputBase) + ext

	def prepareReceptor(self):
		pdbFile = self.pathForExtension(".receptor.pdb")
		receptorFile = self.pathForExtension(".receptor.pdbqt")
		refModel = self.searchVolume.box_model.model()
		import Midas
		Midas.write(self.receptor, refModel, pdbFile)
		from ws import prepareReceptor
		prepareReceptor(pdbFile, receptorFile,
				self._nphs.get(), self._lps.get(),
				self._waters.get(), self._nonstdres.get(),
				self._nonstd.get())
		return receptorFile

	def prepareConf(self):
		center, size = self.receptorBounds()
		opts = dict()
		for opt in _AdvOpts:
			o = getattr(self, opt[0])
			cvt = opt[-1]
			if callable(cvt):
				opts[opt[0]] = cvt(o.get())
			else:
				opts[opt[0]] = o.get()
		confFile = self.pathForExtension(".conf")
		from ws import prepareConf
		prepareConf(confFile, center, size, opts)
		return confFile

	def receptorXform(self):
		# Return the xform of the search volume relative
		# to the receptor xform
		from chimera import Xform
		try:
			box_xform = self.searchVolume.box_model.xform()
		except AttributeError:
			box_xform = None
		if not isinstance(box_xform, Xform):
			return Xform.identity()
		xf = self.receptor.openState.xform
		xf.invert()
		xf.multiply(box_xform)
		return xf

	def receptorBounds(self):
		if not self.searchVolume.hasBounds():
			raise UserError("receptor search volume must be set")
		return self.searchVolume.bounds()

	def setReceptorBounds(self, center, size):
		self.getSearchVolume().setBounds(center, size)

	def prepareLigand(self):
		pdbFile = self.pathForExtension(".ligand.pdb")
		ligandFile = self.pathForExtension(".ligand.pdbqt")
		import Midas
		Midas.write(self.ligand, None, pdbFile)
		from ws import prepareLigand
		prepareLigand(pdbFile, ligandFile,
				self._ligand_nphs.get(), self._ligand_lps.get())
		return ligandFile

	def _runVina(self):
		self._runDocking()
#		if self.dockWith.get() == "single ligand":
#			self._runDocking()
#		else:
#			self._runScreening()

	def _runDocking(self):
		xf = self.receptorXform()
		output = self.output.get()
		from ws import VinaDocking
		backend, service, server = self.serviceLocation.getLocation()
		VinaDocking(serviceType=backend,
				serviceName=service,
				serviceURL=server,
				receptorFile=self.prepareReceptor(),
				receptor=self.receptor,
				ligandFile=self.prepareLigand(),
				ligand=self.ligand,
				confFile=self.prepareConf(),
				xform=xf,
				output=output)
		from chimera import replyobj
		replyobj.info("Autodock Vina ligand docking "
				"initiated for %s\n" % self.receptor.name)

#	def _runScreening(self):
#		xf = self.receptorXform()
#		output = self.output.get()
#		from ws import VinaScreening
#		VinaScreening(receptorFile=self.prepareReceptor(),
#				receptor=self.receptor,
#				database=self.database.get(),
#				confFile=self.prepareConf(),
#				xform=xf,
#				output=output)
#		from chimera import replyobj
#		replyobj.info("Autodock Vina screening "
#				"initiated for %s\n" % self.receptor.name)

	def OK(self):
		answer = self._confirm()
		if answer == "yes":
			self._confirmed = True
			ModelessDialog.OK(self)

	def Apply(self):
		if self.receptor is self.ligand:
			from chimera import replyobj
			replyobj.error("receptor and ligand cannot be "
					"the same model")
			return
		from ws import checkLigand
		try:
			checkLigand(self.ligand)
		except ValueError as e:
			from chimera import replyobj
			replyobj.error(str(e))
			return
		if not self._confirmed:
			answer = self._confirm()
			if answer != "yes":
				return
		else:
			# Reset for next time
			self._confirmed = False
		if self._addHyd.get():
			from AddH.unknownsGUI import initiateAddHyd
			initiateAddHyd([ self.receptor ], okCB=self._runVina)
		else:
			self._runVina()

	def _confirm(self):
		backend, service, server = self.serviceLocation.getLocation()
		if backend == "local":
			return "yes"
		from chimera.baseDialog import AskYesNoDialog
		return AskYesNoDialog(CautionMsg).run(self.uiMaster())

	def unmap(self):
		sv = self.searchVolume
		if sv:
			sv.box_model.display_box(False)
			sv.unbind_mouse_button()
		ModelessDialog.unmap(self)

	def map(self):
		sv = self.searchVolume
		if sv:
			sv.box_model.display_box(True)
			self._searchVolumeCB()
		ModelessDialog.map(self)

	def sessionData(self):
		from SimpleSession import sessionID
		def sesId(o):
			if o and not o.__destroyed__:
				return sessionID(o)
			else:
				return None
		version = 1
		advOpts = [ getattr(self, opt[0]).get()
						for opt in _AdvOpts ]
		receptorOpts = [ getattr(self, opt[0]).get()
						for opt in _ReceptorOpts ]
		searchVolumeOpts = [
			self.searchVolumeActive.get(),
			self.searchVolumeButtonMenu.variable.get(),
		]
		ligandOpts = [ getattr(self, opt[0]).get()
						for opt in _LigandOpts ]
		boxModel = (self.searchVolume and
				self.searchVolume.box_model.model()) or None
		sesData = [ version,
				self.outputFile,
				advOpts,
				sesId(self.receptor),
				receptorOpts,
				sesId(boxModel),
				searchVolumeOpts,
#				self.dockWith.get()
#				self.database.get()
				sesId(self.ligand),
				ligandOpts ]
		return sesData

	def _saveSessionCB(self, trigger, myData, sesFile):
		from SimpleSession import sesRepr
		className = self.__class__.__name__
		print >> sesFile, """
try:
	from %s import %s
	%s(sessionData=%s)
except:
	reportRestoreError("Error restoring %s instance")
""" % (self.__module__, className,
		className, sesRepr(self.sessionData()), className)

	def _restoreSession(self, sessionData):
		version = sessionData[0]
		if version == 1:
			self._restoreSession1(sessionData)
		else:
			from chimera import replyobj
			replyobj.error("cannot restore %s instance: "
					"session version %d too new" % (
						self.__class__.__name__,
						version))

	def _restoreSession1(self, sessionData):
		# Implement session restoration version=1 here
		# (should be the inverse of self.sessionData())
		( version, outputFile, advOpts, receptorId,
			receptorOpts, boxModelId,
			searchVolumeOpts,
#			dockWith, database,
			ligandId, ligandOpts ) = sessionData
		self.output.set(outputFile)
		self._outputCB(self.output)     # Force update
		for i, opt in enumerate(_AdvOpts):
			getattr(self, opt[0]).set(advOpts[i])
		from SimpleSession import idLookup
		if receptorId is not None:
			receptor = idLookup(receptorId)
			self.receptorMenu.set(receptor)
		for i, opt in enumerate(_ReceptorOpts):
			getattr(self, opt[0]).set(receptorOpts[i])
		if boxModelId is not None:
			m = idLookup(boxModelId)
			self.getSearchVolume().restore_box(m)
			self._searchVolumeChangedCB(True)
		self.searchVolumeActive.set(searchVolumeOpts[0])
		self.searchVolumeButtonMenu.variable.set(searchVolumeOpts[1])
#		self.dockWith.set(dockWith)
#		self.database.set(database)
		if ligandId is not None:
			ligand = idLookup(ligandId)
			self.ligandMenu.set(ligand)
		for i, opt in enumerate(_LigandOpts):
			getattr(self, opt[0]).set(ligandOpts[i])

	def _restorePreferences(self):
		for opt in (_AdvOpts + _ReceptorOpts + _LigandOpts):
			getattr(self, opt[0]).set(prefs[opt[0]])
#		self.dockWith.set(prefs["dockWith"])
#		self.database.set(prefs["database"])

	def emRaise(self):
		self.enter()

	def emHide(self):
		self.Close()

	def emQuit(self, *args):
		self.destroy()

from chimera import dialogs
dialogs.register(VinaDialog.name, VinaDialog)
