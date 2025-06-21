"""Class and function that emulates Opal API but runs locally."""

class LocalOpalService:

	StatusFile = "__status"
	LockFile = "__lock"
	MonitorScript = """
cmdLine = %s
import filelock
with filelock.FileLock(%s):
	import sys, subprocess, time
	with file("stderr.txt", "w") as sys.stderr:
		with file("stdout.txt", "w") as sys.stdout:
			startTime = time.time()
			try:
				exitStatus = subprocess.call(cmdLine,
							shell=True,
							stdin=None,
							stdout=sys.stdout,
							stderr=sys.stderr)
			except:
				import traceback
				traceback.print_exc()
				exitStatus = -1
			endTime = time.time()
			with file(%s, "w") as f:
				print >> f, exitStatus
				print >> f, startTime
				print >> f, endTime
"""

	def __init__(self, serviceName=None, opalURL=None, sessionData=None):
		# serviceName is actually path to executable
		import socket
		self.hostname = socket.gethostname()
		import os, os.path
		if sessionData:
			(hostname, self.exePath, self.pid,
				self.tmpdir, self.status) = sessionData
			if hostname != self.hostname:
				from chimera import UserError
				raise UserError("job ran on host %s, "
						"this is host %s" % (
							hostname,
							self.hostname))
			lockFile = os.path.join(self.tmpdir, self.LockFile)
			import filelock
			self.lock = filelock.FileLock(lockFile)
		else:
			self.exePath = serviceName
			self.pid = None
			self.tmpdir = None
			self.status = "not running"
			self.lock = None
		if (not os.path.isfile(self.exePath)
		or  not os.access(self.exePath, os.X_OK)):
			from chimera import UserError
			raise UserError("\"%s\" is not an executable"
								% self.exePath)
		self.times = None
		self.exitStatus = None
		self.fileMap = None

	def sessionData(self):
		return (self.hostname, self.exePath, self.pid,
				self.tmpdir, self.status)

	def currentStatus(self):
		return self.status

	def logJobID(self):
		if self.status != "running":
			print "Local job: %s (%s)" % (self.exePath, self.status)
		else:
			print "Local job: %s (PID: %d)" % (self.exePath,
								self.pid)

	def launchJob(self, options, _inputFile=None, **kw):
		self._mktmpdir()
		if _inputFile:
			self._copyInputFiles(_inputFile)
		p = self._runMonitor(options)
		import os.path
		lockFile = os.path.join(self.tmpdir, self.LockFile)
		import filelock
		self.lock = filelock.FileLock(lockFile)
		self.pid = p.pid
		self.status = "running"
	
	def launchJobBlocking(self, options, _inputFile=None, **kw):
		self._mktmpdir()
		if _inputFile:
			self._copyInputFiles(_inputFile)
		p = self._runMonitor(options)
		self.exitStatus = p.wait()
		self.status = "finished"
		return self.exitStatus == 0, self.getOutputs()

	def _mktmpdir(self):
		import tempfile
		self.tmpdir = tempfile.mkdtemp(prefix="ch", suffix=".d")

	def _copyInputFiles(self, inputFiles):
		# inputFiles is a list of tuples returned by 
		# makeInputFile (see below)
		import shutil
		import os.path
		for name, path in inputFiles:
			target = os.path.join(self.tmpdir, name)
			shutil.copyfile(path, target)

	def _runMonitor(self, options):
		import os.path
		cmdLine = "\"%s\" %s" % (self.exePath, options)
		script = os.path.join(self.tmpdir, "__monitor.py")
		with file(script, "w") as f:
			print >> f, self.MonitorScript % (repr(cmdLine),
							repr(self.LockFile),
							repr(self.StatusFile))
		import subprocess, sys
		if sys.platform == "darwin":
			from CGLutil.findExecutable import findExecutable
			v = sys.version_info
			python = findExecutable("python%s.%s" % (v.major,
								v.minor))
			if python is None:
				raise ValueError("cannot find %s" % python)
		else:
			python = sys.executable
		p = subprocess.Popen([ python, script ], cwd=self.tmpdir)
		return p

	def showStatus(self):
		print "Status:", self.status
		print "\tDirectory:", self.tmpdir

	def isFinished(self):
		if self.status == "running":
			#print >> sys.__stderr__, "no job"
			return 0
		elif self.status == "finished":
			if self.exitStatus == 0:
				return 1
			else:
				return -1
		else:
			return 2

	def queryStatus(self):
		if self.status != "running" or self.lock.locked():
			return
		self.status = "finished"
		import os.path
		statusFile = os.path.join(self.tmpdir, self.StatusFile)
		try:
			with file(statusFile) as f:
				print "Status file contents:"
				print f.read()
			with file(statusFile) as f:
				self.exitStatus = int(f.readline())
				startTime = float(f.readline())
				endTime = float(f.readline())
				self.times = (startTime, endTime)
		except:
			import traceback, sys
			traceback.print_exc(file=sys.stdout)
			self.exitStatus = -1
			self.times = (None, None)

	def getJobStatistics(self, background=False):
		# Stats fetched when we read status file
		return

	def getOutputs(self):
		if self.fileMap is None:
			import os, os.path
			files = [ fn for fn in os.listdir(self.tmpdir)
					if not fn.startswith("__") ]
			self.fileMap = dict([ (fn,
						os.path.join(self.tmpdir, fn))
						for fn in files ])
		return self.fileMap

	def getStdOut(self):
		if self.status != "finished":
			raise RuntimeError("No job has been launched yet")
		return getFileContent("stdout.txt")

	def destroy(self):
		import shutil
		shutil.rmtree(self.tmpdir)
		self.pid = None
		self.tmpdir = None
		self.status = "not running"

	def getURLContent(self, url):
		# URL is really a path
		# function named to match OpalService API
		with file(url) as f:
			return f.read()

	def showURLContent(self, title, url):
		# URL is really a path
		# function named to match OpalService API
		data = self.getURLContent(url)
		if not data:
			data = "[no output]\n"
		from chimera import replyobj
		replyobj.message("%s\n-----\n%s-----\n" % (title, data))

	def getFileContent(self, filename):
		fm = self.getOutputs()
		if filename in fm:
			return self.getURLContent(fm[filename])
		else:
			return None

def localMakeInputFile(path, name=None, mode="r"):
	if name is None:
		import os.path
		name = os.path.basename(path)
	return (name, path)
