# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: gui.py 41997 2019-01-24 00:15:09Z pett $

import chimera
from chimera.baseDialog import ModelessDialog, ModalDialog
from prefs import prefs, HBOND_GUIDED, MEMORIZED_SETTINGS

class ImpossibleProtonationError(ValueError):
	pass

class AddHDialog(ModelessDialog):
	name = "add hydrogens"
	help = "ContributedSoftware/addh/addh.html"
	buttons = ('OK', 'Close')
	default = 'OK'

	def __init__(self, title="Add Hydrogens", models=None, useHBonds=None,
			cb=None, memorize=False, memorizeName=None, **kw):
		self.title = title
		self.cb = cb
		self.startModels = models
		if useHBonds is None:
			self.startUseHBonds = prefs[HBOND_GUIDED]
		else:
			self.startUseHBonds = useHBonds
		ModelessDialog.__init__(self, **kw)
		self.memorize = memorize
		self.memorizeName = memorizeName
		if memorizeName and not memorize \
		and memorizeName in prefs[MEMORIZED_SETTINGS]:
			self.OK()

	def fillInUI(self, parent):
		import Pmw, Tkinter
		row = 0
		self.resSchemeData = {}
		from chimera.widgets import MoleculeScrolledListBox
		self.molList = MoleculeScrolledListBox(parent, labelpos='w',
					label_text="Add hydrogens to:",
					listbox_selectmode='extended',
					selectioncommand=self._updateTables)
		if self.startModels:
			self.molList.setvalue(self.startModels)
		self.molList.grid(row=row, column=0, sticky="news")
		parent.columnconfigure(row, weight=1)
		parent.rowconfigure(row, weight=1)
		row += 1

		self.isolateVar = Tkinter.IntVar(parent)
		self.isolateVar.set(True)
		Tkinter.Checkbutton(parent, variable=self.isolateVar,
			text="Consider each model in isolation from all others").grid(
			row=row, column=0)
		row += 1

		grp = Pmw.Group(parent, tag_text="Method", hull_padx=2)
		grp.grid(row=row, column=0, sticky="ew")
		row += 1
		self.useHBondsVar = Tkinter.IntVar(parent)
		self.useHBondsVar.set(self.startUseHBonds)
		Tkinter.Radiobutton(grp.interior(), variable=self.useHBondsVar,
				value=False, text="steric only"
				).grid(row=0, sticky='w')
		Tkinter.Radiobutton(grp.interior(), variable=self.useHBondsVar,
			value=True, text="also consider H-bonds (slower)"
			).grid(row=1, sticky='w')

		def settingsToHisType(item):
			if item.delta and item.epsilon:
				return "HIP"
			if item.delta:
				return "HID"
			if item.epsilon:
				return "HIE"
			return "HIS"
		def settingsToAcidType(item, resType=None):
			if resType == "ASP":
				one, two = item.OD1, item.OD2
			else:
				one, two = item.OE1, item.OE2
			if one and two:
				raise ImpossibleProtonationError("%s cannot have both"
					" carboxy oxygens protonated.\nPlease choose another"
					" protonation for %s" % (resType, item.residue))
			if one:
				return 1
			if two:
				return 2
			return 0
		def settingsToLysType(item):
			if item.charged:
				return "LYS"
			return "LYN"
		def settingsToCysType(item):
			if item.negative:
				return "CYM"
			return None
		pageInfo = [
			("histidine", TableGuide(["HIS", "HID", "HIE", "HIP"],
			["unspecified", "delta", "epsilon", "both"], ["delta", "epsilon"],
			None, settingsToHisType, methodApplies="If neither delta nor epsilon is selected")),

			("glutamic acid", TableGuide(["GLU", "GLH"],
			["negatively charged", "neutral [protonated OE2]"], ["OE1", "OE2"],
			None, lambda r: settingsToAcidType(r, resType="GLU"))),

			("aspartic acid", TableGuide(["ASP", "ASH"],
			["negatively charged", "neutral [protonated OD2]"], ["OD1", "OD2"],
			None, lambda r: settingsToAcidType(r, resType="ASP"))),

			("lysine", TableGuide(["LYS", "LYN"],
			["positively charged", "neutral"], ["charged"],
			"charged", settingsToLysType)),

			("cysteine", TableGuide(["CYS", "CYM"],
			["unspecified", "negatively charged"], ["negative"],
			None, settingsToCysType, methodApplies="If negative not selected"))
		]
		self.protNotebook = Pmw.NoteBook(parent, tabpos=None,
				createcommand=lambda pn, pi=pageInfo: self._createPage(pn, pi),
				raisecommand=self._raisePage)
		Pmw.OptionMenu(parent, items=[i[0] for i in pageInfo],
			labelpos='w', label_text="Protonation states for:",
			command=self.protNotebook.selectpage).grid(row=row, sticky='w')
		row += 1
		self.nbRow = row
		for pn, guide in pageInfo:
			self.protNotebook.add(pn)
		self.protNotebook.grid(row=self.nbRow, sticky='nsew')
		row += 1

	def _createPage(self, pageName, pagesInfo):
		for pn, guide in pagesInfo:
			if pn == pageName:
				break
		else:
			raise AssertionError("No page named %s in page info!" % pageName)
		self.resSchemeData[pageName] = self._resGUI(
						self.protNotebook.page(pageName), guide)
		self.protNotebook.setnaturalsize()

	def _getTableData(self, guide):
		items = []
		for m in self.molList.getvalue():
			for r in m.residues:
				if r.type in guide.resTypes:
					items.append(guide.makeItem(r))
		return items

	def _raisePage(self, pageName):
		if self.resSchemeData[pageName]['var'].get() == "pick":
			self.uiMaster().rowconfigure(self.nbRow, weight=4)
		else:
			self.uiMaster().rowconfigure(self.nbRow, weight=0)

	def _resGUI(self, frame, guide):
		import Tkinter
		info = {}
		info['group frame'] = frame
		info['guide'] = guide
		info['var'] = var = Tkinter.StringVar(frame)
		var.set("name")
		cmd = lambda i=info: self._switchList(i)
		Tkinter.Radiobutton(frame, variable=var,
			value="name", text="Residue-name-based\n(%s = %s)"
			% ("/".join(guide.resTypes), "/".join(guide.protNames)),
			command=cmd, justify="left").grid(
			row=0, sticky='w')
		info['pick text'] = pickText = Tkinter.StringVar(frame)
		pickText.set("Specified individually...")
		Tkinter.Radiobutton(frame, variable=var,
				value="pick", textvariable=pickText,
				command=cmd,).grid(row=1, sticky='w')
		if guide.methodApplies:
			defaultText = "Unspecified (determined by method)"
		elif guide.default:
			defaultText = guide.default.capitalize()
		else:
			defaultText = "Charged"
		Tkinter.Radiobutton(frame, variable=var,
				value="default", command=cmd,
				text=defaultText).grid(row=3, sticky='w')
		return info

	def _switchList(self, data):
		if 'table' not in data:
			if data['var'].get() != "pick":
				return
			import Tkinter
			data['choice frame'] = frame = Tkinter.Frame(data['group frame'])
			guide = data['guide']
			if guide.methodApplies:
				Tkinter.Label(frame, text="%s\nthen chosen method determines"
					" protonation" % guide.methodApplies).grid(row=0, column=0)
			from CGLtk.Table import SortableTable
			data['table'] = table = SortableTable(frame)
			table.grid(row=1, column=0, sticky="nsew")
			frame.rowconfigure(1, weight=1)
			frame.columnconfigure(0, weight=1)
			frame.columnconfigure(1, weight=1)
			table.addColumn("Model", "model")
			table.addColumn("Residue", "residue")
			dispCNs = []
			for cn in guide.colNames:
				if cn[0].isupper():
					dispCN = cn
				else:
					dispCN = cn.capitalize()
				table.addColumn(dispCN, cn, format=bool)
				dispCNs.append(dispCN)
			table.setData(self._getTableData(guide))
			table.launch()

			buttonFrame = Tkinter.Frame(frame)
			buttonFrame.grid(row=2, sticky="nsew")
			for i, cn in enumerate(guide.colNames):
				Tkinter.Button(buttonFrame, text="Toggle %s" % dispCNs[i],
					pady=0, highlightthickness=0,
					command=lambda t=table, cn=cn: self._toggleColumn(t, cn)
					).grid(row=0, column=i)
				buttonFrame.columnconfigure(i, weight=1)

		if data['var'].get() == "pick":
			data["pick text"].set("Individually chosen:")
			data["choice frame"].grid(row=2, sticky="nsew")
			interior = data["group frame"]
			interior.columnconfigure(0, weight=1)
			interior.rowconfigure(2, weight=1)
			self.uiMaster().rowconfigure(self.nbRow, weight=4)
			self.protNotebook.setnaturalsize()
		else:
			data["pick text"].set("Individually chosen...")
			data["choice frame"].grid_forget()
			interior = data["group frame"]
			interior.columnconfigure(0, weight=0)
			interior.rowconfigure(2, weight=0)
			self.uiMaster().rowconfigure(self.nbRow, weight=0)
			self.protNotebook.setnaturalsize()

	def _toggleColumn(self, table, attrName):
		for i in table.data:
			setattr(i, attrName, not getattr(i, attrName))
		table.refresh()

	def _updateTables(self):
		for data in self.resSchemeData.values():
			if 'table' not in data:
				continue
			data['table'].setData(self._getTableData(data['guide']))

	def Apply(self):
		from chimera import openModels, Molecule
		from AddH import simpleAddHydrogens, hbondAddHydrogens
		from unknownsGUI import initiateAddHyd
		prefs[HBOND_GUIDED] = self.useHBondsVar.get()
		addhFuncs = [simpleAddHydrogens, hbondAddHydrogens]
		method = addhFuncs[prefs[HBOND_GUIDED]]
		kw = { 'inIsolation': self.isolateVar.get() }
		memorizeOK = True
		for protName, data in self.resSchemeData.items():
			var = data['var']
			if var.get() == "name":
				scheme = None
			elif var.get() == "pick":
				memorizeOK = False
				try:
					raw = [(i.residue, data['guide'].settingsToResType(i))
									for i in data['table'].data]
					scheme = dict([(k,v) for k,v in raw if v is not None])
				except ImpossibleProtonationError, v:
					self.enter()
					from chimera import UserError
					raise UserError(str(v))
			else:
				scheme = {}
			# reminder: kw will only be populated by pages that have been raised
			kw[data['guide'].resTypes[0].lower() + "Scheme"] = scheme
		# use memorized settings (or save them) as appropriate
		if self.memorizeName:
			if self.memorize:
				if memorizeOK:
					settings = {
						'hbond guided': prefs[HBOND_GUIDED],
					}
					settings.update(kw)
					allSettings = prefs[MEMORIZED_SETTINGS].copy()
					allSettings[self.memorizeName] = settings
					prefs[MEMORIZED_SETTINGS] = allSettings
			elif self.memorizeName in prefs[MEMORIZED_SETTINGS]:
				settings = prefs[MEMORIZED_SETTINGS][self.memorizeName]
				method = addhFuncs[settings['hbond guided']]
				kw = settings.copy()
				del kw['hbond guided']
		initiateAddHyd(self.molList.getvalue(), addFunc=method, okCB=self.cb, **kw)

