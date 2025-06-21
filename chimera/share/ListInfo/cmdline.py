# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

def process(cmdName, args):
	if cmdName == "list":
		doList(args)
		return
	from Midas.midas_text import doExtensionFunc
	try:
		func, kwargs = _cmdTable[cmdName]
	except KeyError:
		# We only get here if the command was registered
		# in ChimeraExtension.py but is not in our command table.
		# Assume that registration is correct and that we
		# just haven't implemented the function yet.
		import chimera
		raise chimera.UserError("%s: unimplemented command" % cmdName)
	doExtensionFunc(func, args, **kwargs)

AveragePrefix = "average."

def averageAttrString(obj, attr):
	# Assume that the attribute holds a numeric value
	total = 0.0
	count = 0
	for o in obj.oslChildren():
		try:
			total += getattr(o, attr)
			count += 1
		except (AttributeError, TypeError, ValueError):
			pass
		except:
			import traceback
			traceback.print_exc()
	if count == 0:
		raise AttributeError("no attribute named \"%s\"" % attr)
	return "%.3f" % (total / count)

def attrString(obj, attr):
	s = getattr(obj, attr)
	import chimera
	if isinstance(s, chimera.Color):
		r, g, b, a = s.rgba()
		if s.isTranslucent():
			return "%.3f,%.3f,%.3f,%.3f" % (r, g, b, a)
		else:
			return "%.3f,%.3f,%.3f" % (r, g, b)
	v = str(s)
	l = [ '"' ]
	needQuotes = False
	for c in v:
		if c in '"\\':
			l.append('\\')
		elif c in ' \t':
			needQuotes = True
		l.append(c)
	if needQuotes:
		l.append('"')
		return ''.join(l)
	else:
		return v

def getAttrFunc(attr):
	if attr.startswith(AveragePrefix):
		return attr[len(AveragePrefix):], averageAttrString
	else:
		return attr, attrString

def listm(models=None, type="any", attribute="name"):
	import chimera
	if models is None:
		models = chimera.openModels.list()
	wantedType = type.lower()
	keep = []
	for m in models:
		molType = m.__class__.__name__
		if wantedType != "any" and wantedType != molType.lower():
			continue
		keep.append(m)
	_reportModels(keep, attribute)

def _reportModels(models, attribute):
	from chimera import replyobj
	attribute, attrGet = getAttrFunc(attribute)
	for m in models:
		try:
			attrValue = attrGet(m, attribute)
		except AttributeError:
			continue
		molType = m.__class__.__name__
		info = "model id %s type %s %s %s\n" % (m.oslIdent(), molType,
							attribute, attrValue)
		replyobj.info(info)

def listc(molecules=None, attribute="chain"):
	import chimera
	if molecules is None:
		molecules = chimera.openModels.list(modelTypes=[chimera.Molecule])
	chains = []
	for m in molecules:
		chains += m.sequences()
	_reportChains(chains, attribute)

def _reportChains(chains, attribute):
	from chimera import replyobj
	attribute, attrGet = getAttrFunc(attribute)
	for seq in chains:
		try:
			attrValue = attrGet(seq, attribute)
		except AttributeError:
			continue
		info = "chain id %s %s %s\n" % (_seqIdent(seq),
							attribute, attrValue)
		replyobj.info(info)

def _seqIdent(seq):
	return "%s:.%s" % (seq.molecule.oslIdent(), seq.chain)

def listp(molecules=None):
	import chimera
	if molecules is None:
		molecules = chimera.openModels.list(modelTypes=[chimera.Molecule])
	from ModelPanel import getPhysicalChains
	for m in molecules:
		chains = getPhysicalChains(m)
		_reportPhysicalChains(chains)

def _reportPhysicalChains(chains):
	from chimera import replyobj
	# chains[0] is reserved for 1-residue "chains"
	for pc in chains[1:]:
		lowRes = pc[0]
		highRes = pc[0]
		for r in pc:
			if r.id.position > highRes.id.position:
				highRes = r
			elif r.id.position < lowRes.id.position:
				lowRes = r
		replyobj.info("physical chain %s %s\n" % (lowRes.oslIdent(),
							highRes.oslIdent()))

