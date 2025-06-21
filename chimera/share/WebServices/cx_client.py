#!/usr/local/bin/python2.5

#NOTE: requires installation of urllib3 and six
import time
import json
from cxservices.api import default_api
from cxservices.rest import ApiException
import six
from six.moves.urllib.error import URLError
from urllib3.exceptions import MaxRetryError, NewConnectionError

class JobMonitorError(RuntimeError):
	pass

job_ended_statuses = set(["finished", "failed", "deleted", "canceled"])
def result_to_code(result):
	status = result.status
	if status not in job_ended_statuses:
		return 0
	return 8 if status == "finished" else 4

class CxService:

	'''
	DefaultOpalURL="http://webservices.rbvi.ucsf.edu/opal2/services/"
	'''
	chimerax_api = default_api.DefaultApi()
	chimerax_api.api_client.user_agent = "UCSF Chimera"

	session_attrs = ["service_name", "job_id", "status"]

	def __init__(self, serviceName=None, opalURL=None, sessionData=None):
		self.busy = False
		self.job_id = self.launch_time = self.end_time = self.status = self.outputs = self.next_poll = None
		self.service_name = serviceName
		if sessionData:
			for attr_name, value in sessionData.items():
				setattr(self, attr_name, value)

		from chimera import preferences
		from DBPuppet.waprefs import WEBACCESS_PREF, WA_PROXY
		from DBPuppet.waprefs import WA_PROXY_HOST, WA_PROXY_PORT
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
			self.chimerax_api.api_client.configuration.proxy = "%s:%d" % (h, p)
		else:
			self.chimerax_api.api_client.configuration.proxy = None
		self.busy = False
		'''
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
		'''

	def _setup(self, serviceName, opalURL, sessionData):
		raise NotImplementedError("_setup")
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
		return { attr_name: getattr(self, attr_name) for attr_name in self.session_attrs }
		'''
		raise NotImplementedError("sessionData")
		return self.serviceURL, self.jobID, self.status
		'''

	def _saveStatus(self, status):
		raise NotImplementedError("_saveStatus")
		self.status = (status.code, str(status.message),
						str(status.baseURL))

	def currentStatus(self):
		if self.status:
			return self.status[1]
		elif self.busy:
			return "waiting for response from server"
		else:
			return "no job running"
		"""
		raise NotImplementedError("currentStatus")
		if self.status:
			return self.status[1]
		elif self.busy:
			return "waiting for response from Opal server"
		else:
			return "no Opal job running"
		"""

	def logJobID(self):
		print "%s web service job ID: %s" % (self.service_name.replace('_', ' ').title(), self.job_id)
		"""
		raise NotImplementedError("logJobID")
		print "Opal service URL: %s" % self.serviceURL
		if self.status:
			print "Opal job URL: %s" % self.status[2]
		"""

	def launchJob(self, cmdLine, **kw):
		import chimera
		self._launch(cmdLine, kw, blocking=chimera.nogui)
		"""
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
		"""

	def _jobArgs(self, **kw):
		raise NotImplementedError("_jobArgs")
		return dict([ (k[1:], v) for k, v in kw.items()
						if k.startswith("_") ])

	def _launch(self, cmd_line, kw, blocking=False):
		params, files_to_upload = self._process_input(cmd_line, kw)
		if self.launch_time is not None:
			raise RuntimeError("REST job has already been launched")
		self.launch_time = time.time()
		if blocking:
			try:
				result = self.chimerax_api.submit_job(
					job_type=self.service_name,
					params=params,
					filepaths=files_to_upload
				)
			except ApiException as e:
				self.status = (4, "failed", None)
				self.end_time = time.time()
				reason = json.loads(e.body)['description']
				print "Error launching job:", reason
			except (URLError, MaxRetryError, NewConnectionError) as e:
				self.status = (4, "failed", None)
				self.end_time = time.time()
				print "Error launcing job: web services unavailable.  Please try again soon."
			else:
				self.status = (0, "running", None)
				self.job_id = result.job_id
				self.urls = {
					"status": result.status_url,
					"results": result.results_url
				}
				self.next_poll = int(result.next_poll)
				self.logJobID()
				self.run()
				#TODO: return values
		else:
			from chimera.threadq import runThread
			self.busy = True
			runThread(self._launchJobInThread, (params, files_to_upload), daemon=True)

	def run(self):
		while self.running():
			if self.terminating():
				break
			time.sleep(float(self.next_check()))
			if self.running():
				self.monitor()

	def running(self):
		return self.launch_time is not None and self.end_time is None

	def terminating(self):
		#TODO
		return False

	def next_check(self):
		return self.next_poll

	def monitor(self):
		try:
			result = self.chimerax_api.get_status(job_id=self.job_id)
		except ApiException as e:
			raise JobMonitorError(e)
		self.status = (result_to_code(result), result.status, self.job_id)
		self.next_poll = result.next_poll
		if self.status[1] in ("finished", "failed", "deleted", "canceled") and self.end_time is None:
			self.end_time = time.time()

	def _process_input(self, cmd_line, kw):
		if self.service_name == "modeller":
			input_files = []
			import os.path
			for path in kw['_inputFile']:
				folder, fname = os.path.split(path)
				if fname == "ModellerScriptConfig.xml":
					config_path = path
				else:
					input_files.append(path)
			f = open(config_path, 'r')
			config_text = f.read()
			f.close()
			params = {}
			bool_func = lambda val: bool(int(val))
			for param_name, key_name, key_type in [
				("key", "key", str),
				("version", "version", int),
				("numModels", "numModel", int),
				("hetAtom", "hetAtom", bool_func),
				("water", "water", bool_func),
				("allHydrogen", "allHydrogen", bool_func),
				("veryFast", "veryFast", bool_func),
				("loopInfo", "loopInfo", eval),
			]:
				key_marker = '<' + key_name + '>'
				start = config_text.find(key_marker) + len(key_marker)
				end = start + config_text[start:].find('<')
				params[param_name] = key_type(config_text[start:end])
			if params['loopInfo']:
				# have to inherit from LoopModel, not AllHModel, so...
				params['allHydrogen'] = False
		else:
			fixed_args, arg_mapping, file_mapping_key = {
				'muscle': (
					{ 'in_flag': '-in', 'out_flag': '-out' },
					{ '-in': (True, None), '-out': (True, None),
						'-maxiters': (True, 'maxiters'), '-maxhours': (True, None), },
					'_inputFile'
				),
				'clustal_omega': (
					{ 'in_flag': '-i', 'out_flag': '-o' },
					{ '-i': (True, None), '-o': (True, None), '--iterations': (True, 'iterations'),
						'--full': (False, None), '--full-iter': (False, None), },
					'_inputFile'
				),
				'blast': (
					{ 'blimit': "1000" },
					{ '-i': (True, None), '-o': (True, None), '-d': (True, 'db'),
						'-e': (True, 'evalue'), '-M': (True, 'matrix'), '-seq': (True, 'input_seq') },
					'_inputFile'
				),
			}[self.service_name]
			params = fixed_args
			args = cmd_line.split()
			while args:
				flag = args.pop(0)
				has_val, mapping = arg_mapping[flag]
				if has_val:
					val = args.pop(0)
				if mapping is not None:
					params[mapping] = val
			input_files = kw[file_mapping_key]
		return json.dumps(params), {"job_files": input_files}

	def _launchJobInThread(self, q, args):
		params, files_to_upload = args
		try:
			result = self.chimerax_api.submit_job(
				job_type=self.service_name,
				params=params,
				filepaths=files_to_upload
			)
		except ApiException as e:
			self.dumpTraceback("launchJobInThread", q)
			self.status = (4, "failed", None)
			self.end_time = time.time()
			reason = json.loads(e.body)['description']
			def printReason(reason=reason):
				print "Error launching job:", reason
			q.put(printReason)
		except (URLError, MaxRetryError, NewConnectionError) as e:
			self.status = (4, "failed", None)
			self.end_time = time.time()
			def printLaunchFailure():
				print "Error launcing job: web services unavailable.  Please try again soon."
			q.put(printLaunchFailure)
		else:
			self.status = (0, "running", None)
			self.job_id = result.job_id
			self.urls = {
				"status": result.status_url,
				"results": result.results_url
			}
			self.next_poll = int(result.next_poll)
			q.put(self.logJobID)
		self.busy = False
		q.put(q)
		if self.status[0] == 0:
			self.run()
		"""
		raise NotImplementedError("_launchJobInThread")
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
		"""

	def launchJobBlocking(self, cmdLine, **kw):
		#self._launch(cmdLine, kw, blocking=True)
		#TODO: needs to return (success, file_map)
		raise NotImplementedError("launchJobBlocking")
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
		raise NotImplementedError("showStatus")
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
		if self.busy:
			return
		if self.status is None:
			raise RuntimeError("No job has been launched yet")
		import chimera
		if chimera.nogui:
			try:
				result = self.chimerax_api.get_status(job_id=self.jobID)
			except ApiException as e:
				self.dumpTraceback("queryStatus")
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			self.status = (result_to_code(result), result.status, None)
		else:
			from chimera.threadq import runThread
			self.busy = True
			#import sys
			#print >> sys.__stderr__, "calling from queryStatusInThread"
			runThread(self._queryStatusInThread, self.job_id)
		"""
		raise NotImplementedError("queryStatus")
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
		"""

	def _queryStatusInThread(self, q, jobID):
		try:
			result = self.chimerax_api.get_status(job_id=self.job_id)
		except ApiException as e:
			self.dumpTraceback("queryStatusInThread")
			def f(e=e):
				from chimera import NonChimeraError
				raise NonChimeraError(str(e))
			q.put(f)
		else:
			self.status = (result_to_code(result), result.status, None)
		self.busy = False
		q.put(q)
		"""
		raise NotImplementedError("_queryStatusInThread")
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
		"""

	def getJobStatistics(self, background=False):
		self.times = (self.launch_time, self.end_time)
		"""
		raise NotImplementedError("getJobStatistics")
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
		"""

	def _getJobStatisticsInThread(self, q, jobID):
		raise NotImplementedError("_getJobStatisticsInThread")
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
		raise NotImplementedError("_saveTimes")
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
		return self._make_outputs()
		"""
		raise NotImplementedError("getOutputs")
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
		"""

	def _make_outputs(self):
		try:
			file_names = self.chimerax_api.get_job_filenames(self.job_id).files
		except ApiException as e:
			self.dumpTraceback("_make_outputs (file names)")
			from chimera import NonChimeraError
			raise NonChimeraError(str(e))
		import StringIO
		outputs = {}
		for fn in file_names:
			try:
				content = self.chimerax_api.get_file(self.job_id, fn)
			except ApiException as e:
				self.dumpTraceback("_make_outputs (file contents)")
				from chimera import NonChimeraError
				raise NonChimeraError("%s: %s" % (fn, str(e)))
			outputs[fn] = StringIO.StringIO(content)
		return outputs

	def _makeOutputs(self, out):
		raise NotImplementedError("_makeOutputs")
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
	
	def get_results(self):
		return self.chimerax_api.get_results(self.job_id)

	def get_stderr(self):
		raise NotImplementedError("get_stderr")

	def get_stdout(self):
		raise NotImplementedError("get_stdout")

	def getStdOut(self):
		try:
			return self.chimerax_api.get_file(self.job_id, "stdout.txt")
		except ApiException as e:
			self.dumpTraceback("getStdOut")
			from chimera import NonChimeraError
			raise NonChimeraError("stdout.txt: %s" % str(e))
		'''
		raise NotImplementedError("getStdOut")
		"""
		return the content of stdout.txt file
		"""
		if self.status is None:
			raise RuntimeError("No job has been launched yet")
		stdOut_URL = self.status[2] + '/stdout.txt'
		return self.getURLContent(stdOut_URL)
		'''

	def destroy(self):
		raise NotImplementedError("destroy")
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
		return url.getvalue()
		"""
		raise NotImplementedError("getURLContent")
		import urllib2
		f = urllib2.urlopen(url)
		data = f.read()
		f.close()
		return data
		"""

	def showURLContent(self, title, url):
		data = url.getvalue()
		if not data:
			data = "[no output]\n"
		from chimera import replyobj
		replyobj.message("%s\n-----\n%s-----\n" % (title, data))
		"""
		raise NotImplementedError("showURLContent")
		from chimera import replyobj
		data = self.getURLContent(url)
		if not data:
			data = "[no output]\n"
		replyobj.message("%s\n-----\n%s-----\n" % (title, data))
		"""
	
	def getFileContent(self, filename):
		if hasattr(self, 'fileMap'):
			fm = self.fileMap
		else:
			fm = self.getOutputs()
		if filename in fm:
			return self.getURLContent(fm[filename])
		else:
			return None

	def dumpTraceback(self, msg, q=None):
		import traceback, sys
		def printError(msg=msg, tb=traceback.format_exc()):
			print "Traceback from web service request (%s):" % msg
			print tb
		if q is None:
			printError()
		else:
			q.put(printError)
		"""
		raise NotImplementedError("dumpTraceback")
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
		"""
	
def makeInputFile(path, name=None, mode="r"):
	try:
		# Path can be a 2-tuple of (file path, open mode)
		path, mode = path
	except ValueError:
		pass
	return path
	'''
	if name is None:
		import os.path
		name = os.path.basename(path)
	with open(path, mode) as f:
		return makeInputFileWithContents(name, f.read())
	'''

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
