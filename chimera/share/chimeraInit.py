"""module to initialize chimera environment

--- UCSF Chimera Copyright ---
Copyright (c) 2000 Regents of the University of California.
All rights reserved.  This software provided pursuant to a
license agreement containing restrictions on its disclosure,
duplication and use.  This notice must be embedded in or
attached to all copies, including partial copies, of the
software or any revisions or derivations thereof.
--- UCSF Chimera Copyright ---
"""
__rcsid__ = "$Id: chimeraInit.py 41967 2018-11-17 22:08:30Z gregc $"

# TODO: support some of the Xt arguments below on Posix platforms
#XtArgs = [
#	"+rv",
#	"+synchronous",
#	("-background", "*background"),
#	("-bd",         "*borderColor"),
#	("-bg",         "*background"),
#	("-bordercolor","*borderColor"),
#	("-borderwidth",".borderWidth"),
#	("-bw",         ".borderWidth"),
#	("-display",    ".display"),
#	("-fg",         "*foreground"),
#	("-fn",         "*font"),
#	("-font",       "*font"),
#	("-foreground", "*foreground"),
#	("-geometry",   ".geometry"),
#	"-iconic",
#	("-name",       ".name"),
#	"-reverse",
#	"-rv",
#	("-selectionTimeout", ".selectionTimeout"),
#	"-synchronous",
#	("-title",      ".title"),
#	("-xnllanguage",".xnlLanguage"),
#	("-xrm",        ""),
#	("-xtsessionID",".sessionID"),
#]

def _findRoot():
	# New _findRoot() logic: we hard code the installation location
	# of chimera.
	import os
	try:
		root = os.environ["CHIMERA"]
	except KeyError:
		raise RuntimeError, "can not find chimera installation directory"
	return root

_original_environ = {}		# env. that chimera "started" with
_CHIMERA_SETENV = set()		# env. variables to reset to pre-chimera values
_CHIMERA_ = "CHIMERA_"		# prefix for saved pre-chimera env. variables

def putenv(name, value):
	"""Similar to os.putenv.  Use this for environment changes
	that shouldn't propagate to non-chimera processes.  Also
	updates os.environ."""
	import os
	ch_name = _CHIMERA_ + name
	if name not in _CHIMERA_SETENV and name in _original_environ:
		_original_environ[ch_name] = _original_environ[name]
	_original_environ[name] = value
	import sys
	if not sys.platform.startswith('win') and isinstance(value, unicode):
		value = value.encode('utf-8')
	os.environ[name] = value
	_CHIMERA_SETENV.add(name)

def _fix_environ(path, chimera_env):
	# Chimera always calls its own programs with the full path.
	import sys, os
	if sys.platform.startswith('win'):
		cmd = os.getenv("COMSPEC")
		if not cmd:
			cmd = "cmd"
		SYSTEM = [cmd, '/c']
		SHELL_VAR = "%CHIMERA%\\"
	else:
		SYSTEM = ['/bin/sh', '-c']
		SHELL_VAR = "$CHIMERA/"
	if path:
		shell = False
		if not isinstance(path, basestring):
			if list(path[0:2]) == SYSTEM:
				shell = True
				path = path[2]
			else:
				path = path[0]
		if (shell and path.startswith(SHELL_VAR)) \
		or path.startswith(os.getenv("CHIMERA")):
			return chimera_env
	fixed_env = {}
	if chimera_env is None:
		chimera_env = os.environ
	for e in chimera_env:
		if e in _CHIMERA_SETENV:
			if chimera_env.get(e) == _original_environ.get(e):
				continue
			# Potentially bad -- a chimera startup environment
			# modification has been further modified, don't
			# know how to apply differences, so just use it.
		if e.startswith(_CHIMERA_):
			k = e[8:]
			if k not in fixed_env:
				fixed_env[k] = chimera_env[e]
		else:
			fixed_env[e] = chimera_env[e]
	return fixed_env

