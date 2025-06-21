import chimera
from chimera import replyobj

RegistrationFile = 'registration'
UsageFile = 'preregistration'

# FreeUsageDays is the numbers of days that an user can start
# Chimera without registration.
FreeUsageDays = 15

def checkRegistration(nag=1):
	"Check registration status."

	pf = chimera.pathFinder()
	filenames = pf.allExistingFiles('', RegistrationFile)
	if not filenames:
		if nag:
			return _checkUsage(pf)
		else:
			return None
	for filename in filenames:
		try:
			f = open(filename)
		except IOError, e:
			replyobj.warning("Cannot open file %s: %s"
						% (filename, str(e)))
			continue
		text = f.read()
		f.close()
		lines = text.splitlines()
		param = {}
		for line in lines:
			try:
				key, value = [ s.strip()
						for s in line.split(':', 1) ]
			except ValueError:
				pass
			else:
				param[key] = value
		if not param.has_key('User') or not param.has_key('Email'):
			if nag:
				replyobj.warning('Registration file "%s" '
						'is invalid.\n' % filename)
			continue
		from time import strptime, mktime, time
		try:
			expires = mktime(strptime(param['Expires']))
		except KeyError:
			t = param.get("Signed", "Wed Jan 25 00:00:00 2010")
			expires = mktime(strptime(t)) + 365 * 24 * 60 * 60
		if time() > expires:
			if nag:
				replyobj.warning('Registration file "%s" '
					'has expired.\n' % filename)
			continue
		# Other parameter-dependent processing can go here
		return param

	if nag:
		return _checkUsage(pf)
	else:
		return None

def _checkUsage(pf):
	"Check whether it's time to nag."

	from time import localtime, time
	t = localtime(time())
	thisUse = '%d-%d-%d' % (t[0], t[1], t[2])
	for filename in pf.allExistingFiles('', UsageFile):
		try:
			f = open(filename, 'rU')
		except IOError:
			continue
		param = {}
		while 1:
			line = f.readline()
			if not line:
				break
			try:
				key, value = [ s.strip()
						for s in line.split(':', 1) ]
			except ValueError:
				pass
			else:
				param[key] = value
		f.close()
		if not param.has_key('time') or not param.has_key('count'):
			continue
		lastUse = param['time']
		usageCount = int(param['count'])
		if thisUse != lastUse:
			usageCount = usageCount + 1
			_createUsage(pf, thisUse, usageCount, prefer=filename)
		if usageCount < FreeUsageDays:
			return None

		from baseDialog import ModelessDialog
		import Tkinter
		class RegisterDialog(ModelessDialog):
			title = "Registration Reminder"
			buttons = ("Register", "Later")

			def __init__(self):
				ModelessDialog.__init__(self, oneshot=1)

			def fillInUI(self, parent):
				l = Tkinter.Label(parent, text=
				"You have used Chimera for %d days.\n"
				"You can either register now by\n"
				"clicking the 'Register' button below,\n"
				"below or by selecting 'Registration...'\n"
				"from the Help menu at any time.\n"
				"\n"
				"Registration is free.  By providing the\n"
				"information requested you will be helping\n"
				"us document the impact this software is\n"
				"having in the scientific community. The\n"
				"information you supply will only be used\n"
				"for reporting summary statistics to NIH."
						               % usageCount)
				l.grid(row=0, column=0, sticky="nsew")
				parent.rowconfigure(0,weight=1)
				parent.columnconfigure(0, weight=1)

			def Register(self):
				from chimera import dialogs, register
				dialogs.display(register.RegDialog.name)
				self.Cancel()
			def Later(self):
				self.Cancel()
		if chimera.nogui:
			import sys
			sys.stderr.write(
	"You have used an unregistered copy of Chimera for %d days.\n"
	"You can either register now by visiting:\n"
	"   http://www.cgl.ucsf.edu/cgi-bin/chimera_registration.py\n"
	"or by choosing 'Registration...' from the 'Help' menu next\n"
	"time you start Chimera with the gui enabled.\n"
	"\n"
	"Registration is free.  By providing the information requested\n"
	"you will be helping us document the impact this software is\n"
	"having in the scientific community. The information you supply\n"
	"will only be used for reporting summary statistics to NIH.\n"
					 % usageCount)
		else:
			RegisterDialog()			     

		return None
	_createUsage(pf, thisUse, 1)
	return None

def _openFile(pf, filename):
	"Open a (pre)registration file for writing."

	# Try creating .chimera in the home directory
	try:
		import os
		os.makedirs(pf.pathList('', '', 0, 0, 1)[0])
	except (IndexError, OSError):
		pass

	filenames = pf.pathList('', filename, 0, 1, 1)
	filenames.reverse()
	for path in filenames:
		try:
			f = open(path, 'w')
		except IOError:
			continue
		return f, path
	return None, None

def _createUsage(pf, thisUse, usageCount, prefer=None):
	"Create a new preregistration usage file."

	f = None
	if prefer:
		try:
			f = open(prefer, 'w')
		except IOError:
			f = None
	if not f:
		f, path = _openFile(pf, UsageFile)
	if f:
		f.write('time: %s\n' % thisUse)
		f.write('count: %d\n' % usageCount)
		f.close()

def install(msg):
	pf = chimera.pathFinder()
	f, path = _openFile(pf, RegistrationFile)
	if not f:
		errormsg = 'Cannot find a writable file for registration message.'
		#print errormsg
		return (0,errormsg)
	f.write(msg)
	f.close()
	#print 'Registration message installed in "%s".' % path
	return (1,'Registration message installed in "%s".' % path)

#def register(user, organization, email):
#	import httplib
#	conn = httplib.HTTP('www.cgl.ucsf.edu', 16160)
#	conn.putrequest('POST', '/cgi-bin/chimera_registration.py')
#	dataList = [ combine('user', user), ]
#	if organization:
#		dataList.append(combine('organization', organization))
#	if email:
#		dataList.append(combine('email', email))
#	request = '&'.join(dataList)
#	conn.putheader('Content-Type', 'application/x-www-form-urlencoded')
#	conn.putheader('Content-Length', str(len(request)))
#	conn.endheaders()
#	conn.send(request)
#	code, msg, headers = conn.getreply()
#	if code != 200:
#		raise IOError, msg
#	f = conn.getfile()
#	reply = f.read()
#	f.close()
#	print reply
#	
#def combine(key, value):
#	import urllib
#	return '%s=%s' % (key, urllib.quote_plus(value))	
