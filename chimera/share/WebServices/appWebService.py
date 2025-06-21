class AppWebService:
	"""
	This class serves as a port to web services and local executables.
	A typical example can be found in libs/MultiAlignViewer/ModellerDialog.py
	To initialize and launch the web service call: 
		for initial launch, kw["params"] = (serviceName, title, inputFileMap, command)
		for session restore, kw["sessionData"] = sessionData
	Optional parameters:
		kw["finishTest"] = "key output file name"
		kw["progressCB"] = progressCallBackFunction : it pass a stdout.txt strings to the callback function
							from the stdout.txt the callback function will returen the progress between [0.0, 1.0]
	FinishCB: the finish callback funcion, two parameters returned:
			service: instance that is API-compatible with OpalService in opal_client
			fileMap: service.getOutputs() the output file map
	serviceName: the web service name when deploy the service after '-DserviceName'
	title: the name showing in the task manager after words 'Running %s via web service' %title
	inputFileMap: a map of input files {'filename': 'path to file'}
	command: the arguments list in strings (or filenames) to feed the binary file on the webservice 
	
	finishTest: the file name of a fixed output file to test the false finish. If finishTest is specified,
			then it will be tested the existence in the end after self.backend.isFinished() return true.
	"""

	def __init__(self, finishCB, params=None, sessionData=None,
			finishTest=None, progressCB=None, cleanupCB=None, backend="opal"):
		self.finishCB = finishCB
		self.finishTest = finishTest
		self.progressCB = progressCB
		self.cleanupCB = cleanupCB
		self.errorCount = 0
		if params is not None:
			if len(params) < 7:
				self._initApp(*params, backend=backend)
			else:
				self._initApp(*params)
		else:
			self._initSession(*sessionData)

	def _initApp(self, serviceName, title, inputFileMap, command,
						wait=False, url=None, backend="opal"):
		self.params = (serviceName, title, inputFileMap, command,
								url, backend)
		Backend, makeInputFile = self._getBackend(backend)
		inputFiles = []
		#print "###I am running WebServices.AppWebService. ###"
		for name, path in inputFileMap.iteritems():
			inputFiles.append(makeInputFile(path, name=name))
		service = serviceName 
		#argList = script
		try:
			self.backend = Backend(service, url)
		except:
			import traceback, sys
			print "Traceback from web application request:"
			traceback.print_exc(file=sys.stdout)
			#print """
#Typically, if you get a TypeError, it's a problem on the remote server
#and it should be fixed shortly.  If you get a different error or 
#get TypeError consistently for more than a day, please report the
#problem using the Report a Bug... entry in the Help menu.  Please
#include the traceback printed above as part of the problem description."""
			from chimera import NonChimeraError
			raise NonChimeraError("Service '%s:%s' is unavailable.  "
					"See Reply Log for more details." %
					(backend, serviceName))
		if wait:
			success, fileMap = self.backend.launchJobBlocking(
							command,
							_inputFile=inputFiles)
			if success and self.finishCB:
				self.finishCB(self.backend, fileMap)
			if self.cleanupCB:
				self.cleanupCB(self.backend, True, success)
			self.task = None
		else:
			self.backend.launchJob(command, _inputFile=inputFiles)
			from chimera.tasks import Task
			self.task = Task(self._title(), self.cancelCB,
							self.statusCB)

	def _initSession(self, params, running, backendData, startTime=None):
		self.params = params
		# params = (serviceName, title, inputFileMap,
		#			command, url, backend)
		# In older versions, only the first four parameters
		# are present, in which case we assume we are
		# using the real opal backend
		try:
			backend = params[5]
		except IndexError:
			backend = "opal"
		Backend, makeInputFile = self._getBackend(backend)
		self.backend = Backend(sessionData=backendData)
		if not running:
			self.task = None
		else:
			from chimera.tasks import Task
			self.task = Task(self._title(), self.cancelCB,
								self.statusCB)
			if startTime:
				self.task.setStartTime(startTime)
			try:
				self.backend.queryStatus()
			except RuntimeError:
				import traceback, sys
				traceback.print_exc(file=sys.stdout)
				self.task.cancel()

	def _title(self):
		return "Running %s" % self.params[1]

	def sessionData(self):
		if self.task:
			# Use int so that sesRepr keeps the exact value
			startTime = int(self.task.getStartTime())
		else:
			startTime = None
		return (self.params,
				self.task is not None,
				self.backend.sessionData(),
				startTime)

	def cancelCB(self):
		self.task.finished()
		self.task = None
		if self.cleanupCB:
			self.cleanupCB(self.backend, False, False)

	def statusCB(self):
		self.task.updateStatus(self.backend.currentStatus())
		if self.progressCB and self.backend.status:
			pgs = 100.0 * self.progressCB( self.backend.getStdOut() ) 
			self.task.updateStatus("progress : %d%% completed" %pgs)
		finished = self.backend.isFinished()
		if not finished:
			try:
				self.backend.queryStatus()
			except RuntimeError:
				import traceback, sys
				traceback.print_exc(file=sys.stdout)
				self.errorCount += 1
				if self.errorCount > 10:
					self.task.cancel()
			return
		if finished == 2:
			# Job has not started, wait some more
			return
		try:
			fileMap = self.backend.getOutputs()
		except Exception as e:
			self.errorCount += 1
			if self.errorCount > 2:
				from chimera import replyobj
				replyobj.error("%s failed; unable to get output files from server\n" % self._title())
				self.task.cancel()
			return
		if finished > 0: 
			# Test the existence of output file self.finishTest
			if self.finishTest:
				if self.finishTest in fileMap and len(self.backend.getFileContent(self.finishTest)) >0:
					# true finish: completed and generated the wanted output file
					self.task.updateStatus("Calculation completed, file %s was generated." %self.finishTest)
					callCallback = True
				else:
					# false finish: completed but not generated the wanted output file
					self.task.updateStatus("Calculation failed, file %s was NOT generated." %self.finishTest)
					callCallback = False
			else:
				# without output file testing, finish the self.task anyway
				callCallback = True
		else:
			# backend failed
			callCallback = False
		self.backend.getJobStatistics()
		if self.backend.times[0]:
			self.task.setStartTime(self.backend.times[0])
		if self.backend.times[1]:
			self.task.setEndTime(self.backend.times[1])
		self.task.finished()
		self.task = None
		self.errorCount = 0
		if callCallback:
			self.finishCB(self.backend, fileMap)
		else:
			self._failedReturnInfo(fileMap)
		if self.cleanupCB:
			self.cleanupCB(self.backend, True, callCallback)

	def _failedReturnInfo(self, fileMap):
		# Failed
		from chimera import replyobj
		replyobj.error("%s failed; "
				"see Reply Log for more information\n"
				% self._title())
		self.backend.showURLContent("Application stderr",
					fileMap["stderr.txt"])
		self.backend.showURLContent("Application stdout",
					fileMap["stdout.txt"])

	def _getBackend(self, backend):
		if backend == "opal":
			from opal_client import OpalService, makeInputFile
			return OpalService, makeInputFile
		elif backend == "local":
			from opal_local import LocalOpalService, localMakeInputFile
			return LocalOpalService, localMakeInputFile
		elif backend == "cx":
			from cx_client import CxService, makeInputFile
			return CxService, makeInputFile
		else:
			raise ValueError("unsupported backend: %s" % backend)
