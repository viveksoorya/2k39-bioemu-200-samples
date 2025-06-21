# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: gui.py 42333 2021-10-20 18:03:27Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import UserError, replyobj
from prefs import prefs
from SimpleSession import SAVE_SESSION, registerAttribute

def processModBaseID(IDcode, ignore_cache=False):
	"""Locate a database ID code via ModBase, read it, and add it to the list of open models.

	_openModBaseIDModel(IDcode) => [model(s)]

	'explodeNMR' controls whether multi-MODEL files are split into
	multiple Molecules (if False, use coord sets instead)
	"""
	identifyAs = IDcode

	from chimera import replyobj
	statusName = identifyAs or IDcode

	path = fetchModBase(IDcode, ignore_cache=ignore_cache)

	# Open PDB file as models
	from chimera import PDBio
	import os
	pdbio = PDBio()
	pdbio.explodeNMR = False
	molList = pdbio.readPDBfile(path)
	if not pdbio.ok():
		replyobj.status("")
		raise UserError("Error reading PDB file: %s" % pdbio.error())
	for m in molList:
		m.name = identifyAs

	# Post-process models to convert remark records
	# into molecule dictionary attribute
	#from baseDialog import buttonFuncName as makeIdentifier
	for m in molList:
		attr = {}
		remarks = m.pdbHeaders.get("REMARK", [])
		for remark in remarks:
			parts = remark.split(None, 2)
			try:
				info = parts[2]
			except IndexError:
				continue
			try:
				key, value = [ v.strip()
						for v in info.split(':', 1) ]
			except ValueError:
				continue
			try:
				value = int(value)
			except ValueError:
				try:
					value = float(value)
				except ValueError:
					pass
			attr[key] = value
			#setattr(m, "modbase_%s" % makeIdentifier(key), value)
		assignModbaseInfo(m, attr)

	# Register open message
	chimera._openedInfo = "Opened %s" % statusName
	ModBaseDialog(IDcode, molList)
	return molList

def fetchModBase(IDcode, ignore_cache=False):
	"""Fetch the output from ModBase and fix it up since the generated file
	(illegally) contains multiple XML tags at the document level"""

	from chimera import fetch
	if not ignore_cache:
		path = fetch.fetch_local_file('ModBase', IDcode + '.pdb')
		if path:
			return path

	from urllib import FancyURLopener
	class Wget(FancyURLopener):
		version = "Wget/1.10.2"
	f = Wget().open("http://salilab.org/modbase/retrieve/modbase"
				"?databaseID=%s" % IDcode)
	from OpenSave import osTemporaryFile
	filename = osTemporaryFile()
	tf = open(filename, "w")
	tf.write(f.readline())
	tf.write("<document>\n")
	tf.write(f.read())
	tf.write("</document>\n")
	tf.close()
	f.close()

	# Parse the XML file and write out
	# a temporary PDB file
	import xml.sax, xml.sax.handler
	from xml.sax import SAXException
	from xml.sax.handler import ContentHandler
	class Handler(ContentHandler):
		def __init__(self, *args, **kw):
			ContentHandler.__init__(self, *args, **kw)
			self.pdbContent = []
			self.pdbActive = False
		def pdbFile(self):
			return ''.join(self.pdbContent).strip()
		def startElement(self, name, attrs):
			self.pdbActive = (name == "content")
			ContentHandler.startElement(self, name, attrs)
		def endElement(self, name):
			if name == "content":
				self.pdbActive = False
			ContentHandler.endElement(self, name)
		def characters(self, content):
			if self.pdbActive:
				self.pdbContent.append(content)
			ContentHandler.characters(self, content)
	handler = Handler()
	try:
		xml.sax.parse(filename, handler)
	except SAXException:
		raise UserError("No matching ModBase entry found for %s"
					% IDcode)
	content = handler.pdbFile()
	del handler
	if not content:
		raise UserError("No ModBase structure found for %s" % IDcode)
	f = open(filename, "w")
	print >> f, content
	f.close()
	del content

	spath = fetch.save_fetched_file(filename, 'ModBase', IDcode + '.pdb')
	if spath:
		return spath

	return filename