def listr(residues=None, molecules=None, attribute="type"):
	# Directly output because some "residues" may be None
	# and cannot be reported the same way as "real" residues
	attribute, attrGet = getAttrFunc(attribute)
	def getAAType(r, v):
		if r is None:
			return protein1to3.get(v, v)
		else:
			return getattr(r, attribute, v)
	def getType(r, v):
		if r is None:
			return v
		else:
			return getattr(r, attribute, v)
	def getAttr(r, v):
		if r is None:
			raise AttributeError(attribute)
		else:
			return attrGet(r, attribute)
	def getIdent(r, seq):
		if r:
			return r.oslIdent()
		else:
			return _seqIdent(seq)
	from chimera.resCode import protein1to3
	from chimera import replyobj, openModels, Molecule
	fmt = "residue id %%s %s %%s\n" % attribute
	ifmt = "residue id %%s %s %%s index %%d\n" % attribute
	if residues is not None:
		if attribute != "type":
			getValue = getAttr
		else:
			getValue = getType
		for r in residues:
			try:
				v = getValue(r, None)
			except AttributeError:
				continue
			try:
				s = r.molecule.sequence(r.id.chainId)
				i = s.residues.index(r)
				info = ifmt % (getIdent(r, None), v, i + 1)
			except (KeyError, ValueError, AssertionError):
				info = fmt % (getIdent(r, None), v)
			replyobj.info(info)
	else:
		if molecules is None:
			molecules = openModels.list(modelTypes=[Molecule])
		for m in molecules:
			used = set()
			for seq in m.sequences():
				if attribute != "type":
					getValue = getAttr
				elif seq.hasProtein():
					getValue = getAAType
				else:
					getValue = getType
				for i in range(len(seq)):
					r = seq.residues[i]
					if r:
						used.add(r)
					try:
						v = getValue(r, seq[i])
					except AttributeError:
						continue
					info = ifmt % (getIdent(r, seq),
								v, i + 1)
					replyobj.info(info)
			for r in m.residues:
				if r not in used:
					try:
						v = getValue(r, seq[i])
					except AttributeError:
						continue
					info = fmt % (getIdent(r, seq), v)
					replyobj.info(info)

def _reportResidues(residues, attribute):
	# No longer used by listr but still used by lists
	from chimera import replyobj
	attribute, attrGet = getAttrFunc(attribute)
	for r in residues:
		try:
			attrValue = attrGet(r, attribute)
		except AttributeError:
			continue
		info = "residue id %s %s %s\n" % (r.oslIdent(),
							attribute, attrValue)
		replyobj.info(info)

def lista(atoms=None, attribute="idatmType"):
	import chimera
	from chimera import replyobj
	if atoms is None:
		atoms = []
		for m in chimera.openModels.list(modelTypes=[chimera.Molecule]):
			atoms += m.atoms
	_reportAtoms(atoms, attribute)

def _reportAtoms(atoms, attribute):
	from chimera import replyobj
	attribute, attrGet = getAttrFunc(attribute)
	for a in atoms:
		try:
			attrValue = attrGet(a, attribute)
		except AttributeError:
			continue
		info = "atom id %s" % a.oslIdent()
		info += " %s %s" % (attribute, attrValue)
		info += '\n'
		replyobj.info(info)

def lists(level="atom", mode="any", attribute=None):
	import chimera
	from chimera import replyobj, selection
	mode = findBestMatch(mode, ["any", "all"])
	level = findBestMatch(level, ["atom", "residue", "chain", "molecule"])
	if level == "atom":
		if attribute is None:
			attribute = "idatmType"
		_reportAtoms(selection.currentAtoms(), attribute)
	elif level == "residue":
		if mode == "any":
			residues = selection.currentResidues()
		else:
			rMap = {}
			for a in selection.currentAtoms():
				l = rMap.setdefault(a.residue, [])
				l.append(a)
			residues = []
			for r, aList in rMap.iteritems():
				if len(r.atoms) == len(aList):
					residues.append(r)
		if attribute is None:
			attribute = "type"
		_reportResidues(residues, attribute)
	elif level == "chain":
		if mode == "any":
			chains = selection.currentChains()
		else:
			rcMap = {}
			cached = set([])
			cMap = {}
			for r in selection.currentResidues():
				if r.molecule not in cached:
					cached.add(r.molecule)
					for seq in r.molecule.sequences():
						for res in seq.residues:
							rcMap[res] = seq
				try:
					seq = rcMap[r]
				except KeyError:
					pass
				else:
					l = cMap.setdefault(seq, [])
					l.append(r)
			chains = []
			for seq, rList in cMap.iteritems():
				if len(seq) == len(rList):
					chains.append(seq)
		if attribute is None:
			attribute = "chain"
		_reportChains(chains, attribute)
	elif level == "molecule":
		if mode == "any":
			molecules = selection.currentMolecules()
		else:
			mMap = {}
			for a in selection.currentAtoms():
				l = mMap.setdefault(a.molecule, [])
				l.append(a)
			molecules = []
			for m, aList in mMap.iteritems():
				if len(m.atoms) == len(aList):
					molecules.append(m)
		if attribute is None:
			attribute = "name"
		_reportModels(molecules, attribute)
	else:
		raise chimera.UserError("\"%s\": unknown listselection level"
					% level)

