import Queue, threading, sys
import chimera

singleton = None

def run():
	global singleton
	if not singleton:
		singleton = RESTServer()

class RESTServer:

	def __init__(self, ssl=False):
		import chimera
		chimera.extension.manager.registerInstance(self)
		from BaseHTTPServer import HTTPServer
		self.httpd = HTTPServer(("localhost", 0), RESTHandler)
		if ssl:
			import os.path, ssl
			cert = os.path.join(os.path.dirname(__file__),
							"server.pem")
			self.httpd.socket = ssl.wrap_socket(self.httpd.socket,
						certfile=os.path.join(cert))
		msg = ("REST server on host %s port %d" % 
						self.httpd.server_address)
		chimera.replyobj.status(msg, log=True)
		import sys
		try:
			print >> sys.__stdout__, msg
			sys.__stdout__.flush()
		except IOError:
			# This can happen on Windows when console
			# is not connected
			pass
		from chimera import threadq
		self.thread = threadq.runThread(self._runServer, daemon=True)

	def _runServer(self, q):
		self.httpd.cmdQueue = q
		self.httpd.serve_forever()
		q.put(q)

	def emRaise(self):
		# Do nothing
		pass

	def emHide(self):
		# Do nothing
		pass

	def emQuit(self):
		self.httpd.shutdown()
		chimera.extension.manager.deregisterInstance(self)

from BaseHTTPServer import BaseHTTPRequestHandler
class RESTHandler(BaseHTTPRequestHandler):

	ContentTypes = [
		( ".html", "text/html", "r" ),
		( ".png", "image/png", "rb" ),
	]

	def do_GET(self):
		import urlparse
		r = urlparse.urlparse(self.path)
		# path starts with /
		path = r.path[1:]
		if path == "run":
			args = urlparse.parse_qs(r.query)
			if self.command == "POST":
				postArgs = self._parsePost()
				if postArgs:
					for k, v in postArgs.iteritems():
						try:
							l = args[k]
						except KeyError:
							args[k] = v
						else:
							l.extend(v)
			from Queue import Queue
			q = Queue()
			def run(q=q, h=self, args=args):
				_run(q, h, args)
			self.server.cmdQueue.put(run)
			q.get()
		elif path == "favicon.ico":
			import os.path
			dirname = os.path.dirname(__file__)
			try:
				with file(os.path.join(dirname, path), "rb") as f:
					data = f.read()
			except IOError:
				self.send_error(404)
			else:
				self.send_response(200)
				self.send_header("Content-Type", "image/png")
				self.send_header("Content-Length", str(len(data)))
				self.end_headers()
				self.wfile.write(data)
		elif path.startswith("static/"):
			for suffix, c, m in self.ContentTypes:
				if path.endswith(suffix):
					ctype = c
					mode = m
					break
			else:
				ctype = "text/plain"
				mode = "r"
			import os.path
			dirname = os.path.dirname(__file__)
			try:
				with file(os.path.join(dirname, path), mode) as f:
					self.send_response(200)
					self.send_header("Content-Type", ctype)
					self.end_headers()
					self.wfile.write(f.read())
			except IOError:
				self.send_error(404)
		else:
			self.plainText()
			print >> self.wfile, "Bad path: \"%s\"" % r.path

	do_POST = do_GET

	def _parsePost(self):
		ctype = self.headers.get('content-type')
		if not ctype:
			return None
		import cgi
		ctype, pdict = cgi.parse_header(ctype)
		if ctype == 'multipart/form-data':
			return cgi.parse_multipart(self.rfile, pdict)
		elif ctype == 'application/x-www-form-urlencoded':
			clength = int(self.headers.get('Content-length'))
			return cgi.parse_qs(self.rfile.read(clength), True)
		else:
			return None

	def plainText(self):
		self.send_response(200)
		self.send_header("Content-Type", "text/plain")
		self.end_headers()

def _show(q, h, s):
	h.plainText()
	print >> h.wfile, "_show", s
	q.put("done")

def _run(q, h, args):
	h.plainText()
	import chimera
	r = chimera.replyobj.pushReply(RESTReply(h.wfile))
	try:
		from Midas import MidasError
		from chimera.oslParser import OSLSyntaxError
		from chimera import replyobj
		try:
			for cmd in args["command"]:
				chimera.runCommand(cmd)
		except KeyError, v:
			replyobj.error("command missing")
		except (MidasError, OSLSyntaxError), v:
			replyobj.error(str(v) + '\n')
		except Exception, e:
			if not chimera.nogui:
				raise
			replyobj.reportException()
	finally:
		try:
			chimera.replyobj.popReply(r)
		except (ValueError, IndexError):
			# On exit we might be called after replyobj has
			# already deleted the stack
			pass
		q.put("done")

class RESTReply:

	def __init__(self, f):
		self.f = f

	def writeLine(self, s):
		if s.endswith('\n'):
			self.write(s)
		else:
			self.write(s + '\n')

	def write(self, s):
		if isinstance(s, unicode):
			s = s.encode("utf-8", "backslashreplace")
		self.f.write(s)

	def flush(self):
		pass

	def clear(self):
		pass

	def message(self, s):
		import chimera
		if not chimera.silent:
			self.writeLine(s)

	command = message

	def status(self, s, **kw):
		import chimera
		if not chimera.nostatus:
			self.writeLine(s)

	info = message

	warning = message

	error = writeLine
