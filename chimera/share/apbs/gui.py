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
from chimera import tkoptions

class _bcflOption(tkoptions.SymbolicEnumOption):
	values = [
			"zero",
			"sdh",
			"mdh",
			"focus",
	]
	labels = [
			"zero",
			"single Debye-Huckel",
			"multiple Debye-Huckel",
	]

class _chgmOption(tkoptions.SymbolicEnumOption):
	values = [
			"spl0",
			"spl2",
			"spl4",
	]
	labels = [
			"trilinear interpolation",
			"cubic B-spline discretization",
			"quintic B-spline discretization",
	]

class _srfmOption(tkoptions.SymbolicEnumOption):
	values = [
			"mol",
			"smol",
			"spl2",
			"spl4",
	]
	labels = [
			"molecular surface",
			"smoothed molecular surface",
			"cubic-spline surface",
			"7th-order polynomial",
	]

class _PBEquationOption(tkoptions.SymbolicEnumOption):
	values = [
			"lpbe",
			"npbe",
			"smbpe",
	]
	labels = [
			"linearized (lpbe)",
			"nonlinear (npbe)",
			"size-modified (smpbe)",
	]

_Options = [
	# attribute name, title, enabled,
	#		option type, default value, additional keywords
	( "dime", "Grid dimensions", True,
			tkoptions.Float3TupleOption, None,
			{ "horizontal":True, "converter":int, "format":"%d" } ),
	( "cglen", "Coarse grid lengths", True,
			tkoptions.Float3TupleOption, None,
			{ "horizontal":True } ),
	( "cgcent", "Use molecule center for coarse grid center", True,
			tkoptions.BooleanOption, True, {} ),
	( "_cgcentcoord", "Coarse grid center coordinates", False,
			tkoptions.Float3TupleOption, None,
			{ "horizontal":True } ),
	( "fglen", "Fine grid lengths", True,
			tkoptions.Float3TupleOption, None,
			{ "horizontal":True } ),
	( "fgcent", "Use molecule center for fine grid center", True,
			tkoptions.BooleanOption, True, {} ),
	( "_fgcentcoord", "Fine grid center coordinates", False,
			tkoptions.Float3TupleOption, None,
			{ "horizontal":True } ),
	( "bcfl", "Boundary condition for coarse grid", True,
			_bcflOption, "sdh", {} ),
	( "pdie", "Solute dielectric constant", True,
			tkoptions.FloatOption, "2.00", {} ),
	( "sdie", "Solvent dielectric constant", True,
			tkoptions.FloatOption, "78.54", {} ),
	( "chgm", "Charge mapping method", True,
			_chgmOption, "spl2", {} ),
	( "ion", "Include mobile ions", True,
			tkoptions.BooleanOption, False, {} ),
	( "_posion", "Positive ion charge (e), conc. (M), and radius", False,
			tkoptions.Float3TupleOption, None,
			{ "horizontal":True } ),
	( "_negion", "Negative ion charge (e), conc. (M), and radius", False,
			tkoptions.Float3TupleOption, None,
			{ "horizontal":True } ),
	( "_equation", "Poisson-Boltzmann equation", True,
			_PBEquationOption, "lpbe", {} ),
	( "srfm", "How to map dielectric values and ion accessibility", True,
			_srfmOption, "smol", {} ),
	( "sdens", "Surface density", True,
			tkoptions.FloatOption, "10.00", {} ),
	( "srad", "Solvent radius", True,
			tkoptions.FloatOption, "1.40", {} ),
	( "temp", "System temperature", True,
			tkoptions.FloatOption, "298.15", {} ),
	( "solvent", "Include explicit solvent", True,
			tkoptions.BooleanOption, False, {} ),
]

_StickyOptions = set([
	"bcfl",
	"pdie",
	"sdie",
	"chgm",
	"_equation",
	"srfm",
	"sdens",
	"srad",
	"temp",
	"solvent",
])

