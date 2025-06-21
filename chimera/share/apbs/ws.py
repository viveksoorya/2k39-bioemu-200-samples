ForceFields = [
	"Amber",
	"CHARMM",
	"Parse",
	"TYL06"
]
ForceFieldsLowercase = [ ff.lower() for ff in ForceFields ]
FFDefault = 2	# default force field same as APBS default

def _moleculeID(molRef):
	mol = molRef()
	if not mol:
		return None
	from SimpleSession import sessionID
	return sessionID(mol)

def _moleculeLookup(oid):
	from SimpleSession import idLookup
	mol = idLookup(oid)
	from weakref import ref
	return ref(mol)

class Apbs:

	ServiceName = "apbs_1.3"
	ServiceURL = "http://nbcr-222.ucsd.edu/opal2/services/"
	InputFileName = "apbs.in"
	InputPQRFileName = "apbs.pqr"
	OutputPrefix = "apbs"
	OutputSuffix = ".dx"
	# If more attributes need to be added, add them at the end
	# so that session restore will work properly.  Never delete
	# any attributes from the list.
	# All attributes have a default value of None if missing
	# from saved session.
	SessionAttrs = [
		( "molRef", _moleculeID, _moleculeLookup, ),
		( "output", None, None, ),
		( "dime", None, None ),
		( "cglen", None, None ),
		( "cgcent", None, None ),
		( "_cgcentcoord", None, None ),
		( "fglen", None, None ),
		( "fgcent", None, None ),
		( "_fgcentcoord", None, None ),
		( "bcfl", None, None ),
		( "pdie", None, None ),
		( "sdie", None, None ),
		( "chgm", None, None ),
		( "srfm", None, None ),
		( "ion", None, None ),
		( "_posion", None, None ),
		( "_negion", None, None ),
		( "_equation", None, None ),
		( "sdens", None, None ),
		( "srad", None, None ),
		( "temp", None, None ),
		( "solvent", None, None ),
	]

	def __init__(self, sessionData=None, **kw):
		self.saveSesHandler = None
		if sessionData:
			self._initSession(sessionData)
		else:
			self._initApp(**kw)
		import chimera
		from SimpleSession import SAVE_SESSION
		self.saveSesHandler = chimera.triggers.addHandler(
						SAVE_SESSION,
						self._saveSessionCB, None)

	def _initSession(self, sessionData):
		from WebServices import appWebService
		wsData = sessionData[0]
		for i, (attr, saver, restorer) in enumerate(self.SessionAttrs):
			try:
				rawData = sessionData[i + 1]
			except IndexError:
				data = None
			else:
				if restorer:
					data = restorer(rawData)
				else:
					data = rawData
			setattr(self, attr, data)
		self.ws = appWebService.AppWebService(self._wsFinish,
							sessionData=wsData)

	def sessionData(self):
		data = [ self.ws.sessionData() ]
		for attr, saver, restorer in self.SessionAttrs:
			rawData = getattr(self, attr)
			if saver:
				data.append(saver(rawData))
			else:
				data.append(rawData)
		return data

	def _initApp(self, serviceType="opal",
			serviceName=ServiceName,
			serviceURL=ServiceURL,
			molecule=None,
			output=None,
			dime=None,
			cglen=None,
			cgcent=True,
			_cgcentcoord=None,
			fglen=None,
			fgcent=True,
			_fgcentcoord=None,
			bcfl="sdh",
			pdie=2.00,
			sdie=78.54,
			chgm="spl2",
			srfm="smol",
			ion=False,
			_posion=( 1.0,0.15,2.0),
			_negion=(-1.0,0.15,2.0),
			_equation="nbpe",
			sdens=10.00,
			srad=1.40,
			temp=298.15,
			solvent=False,
			wait=False):
		import weakref
		self.molRef = weakref.ref(molecule)
		self.output = output
		self.dime = dime
		self.cglen = cglen
		self.cgcent = cgcent
		self._cgcentcoord = _cgcentcoord
		self.fglen = fglen
		self.fgcent = fgcent
		self._fgcentcoord = _fgcentcoord
		self.bcfl = bcfl
		self.pdie = pdie
		self.sdie = sdie
		self.chgm = chgm
		self.srfm = srfm
		self.ion = ion
		self._posion = tuple(_posion)
		self._negion = tuple(_negion)
		self._equation = _equation
		self.sdens = sdens
		self.srad = srad
		self.temp = temp
		self.solvent = solvent

		self._checkParameters()

		fileMap = self._makeInputs(molecule, self.solvent)
		options = []
		options.append(self.InputFileName)
		command = " ".join(options)
		params = (serviceName,
				"APBS for %s" % molecule.name,
				fileMap,
				command,
				wait,
				serviceURL,
				serviceType)	# not default RBVI one
		from WebServices import appWebService
		self.ws = appWebService.AppWebService(self._wsFinish,
						params=params,
						cleanupCB=self._wsCleanup)

	def _checkParameters(self):
		from chimera import UserError
		if not self.dime:
			raise UserError("grid dimensions unspecified")
		if not self.cgcent and not self._cgcentcoord:
			raise UserError("coarse grid center unspecified")
		if not self.cglen:
			raise UserError("coarse grid length")
		if not self.fgcent and not self._fgcentcoord:
			raise UserError("fine grid center unspecified")
		if not self.fglen:
			raise UserError("fine grid length")
		if self.ion:
			try:
				pCharge, pConc, pRadius = self._posion
				nCharge, nConc, nRadius = self._negion
				netCharge = pCharge * pConc + nCharge * nConc
			except (ValueError, TypeError):
				raise UserError("bad ion parameters")
			import math
			if math.fabs(netCharge) > 1e-6:
				raise UserError("net ion charge not neutral")

	def _makeInputs(self, m, includeSolvent):
		fileMap = dict()
		import Midas, OpenSave
		import chimera
		saveXform = m.openState.xform
		m.openState.xform = chimera.Xform.identity()
		fn = OpenSave.osTemporaryFile(suffix=".pqr")
		# If not including solvent, create a selection
		# of the non-solvent atoms in "m" and temporarily make
		# it the current selection.  Write out the PDB file
		# with selOnly=True.  Restore current selection.
		modelList = [ m ]
		kw = { "format":"pqr", "temporary":True }
		if includeSolvent:
			Midas.write(modelList, None, fn, **kw)
		else:
			from chimera.selection import copyCurrent, setCurrent
			origSel = copyCurrent()
			from chimera.specifier import evalSpec
			setCurrent(evalSpec("~solvent", models=modelList))
			Midas.write(modelList, None, fn, selOnly=True, **kw)
			setCurrent(origSel)
		import os
		m.openState.xform = saveXform
		fileMap[self.InputPQRFileName] = fn
		fn = OpenSave.osTemporaryFile(suffix=".in")
		self._makeAPBSInput(fn)
		fileMap[self.InputFileName] = fn
		return fileMap

	def _makeAPBSInput(self, fn):
		f = open(fn, "w")
		try:
			print >> f, "read"
			print >> f, "\tmol pqr %s" % self.InputPQRFileName
			print >> f, "end"
			self._printElec(f, True)
			print >> f, "quit"
		finally:
			f.close()

	def _printElec(self, f, solvated):
		print >> f, "elec"
		print >> f, "\tmg-auto"
		print >> f, "\tdime %d %d %d" % (
					self.dime[0],
					self.dime[1],
					self.dime[2])
		print >> f, "\tcglen %.2f %.2f %.2f" % (
					self.cglen[0],
					self.cglen[1],
					self.cglen[2])
		print >> f, "\tfglen %.2f %.2f %.2f" % (
					self.fglen[0],
					self.fglen[1],
					self.fglen[2])
		if self.cgcent:
			print >> f, "\tcgcent mol 1"
		else:
			print >> f, "\tcgcent mol %.2f %.2f %.2f" % (
					self._cgcentcoord[0],
					self._cgcentcoord[1],
					self._cgcentcoord[2])
		if self.fgcent:
			print >> f, "\tfgcent mol 1"
		else:
			print >> f, "\tfgcent mol %.2f %.2f %.2f" % (
					self._fgcentcoord[0],
					self._fgcentcoord[1],
					self._fgcentcoord[2])
		print >> f, "\tmol 1"
		print >> f, "\t%s" % self._equation
		print >> f, "\tbcfl %s" % self.bcfl
		print >> f, "\tpdie %.2f" % self.pdie
		if solvated:
			print >> f, "\tsdie %.2f" % self.sdie
		else:
			print >> f, "\tsdie %.2f" % self.pdie
		print >> f, "\tchgm %s" % self.chgm
		if self.ion:
			print >> f, ("\tion charge %.3f conc %.3f radius %.3f"
								% self._posion)
			print >> f, ("\tion charge %.3f conc %.3f radius %.3f"
								% self._negion)
		print >> f, "\tsrfm %s" % self.srfm
		print >> f, "\tswin 0.3"
		print >> f, "\tsdens %.2f" % self.sdens
		print >> f, "\tsrad %.2f" % self.srad
		print >> f, "\ttemp %.2f" % self.temp
		print >> f, "\tcalcenergy total"
		print >> f, "\tcalcforce no"
		if solvated:
			import os.path
			root = self.OutputPrefix
			print >> f, "\twrite pot dx %s" % root
		print >> f, "end"

	def _wsFinish(self, opal, outputFileMap):
		mol = self.molRef()
		if not mol:
			# Molecule no longer around, no need to do anything
			return
		#
		# Show output and error messages
		#
		opal.showURLContent("standard output",
					outputFileMap["stdout.txt"])
		opal.showURLContent("standard error",
					outputFileMap["stderr.txt"])

		#
		# Convert PQR file into model and save if requested
		#
		for filename, url in outputFileMap.iteritems():
			if (filename.startswith(self.OutputPrefix)
			and filename.endswith(self.OutputSuffix)):
				data = opal.getURLContent(url)
				break
		else:
			from chimera import NonChimeraError
			raise NonChimeraError("No data file returned from "
						"APBS web service")
		kw = {
			"type": "APBS potential",
		}
		import OpenSave
		if self.output:
			output = OpenSave.tildeExpand(self.output)
			kw["temporary"] = False
		else:
			output = OpenSave.osTemporaryFile(suffix=".dx")
			kw["temporary"] = True
			kw["identifyAs"] = mol.name + " APBS"
		f = OpenSave.osOpen(output, "wb")
		f.write(data)
		f.close()
		import chimera
		mList = chimera.openModels.open(output, **kw)
		if len(mList) != 1:
			from chimera import NonChimeraError
			raise NonChimeraError("Expected one model from APBS "
						"and received %d", len(mList))
		mList[0].openState.xform = mol.openState.xform

	def _wsCleanup(self, opal, completed, success):
		if self.saveSesHandler:
			from SimpleSession import SAVE_SESSION
			import chimera
			chimera.triggers.deleteHandler(SAVE_SESSION,
							self.saveSesHandler)
			self.saveSesHandler = None

	def _saveSessionCB(self, trigger, myData, sesFile):
		from SimpleSession import sesRepr
		print >> sesFile, """
try:
	from apbs.ws import sessionRestore
	sessionRestore(%s)
except:
	reportRestoreError("Error restoring apbs web service job info")
""" % sesRepr(self.sessionData())

def sessionRestore(sessionData):
	# We don't bother to keep a reference because the
	# session callback in the Apbs instance should keep
	# the instance alive
	Apbs(sessionData=sessionData)

#
# Derived class for estimating good initial parameter values
#
from psize import Psize
class ChimeraPsize(Psize):

	def __init__(self, mol):
		Psize.__init__(self)
		def skipHet(a):
			return a.residue.isHet
		if self.parseMolecule(mol, skipHet) == 0:
			self.parseMolecule(mol, None)

	def parseMolecule(self, mol, skip):
		""" Parse data from a Chimera molecule """
		self.gotatom = 0
		for a in mol.atoms:
			if skip and skip(a):
				continue
			self.gotatom += 1
			self.q += getattr(a, "charge", 0.0)
			rad = getattr(a, "radius", 0.0)
			center = a.coord()
			for i in range(3):
				if (self.minlen[i] == None
				or (center[i] - rad) < self.minlen[i]):
					self.minlen[i] = center[i] - rad
				if (self.maxlen[i] == None
				or (center[i] + rad) > self.maxlen[i]):
					self.maxlen[i] = center[i] + rad
		return self.gotatom
