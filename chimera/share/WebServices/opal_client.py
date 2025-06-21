#!/usr/local/bin/python2.5

class OpalService:

	DefaultOpalURL="http://webservices.rbvi.ucsf.edu/opal2/services/"

	def __init__(self, serviceName=None, opalURL=None, sessionData=None):
		if opalURL is None:
			opalURL = self.DefaultOpalURL
		try:
			self._setup(serviceName, opalURL, sessionData)
		except:
			self.dumpTraceback("connection setup")
			print """
Typically, if you get a TypeError, it's a problem on the remote server
and it should be fixed shortly.  If you get a different error or
get TypeError consistently for more than a day, please report the
problem using the Report a Bug... entry in the Help menu.  Please
include the traceback printed above as part of the problem description."""
			from chimera import NonChimeraError
			raise NonChimeraError("Web service appears "
						"to be down.  See Reply Log "
						"for more details.")

	def _setup(self, serviceName, opalURL, sessionData):
		from chimera import preferences
		from DBPuppet.waprefs import WEBACCESS_PREF, WA_PROXY
		from DBPuppet.waprefs import WA_PROXY_HOST, WA_PROXY_PORT
		kw = {}
		if preferences.get(WEBACCESS_PREF, WA_PROXY):
			h = preferences.get(WEBACCESS_PREF, WA_PROXY_HOST)
			p = preferences.get(WEBACCESS_PREF, WA_PROXY_PORT)
			try:
				p = int(p)
				if p < 1 or p > 65535:
					raise ValueError("out of range")
			except ValueError:
				from chimera import UserError
				raise UserError("illegal proxy port number")
			kw["proxy"] = { "http":"%s:%d" % (h, p) }
		self.busy = False
		if sessionData:
			self.serviceURL, self.jobID, self.status = sessionData
		else:
			self.serviceURL = opalURL + serviceName
			self.jobID = None
			self.status = None
		self.times = None
		from suds.client import Client
		self.sudsClient = Client(self.serviceURL + "?wsdl", **kw)
		# Just to save some typing and shorten lines
		md = self.sudsClient.service.getAppMetadata()
		print "Web Service:", md.usage

	def sessionData(self):
		return self.serviceURL, self.jobID, self.status

	def _saveStatus(self, status):
		self.status = (status.code, str(status.message),
						str(status.baseURL))

	def currentStatus(self):
		if self.status:
			return self.status[1]
		elif self.busy:
			return "waiting for response from Opal server"
		else:
			return "no Opal job running"

	def logJobID(self):
		print "Opal service URL: %s" % self.serviceURL
		if self.status:
			print "Opal job URL: %s" % self.status[2]

	def launchJob(self, cmdLine, **kw):
		if self.jobID is not None or self.busy:
			raise RuntimeError("Job has been launched already")
		jobArgs = self._jobArgs(**kw)
		import chimera
		if chimera.nogui:
			from suds import WebFault
			try:
				resp = self.sudsClient.service.launchJob(cmdLine, **jobArgs)
			except WebFault as e:
				self.dumpTraceback("launchJob")
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			self.jobID = resp.jobID
			self._saveStatus(resp.status)
		else:
			from chimera.tkgui import runThread
			self.busy = True
			#import sys
			#print >> sys.__stderr__, "calling launchJobInThread"
			runThread(self._launchJobInThread, (cmdLine, jobArgs))

	def _jobArgs(self, **kw):
		return dict([ (k[1:], v) for k, v in kw.items()
						if k.startswith("_") ])

	def _launchJobInThread(self, q, args):
		#import sys
		#print >> sys.__stderr__, "executing launchJobInThread"
		cmdLine, jobArgs = args
		from suds import WebFault
		try:
			resp = self.sudsClient.service.launchJob(cmdLine, **jobArgs)
		except WebFault as e:
			self.dumpTraceback("launchJobInThread")
			def f(e=e):
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			self.status = (4, "launchJob failed", "")
			q.put(f)
		else:
			self.jobID = str(resp.jobID)
			self._saveStatus(resp.status)
			q.put(self.logJobID)
		self.busy = False
		q.put(q)
		#import sys
		#print >> sys.__stderr__, "returning from launchJobInThread"

	def launchJobBlocking(self, cmdLine, **kw):
		if self.jobID is not None:
			raise RuntimeError("Job has been launched already")
		jobArgs = self._jobArgs(**kw)
		from suds import WebFault
		try:
			resp = self.sudsClient.service.launchJobBlocking(cmdLine, **jobArgs)
		except WebFault as e:
			self.dumpTraceback("launchJobBlocking")
			self.status = (4, "launchJobBlocking failed", "")
			from chimera import NonChimeraError
			raise NonChimeraError(str(e))
		self._saveStatus(resp.status)
		self.logJobID()
		try:
			fileMap = self._makeOutputs(resp.jobOut)
		except:
			self.dumpTraceback("_makeOutputs")
			fileMap = None
		return (resp.status.code == 8, fileMap)

	def showStatus(self):
		print "Status:"
		code, message, baseURL = self.status
		print "\tCode:", code
		print "\tMessage:", message
		print "\tOutput Base URL:", baseURL

	def isFinished(self):
		#import sys
		#print >> sys.__stderr__, "executing isFinished", self.busy
		if self.busy:
			#print >> sys.__stderr__, "busy"
			return 0
		if self.status is None:
			#print >> sys.__stderr__, "no job"
			return 2
		code = self.status[0]
		if code == 8:
			# Normal finish
			#print >> sys.__stderr__, "normal"
			return 1
		elif code == 4:
			# Abnormal finish
			#print >> sys.__stderr__, "abnormal"
			return -1
		else:
			# Not finished
			#print >> sys.__stderr__, "not finished"
			return 0

	def queryStatus(self):
		#import sys
		#print >> sys.__stderr__, "calling from queryStatus", self.busy
		if self.busy:
			return
		if self.status is None:
			raise RuntimeError("No job has been launched yet")
		import chimera
		if chimera.nogui:
			from suds import WebFault
			try:
				status = self.sudsClient.service.queryStatus(self.jobID)
			except WebFault as e:
				self.dumpTraceback("queryStatus")
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			self._saveStatus(status)
		else:
			from chimera.tkgui import runThread
			self.busy = True
			#import sys
			#print >> sys.__stderr__, "calling from queryStatusInThread"
			runThread(self._queryStatusInThread, self.jobID)

	def _queryStatusInThread(self, q, jobID):
		#import sys
		#print >> sys.__stderr__, "executing from queryStatusInThread"
		import socket
		from suds import WebFault
		try:
			status = self.sudsClient.service.queryStatus(jobID)
		except WebFault as e:
			self.dumpTraceback("queryStatusInThread")
			def f(e=e):
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			q.put(f)
		else:
			self._saveStatus(status)
		self.busy = False
		q.put(q)
		#import sys
		#print >> sys.__stderr__, "returning from queryStatusInThread"

	def getJobStatistics(self, background=False):
		#import sys
		#print >> sys.__stderr__, "calling from getJobStatistics", self.busy
		if self.busy:
			return
		if self.status is None:
			raise RuntimeError("No job has been launched yet")
		import chimera
		if chimera.nogui or not background:
			from suds import WebFault
			try:
				stats = self.sudsClient.service.getJobStatistics(self.jobID)
			except WebFault as e:
				self.dumpTraceback("getJobStatistics")
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			self._saveTimes(stats)
		else:
			from chimera.tkgui import runThread
			self.busy = True
			#import sys
			#print >> sys.__stderr__, "calling from getJobStatisticsInThread"
			runThread(self._getJobStatisticsInThread, self.jobID)

	def _getJobStatisticsInThread(self, q, jobID):
		#import sys
		#print >> sys.__stderr__, "executing from getJobStatisticsInThread"
		from suds import WebFault
		try:
			stats = self.sudsClient.service.getJobStatistics(jobID)
		except WebFault as e:
			self.dumpTraceback("getJobStatisticsInThread")
			def f(e=e):
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			q.put(f)
		else:
			self._saveTimes(stats)
		self.busy = False
		q.put(q)
		#import sys
		#print >> sys.__stderr__, "returning from getJobStatisticsInThread"

	def _saveTimes(self, stats):
		import time
		# Assumes that startTime and completionTime are
		# datetime.datetime objects.  True for suds.
		try:
			self.times = (time.mktime(stats.startTime.timetuple()),
				time.mktime(stats.completionTime.timetuple()))
		except:
			self.dumpTraceback("_saveTimes")

	def getOutputs(self):
		if self.status is None:
			raise RuntimeError("No job has been launched yet")
		from suds import WebFault
		try:
			resp = self.sudsClient.service.getOutputs(self.jobID)
		except WebFault as e:
			self.dumpTraceback("getOutputs")
			from chimera import NonChimeraError
			raise NonChimeraError(str(e))
		return self._makeOutputs(resp)

	def _makeOutputs(self, out):
		self.fileMap = {
			"stdout.txt": out.stdOut,
			"stderr.txt": out.stdErr,
		}
		try:
			outputFiles = out.outputFile
		except AttributeError:
			# No extra output files created
			pass
		else:
			for file in out.outputFile:
				self.fileMap[file.name] = file.url
		return self.fileMap
	
	def getStdOut(self):
		"""
		return the content of stdout.txt file
		"""
		if self.status is None:
			raise RuntimeError("No job has been launched yet")
		stdOut_URL = self.status[2] + '/stdout.txt'
		return self.getURLContent(stdOut_URL)

	def destroy(self):
		if self.jobID is None:
			self.status = None
			return
		from suds import WebFault
		try:
			status = self.sudsClient.service.destroy(self.jobID)
		except WebFault as e:
			self.dumpTraceback("destroy")
			from chimera import NonChimeraError
			raise NonChimeraError(str(e))
		#self.status = self._saveStatus(status)
		#self.showStatus()
		# Mark that no jobs are running
		self.status = None
		self.jobID = None

	def getURLContent(self, url):
		import urllib2
		f = urllib2.urlopen(url)
		data = f.read()
		f.close()
		return data

	def showURLContent(self, title, url):
		from chimera import replyobj
		data = self.getURLContent(url)
		if not data:
			data = "[no output]\n"
		replyobj.message("%s\n-----\n%s-----\n" % (title, data))
	
	def getFileContent(self, filename):
		if hasattr(self, 'fileMap'):
			fm = self.fileMap
		else:
			fm = self.getOutputs()
		if filename in fm:
			return self.getURLContent(fm[filename])
		else:
			return None

	def dumpTraceback(self, msg):
		import traceback, sys
		print "Traceback from web service request (%s):" % msg
		traceback.print_exc(file=sys.stdout)
		try:
			asp = self.appServicePort
			b = asp.binding
		except AttributeError:
			pass
		else:
			print "appServicePort", asp, "url:", b.url
	