from chimera import preferences
options = dict()
for opt in _Options:
	if opt[0] in _StickyOptions:
		options[opt[0]] = opt[4]
del opt
prefs = preferences.addCategory("apbs", preferences.HiddenCategory,
							optDict=options)

class ApbsDialog(ModelessDialog):
	name = "ApbsDialog"
	title = "Compute Electrostatic Potential with APBS"
	help = "ContributedSoftware/apbs/apbs.html"
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
		self._moleculeCB(None)

	def _makeMainDialog(self, parent):
		import Tkinter
		f = Tkinter.Frame(parent)
		f.pack(fill="x")
		row = 0
		self.molMenu = tkoptions.MoleculeOption(f, row,
						"Molecule", None, None,
						command=self._moleculeCB)
		row += 1
		self.dx = tkoptions.OutputFileOption(f, row,
						"DX output file (optional)",
						None, None,
						filters=[ ("APBS potential",
								"*.dx",
								".dx") ])
		row += 1

	def _moleculeCB(self, ignore):
		mol = self.molMenu.get()
		if not mol:
			return
		from ws import ChimeraPsize
		ps = ChimeraPsize(mol)
		ps.setAll()
		self.cglen.set(ps.getCoarseGridDims())
		self.fglen.set(ps.getFineGridDims())
		self.dime.set(ps.getFineGridPoints())

	def _makeOptions(self, parent):
		from chimera.widgets import DisclosureFrame
		df = DisclosureFrame(parent, text="Options")
		df.pack(fill="x")
		sf = df.frame
		row = 0
		for attr, title, enabled, opt, default, kw in _Options:
			if attr.startswith('_'):
				s = title
			else:
				s = "%s (%s)" % (title, attr)
			w = opt(sf, row, s, default, self._advoptCB, **kw)
			w.attr = attr
			if not enabled:
				w.disable()
			setattr(self, attr, w)
			row += 1

	def _advoptCB(self, opt):
		if self.cgcent.get():
			self._cgcentcoord.disable()
		else:
			self._cgcentcoord.enable()
		if self.fgcent.get():
			self._fgcentcoord.disable()
		else:
			self._fgcentcoord.enable()
		if self.ion.get():
			self._posion.enable()
			self._negion.enable()
		else:
			self._posion.disable()
			self._negion.disable()
		if opt.attr in _StickyOptions:
			prefs[opt.attr] = opt.get()

	def _makeWSLocation(self, parent):
		from WebServices.gui import addServiceSelector
		from ws import Apbs
		backends = (
			# No replacement available for NBCR service
			#( "opal", ( Apbs.ServiceName, Apbs.ServiceURL ) ),
			( "local", ( "", None ) ),
		)
		df, self.serviceLocation = addServiceSelector(parent, self.name,
								backends)
		df.pack(fill="x")

	def _restorePreferences(self):
		for opt in _Options:
			if opt[0] in _StickyOptions:
				getattr(self, opt[0]).set(prefs[opt[0]])

	def Apply(self):
		m = self.molMenu.get()
		try:
			# are charges missing or None?
			[a.charge + 1.0 for a in m.atoms]
		except (AttributeError, TypeError):
			from chimera import UserError
			raise UserError("Charges are missing for some atoms.\n"
					"Please run Add Charge or PDB2PQR.")
		dx = self.dx.get()
		backend, service, server = self.serviceLocation.getLocation()
		kw = {
			"serviceType": backend,
			"serviceName": service,
			"serviceURL": server,
			"molecule": m,
			"output": dx,
		}
		for opt in _Options:
			o = getattr(self, opt[0])
			kw[opt[0]] = o.get()
		from ws import Apbs
		Apbs(**kw)
		from chimera import replyobj
		replyobj.info("APBS initiated for %s\n" % m.name)

from chimera import dialogs
dialogs.register(ApbsDialog.name, ApbsDialog)