class AlertData:

	def __init__(self, prefix=None, url=None):
		self.prefix = prefix
		self.url = url

addModelHandler = None
removeModelHandler = None
def _alertModel(trigger, adata, molecules):
	from chimera import replyobj
	msg = ''.join([ "%smodel %s\n" % (adata.prefix, m.oslIdent())
							for m in molecules ])
	if adata.url is not None:
		from chimera import threadq
		threadq.runThread(_sendRESTrequest, adata.url, msg)
	else:
		import sys
		r = replyobj.pushReply(None)
		sys.stdout.write(msg)
		sys.stdout.flush()
		replyobj.popReply(r)

selectionHandler = None
def _alertSelection(trigger, adata, curSel):
	from chimera import replyobj
	msg = "%s: selection changed\n" % adata.prefix
	if adata.url is not None:
		from chimera import threadq
		threadq.runThread(_sendRESTrequest, adata.url, msg)
	else:
		r = replyobj.pushReply(None)
		import sys
		sys.stdout.write(msg)
		sys.stdout.flush()
		replyobj.popReply(r)

def _sendRESTrequest(q, url, msg):
	import urllib
	data = urllib.urlencode([("chimeraNotification", msg)])
	import urllib2
	try:
		# Use GET instead of POST for Cytoscape
		getRequest = "%s?%s"%(url,data)
		f = urllib2.urlopen(getRequest, None, 30)
		# Wait for operation to complete
		if f is not None:
			reply = f.read()
	except urllib2.URLError:
		pass
	q.put(q)

def listen(mode, what, prefix=None, url=None):
	from chimera import replyobj
	mode = findBestMatch(mode, ["start", "stop"])
	what = findBestMatch(what, ["models", "selection"])
	if what == "models":
		from chimera import openModels
		global addModelHandler, removeModelHandler
		if mode == "start":
			if addModelHandler is not None:
				msg = "already listening for models\n"
			else:
				if prefix is None:
					prefix = "ModelChanged"
				addPrefix = "%s: add " % prefix
				adata = AlertData(prefix=addPrefix, url=url)
				addModelHandler = openModels.addAddHandler(
							_alertModel, adata)
				removePrefix = "%s: remove " % prefix
				adata = AlertData(prefix=removePrefix, url=url)
				removeModelHandler = openModels.addRemoveHandler(
							_alertModel, adata)
				msg = "listening for models\n"
		else:
			if addModelHandler is None:
				msg = "not listening for models\n"
			else:
				openModels.deleteAddHandler(addModelHandler)
				addModelHandler = None
				openModels.deleteRemoveHandler(removeModelHandler)
				removeModelHandler = None
				msg = "stopped listening for models\n"
		replyobj.info(msg)
	elif what == "selection":
		import chimera
		global selectionHandler
		if mode == "start":
			if selectionHandler is not None:
				msg = "already listening for selection\n"
			else:
				if prefix is None:
					prefix = "SelectionChanged"
				adata = AlertData(prefix=prefix, url=url)
				selectionHandler = chimera.triggers.addHandler(
						"selection changed",
						_alertSelection, adata)
				msg = "listening for selection\n"
		else:
			if selectionHandler is None:
				msg = "not listening for selection\n"
			else:
				chimera.triggers.deleteHandler(
						"selection changed",
						selectionHandler)
				selectionHandler = None
				msg = "stopped listening for selection\n"
		replyobj.info(msg)