class TableGuide:
	def __init__(self, resTypes, protNames, colNames, default, settingsToResType,
						methodApplies=False):
		self.resTypes = resTypes
		self.protNames = protNames
		self.colNames = colNames
		self.methodApplies = methodApplies
		self.settingsToResType = settingsToResType
		self.default = default

	def makeItem(self, res):
		class Item:
			pass
		i = Item()
		i.model = res.molecule
		i.residue = res
		for cn in self.colNames:
			setattr(i, cn, cn==self.default)
		return i

def checkNoHyds(items, cb, process):
	noHyds = []
	for item in items:
		for a in item.atoms:
			if a.element.number == 1:
				break
		else:
			noHyds.append(item)
	if items and type(items[0]) == chimera.Residue:
		objDesc = "residue"
		attrName = "type"
		noHydModels = list(set([r.molecule for r in noHyds]))
	else:
		objDesc = "model"
		attrName = "name"
		noHydModels = noHyds
	if not noHyds:
		from AddH import determineTerminii
		realN, realC, fakeN, fakeC = determineTerminii(noHydModels)
		# ensure that N terminii that aren't actual N terminii
		# are Npl so that AddCharge works (recognizes H)
		for nter in fakeN:
			if "H" not in nter.atomsMap:
				continue
			try:
				n = nter.atomsMap["N"][0]
			except KeyError:
				continue
			n.idatmType = "Npl"
		cb()
		return
	from chimera.baseDialog import AskYesNoDialog
	msg = "Hydrogens must be present for %s to work correctly.\n" % process
	if len(items) == len(noHyds):
		msg += "No %ss have hydrogens.\n" % objDesc
	else:
		msg += "The following %ss have no hydrogens:\n" % objDesc
		for nh in noHyds:
			msg += "\t%s (%s)\n" % (getattr(nh, attrName),
								nh.oslIdent())
	msg += "You can add hydrogens using the AddH tool.\n"
	msg += "What would you like to do?"
	userChoice = NoHydsDialog(msg).run(chimera.tkgui.app)
	if userChoice == "add hydrogens":
		AddHDialog(title="Add Hydrogens for %s" % process.title(),
			models=noHydModels, useHBonds=True, oneshot=True, cb=cb)
	elif userChoice == "continue":
		cb()

class NoHydsDialog(ModalDialog):
	title = "No Hydrogens..."
	help = "UsersGuide/midas/addcharge.html#needH"
	buttons = ('Abort', 'Add Hydrogens', 'Continue Anyway')
	default = 'Add Hydrogens'
	oneshot = True

	def __init__(self, msg):
		self.msg = msg
		ModalDialog.__init__(self)

	def fillInUI(self, parent):
		import Tkinter
		message = Tkinter.Label(parent, text=self.msg)
		message.grid(sticky='nsew')

	def Abort(self):
		self.Cancel("cancel")

	def AddHydrogens(self):
		self.Cancel("add hydrogens")

	def ContinueAnyway(self):
		self.Cancel("continue")

from chimera import dialogs
dialogs.register(AddHDialog.name, AddHDialog)
