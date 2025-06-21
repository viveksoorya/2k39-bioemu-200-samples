# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

class RunRealignmentWS:
	def __init__(self, startCB, cancelCB, finishCB, mav=None, seqs=None,
			serviceName=None, inOutFlags=None, options=None, sessionData=None,
			reordersSequences=False):
		"""
		Prepare input and call Clustal Omega web service

		startCB		: called once web service started with service instance
						as first arg and value of 'mav' as second arg;
						can be None
		cancelCB	: called if web service cancelled with service instance
						as first arg and value of 'mav' as second arg;;
						can be None
		finishCB	: called once web service finished with service instance
						as first arg, the value of 'mav' as second arg and
						the third arg determined by value of 'mav', below;
						can be None
		mav			: determines what the third arg given to the finishCB
						will be:  if False, return a list of Sequences; if
						a string, create a new MAViewer instance (whose
						title is the string) containing the alignment and
						return the instance; if an MAViewer instance, use
						the realign() method of the instance to update the
						alignment and return the instance
		# the following 4 should be None if sessionData is not None
		seqs		: a list of Sequences,
		serviceName	: name of the Opal2 web service
		inOutFlags	: 2-tuple of the flags used by the service to specify
						the input and output files (e.g. ("-i", "-o") for
						Clustal Omega
		options		: option string to hand off to the web service
		sessionData	: if restoring from session, data needed to relink to
						web service; obtained from the sessionData()
						method of the web service instance
		"""
		self.cancelCB = cancelCB
		self.finishCB = finishCB
		self.mav = mav
		self.reordersSequences = reordersSequences

		from chimera import replyobj

		realignKw = { 'cleanupCB': self._cancelOrDone, "backend": "cx" }
		if sessionData:
			realignKw['sessionData'] = sessionData
		else:
			from formatters.saveFASTA import save
			from OpenSave import osTemporaryFile
			inFasta = osTemporaryFile(suffix=".fa")
			f = open(inFasta, "w")
			save(f, None, seqs, None)
			f.close()
			finalOptions = "%s input.fa %s output.fa" % inOutFlags
			if options:
				finalOptions += " " + options
			realignKw['params'] = (serviceName, "Alignment of %d sequences"
				% len(seqs), {'input.fa': inFasta}, finalOptions)

		from WebServices import appWebService
		self.ws = appWebService.AppWebService(self._wsFinish, **realignKw)
		self.ws.mavReordersSequences = reordersSequences
		if startCB:
			startCB(self.ws, mav)

	def _cancelOrDone(self, backend, completed, success):
		if self.cancelCB and not completed and not success:
			self.cancelCB(self.ws, self.mav)

	def _wsFinish(self, opal, fileMap):
		from OpenSave import osOpen
		from parsers import readFASTA
		seqs = readFASTA.parse(osOpen(fileMap['output.fa'], 'r'))[0]
		if self.mav is False:
			if self.finishCB:
				self.finishCB(self.ws, self.mav, seqs)
			return
		from MAViewer import MAViewer
		if isinstance(self.mav, MAViewer):
			if self.reordersSequences:
				# put result in same order as original sequences
				origNames = set([s.name for s in self.mav.seqs])
				newNames = set([s.name for s in seqs])
				if origNames == newNames:
					# names match, so correct reordering is possible
					if len(newNames) == len(seqs):
						# names are unique, so use simpler sort func
						order = {}
						for i, s in enumerate(self.mav.seqs):
							order[s.name] = i
						sortFunc = lambda s1, s2, o=order: cmp(o[s1.name], o[s2.name])
					else:
						order = {}
						for i, s in enumerate(self.mav.seqs):
							order[(s.name, s.ungapped())] = i
						sortFunc = lambda s1, s2, o=order: cmp(o[(s1.name, s1.ungapped())],
							o[(s2.name, s2.ungapped())])
					seqs.sort(sortFunc)
				else:
					raise ValueError("Returned sequence names don't match original sequence names!")
			self.mav.realign(seqs)
			if self.finishCB:
				self.finishCB(self.ws, self.mav, self.mav)
			return
		mav = MAViewer(seqs, title=self.mav)
		if self.finishCB:
			self.finishCB(self.ws, self.mav, mav)

from prefs import prefs, REALIGN_DEST, REALIGN_DEFAULT_SERVICE
from chimera.tkoptions import SymbolicEnumOption
class _DestinationViewerOption(SymbolicEnumOption):
	name = "Open realigned sequences in"
	values = ["current", "new"]
	labels = ["the current alignment window", "a new alignment window"]
	default = prefs[REALIGN_DEST]

	def get(self, setPref=True):
		val = SymbolicEnumOption.get(self)
		if setPref:
			prefs[REALIGN_DEST] = val
		return val

class DestinationOptions:
	def __init__(self, master, rowCounter):
		self.options = []
		from chimera.tkoptions import StringOption
		self.viewerOpt = _DestinationViewerOption(master, rowCounter.next(),
			None, None, self._viewerChangedCB)
		self.options.append(self.viewerOpt)
		self.titleOpt = StringOption(master, rowCounter.next(), "Title"
			" for new alignment window", "Realigned Sequences", None)
		if self.viewerOpt.get() == "current":
			self.titleOpt.forget()
		self.options.append(self.titleOpt)

	def get(self, setPrefs=True):
		viewer = self.viewerOpt.get(setPref=setPrefs)
		if viewer == "current":
			return True
		return self.titleOpt.get()

	def _viewerChangedCB(self, opt):
		if opt.get() == "current":
			self.titleOpt.forget()
		else:
			self.titleOpt.manage()

class ServiceOptions:
	registeredServices = {}
	defaultDefaultService = None

	@classmethod
	def registerService(cls, options):
		"""name' is the human-readble name, not the web service name"""
		if cls.defaultDefaultService is None:
			cls.defaultDefaultService = options.name
		cls.registeredServices[options.name] = options

	@classmethod
	def names(cls):
		names = cls.registeredServices.keys()
		names.sort()
		return names

	def __init__(self, master, rowCounter):
		from chimera.tkoptions import EnumOption
		serviceNames = self.registeredServices.keys()
		serviceNames.sort()
		class Services(EnumOption):
			values = serviceNames

		defaultService = prefs[REALIGN_DEFAULT_SERVICE]
		if defaultService is None:
			defaultService = self.defaultDefaultService
		self.serviceOpt = Services(master, rowCounter.next(), "Alignment"
			" program", defaultService, self._serviceChanged)

		self.options = {}
		for name, options in self.registeredServices.items():
			self.options[name] = options(master, rowCounter)
			if name != defaultService:
				self.options[name].grid_remove()
		self._shownService = defaultService

	def _serviceChanged(self, opt):
		self.options[self._shownService].grid_remove()
		self._shownService = opt.get()
		self.options[self._shownService].grid()

	def get(self, setPrefs=False):
		service = self.serviceOpt.get()
		prefs[REALIGN_DEFAULT_SERVICE] = service

		serviceOptions = self.options[service]
		return serviceOptions.get(setPrefs=setPrefs) + (getattr(serviceOptions,
			'reordersSequences', False),)

# get the services we know about registered
import ClustalOmega, Muscle