def _emulate_python3():
	# Windows only
	import sys, os
	if sys.version_info >= (3, 0):
		return
	try:
		import subprocess3
		sys.modules['_subprocess'] = subprocess3
	except ImportError:
		pass
	try:
		# incorporate Python 3 versions of os.environ, execve, etc.
		import _environ3
	except ImportError:
		# Python 2.7 can't handle unicode values in the environment
		def putenv(key, value):
			if isinstance(value, unicode):
				value = value.encode('mbcs')
			return os._putenv(key, value)
		os._putenv = os.putenv
		os.putenv = putenv
		return
	attrs = [attr for attr in dir(_environ3)
					if not attr.startswith('_')]
	for attr in attrs:
		setattr(os, attr, getattr(_environ3, attr))
	import UserDict
	class _Environ(UserDict.IterableUserDict):
		# like os._Environ, but make key and data unicode
		def __init__(self, environ):
			UserDict.UserDict.__init__(self)
			data = self.data
			for k, v in environ.items():
				data[k.upper()] = v
		def __setitem__(self, key, item):
			k = unicode(key).upper()
			os.putenv(k, unicode(item))
			self.data[k] = item
		def __getitem__(self, key):
			k = unicode(key).upper()
			return self.data[k]
		def __delitem__(self, key):
			k = unicode(key).upper()
			os.putenv(k, u"")
			del self.data[k]
		def clear(self):
			for key in self.data.keys():
				os.putenv(key, u"")
				del self.data[key]
		def pop(self, key, *args):
			k = unicode(key).upper()
			os.putenv(k, u"")
			return self.data.pop(k, *args)
		def has_key(self, key):
			k = unicode(key).upper()
			return k in self.data
		def __contains__(self, key):
			k = unicode(key).upper()
			return k in self.data
		def get(self, key, failobj=None):
			k = unicode(key).upper()
			return self.data.get(k, failobj)
		def update(self, dict=None, **kwargs):
			if dict:
				try:
					keys = dict.keys()
				except AttributeError:
					# List of (key, value)
					for k, v in dict:
						self[k] = v
				else:
					# got keys
					# cannot use items(), since mappings
					# may not have them.
					for k in keys:
						self[k] = dict[k]
			if kwargs:
				self.update(kwargs)
		def copy(self):
			return dict(self)

	os.environ = _Environ(os.environ)
	def unsetenv(key):
		del os.environ[key]
	os.unsetenv = unsetenv

        import __builtin__
        original_execfile = __builtin__.execfile
        def execfile(filename, exec_globals=None, exec_locals=None, original_execfile=original_execfile):
            if isinstance(filename, unicode):
                filename = filename.encode('mbcs')
            if exec_globals is None:
                import inspect
                exec_frame = inspect.currentframe().f_back
                exec_globals = exec_frame.f_globals
                if exec_locals is None:
                    exec_locals = exec_frame.f_locals
            original_execfile(filename, exec_globals, exec_locals)
        __builtin__.execfile = execfile

