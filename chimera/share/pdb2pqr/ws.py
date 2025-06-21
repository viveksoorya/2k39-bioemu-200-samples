ForceFields = [
	"AMBER",
	"CHARMM",
	"PARSE",
	"PEOEPB",
	"SWANSON",
	"TYL06"
]
ForceFieldsLowercase = [ ff.lower() for ff in ForceFields ]
FFDefault = 2	# default force field same as pdb2pqr default

def _moleculeID(molRef):
	if not molRef:
		return None
	mol = molRef()
	if not mol:
		return None
	from SimpleSession import sessionID
	try:
		return sessionID(mol)
	except KeyError:
		# Molecule is gone
		return None

def _moleculeLookup(oid):
	if oid is None:
		return None
	from SimpleSession import idLookup
	mol = idLookup(oid)
	from weakref import ref
	return ref(mol)

class Pdb2pqr:

	ServiceName = "pdb2pqr_2.0.0"
	ServiceURL = "http://nbcr-222.ucsd.edu/opal2/services/"
	InputFileName = "input.pdb"
	LigandFileName = "input.mol2"
	OutputFileName = "output.pqr"
	SessionAttrs = [
		( "molRef", _moleculeID, _moleculeLookup, ),
		( "hbonds", None, None, ),
		( "propkaph", None, None, ),
		( "debump", None, None, ),
		( "optHbond", None, None, ),
		( "apbs", None, None, ),
		( "neutraln", None, None, ),
		( "neutralc", None, None, ),
		( "angleCutoff", None, None, ),
		( "distCutoff", None, None, ),
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
						finishTest=self.OutputFileName,
						sessionData=wsData,
						cleanupCB=self._wsCleanup)

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
			molecule=None, forcefield="amber", ligands=False,
			hbonds=False, propkaph=None,
			debump=True, optHbond=True,
			apbs=False, pqr=None,
			neutraln=False, neutralc=False,
			angleCutoff=None, distCutoff=None,
			wait=False):
		import weakref
		self.molRef = weakref.ref(molecule)
		self.hbonds = hbonds
		self.propkaph = propkaph
		self.debump = debump
		self.optHbond = optHbond
		self.apbs = apbs
		self.pqr = pqr
		self.neutraln = neutraln
		self.neutralc = neutralc
		self.angleCutoff = angleCutoff
		self.distCutoff = distCutoff

		fileMap = self._makeInputs(molecule, ligands)
		options = [ "--chain" ]
		if hbonds:
			options.append("--hbond")
		if propkaph:
			options.append("--with-ph=%s" % propkaph)
		if not debump:
			options.append("--nodebump")
		if not optHbond:
			options.append("--noopt")
		if apbs:
			options.append("--apbs-input")
		if forcefield.lower() == "parse":
			if neutraln:
				options.append("--neutraln")
			if neutralc:
				options.append("--neutralc")
		if angleCutoff:
			options.append("--angle_cutoff=%.2f" % angleCutoff)
		if distCutoff:
			options.append("--distance_cutoff=%.2f" % distCutoff)
		if fileMap.has_key(self.LigandFileName):
			options.append("--ligand=%s" % self.LigandFileName)
		options.append("--ff=%s " % forcefield.lower())
		options.append(self.InputFileName)
		options.append(self.OutputFileName)
		command = " ".join(options)
		params = (serviceName,
				"PDB2PQR for %s" % molecule.name,
				fileMap,
				command,
				wait,
				serviceURL,	# not default RBVI one
				serviceType)
		from WebServices import appWebService
		self.ws = appWebService.AppWebService(self._wsFinish,
						finishTest=self.OutputFileName,
						params=params,
						cleanupCB=self._wsCleanup)

	def _makeInputs(self, m, ligands):
		fileMap = dict()
		import Midas, OpenSave
		import chimera
		if ligands:
			sel = chimera.specifier.evalSpec("ligand", models=[ m ])
			if len(sel) == 0:
				ligands = False
		if not ligands:
			fn = OpenSave.osTemporaryFile(suffix=".pdb")
			Midas.write([ m ], m, fn, format="pdb", temporary=True)
			fileMap[self.InputFileName] = fn
		else:
			saveSel = chimera.selection.copyCurrent()
			chimera.selection.setCurrent(sel)
			fn = OpenSave.osTemporaryFile(suffix=".mol2")
			Midas.write([ m ], m, fn, format="mol2",
						temporary=True, selOnly=True)
			fileMap[self.LigandFileName] = fn
			chimera.selection.invertCurrent(allModels=False)
			fn = OpenSave.osTemporaryFile(suffix=".pdb")
			Midas.write([ m ], m, fn, format="pdb",
						temporary=True, selOnly=True)
			fileMap[self.InputFileName] = fn
			chimera.selection.setCurrent(saveSel)
		return fileMap

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
		try:
			url = outputFileMap[self.OutputFileName]
		except KeyError:
			from chimera import NonChimeraError
			raise NonChimeraError("no output from pdb2pqr")
		data = opal.getURLContent(url)
		kw = {}
		if self.pqr:
			from OpenSave import osOpen
			f = osOpen(self.pqr, "w")
			f.write(data)
			f.close()
			f = self.pqr
		else:
			import chimera
			try:
				from cStringIO import StringIO
			except ImportError:
				from StringIO import StringIO
			f = StringIO(data)
			kw["identifyAs"] = mol.name + " PDB2PQR"
		import chimera
		mList = chimera._openPDBModel(f, **kw)
		if len(mList) != 1:
			raise LimitationError("Expected one model from PDB2PQR "
						"and received %d", len(mList))
		self._copyAttributes(mol, mList[0])
		chimera.openModels.add(mList)
		mList[0].openState.xform = mol.openState.xform

		#
		# Display hydrogen bond information and run ABPS
		# if requested
		#
		def withSuffix(suffix):
			fn = self.OutputFileName.replace(".pqr", suffix)
			return outputFileMap[fn]
		if self.hbonds:
			opal.showURLContent("hydrogen bonds",
						withSuffix(".hbond"))
		if self.apbs:
			inData = opal.showURLContent("in",
						withSuffix(".in"))

	def _copyAttributes(self, old, new):
		for attr in _MoleculeAttrList:
			try:
				v = getattr(old, attr)
			except AttributeError:
				pass
			else:
				setattr(new, attr, v)
		resMap = dict()
		for oldr in old.residues:
			resMap[(oldr.id, oldr.type)] = oldr
		atomMap = dict()
		for newr in new.residues:
			try:
				oldr = resMap[(newr.id, newr.type)]
			except KeyError:
				raise ValueError("non-matching residue found in pdb2pqr output")
			for attr in _ResidueAttrList:
				try:
					v = getattr(oldr, attr)
				except AttributeError:
					pass
				else:
					setattr(newr, attr, v)
			for olda in oldr.atoms:
				newa = newr.findAtom(olda.name)
				if not newa:
					continue
				atomMap[newa] = olda
				for attr in _AtomAttrList:
					try:
						v = getattr(olda, attr)
					except AttributeError:
						pass
					else:
						setattr(newa, attr, v)
		bondMap = dict()
		for oldb in old.bonds:
			oa1, oa2 = oldb.atoms
			bondMap[(oa1, oa2)] = oldb
		for newb in new.bonds:
			na1, na2 = newb.atoms
			try:
				oa1 = atomMap[na1]
				oa2 = atomMap[na2]
			except KeyError:
				continue
			try:
				oldb = bondMap[(oa1, oa2)]
			except KeyError:
				try:
					oldb = bondMap[(oa2, oa1)]
				except KeyError:
					continue
			for attr in _BondAttrList:
				try:
					v = getattr(oldb, attr)
				except AttributeError:
					pass
				else:
					setattr(newb, attr, v)

	def _wsCleanup(self, opal, completed, succeeded):
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
	from pdb2pqr.ws import sessionRestore
	sessionRestore(%s)