class ModBaseDialog(ModelessDialog):

	buttons = ( "Hide", "Quit" )
	help = "UsersGuide/modbase.html"

	provideStatus = True
	statusPosition = "left"

	def __init__(self, name, molList, tableData=None, alignment=None):
		if name:
			if name == "ModBase: Modeller Results":
				name = "Modeller Results" # for previous bug
			if name.startswith("ModBase: ") or name.startswith("Modeller Results"):
				self.title = name
			else: 
				self.title = "ModBase: %s" % name
		else:
			self.title = "Modeller Results"
		self.molList = molList
		self.tableData = tableData
		self.alignment = alignment
		ModelessDialog.__init__(self)
		self.closeHandler = chimera.openModels.addRemoveHandler(
						self._modelClosedCB, None)
		self.selHandler = None
		self.sesHandler = chimera.triggers.addHandler(
						SAVE_SESSION,
						self._sessionCB, None)
		chimera.extension.manager.registerInstance(self)

	def fillInUI(self, parent):
		import Tkinter
		top = parent.winfo_toplevel()
		menubar = Tkinter.Menu(top, type="menubar", tearoff=False)
		top.config(menu=menubar)
		self.columnMenu = Tkinter.Menu(menubar)
		menubar.add_cascade(label="Columns", menu=self.columnMenu)
		fetchMenu = Tkinter.Menu(menubar)
		menubar.add_cascade(label="Fetch Scores", menu=fetchMenu)
		fetchMenu.add_command(label="zDOPE and Estimated RMSD/Overlap",
				command=self.fetchModbaseScores)

		from chimera.tkgui import aquaMenuBar
		aquaMenuBar(menubar, parent, pack = 'top')

		self._makeActionGroup(parent)

		from CGLtk.Table import SortableTable
		from prefs import colAttr, colOrder, prefs, defaults, colOrderModellerResults
		self.modBaseTable = SortableTable(parent, menuInfo=(
							self.columnMenu,
							prefs,
							defaults,
							False ))
		if not self.tableData:
			self._addColumn("Model",
					"lambda m: m.oslIdent()",
					format="%s",
					shown=True)
			if self.title == "Modeller Results":
				order = colOrderModellerResults
			else:
				order = colOrder
			for fieldName in order:
				keyName, format = colAttr[fieldName]
				self._addColumn(fieldName,
					"lambda m: m.modbaseInfo.get('%s', None)"
						% keyName,
					format=format)
		self.modBaseTable.setData(self.molList)
		chimera.triggers.addHandler("post-frame", self._launchTable,
						None)
		self.modBaseTable.pack(expand=True, fill="both")

	def fetchModbaseScores(self, modkey=None):
		from MultAlignViewer.prefs import prefs, MODELLER_KEY
		if not modkey:
			modkey = prefs[MODELLER_KEY]
		if not modkey:
			modkey = ModKeyDialog(prefs[MODELLER_KEY]).run(self.uiMaster())
			if modkey:
				prefs[MODELLER_KEY] = modkey
		if not modkey:
			self.status("No Modeller license key provided", color="red")
			return
		FetchScores(self.molList, self.alignment, modkey, self.modBaseTable,
					self.status)
		
	def _makeActionGroup(self, parent):
		from prefs import prefs
		from chimera import chimage
		import Tkinter, Pmw

		d = prefs.get("treatment", {})
		self.treatmentShow = d.get("show", 0)
		selAtoms = d.get("selectAtoms", 0)
		selModels = d.get("selectModels", 0)
		hideOthers = d.get("hideOthers", 1)

		self.rightArrow = chimage.get("rightarrow.png", parent)
		self.downArrow = chimage.get("downarrow.png", parent)

		if self.treatmentShow:
			relief = "groove"
			image = self.downArrow
		else:
			relief = "flat"
			image = self.rightArrow
		self.treatmentGroup = Pmw.Group(parent,
				collapsedsize=0,
				tagindent=0,
				ring_relief=relief,
				tag_pyclass=Tkinter.Button,
				tag_text=" Treatment of Chosen Models",
				tag_relief="flat",
				tag_compound="left",
				tag_image=image,
				tag_command=self._treatmentCB)
		if not self.treatmentShow:
			self.treatmentGroup.collapse()
		self.treatmentGroup.pack(side="top", fill="x", padx=3)
		interior = self.treatmentGroup.interior()
		self.treatmentSelAtom = Tkinter.IntVar(parent)
		self.treatmentSelAtom.set(selAtoms)
		b = Tkinter.Checkbutton(interior,
					text="Select atoms",
					onvalue=1, offvalue=0,
					variable=self.treatmentSelAtom,
					command=self._treatmentChangedCB)
		b.pack(side="left")
		self.treatmentSelModel = Tkinter.IntVar(parent)
		self.treatmentSelModel.set(selModels)
		b = Tkinter.Checkbutton(interior,
					text="Choose in Model Panel",
					onvalue=1, offvalue=0,
					variable=self.treatmentSelModel,
					command=self._treatmentChangedCB)
		b.pack(side="left")
		self.treatmentHideOthers = Tkinter.IntVar(parent)
		self.treatmentHideOthers.set(hideOthers)
		b = Tkinter.Checkbutton(interior,
					text="Hide others",
					onvalue=1, offvalue=0,
					variable=self.treatmentHideOthers,
					command=self._treatmentChangedCB)
		b.pack(side="left")

	def _treatmentCB(self):
		self.treatmentShow = not self.treatmentShow
		if self.treatmentShow:
			self.treatmentGroup.configure(ring_relief="groove",
						tag_image=self.downArrow)
			self.treatmentGroup.expand()
		else:
			self.treatmentGroup.configure(ring_relief="flat",
						tag_image=self.rightArrow)
			self.treatmentGroup.collapse()
		self._savePrefs()

	def _addColumn(self, title, attrFetch, format="%s", shown=None):
		if title in [c.title for c in self.modBaseTable.columns]:
			return
		if format[-1] == "f":
			# try to align decimal points
			kw = {'font': 'TkFixedFont'}
		else:
			kw = {}
		c = self.modBaseTable.addColumn(title, attrFetch, format=format,
						display=shown, **kw)
		self.modBaseTable.columnUpdate(c)

	def _launchTable(self, trigger, closure, mols):
		# There may be a small window where the dialog
		# can be destroyed before _launchTable gets
		# called in the post-frame trigger.
		if self.modBaseTable:
			self.modBaseTable.launch(browseCmd=self._selectModelCB,
						restoreInfo=self.tableData)
			self.selHandler = chimera.triggers.addHandler(
						"selection changed",
						self._selectionChangedCB, None)
		return chimera.triggerSet.ONESHOT

	def _modelClosedCB(self, trigger, closure, mols):
		remainder = [ m for m in self.molList if m not in mols ]
		if len(remainder) == 0:
			self.molList = []
			self.exit()
		elif len(remainder) != len(self.molList):
			self.molList = remainder
			self.modBaseTable.setData(self.molList)
			self.modBaseTable.refresh(rebuild=True)

	def _selectionChangedCB(self, trigger, closure, ignore):
		from chimera import selection
		mols = selection.currentMolecules()
		selected = [ m for m in mols if m in self.molList ]
		self.modBaseTable.highlight(selected)

	def _selectModelCB(self, tableSel):
		if self.treatmentSelAtom.get():
			from chimera import selection
			selection.clearCurrent()
			selection.addCurrent(tableSel)
			selection.addImpliedCurrent()
		if self.treatmentSelModel.get():
			from ModelPanel import ModelPanel
			from chimera import dialogs
			d = dialogs.display(ModelPanel.name)
			d.selectionChange(tableSel)
		shown = {}
		if self.treatmentHideOthers.get():
			for m in self.molList:
				key = (m.id, m.subid)
				shown[key] = m in tableSel or not tableSel
		else:
			for m in tableSel:
				key = (m.id, m.subid)
				shown[key] = True
		for m in chimera.openModels.list():
			key = (m.id, m.subid)
			try:
				m.display = shown[key]
			except KeyError:
				pass

	def _treatmentChangedCB(self):
		self._selectModelCB(self.modBaseTable.selected())
		self._savePrefs()

	def _savePrefs(self):
		from prefs import prefs
		prefs["treatment"] = {
			"show": self.treatmentShow,
			"selectAtoms": self.treatmentSelAtom.get(),
			"selectModels": self.treatmentSelModel.get(),
			"hideOthers": self.treatmentHideOthers.get(),
		}
		prefs.save()

	def _sessionCB(self, trigger, myData, sesFile):
		from SimpleSession import sessionID
		data = (1,					# version
			self.title,				# title
			[ sessionID(m) for m in self.molList ],	# molecules
			[ m.modbaseInfo for m in self.molList ],# stats
			self.modBaseTable.getRestoreInfo())	# GUI
		print >> sesFile, """
try:
	from ModBase.gui import sessionRestore
	sessionRestore(%s)
except:
	reportRestoreError("Error restoring ModBase")
""" % repr(data)

	def exit(self):
		if self.molList:
			molList = []
			for m in self.molList:
				molList.extend(chimera.openModels.list(
								m.id, m.subid))
			chimera.openModels.close(molList)
		if self.closeHandler:
			chimera.openModels.deleteRemoveHandler(
							self.closeHandler)
			self.closeHandler = None
		if self.selHandler:
			chimera.triggers.deleteHandler("selection changed",
							self.selHandler)
			self.selHandler = None
		if self.sesHandler:
			chimera.triggers.deleteHandler(SAVE_SESSION,
							self.sesHandler)
			self.sesHandler = None
		chimera.extension.manager.deregisterInstance(self)
		self.destroy()
		self.modBaseTable = None

	def emName(self):
		return self.title

	def emRaise(self):
		self.enter()

	def emHide(self):
		self.Close()
	Hide = emHide

	def emQuit(self):
		self.exit()
	Quit = emQuit

	def addScoreColumn(self, scoreName):
		attrFetch = "lambda m: m.modbaseInfo.get('%s', None)" % scoreName
		self._addColumn(scoreName, attrFetch, format="%.2f", shown=True)

	def hideEmptyColumns(self):
		for col in self.modBaseTable.columns:
			for mol in self.molList:
				if col.displayValue(mol):
					break
			else:
				self.modBaseTable.columnUpdate(col, display=False)

