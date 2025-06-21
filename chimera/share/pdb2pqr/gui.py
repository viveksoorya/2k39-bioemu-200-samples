# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera
from chimera.baseDialog import ModelessDialog

# Options
from chimera.tkoptions import BooleanOption, FloatOption, OutputFileOption
_Options = [
	# attribute name, title,
	#		enabled, option type, default value, additional keywords
	( "propka", "Use PROPKA to predict protonation states",
			True, BooleanOption, False, {} ),
	( "propkaph", "pH value to use with PROPKA",
			False, FloatOption, 7.0, { "min":0.0, "max":14.0 } ),
	( "neutraln", "Make protein N-terminus neutral (PARSE only)",
			True, BooleanOption, False, {} ),
	( "neutralc", "Make protein C-terminus neutral (PARSE only)",
			True, BooleanOption, False, {} ),
	( "debump", "Debump added atoms",
			True, BooleanOption, True, {} ),
	( "optHbond", "Optimize hydrogen bonds",
			True, BooleanOption, True, {} ),
	( "distanceCutoff", "Hydrogen bond distance cutoff",
			True, FloatOption, 3.4, { "min":0.0, "max":10.0 } ),
	( "angleCutoff", "Hydrogen bond angle cutoff",
			True, FloatOption, 30.0, { "min":0.0, "max":90.0 } ),
	( "hbonds", "Report hydrogen bonds in Reply Log",
			True, BooleanOption, False, {} ),
	( "ligands", "Assign charges to ligands",
			True, BooleanOption, False, {} ),
	( "apbs", "Display APBS control file in Reply Log",
			True, BooleanOption, False, {} ),
]

from chimera import preferences
options = dict()
for opt in _Options:
	options[opt[0]] = opt[4]
del opt
prefs = preferences.addCategory("pdb2pqr", preferences.HiddenCategory,
							optDict=options)

class Pdb2pqrDialog(ModelessDialog):
	name = "Pdb2pqrDialog"
	title = "Assign Charges and Radii with PDB2PQR"
	help = "ContributedSoftware/apbs/pdb2pqr.html"
	buttons = ("OK", "Apply", "Close")
	default = "OK"

	def __init__(self, *args, **kw):
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		# Fill in Tkinter user interface in parent frame
		self._makeMainDialog(parent)
		self._makeOptions(parent)
		self._makeWSLocation(parent)
		self._restorePreferences()
		self._ffCB(self.ffMenu, False)
		self._propkaCB(self.propka, False)

	def _makeMainDialog(self, parent):
		import Tkinter
		f = Tkinter.Frame(parent)
		f.pack(fill="x")
		row = 0
		from chimera.tkoptions import MoleculeOption
		self.molMenu = MoleculeOption(f, row, "Molecule", None, None)
		row += 1
		from chimera.tkoptions import EnumOption
		from ws import ForceFields, FFDefault
		class ForceFieldOption(EnumOption):
			values = ForceFields
		self.ffMenu = ForceFieldOption(f, row,
						"Force field",
						ForceFields[FFDefault],
						self._ffCB)
		row += 1
		self.pqr = OutputFileOption(f, row,
						"PQR output file (optional)",
						None, None,
						filters=[ ("PQR",
								"*.pqr",
								".pqr") ])

	def _makeOptions(self, parent):
		from chimera.widgets import DisclosureFrame
		df = DisclosureFrame(parent, text="Options")
		df.pack(fill="x")
		sf = df.frame
		row = 0
		for attr, title, enabled, opt, default, kw in _Options:
			if attr == "propka":
				cb = self._propkaCB
			else:
				cb = self._recordPrefCB
			w = opt(sf, row, title, default, cb, **kw)
			if not enabled:
				w.disable()
			w.attr = attr
			setattr(self, attr, w)
			row += 1

	def _makeWSLocation(self, parent):
		from WebServices.gui import addServiceSelector
		from ws import Pdb2pqr
		backends = (
			# No replacement available for NBCR service
			#( "opal", (Pdb2pqr.ServiceName, Pdb2pqr.ServiceURL ) ),
			( "local", ( "", None ) ),
		)
		df, self.serviceLocation = addServiceSelector(parent, self.name,
								backends)
		df.pack(fill="x")

	def _restorePreferences(self):
		for opt in _Options:
			getattr(self, opt[0]).set(prefs[opt[0]])
		try:
			self.ffMenu.set(prefs["ff"])
		except KeyError:
			pass

	def _ffCB(self, opt, record=True):
		if opt.get() == "PARSE":
			self.neutraln.enable()
			self.neutralc.enable()
		else:
			self.neutraln.disable()
			self.neutralc.disable()
		if record:
			prefs["ff"] = opt.get()

	def _propkaCB(self, opt, record=True):
		if opt.get():
			self.propkaph.enable()
		else:
			self.propkaph.disable()
		if record:
			self._recordPrefCB(opt)

	def _recordPrefCB(self, opt):
		prefs[opt.attr] = opt.get()

	def setMolecules(self, molecules):
		self.molMenu.setitems(molecules)

	def Apply(self):
		m = self.molMenu.get()
		backend, service, server = self.serviceLocation.getLocation()
		kw = {
			"serviceType": backend,
			"serviceName": service,
			"serviceURL": server,
			"molecule": m,
			"forcefield": self.ffMenu.get(),
			"hbonds": self.hbonds.get(),
			"propkaph": (self.propka.get() and self.propkaph.get()
									or ""),
			"debump": self.debump.get(),
			"apbs": self.apbs.get(),
			"pqr": self.pqr.get(),
			"neutraln": self.neutraln.get(),
			"neutralc": self.neutralc.get(),
			"optHbond": self.optHbond.get(),
			"angleCutoff": self.angleCutoff.get(),
			"distCutoff": self.distanceCutoff.get(),
			"ligands": self.ligands.get(),
		}
		from ws import Pdb2pqr
		Pdb2pqr(**kw)
		from chimera import replyobj
		replyobj.info("PDB2PQR initiated for %s\n" % m.name)

from chimera import dialogs
dialogs.register(Pdb2pqrDialog.name, Pdb2pqrDialog)
