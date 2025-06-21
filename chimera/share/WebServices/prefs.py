# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

from chimera import preferences
prefs = preferences.addCategory("WebServices", preferences.HiddenCategory,
								optDict={})
# prefs keys are extension names and values are 2-tuples of
#   (selectedType, typeValueDictionary)
# where "selectedType" is the preferred server type (eg "opal" or "local")
# and "typeValueDictionary" is a dictionary whose keys are the various
# backends and whose values are the backend parameters.

# Backend parameters are 2-tuples: (service, server).
# (This design is historical for backwards compatibility
# with appWebService's and opal_client's requirement for 
# the calling parameter being split into serviceName=service
# and url=server.)
# For Opal, the service name is the opal service name and
# server is the prefix URL; for local, the service
# name is the path to the executable and server is always None.

# The following functions are useful for converting between different
# forms for displaying, calling appWebService, etc.

def getServicePrefs(extensionName, backendType):
	"""Return (service, server).

	"extensionName" is the name of the extension
	"backendType" is type of backend ("opal" or "local")
	"""
	try:
		service, server = prefs[extensionName][backendType]
	except KeyError:
		return (None, None)
	try:
		getFunc = _registry[backendType]["get"]
	except KeyError:
		return service, server
	else:
		return getFunc(service, server)

def setServicePrefs(extensionName, backendType, service, server):
	try:
		d = prefs[extensionName]
	except KeyError:
		d = dict()
	try:
		setFunc = _registry[backendType]["set"]
	except KeyError:
		parameters = (service, server)
	else:
		parameters = getFunc(service, server)
	d[backendType] = parameters
	prefs[extensionName] = d

def getSelectedPrefs(extensionName):
	try:
		return prefs[extensionName]["selected"]
	except KeyError:
		return None

def setSelectedPrefs(extensionName, backendType):
	try:
		d = prefs[extensionName]
	except KeyError:
		d = dict()
	d["selected"] = backendType
	prefs[extensionName] = d

def service2display(backendType, service, server):
	try:
		displayFunc = _registry[backendType]["display"]
	except KeyError:
		return "%s - %s" % (service, server)
	else:
		return displayFunc(service, server)

def display2service(backendType, s):
	try:
		parseFunc = _registry[backendType]["parse"]
	except KeyError:
		return tuple(s.split(" - ", 1))
	else:
		return parseFunc(s)

_registry = dict()

def register(backendType, valueType, value):
	d = _registry.setdefault(backendType, dict())
	d[valueType] = value

def knownBackend(backend):
	return backend in _registry

#
# Opal support routines
#
def _opalParse(url):
	"""Returns (service, server) for given URL.

	"service" is the last component of the URL.
	"server" is everything before.  If "server" turns out
	to be the same as the default, None is used instead.
	"""
	server, service = url.rsplit('/', 1)
	if not server.endswith('/'):
		server += '/'
	from opal_client import OpalService
	if server == OpalService.DefaultOpalURL:
		server = None
	return (service, server)

def _opalDisplay(service, server):
	"""Returns full URL to opal service
	"""
	if server is None:
		from opal_client import OpalService
		server = OpalService.DefaultOpalURL
	return server + service

register("opal", "parse", _opalParse)
register("opal", "display", _opalDisplay)

#
# Local executable support routines
#
def _localParse(path):
	"""Returns (service, server) for given path.
	"""
	return (path, None)

def _localDisplay(service, server):
	return service

register("local", "parse", _localParse)
register("local", "display", _localDisplay)