def assignModbaseInfo(m, info):
	from prefs import attrMap
	from SimpleSession.save import registerAttribute
	m.modbaseInfo = info
	for k, v in info.iteritems():
		try:
			attrName = attrMap[k]
		except KeyError:
			pass
		else:
			setattr(m, attrName, v)
			registerAttribute(m.__class__, attrName)

def sessionRestore(sessionData):
	from SimpleSession import idLookup
	version = sessionData[0]
	if version == 1:
		ignore, name, molIdList, infoList, tableData = sessionData
		molList = [ idLookup(mid) for mid in molIdList ]
		for m, info in zip(molList, infoList):
			assignModbaseInfo(m, info)
	else:
		raise ValueError("unknown ModBase version: %s" % str(version))
	ModBaseDialog(name, molList, tableData=tableData)

from chimera.baseDialog import ModalDialog
class ModKeyDialog(ModalDialog):
	buttons = ('OK', 'Cancel')
	default = 'OK'
	help = "UsersGuide/modbase.html#fetchscores"

	def __init__(self, initialKey):
		self.initialKey = initialKey
		ModalDialog.__init__(self)

	def fillInUI(self, parent):
		from chimera.HtmlText import HtmlText
		ht = HtmlText(parent, relief='flat', width=30, height=3, wrap="word")
		ht.grid(row=0, column=0, columnspan=2)
		ht.insert('0.0',
"""The <a href="https://modbase.compbio.ucsf.edu/evaluation/">SaliLab Model Evaluation Server</a> requires a <a href="https://salilab.org/modeller/registration.html">Modeller license key</a> to access.  Please enter a valid key.""")
		from chimera.tkoptions import StringOption
		self.keyOption = StringOption(parent, 1, "Modeller license key",
									self.initialKey, None)

	def OK(self):
		self.Cancel(value=self.keyOption.get())