def showSeq(osl):
	molChain = set()
	for r in osl.residues():
		molChain.add((r.molecule, r.id.chainId))
	from ModelPanel.base import seqCmd
	seqs = []
	for (m, chainId) in molChain:
		try:
			seqs.append(m.sequence(chainId))
		except AssertionError:
			pass
	seqCmd(seqs)
#	from chimera import selection
#	selection.setCurrent(osl)

_cmdTable = {
	"listmodels":	( listm, { "specInfo":
					[("spec", "models", "models")] }),
	"listchains":	( listc, { "specInfo":
					[("spec", "molecules", "molecules")] }),
	"listresidues":	( listr, { "specInfo":
					[("spec", "residues", "residues"),
					 ("molspec", "molecules", "molecules")] }),
	"listatoms":	( lista, { "specInfo":
					[("spec", "atoms", "atoms")] }),
	"listphysicalchains":	( listp, { "specInfo":
					[("spec", "molecules", "molecules")] }),
	"listselection":( lists, {} ),
	"listen":	( listen, {} ),
	"sequence":	( showSeq, { "specInfo":
					[("spec", "osl", None)] }),
}

def findBestMatch(input, choices):
	bestMatch = None
	for choice in choices:
		if choice.startswith(input):
			if bestMatch is not None:
				from Midas import MidasError
				raise MidasError("\"%s\" is ambiguous" % input)
			else:
				bestMatch = choice
	if bestMatch is None:
		from Midas import MidasError
		raise MidasError("\"%s\" does not match any available choice"
				% input)
	return bestMatch

#
# ----------------------------------------------------------------------------
# New commands are added as subcommands to "list"
#

def distmat(atoms):
	from chimera import replyobj
	coords = [ a.xformCoord() for a in atoms ]
	names = [ a.oslIdent() for a in atoms ]
	for i in range(len(atoms)):
		for j in range(i + 1, len(atoms)):
			replyobj.info("distmat %s %s %.3f\n" % (
						names[i], names[j],
						coords[i].distance(coords[j])))

def resattr():
	# Okay, this is a tremendous hack.  Since Render by Attribute
	# already computes the available list of residue attributes,
	# we want to leverage the code.  However, it is embedded in
	# a Dialog class.  So we subclass it and make sure that the
	# dialog does not get displayed.  We create the dialog instance;
	# update the menus; and pull the attribute list from the instance.
	import ShowAttr
	class Fake(ShowAttr.ShowAttrDialog):
		def initialPosition(self):
			self.Close()
	d = Fake()
	d.configure()
	from chimera import replyobj
	for a in d.useableAttrs[ShowAttr.residueAttrs]:
		replyobj.info("resattr %s\n" % a)
	for a in d.additionalNumericAttrs[ShowAttr.residueAttrs]:
		replyobj.info("resattr %s\n" % a)
	for a in d.additionalOtherAttrs[ShowAttr.residueAttrs]:
		replyobj.info("resattr %s\n" % a)

	for a in d.useableAttrs[ShowAttr.atomAttrs]:
		replyobj.info("resattr %s%s\n" % (AveragePrefix, a))
	for a in d.additionalNumericAttrs[ShowAttr.atomAttrs]:
		replyobj.info("resattr %s%s\n" % (AveragePrefix, a))

_listTable = {
	"distmat":	( distmat, { "specInfo":
					[("spec", "atoms", "atoms")] }),
	"resattr":	( resattr, {} ),
	"models":	_cmdTable["listmodels"],
	"chains":	_cmdTable["listchains"],
	"residues":	_cmdTable["listresidues"],
	"atoms":	_cmdTable["listatoms"],
	"physicalchains":	_cmdTable["listphysicalchains"],
	"selection":	_cmdTable["listselection"],
}

def doList(args):
	parts = args.split(None, 1)
	if len(parts) > 1:
		cmd, otherArgs = parts
	else:
		cmd = args
		otherArgs = ""
	fullCmd = findBestMatch(cmd, _listTable.iterkeys())
	func, kwargs = _listTable[fullCmd]
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(func, otherArgs, **kwargs)