except:
	reportRestoreError("Error restoring PDB2PQR web service job info")
""" % sesRepr(self.sessionData())

def sessionRestore(sessionData):
	# We don't bother to keep a reference because the
	# session callback in the Apbs instance should keep
	# the instance alive
	Pdb2pqr(sessionData=sessionData)

_MoleculeAttrList = [
	"autochain",
	"ballScale",
	"color",
	"lineWidth",
	"pointSize",
	"ribbonHidesMainchain",
	"stickScale",
	"surfaceColor",
	"surfaceOpacity",
	"vdwDensity",
	"wireStipple",
]
_ResidueAttrList = [
	"isHelix",
	"isHet",
	"isSheet",
	"label",
	"labelColor",
	"labelOffset",
	"ribbonColor",
	"ribbonDisplay",
	"ribbonDrawMode",
	"ribbonResidueClass",
	"ribbonStyle",
	"ribbonXSection",
]
_AtomAttrList = [
# Don't copy altLoc since we're only using primary locations
#	"altLoc",
	"bfactor",
	"color",
	"display",
	"drawMode",
	"label",
	"labelColor",
	"labelOffset",
	"occupancy",
# Don't copy radius since we want to keep the pdb2pqr value
#	"radius",
	"serialNumber",
	"surfaceCategory",
	"surfaceColor",
	"surfaceDisplay",
	"surfaceOpacity",
	"vdw",
	"vdwColor",
]
_BondAttrList = [
	"color",
	"display",
	"drawMode",
	"halfbond",
	"label",
	"labelColor",
	"labelOffset",
# Don't copy radius since it might not match the atom radius
#	"radius",
]