def _protect_environ():
	import sys, os
	global _original_environ
	_original_environ = os.environ.copy()
	_CHIMERA_SETENV.update((
		'PYTHONPATH', 'PYTHONHOME', 'PYTHONNOUSERSITE',
		'PYTHONIOENCODING', 'TCL_LIBRARY', 'TCLLIBPATH',
	))
	if sys.platform.startswith('linux'):
		_CHIMERA_SETENV.add('LD_LIBRARY_PATH')
	elif sys.platform.startswith('darwin'):
		_CHIMERA_SETENV.update(('DYLD_FALLBACK_LIBRARY_PATH',
				'DYLD_FRAMEWORK_PATH', 'FONTCONFIG_FILE'))
	elif sys.platform.startswith('win'):
		_CHIMERA_SETENV.add('PATH')

	# monkey patch os.execv, etc. to reset environment to what
	# chimera was started with, so that chimera's runtime libraries
	# don't break what's exectuted.  Only the lowest-level routines
	# fix the environment, the others are replaced with ones that
	# use the subprocess module as per the subprocess documentation.
	def execv(path, args):
		fixed_env = _fix_environ(args, os.environ)
		return os._execve(path, args, fixed_env)
	os._execv = os.execv
	os.execv = execv

	def execve(path, args, env):
		if env is None:
			env = os.environ
		fixed_env = _fix_environ(args, env)
		return os._execve(path, args, fixed_env)
	os._execve = os.execve
	os.execve = execve

	def system(cmd):
		import subprocess
		return subprocess.call(cmd, shell=True)
	os._system = os.system
	os.system = system

	def popen(cmd, mode='r', bufsize=-1):
		from subprocess import Popen, PIPE
		shell = isinstance(cmd, basestring)
		if mode.startswith('r'):
			return Popen(cmd, shell=shell, bufsize=bufsize,
					stdout=PIPE, close_fds=True).stdout
		return Popen(cmd, shell=shell, bufsize=bufsize,
					stdin=PIPE, close_fds=True).stdin
	os.popen = popen

	if sys.platform.startswith('win'):
		_emulate_python3()

		import _subprocess
		def CreateProcess(application_name, command_line, process_attributes, thread_attributes, inherit_handles, creation_flags, env_mapping, current_directory, startup_info):
			fixed_env = _fix_environ(application_name, env_mapping)
			return _subprocess._CreateProcess(application_name,
					command_line, process_attributes,
					thread_attributes, inherit_handles,
					creation_flags, fixed_env,
					current_directory, startup_info)
		_subprocess._CreateProcess = _subprocess.CreateProcess
		_subprocess.CreateProcess = CreateProcess

		def spawnv(mode, path, args):
			fixed_env = _fix_environ(path, os.environ)
			return os._spawnve(mode, path, args, fixed_env)
		os._spawnv = os.spawnv
		os.spawnv = spawnv

		def spawnve(mode, path, args, env):
			if env is None:
				env = os.environ
			fixed_env = _fix_environ(path, env)
			return os.spawnve(mode, path, args, fixed_env)
		os._spawnve = os.spawnve
		os.spawnve = spawnve

		def popen2(cmd, mode='t', bufsize=-1):
			from subprocess import Popen, PIPE
			shell = isinstance(cmd, basestring)
			p = Popen(cmd, shell=shell, bufsize=bufsize,
				stdin=PIPE, stdout=PIPE, close_fds=True)
			return (p.stdin, p.stdout)
		os.popen2 = popen2

		def popen3(cmd, mode='t', bufsize=-1):
			from subprocess import Popen, PIPE
			shell = isinstance(cmd, basestring)
			p = Popen(cmd, shell=shell, bufsize=bufsize,
				stdin=PIPE, stdout=PIPE, stderr=PIPE,
				close_fds=True)
			return (p.stdin, p.stdout, p.stderr)
		os.popen3 = popen3

		def popen4(cmd, mode='t', bufsize=-1):
			from subprocess import Popen, PIPE, STDOUT
			shell = isinstance(cmd, basestring)
			p = Popen(cmd, shell=shell, bufsize=bufsize,
				stdin=PIPE, stdout=PIPE, stderr=STDOUT,
				close_fds=True)
			return (p.stdin, p.stdout)
		os.popen4 = popen4

def initialize_ssl_cert_dir():
	"""For Linux, initialize OpenSSL's CA certificates location.

	Makes it so certificates can be verified.
	"""
	import os
	import ssl
	dvp = ssl.get_default_verify_paths()
	# from https://golang.org/src/crypto/x509/root_linux.go
	cert_files = [
		"/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu/Gentoo etc.
		"/etc/pki/tls/certs/ca-bundle.crt",    # Fedora/RHEL 6
		"/etc/ssl/ca-bundle.pem",              # OpenSUSE
		"/etc/pki/tls/cacert.pem",             # OpenELEC
		"/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem", # CentOS/RHEL 7
	]
	for fn in cert_files:
		if os.path.exists(fn):
			putenv(dvp.openssl_cafile_env, fn)
			# putenv(dvp.openssl_capath_env, os.path.dirname(fn))
			return

def initialize_ssl_cert_file(update=False):
	"""For Mac OS X, initialize OpenSSL's CA certificates location.

	Makes it so certificates can be verified.
	"""
	if not update:
		try:
			import certifi
		except ImportError:
			update = True
	if update:
		from pip.__main__ import _main as pip_main
		if pip_main([ "install", "--upgrade", "certifi" ]) != 0:
			from os import stat
			from pwd import getpwuid
			from site import getsitepackages
			uid = stat(getsitepackages()[0]).st_uid
			account = getpwuid(uid).pw_name
			print "Update certificates failed."
			print "Operations requiring SSL protocol will not work."
			print "Please make sure to run this command using the "
			print "\"%s\" account." % account
			return 1
		import certifi
	import ssl
	dvp = ssl.get_default_verify_paths()
	putenv(dvp.openssl_cafile_env, certifi.where())
	return 0

