ReceptorFile = "receptor.pdbqt"
LigandFile = "ligand.pdbqt"
ConfFile = "vina.conf"
OutputFile = "results.pdbqt"

def _moleculeID(molRef):
	if molRef is None:
		return None
	mol = molRef()
	if not mol or mol.__destroyed__:
		return None
	from SimpleSession import sessionID
	return sessionID(mol)

def _moleculeLookup(oid):
	if oid is None:
		return None
	from SimpleSession import idLookup
	mol = idLookup(oid)
	from weakref import ref
	return ref(mol)

class VinaService:

	# Abstract base class for Vina services
	# Subclass needs to define:
	#   ServiceName: Opal service name
	#   ServiceURL: Opal service URL prefix
	#   SessionAttrs: list of attributes to save in sessions
	#   SessionRestore: name of session restore function
	#   _initApp: method to initialize service
	#   _wsFinish: method to process service results

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
	from vina.ws import %s
	%s(%s)
except:
	reportRestoreError("Error restoring apbs web service job info")
""" % (self.SessionRestore, self.SessionRestore, sesRepr(self.sessionData()))

def dockingSessionRestore(sessionData):
	# We don't bother to keep a reference because the
	# session callback in the VinaDocking instance should keep
	# the instance alive
	VinaDocking(sessionData=sessionData)


class VinaDocking(VinaService):

	ServiceName = "vina_1.1.2"
	ServiceURL = "http://nbcr-222.ucsd.edu/opal2/services/"
	# If more attributes need to be added, add them at the end
	# so that session restore will work properly.  Never delete
	# any attributes from the list.
	# All attributes have a default value of None if missing
	# from saved session.
	SessionAttrs = [
		( "receptorRef", _moleculeID, _moleculeLookup, ),
		( "ligandName", None, None, ),
		( "xform", None, None, ),
		( "output", None, None, ),
	]
	SessionRestore = "dockingSessionRestore"

	def _initApp(self, serviceType="opal",
			serviceName=ServiceName,
			serviceURL=ServiceURL,
			receptorFile=None,
			receptor=None,
			ligandFile=None,
			ligand=None,
			confFile=None,
			xform=None,
			output=None,
			wait=False):
		import weakref
		self.receptorRef = weakref.ref(receptor)
		self.ligandName = "Docked %s" % ligand.name
		self.xform = xform
		self.output = output

		fileMap = dict()
		fileMap[ReceptorFile] = receptorFile
		fileMap[LigandFile] = ligandFile
		fileMap[ConfFile] = confFile
		options = [
			"--receptor", ReceptorFile,
			"--ligand", LigandFile,
			"--config", ConfFile,
			"--out", OutputFile,
		]
		command = " ".join(options)
		params = (serviceName,
				"AutoDock Vina for %s" % receptor.name,
				fileMap,
				command,
				wait,
				serviceURL,
				serviceType)
		from WebServices import appWebService
		self.ws = appWebService.AppWebService(self._wsFinish,
						params=params,
						cleanupCB=self._wsCleanup)

	def _wsFinish(self, opal, outputFileMap):
		#
		# Get initial molecules
		#
		receptor = self.receptorRef()
		if not receptor:
			# Receptor no longer around, no need to do anything
			return

		#
		# Show output and error messages
		#
		opal.showURLContent("standard output",
					outputFileMap["stdout.txt"])
		opal.showURLContent("standard error",
					outputFileMap["stderr.txt"])

		#
		# Copy output file from Opal server
		#
		for filename, url in outputFileMap.iteritems():
			if filename == OutputFile:
				data = opal.getURLContent(url)
				break
		else:
			from chimera import NonChimeraError
			raise NonChimeraError("No data file returned from "
						"AutoDock Vina web service")
		from OpenSave import osOpen
		with osOpen(self.output, "wb") as f:
			f.write(data)

		#
		# Display results in ViewDock
		#
		import chimera
		if not chimera.nogui:
			import ViewDock
			d = ViewDock.ViewDock(self.output, "AutoDock")
			if self.xform:
				xf = receptor.openState.xform
				xf.multiply(self.xform)
				for m in d.models():
					m.openState.xform = xf
			try:
				name = self.ligandName
			except AttributeError:
				pass
			else:
				for m in d.models():
					m.name = name


def screeningSessionRestore(sessionData):
	# We don't bother to keep a reference because the
	# session callback in the VinaScreening instance should keep
	# the instance alive
	VinaScreening(sessionData=sessionData)

class VinaScreening(VinaService):

	ServiceName = "autodockvina_screening_1.1.2"
	ServiceURL = "http://nbcr-222.ucsd.edu/opal2/services/"
	# If more attributes need to be added, add them at the end
	# so that session restore will work properly.  Never delete
	# any attributes from the list.
	# All attributes have a default value of None if missing
	# from saved session.
	SessionAttrs = [
		( "receptorRef", _moleculeID, _moleculeLookup, ),
		( "database", None, None, ),
		( "xform", None, None, ),
		( "output", None, None, ),
	]
	SessionRestore = "screeningSessionRestore"

	def _initApp(self, serviceType="opal",
			serviceName=ServiceName,
			serviceURL=ServiceURL,
			receptorFile=None,
			receptor=None,
			database=None,
			confFile=None,
			xform=None,
			output=None,
			wait=False):
		import weakref
		self.receptorRef = weakref.ref(receptor)
		self.database = database
		self.xform = xform
		self.output = output

		fileMap = dict()
		fileMap[ReceptorFile] = receptorFile
		fileMap[ConfFile] = confFile
		options = [
			"--receptor", ReceptorFile,
			"--ligand_db", database,
			"--config", ConfFile,
		]
		command = " ".join(options)
		params = (serviceName,
				"AutoDock Vina screening for " + receptor.name,
				fileMap,
				command,
				wait,
				serviceURL,
				serviceType)
		from WebServices import appWebService
		self.ws = appWebService.AppWebService(self._wsFinish,
						params=params,
						cleanupCB=self._wsCleanup)

	def _wsFinish(self, opal, outputFileMap):
		#
		# Get initial molecules
		#
		receptor = self.receptorRef()
		if not receptor:
			# Receptor no longer around, no need to do anything
			return

		#
		# Show output and error messages
		#
		opal.showURLContent("standard output",
					outputFileMap["stdout.txt"])
		opal.showURLContent("standard error",
					outputFileMap["stderr.txt"])

		# Copy output from Opal server.
		# Extract pdbqt files from .tar.gz and combine into
		# a single output file.
		#
		for filename, url in outputFileMap.iteritems():
			if filename == OutputFile:
				data = opal.getURLContent(url)
				break
		try:
			url = outputFileMap["results.tar.gz"]
		except KeyError:
			from chimera import NonChimeraError
			raise NonChimeraError("No results returned from "
						"AutoDock Vina virtual "
						"screening web service")
		else:
			data = opal.getURLContent(url)
			try:
				convertScreeningToPdbqt(data, self.output)
			except (IOError, ValueError), e:
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))

		#
		# Display results in ViewDock
		#
		import chimera
		if not chimera.nogui:
			import ViewDock
			d = ViewDock.ViewDock(self.output, "AutoDock")
			if self.xform:
				xf = receptor.openState.xform
				xf.multiply(self.xform)
				for m in d.models():
					m.openState.xform = xf
			name = "Screened %s" % self.ligandName
			for m in d.models():
				m.name = name

def convertScreeningToPdbqt(data, filename):
	from cStringIO import StringIO
	df = StringIO(data)
	import tarfile
	try:
		from OpenSave import osOpen
		with osOpen(filename, "wb") as f, \
			tarfile.open("results.tar.gz", "r:gz", df) as tf:
				_extractPdbqt(f, tf)
	except tarfile.TarError, e:
		raise ValueError("Results from AutoDock Vina virtual "
					"screening web service is not "
					"properly formatted: %s" % str(e))

def _extractPdbqt(f, tf):
	report = tf.extractfile("./screening_report.log")
	if report is None:
		raise ValueError("Results from AutoDock Vina virtual "
					"screening web service is missing "
					"summary report")
	for line in report:
		if line[0] == '#':
			continue
		fields = line.strip().split('\t')
		if len(fields) != 6:
			raise ValueError("Report from AutoDock Vina virtual "
					"screening web service has unexpected "
					"line\n%s" % line)
		(name, energy, ligand_efficiency,
			total_poses, receptor, filename) = fields
		name = name.replace("_out", "")
		qf = tf.extractfile(filename)
		for qline in qf:
			f.write(qline)
			if qline.startswith("MODEL"):
				print >> f, "COMPND    %s" % name
		qf.close()
	report.close()

# --------------------------------------------------------------------------
# Functions for preparing web service input files

def prepareReceptor(pdbFile, pdbqtFile, nphs, lps, waters, nonstdres, nonstd):
	import os.path
	import AutoDockTools
	adDir = os.path.dirname(AutoDockTools.__file__)
	scriptName = "prepare_receptor4.py"
	scriptPath = os.path.join(adDir, "Utilities24", scriptName)
	import sys
	save = sys.argv
	sys.argv = [ scriptName, "-r", pdbFile, "-A", "checkhydrogens",
						"-o", pdbqtFile ]
	cleanup = []
	if nphs:
		cleanup.append("nphs")
	if lps:
		cleanup.append("lps")
	if waters:
		cleanup.append("waters")
	if nonstdres:
		cleanup.append("nonstdres")
	if not cleanup:
		cleanupArg = ""
	else:
		cleanupArg = '_'.join(cleanup)
	sys.argv.append("-U")
	sys.argv.append(cleanupArg)
	if nonstd:
		sys.argv.append("-e")
	d = { "__name__": "__main__" }
	try:
		execfile(scriptPath, d)
	except:
		import traceback
		traceback.print_exc()
		from chimera import replyobj
		replyobj.warning("Receptor preparation for "
					"AutoDock Vina failed; please look in "
					"Reply Log to see error messages.")
	finally:
		sys.argv = save

	if not os.path.exists(pdbqtFile):
		from chimera import LimitationError
		raise LimitationError("cannot prepare receptor for "
					"AutoDock Vina; please look in "
					"Reply Log and/or run Chimera "
					"with --debug flag to see errors.")

def checkLigand(ligand):
	num_heavy = 0
	for a in ligand.atoms:
		if a.element.number > 1:
			num_heavy += 1
	if num_heavy > 100:
		raise ValueError("too many heavy atoms (>100) in ligand")

def prepareLigand(pdbFile, pdbqtFile, nphs, lps):
	import os.path
	import AutoDockTools
	adDir = os.path.dirname(AutoDockTools.__file__)
	scriptName = "prepare_ligand4.py"
	scriptPath = os.path.join(adDir, "Utilities24", scriptName)
	import sys
	save = sys.argv
	sys.argv = [ scriptName, "-l", pdbFile, "-A", "checkhydrogens",
						"-o", pdbqtFile, ]
	cleanup = []
	if nphs:
		cleanup.append("nphs")
	if lps:
		cleanup.append("lps")
	if not cleanup:
		cleanupArg = ""
	else:
		cleanupArg = '_'.join(cleanup)
	sys.argv.append("-U")
	sys.argv.append(cleanupArg)
	d = { "__name__": "__main__" }
	try:
		execfile(scriptPath, d)
	except SystemExit:
		# Successful execution of the script raises
		# SystemExit at the end
		pass
	except:
		import traceback
		traceback.print_exc()
		if not os.path.exists(pdbqtFile):
			from chimera import LimitationError
			raise LimitationError("cannot prepare ligand for "
					"AutoDock Vina; please look in "
					"Reply Log and/or run Chimera "
					"with --debug flag to see errors.")
		else:
			from chimera import replyobj
			replyobj.warning("There was an error during ligand "
					"preparation for AutoDock Vina, but "
					"docking is still being attempted. "
					"See the Reply Log and check output "
					"files carefully. To avoid this "
					"error, it may help to add hydrogens "
					"or run Dock Prep in Chimera before "
					"running AutoDock Vina.")
			
	finally:
		sys.argv = save

def prepareConf(confFile, center, size, opts):
	from OpenSave import osOpen
	with osOpen(confFile, "w") as f:
#		print >> f, "receptor = %s" % ReceptorFile
#		print >> f, "ligand = %s" % LigandFile
#		print >> f
		print >> f, "center_x = %.2f" % center[0]
		print >> f, "center_y = %.2f" % center[1]
		print >> f, "center_z = %.2f" % center[2]
		print >> f, "size_x = %.2f" % size[0]
		print >> f, "size_y = %.2f" % size[1]
		print >> f, "size_z = %.2f" % size[2]
		print >> f
		for opt, val in opts.iteritems():
			if val is None:
				continue
			if opt.startswith("_"):
				opt = opt.replace("_", "", 1)
			print >> f, "%s = %s" % (opt, val)
	#_dumpBild(confFile + ".bild", center, size)

def _dumpBild(bildFile, center, size):
	sz = [ size[i] / 2 for i in range(3) ]
	from OpenSave import osOpen
	with osOpen(bildFile, "w") as f:
		print >> f, ".color red"
		_connect(f, center, sz, -1, -1, -1, -1, +1, -1)
		_connect(f, center, sz, -1, +1, -1, +1, +1, -1)
		_connect(f, center, sz, +1, +1, -1, +1, -1, -1)
		_connect(f, center, sz, +1, -1, -1, -1, -1, -1)
		_connect(f, center, sz, -1, -1, +1, -1, +1, +1)
		_connect(f, center, sz, -1, +1, +1, +1, +1, +1)
		_connect(f, center, sz, +1, +1, +1, +1, -1, +1)
		_connect(f, center, sz, +1, -1, +1, -1, -1, +1)
		_connect(f, center, sz, -1, -1, -1, -1, -1, +1)
		_connect(f, center, sz, -1, +1, -1, -1, +1, +1)
		_connect(f, center, sz, +1, +1, -1, +1, +1, +1)
		_connect(f, center, sz, +1, -1, -1, +1, -1, +1)

def _connect(f, center, sz, dx0, dy0, dz0, dx1, dy1, dz1):
	print >> f, ".m %.2f %.2f %.2f" % (center[0] + dx0 * sz[0],
						center[1] + dy0 * sz[1],
						center[2] + dz0 * sz[2])
	print >> f, ".d %.2f %.2f %.2f" % (center[0] + dx1 * sz[0],
						center[1] + dy1 * sz[1],
						center[2] + dz1 * sz[2])
