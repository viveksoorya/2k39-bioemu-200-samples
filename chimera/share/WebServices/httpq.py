"""HTTPQueue: Class for managing HTTP requests

Accessing some web services (Opal, ModBase evaluation server)
involves sending a "launch" request followed by a series of
"status query" requests.  The service transaction is complete
when a status response declares that the job has completed.

To keep Chimera interactive, these web connections should be
done in a separate thread than the main thread since there is
no guarantee that servers will respond quickly (or at all).

HTTPQueue enables a client class to request for a "slot" for
sending requests to a particular server (as identified by
a host name).  Requests, both launch and status query, are
then initiated via the slot method "call" passing in a function
and the argument that the function will be called with.  The
function will be called in a separate thread at a later time
(more below) and receive _two_ arguments: a GUI request queue
and the passed-in argument.

Because the function will _not_ execute in the main Chimera
thread, it must not make any GUI calls, which includes both
Tkinter calls and printing to either sys.stdout or sys.stderr
(which potentially updates the Reply Log).  Instead, any
GUI activity must be done by posting a callback request to
the GUI request queue (in the form of a function taking no
arguments) and the callback will get invoked at the next
"checkForChanges".

The function is not always called immediately.  HTTPQueue
tracks the number of requests sent to a particular server
and will only allow a certain number of outstanding requests
(for all slots) in an attempt to avoid flooding the server.
As earlier requests are completed, later requests are
initiated.  A request is dropped if there is already an
outstanding one for the same slot.  For example, when a
status query request will be dropped if there is already
a prior one pending.
"""

class HTTPQueue:

	def __init__(self):
		self.serverMap = dict()

	def newSlot(self, serverName):
		try:
			server = self.serverMap[serverName]
		except KeyError:
			server = HTTPQueueServer(self, serverName)
			self.serverMap[serverName] = server
		return server.makeSlot()

	def _deleteServer(self, serverName):
		del self.serverMap[serverName]


class HTTPQueueServer:

	def __init__(self, queue, serverName):
		self.queue = queue
		self.serverName = serverName
		self.slots = set()
		self.requests = list()
		self.running = set()
		self.threadMax = 10

	def makeSlot(self):
		slot = HTTPQueueSlot(self)
		self.slots.add(slot)
		return slot

	def deleteSlot(self, slot):
		self.slots.remove(slot)
		if not self.slots:
			self.queue._deleteServer(self.serverName)

	def newRequest(self, slot):
		self.requests.append(slot)
		self._startRequest()

	def _startRequest(self):
		from chimera.tkgui import runThread
		while len(self.running) < self.threadMax and self.requests:
			slot = self.requests.pop(0)
			if slot in self.running:
				continue
			self.running.add(slot)
			runThread(slot.run)

	def _requestDone(self, slot):
		self.running.remove(slot)
		slot._requestFinished()
		self._startRequest()


class HTTPQueueSlot:

	def __init__(self, server):
		self.server = server
		self.requestData = None
		import Queue
		self.q = Queue.Queue()

	def request(self, func, *args):
		if self.requestData is not None:
			return False
		self.requestData = (func, args)
		self.server.newRequest(self)
		return True

	def run(self, q):
		func, args = self.requestData
		try:
			func(self.q, *args)
		except:
			import sys, traceback
			traceback.print_exc(file=sys.__stderr__)
			exc_type, exc_value, exc_traceback = sys.exc_info()
			ml = traceback.format_exception_only(exc_type,
								exc_value)
			def f(msg=''.join(ml)):
				from chimera import NonChimeraError
				raise NonChimeraError(msg)
			q.put(f)
		def f(s=self):
			s.server._requestDone(s)
		q.put(f)
		while not self.q.empty():
			q.put(self.q.get())
		q.put(q)

	def _requestFinished(self):
		self.requestData = None

	def finished(self):
		self.server.deleteSlot(self)


singleton = None

def get():
	global singleton
	if singleton is None:
		singleton = HTTPQueue()
	return singleton


if 1:
	def demo():
		def printStdout(msg):
			print msg
		def getURL(guiq, host, path):
			import urllib2
			url = "http://%s%s" % (host, path)
			u = urllib2.urlopen(url)
			msg = u.read()
			def f(p=printStdout, m=msg):
				p(m)
			guiq.put(f)
		host = "www.cgl.ucsf.edu"
		path = "/index.html"
		httpq = get()
		import time
		for i in range(5):
			slot = httpq.newSlot(host)
			print "request", slot.request(getURL, host, path)
			print httpq.serverMap
			slot.finished()
		print httpq.serverMap