def init(argv, nogui=False, nomultisample=None, stereo='mono', bgopacity=False,
		visual=None, screen=None, root=None, debug=False,
		geometry=None, title=None, eventloop=True, exitonquit=True,
		nostatus=False, preferencesFile=None, fullscreen=False,
		silent=False):
	"""initialize chimera environment

	optional arguments:

	nogui -- if set, don't start GUI.
	visual -- Tk visual, eg 'pseudocolor 12' or 'truecolor'.
	screen -- screen number if different than default.
	root -- root of chimera installation tree.
	debug -- if set, don't redirect standard error.
	preferencesFile -- path to preferences file to use
	"""

	import sys, os, traceback, getopt
	ARGS = [
		"--help",
		"--nogui",
		"-n",
		"--nostatus",
		"--silent",
		"--nomultisample",
		"--fullscreen",
		"-f",
		"--stereo <mode>",
		"--bgopacity",
		"--geometry wxh+x+y",
		"--title title",
		"--start <extension name>",
		"--pypath <directory>",
		"-P <directory>",
		"--send <file>",
		"--preferences <file>",
		"--visual <visual>",
		"--screen <screen>",
		"--script <python file>",
		"--root",
		"--release",
		"--version",
		"--listfiletypes",
		"--opt",
		"--debug",
		"--debug-opengl",
		"--embed",
		"--updatecertificates",
	]
	if sys.platform.startswith("win"):
		ARGS.extend(["--console", "--noconsole"])
	USAGE = '[' + "] [".join(ARGS) + ']'
	# add in default argument values
	ARGS += [
		"--gui",
		"--status",
		"--nosilent",
		"--multisample",
		"--nofullscreen",
		"--nobgopacity",
		"--nodebug",
		"--nodebug-opengl",
		"--noembed",
	]
	# emulate "python -m py_compile module" for aqua
	ARGS += [ "-m pymodule" ]

	try:
		shortopts = ""
		longopts = []
		for a in ARGS:
			if a.startswith("--"):
				i = a.find(' ')
				if i == -1:
					longopts.append(a[2:])
				else:
					longopts.append(a[2:i] + '=')
			elif a.startswith('-'):
				i = a.find(' ')
				if i == -1:
					shortopts += a[1]
				else:
					shortopts += a[1] + ':'
		optlist, args = getopt.getopt(argv[1:], shortopts, longopts)
	except getopt.error, message:
		sys.stderr.write(argv[0] + ": " + str(message) + '\n')
		sys.stderr.write("usage: %s %s\n" % (argv[0], USAGE))
		return 2

	printRelease = False
	printVersion = False
	printRoot = False
	startExtensions = []
	scripts = []
	pathAdditions = []
	listFileTypes = False
	updateCerts = False
	send = None
	debug_opengl = False
	embed = False
	pymodule = ""
	for o in optlist:
		if o[0] == "--send":
			send = o[1]
		elif o[0] == "-m":
			pymodule = o[1]
		elif o[0] in ("-n", "--nogui"):
			nogui = True
		elif o[0] == "--gui":
			nogui = False
		elif o[0] in ("-f", "--fullscreen"):
			fullscreen = True
		elif o[0] == "--nofullscreen":
			fullscreen = False
		elif o[0] in "--geometry":
			geometry = o[1]
		elif o[0] in "--title":
			title = o[1]
		elif o[0] == "--nomultisample":
			nomultisample = True
		elif o[0] == "--multisample":
			nomultisample = False
		elif o[0] == "--nostatus":
			nostatus = True
		elif o[0] == "--status":
			nostatus = False
		elif o[0] == "--silent":
			nostatus = True
			silent = True
		elif o[0] == "--nosilent":
			nostatus = False
			silent = False
		elif o[0] == "--stereo":
			stereo = o[1]
		elif o[0] == "--bgopacity":
			bgopacity = True
		elif o[0] == "--nobgopacity":
			bgopacity = False
		elif o[0] == "--debug":
			debug = True
		elif o[0] == "--nodebug":
			debug = False
		elif o[0] == "--debug-opengl":
			debug_opengl = True
		elif o[0] == "--nodebug-opengl":
			debug_opengl = False
		elif o[0] == "--embed":
			embed = True
		elif o[0] == "--noembed":
			embed = False
		elif o[0] == "--start":
			startExtensions.append(o[1])
		elif o[0] == "--script":
			scripts.append(o[1])
		elif o[0] in ("-P", "--pypath"):
			pathAdditions.append(o[1])
		elif o[0] in "--visual":
			visual = o[1]
		elif o[0] in "--screen":
			screen = o[1]
		# query options:
		elif o[0] == "--root":
			nogui = True
			printRoot = True
		elif o[0] == "--release":
			printRelease = True
		elif o[0] == "--version":
			printVersion = True
		elif o[0] == "--listfiletypes":
			nogui = True
			listFileTypes = True
		elif o[0] == "--preferences":
			preferencesFile = o[1]
		elif o[0] == "--help":
			sys.stderr.write("usage: %s %s\n" % (argv[0], USAGE))
			return 0
		elif o[0] == "--updatecertificates":
			nogui = True
			updateCerts = True
		# --opt (run python -O) is caught by startup script
		# --console and --noconsole are for the Window startup code

	if pymodule:
		assert pymodule == 'py_compile'
		sys.argv = [pymodule] + args
		main = __import__(pymodule)
		main.main()
		raise SystemExit

	# Figure out which chimera installation tree to use, and tell
	# python where the chimera system python modules are found.

	if not root:
		try:
			root = _findRoot()
		except RuntimeError, e:
			print >> sys.stderr, "Error starting chimera:", e
			raise SystemExit, 1
		except KeyError:
			pass
	_protect_environ()

	# Setup additional environment variables:
	if sys.platform != 'win32':
		if "HOME" not in os.environ:
			import pwd
			putenv("HOME", pwd.getpwuid(os.getuid()).pw_dir)
	else:
		try:
			# use backported Python3 unicode winreg
			import winreg
			sys.modules['_winreg'] = winreg
		except ImportError:
			pass
		# Try to find a "HOME" directory on Windows for .files.
		if "HOME" not in os.environ:
			if "APPDATA" in os.environ:
				putenv("HOME", os.environ["APPDATA"])
			else:
				raise RuntimeError("Windows 98 not supported")
		# On Windows, we need to remove the bin directory from
		# the Python path (because "import zlib" might get the
		# dll instead of the pyd).
		rpath = os.path.realpath(os.path.join(root, "bin")).lower()
		curdir = os.path.realpath(os.getcwd()).lower()
		for p in sys.path[:]:
			try:
				if p == "":
					r = curdir
				else:
					# cleanup Windows filenames
					r = os.path.realpath(p).lower()
					if r[-1] == '\\':
						r = r[0:-1]
					r = r.replace('progra~1', 'program files')
				if r == rpath:
					sys.path.remove(p)
			except OSError:
				pass
		# PATH environment variable is already set up
		# properly by the launcher so we don't touch it
		del rpath, curdir
	if not os.path.exists(os.environ["HOME"]):
		print >> sys.stderr, "warning: home directory does not exist:", os.environ["HOME"]

	if sys.platform != 'win32':
		# prepend machine-dependent directory for shared library modules
		import site
		savePath = sys.path
		sys.path = []
		site.addsitedir(os.path.join(root, "lib"))
		sys.path.extend(savePath)
		del savePath

	# In debug mode '.' is at front of path, otherwise place
	# it at the end. Remove the other occurances first.
	while '' in sys.path > 0:
		sys.path.remove('')
	while '.' in sys.path > 0:
		sys.path.remove('.')
	if debug:
		sys.path.insert(0, os.getcwd())	# put it back
	else:
		sys.path.append(os.getcwd())

	# prepend 'pypath' directories
	pathAdditions.reverse()
	for pa in pathAdditions:
		sys.path.insert(0, pa)

	if send:
		import send_to_chimera
		path = os.path.abspath(send)
		if not os.path.exists(path):
			path = send
		msg = send_to_chimera.send(path)
		if msg == 'SENT':
			# successfully sent send argument to a running chimera
			raise SystemExit, 0
		else:
			print >> sys.stderr, msg
			raise SystemExit, 1

	if printRelease and printVersion:
		from chimera.version import releaseVersion
		print releaseVersion()
		raise SystemExit, 0
	if printRelease:
		from chimera.version import release
		print release
		raise SystemExit, 0
	if printVersion:
		from chimera.version import version
		print 'chimera', version
		raise SystemExit, 0
	if printRoot:
		print root
		raise SystemExit, 0

	if sys.platform in ['irix646', 'irix6-n32']:
		# make C++ shared libraries work when dlopen'd
		import dl
		sys.setdlopenflags(sys.getdlopenflags() | dl.RTLD_GLOBAL)

	if sys.platform.startswith('linux'):
		initialize_ssl_cert_dir()
	elif sys.platform.startswith('darwin'):
		success = initialize_ssl_cert_file(updateCerts)
		if updateCerts:
			raise SystemExit, success

	# now startup chimera
	import chimera
	if chimera.opengl_platform() == 'OSMESA':
		# we only want the graphics, not the gui
		nogui = True
	chimera.visual = visual
	chimera.screen = screen
	chimera.debug = debug
	chimera.nogui = nogui
	if not nomultisample is None:
		chimera.multisample = not nomultisample
	chimera.nostatus = nostatus
	chimera.silent = silent
	try:
		chimera.stereo = chimera.StereoKwMap[stereo]
	except KeyError:
		print >> sys.stderr, "stereo option takes same arguments as stereo command"
		raise SystemExit, 1
	chimera.bgopacity = bgopacity
	chimera.geometry = geometry
	chimera.preferencesFile = preferencesFile
	if title:
		chimera.title = title
	chimera.fullscreen = fullscreen
	from chimera import replyobj

	# Change default HTTP User-Agent to be UCSF-Chimera
	import urllib
	from chimera.version import release
	urllib.URLopener.version = "UCSF-Chimera/%s" % release

	if nogui:
		chimera.initializeGraphics()
		chimera._postGraphics = True
	else:
		from chimera import splash
		splash.create()

		from chimera import tkgui
		tkgui.initializeGUI(exitonquit, debug_opengl, embed)
		chimera.viewer = tkgui.app.viewer
	chimera.registerOSLTests()
	if not nogui:
		replyobj.status('initializing extensions')
	from chimera import extension
	extension.setup()

	if listFileTypes:
		catTypes = chimera.fileInfo.categorizedTypes()
		categories = sorted(list(catTypes.keys()))
		print "category:"
		print "\tfile type: prefix: suffixes"
		print
		for c in categories:
			types = catTypes[c]
			types.sort()
			print '%s:' % c
			for t in types:
				print "\t%s: %s: %s" % (t,
					', '.join(chimera.fileInfo.prefixes(t)),
					', '.join(chimera.fileInfo.extensions(t)))
		raise SystemExit, 0

	if not nogui:
		extraArgs = tkgui.finalizeGUI()
		args.extend(extraArgs)
	extension.startup(startExtensions)
	for extName in startExtensions:
		replyobj.error(
			"Starting extension '%s' failed\n" % extName)

	from chimera import registration
	registration.checkRegistration()

	if not nogui:
		tkgui.periodicCheckForNewerChimera()
		tkgui.setInitialWindowSize()

	for a in args:
		try:
			try:
				chimera.openModels.open(a, prefixableType=1)
			except IOError, value:
				# so that we don't get bug reports when
				# people mistype file names
				raise chimera.UserError(value)
		except SystemExit, value:
			return value
		except:
			replyobj.reportException(
					"Error while processing %s" % a)
	if scripts:
		# execute optional script(s)
		from Midas import midas_text
		for script in scripts:
			try:
				midas_text.doRunScript("runscript", script)
			except SystemExit, value:
				return value
			except:
				replyobj.reportException(
					"Error while processing '%s'" % script)
	if nogui:
		from chimera import triggers, APPQUIT, fileInfo
		for arg in args:
			if fileInfo.category(fileInfo.processName(arg)[0]) == fileInfo.SCRIPT:
				scriptArg = True
				break
		else:
			scriptArg = False
		if not (scripts or scriptArg):
			extension.startup(["ReadStdin"])
		triggers.activateTrigger(APPQUIT, None)
		return 0
	if eventloop:
		# run user interface
		try:
			try:
				tkgui.eventLoop()
			except KeyboardInterrupt:
				pass
		finally:
			pass	# TODO: do exit procedures (e.g., grail stuff)
	else:
		# start monitoring for data changes
		from chimera import update
		update.startFrameUpdate(tkgui.app)
	return 0