def makeInputFile(path, name=None, mode="r"):
	try:
		# Path can be a 2-tuple of (file path, open mode)
		path, mode = path
	except ValueError:
		pass
	if name is None:
		import os.path
		name = os.path.basename(path)
	with open(path, mode) as f:
		return makeInputFileWithContents(name, f.read())

def makeInputFileWithContents(name, contents):
	import base64
	return { "name": name, "contents": base64.b64encode(contents) }

if __name__ in [ "__main__", "chimeraOpenSandbox" ]:
	def launchJobTest(opal, argList, **kw):
		import time, sys
		opal.launchJob(argList, **kw)
		while not opal.isFinished():
			opal.showStatus()
			sys.stdout.flush()
			time.sleep(10)
			opal.queryStatus()
		opal.showStatus()
		success = opal.isFinished() > 0
		fileMap = opal.getOutputs()
		return success, fileMap

	if 0:
		import pprint
		# Test pdb2pqr at NBCR
		service = "Pdb2pqrOpalService"
		NBCR_Opal = "http://ws.nbcr.net:8080/opal/services/"
		argList = "--ff=amber sample.pdb sample.pqr"
		inputFiles = [ makeInputFile("opal_testdata/sample.pdb") ]

		opal = OpalService(service, NBCR_Opal)

		print "Testing non-blocking job"
		success, fileMap = launchJobTest(opal, argList,
							_inputFile=inputFiles)
		print "Success", success
		print "Outputs:"
		pprint.pprint(fileMap)
		opal.destroy()
		print "Finished non-blocking job"

		print "Testing blocking job"
		success, fileMap = opal.launchJobBlocking(argList,
							_inputFile=inputFiles)
		print "Outputs:"
		pprint.pprint(fileMap)
		opal.destroy()
		print "Finished blocking job"

	if 1:
		import pprint
		service = "BlastProteinService"
		argList = "-i blastpdb.in -o blastpdb.out -e 1e-10"
		inputFiles = [ makeInputFile("opal_testdata/blastpdb.in") ]
		print "Launching blastprotein job"
		opal = OpalService(service)
		success, fileMap = launchJobTest(opal, argList,
							_inputFile=inputFiles)
		print "Success", success
		print "Outputs:"
		pprint.pprint(fileMap)
		print "Finished blastpdb job"
		def showFile(name, url):
			import sys, urllib2
			print "%s:" % name
			print "-----"
			f = urllib2.urlopen(url)
			sys.stdout.write(f.read())
			f.close()
			print "-----"
		showFile("blastpdb.in", fileMap["blastpdb.in"])
		if success:
			showFile("blastpdb.out", fileMap["blastpdb.out"])
		else:
			showFile("stdout", fileMap["stdout"])
			showFile("stderr", fileMap["stderr"])