class FetchScores:

	def __init__(self, allMols, alignment, modkey, table, status):
		from prefs import attrMap, ZDOPE_PDB, TSV_RMSD_PDB, TSV_OVERLAP_PDB, \
								ZDOPE_COL, TSV_RMSD_COL, TSV_OVERLAP_COL
		neededAttrs = [attrMap[attr]
					for attr in (ZDOPE_PDB, TSV_RMSD_PDB, TSV_OVERLAP_PDB)]
		for col in table.columns:
			if not col.display and col.title in (
							ZDOPE_COL, TSV_RMSD_COL, TSV_OVERLAP_COL):
				table.columnUpdate(col, display=True)

		status("Initiating %s score requests to Modeller evaluation server"
				% len(allMols))
		self.numRemaining = len(allMols)
		self.table = table
		self.status = status
		self.fetches = [
			FetchScore(m, alignment, modkey, status, self._fsDoneCB)
			for m in allMols]

	def _fsDoneCB(self):
		self.table.refresh()
		self.numRemaining -= 1
		if not self.numRemaining:
			self.status("Scores updated")
		self.fetches = None

class FetchScore:
	Hostname = "modbase.compbio.ucsf.edu"

	def __init__(self, model, alignment, modKey, status, doneCB):
		from WebServices import httpq
		hq = httpq.get()
		self.slot = hq.newSlot(self.Hostname)
		self.model = model
		self.alignment = alignment
		self.modKey = modKey
		self.status = status
		self.doneCB = doneCB
		self.task = None
		from StringIO import StringIO
		io = StringIO()
		chimera.pdbWrite([self.model], chimera.Xform(), io)
		fileContents = io.getvalue()
		io.close()
		self.slot.request(self._submitJob, fileContents)

	def _submitJob(self, q, fileContents):
		from CGLutil.multipart import post_multipart
		fields = [("name", None, "chimera-ModBase"),
				("modkey", None, self.modKey),
				# since only GS341 score needs seq_ident and we don't need that score...
				("seq_ident", None, "100")]
		if self.alignment:
			fields.append(("alignment_file", None, self.alignment))
		from xml.dom.minidom import parseString
		fields.append(("model_file", self.model.name+".pdb",
					fileContents))
		out = post_multipart(self.Hostname, "/modeval/job", fields, acceptType="application/xml", ssl=True)
		dom = parseString(out)
		top = dom.getElementsByTagName('saliweb')[0]
		for results in top.getElementsByTagName('job'):
			self.url = results.getAttribute('xlink:href')
			dom.unlink()
			break
		else:
			dom.unlink()
			q.put(self._submitFailed)
			return
		q.put(self._submitSucceeded)

	def _submitFailed(self):
		self.status("Cannot submit evaluation job for " +
							self.model.name)
		self._done()
		
	def _submitSucceeded(self):
		from chimera.tasks import Task
		self.task = Task("Modeller score for %s" % self.model,
					self._cancelCB)
		self.task.updateStatus("score computation job submitted")
		self.slot.request(self._updateStatus)
	
	def _cancelCB(self):
		self._done()

	def _updateStatus(self, q):
		if self.model.__destroyed__:
			q.put(self._modelClosed)
			return
		import urllib2
		try:
			u = urllib2.urlopen(self.url)
		except urllib2.HTTPError, detail:
			if detail.code == 503:
				import time
				time.sleep(5)
				q.put(self._notFinished)
			else:
				q.put(self._requestFailed)
			return
		from xml.dom.minidom import parseString
		dom = parseString(u.read())

		top = dom.getElementsByTagName('saliweb')[0]
		from prefs import ZDOPE_PDB, attrMap, TSV_RMSD_PDB, TSV_OVERLAP_PDB
		for results in top.getElementsByTagName('results_file'):
			url = results.getAttribute('xlink:href')
			if "evaluation.xml" in url:
				u = urllib2.urlopen(url)
				dom2 = parseString(u.read())
				zdope = dom2.getElementsByTagName("zdope")[0]
				tsvRmsd = dom2.getElementsByTagName("predicted_rmsd")[0]
				tsvOverlap = dom2.getElementsByTagName("predicted_no35")[0]
				for node, pdb in zip((zdope, tsvRmsd, tsvOverlap),
									(ZDOPE_PDB, TSV_RMSD_PDB, TSV_OVERLAP_PDB)):
					val = float(node.firstChild.nodeValue.strip())
					self.model.modbaseInfo[pdb] = val
					setattr(self.model, attrMap[pdb], val)

				dom2.unlink()
		dom.unlink()
		q.put(self._finished)

	def _modelClosed(self):
		self.task.updateStatus("model closed")
		self._done()

	def _notFinished(self):
		if self.task:
			self.task.updateStatus("computing scores")
		if self.slot:
			self.slot.request(self._updateStatus)

	def _requestFailed(self):
		self.task.updateStatus("computation failed")
		self._done()

	def _finished(self):
		self.task.updateStatus("score updated")
		self._done()

	def _done(self):
		if self.task:
			self.task.finished()
			self.task = None
		if self.slot:
			self.slot.finished()
			self.slot = None
		self.doneCB()
