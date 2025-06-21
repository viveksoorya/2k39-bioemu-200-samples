# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: gui.py 38514 2013-03-26 20:50:18Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from prefs import prefs, GRID_PADDING, GRID_SPACING

class EspDialog(ModelessDialog):
	title = "Coulombic Surface Coloring"
	name = "ESP computation"
	help = "ContributedSoftware/coulombic/coulombic.html"

	HB = "estimated from H-bonds"

	def fillInUI(self, parent):
		import Pmw, Tkinter

		row = 0
		self.buttonWidgets['OK']['state'] = 'disabled'
		self.buttonWidgets['Apply']['state'] = 'disabled'
		from chimera.widgets import ModelScrolledListBox
		self.surfListBox = ModelScrolledListBox(parent, labelpos='n',
			label_text='Surfaces to color by ESP:',
			listbox_selectmode="extended",
			filtFunc=lambda m: isinstance(m, chimera.MSMSModel),
			selectioncommand=self._selSurfCB)
		self.surfListBox.grid(row=row, column=0, sticky="nsew",
							columnspan=2)
		row += 1

		self.numValues = Pmw.OptionMenu(parent, command=self._menuCB, initialitem="3",
			items=[str(x) for x in range(2, 12)], labelpos='w',
			label_text="Number of colors/values:")
		self.numValues.grid(row=row, column=0, columnspan=2)
		row += 1
		f = self.interpFrame = Tkinter.Frame(parent)
		f.grid(row=row, column=0, columnspan=2)
		row += 1
		self.wells = []
		self.values = []
		self._entryOpts = {
			'validate': 'real',
			'entry_justify': 'center',
			'entry_width': 6
		}
		from CGLtk.color.ColorWell import ColorWell
		for color, value in [("red", -10), ("white", 0), ("blue", 10)]:
			well = ColorWell(f, color=color)
			well.grid(row=0, column=len(self.wells))
			self.wells.append(well)
			entry = Pmw.EntryField(f, value=str(value),
							**self._entryOpts)
			entry.grid(row=1, column=len(self.values))
			self.values.append(entry)
		unitsLab = Tkinter.Label(f, text="kcal/(mol*e)")
		from CGLtk.Font import shrinkFont
		shrinkFont(unitsLab)
		unitsLab.grid(row=1, column=20)

		from chimera.tkoptions import FloatOption, BooleanOption, StringOption
		self.distDep = BooleanOption(parent, row,
			"Distance-dependent dielectric", True, None, balloon=
			"If true, charge falls off with distance squared to\n"
			"simulate solvent screening effects")
		row += 1
		self.dielectric = FloatOption(parent, row, "Dielectric constant",
								4.0, None)
		row += 1
		self.surfDist = FloatOption(parent, row, "Distance from surface",
			1.4, None, balloon="Potential at this distance from\n"
			"the surface is used for coloring")
		row += 1

		self.hisGroup = Pmw.Group(parent, hull_padx=2,
			tag_text="Implicit Histidine Protonation")
		self.hisGroup.grid(row=row, column=0, columnspan=2, sticky="nsew")
		row += 1
		self.hisProtVar = Tkinter.StringVar(parent)
		self.hisProtVar.set("name")
		interior = self.hisGroup.interior()
		interior.columnconfigure(0, weight=1)
		lab = Tkinter.Label(interior, text="Assumed histidine "
			"protonation for\nstructures without explicit hydrogens")
		shrinkFont(lab, slant="italic")
		lab.grid(row=0)
		self.hisHandling = Tkinter.Radiobutton(interior, variable=self.hisProtVar,
			value="name", text="Residue name-based", command=self._switchHisList)
		self.hisHandling.grid(row=1, sticky='w')
		f = Tkinter.Frame(interior)
		f.grid(row=2)
		Tkinter.Label(f, text="HID/HIE/HIP = delta/epsilon/both").grid(
			row=0, sticky='w')
		self.hisDefault = Pmw.OptionMenu(f, initialitem=self.HB,
			items=[self.HB, "delta", "epsilon", "both"], labelpos='w',
			label_text="HIS = ")
		self.hisDefault.grid(row=1, sticky='w')
		self._pickText = Tkinter.StringVar(parent)
		self._pickText.set("Specified individually...")
		Tkinter.Radiobutton(interior, variable=self.hisProtVar,
			value="pick", textvariable=self._pickText,
			command=self._switchHisList).grid(row=3, sticky='w')

		self.createGridVar = Tkinter.IntVar(parent)
		self.createGridVar.set(False)
		Tkinter.Checkbutton(parent, variable=self.createGridVar,
			command=self._createGridChangeCB, text="Compute grid...").grid(
			row=row, column=0, columnspan=2)
		row += 1
		self._numericGridWidgetsRow = row
		self._ngwFrame = f = Tkinter.Frame(parent)
		self.gridSpacing = FloatOption(f, 0, "Grid spacing",
										prefs[GRID_SPACING], None)
		self.gridBuffer = FloatOption(f, 0, "Padding", prefs[GRID_PADDING],
			None, startCol=3, balloon="Extra space on each side of surface")
		f.columnconfigure(2, minsize="0.125i")
		row += 1
		self._gridNameRow = row
		self._gnFrame = f = Tkinter.Frame(parent)
		from ESP import defaultVolumeName
		self.gridName = StringOption(f, 0, "Volume name",
										defaultVolumeName, None)
		self._gnFrame.columnconfigure(1, weight=1)
		row += 1

		Tkinter.Button(parent, pady=0, command=self._colorKeyCB,
			text="Create corresponding color key").grid(row=row,
			column=0, columnspan=2)
		row += 1

		# save only registered for once we've done something!
		from chimera import triggers, SCENE_TOOL_RESTORE
		triggers.addHandler(SCENE_TOOL_RESTORE, self._sceneRestore, None)

	def Apply(self):
		for entry in self.values:
			entry.invoke()
		colors = [w.rgba for w in self.wells]
		values = [float(e.getvalue()) for e in self.values]
		if self.hisProtVar.get() == "name":
			hisScheme = {
				self.HB: None,
				'delta': 'HID',
				'epsilon': 'HIE',
				'both': 'HIP'
			}[self.hisDefault.getvalue()]
		else:
			hisScheme = self.hisListingData
		if self.createGridVar.get():
			volumeParams = (
				self.gridSpacing.get(),
				self.gridBuffer.get(),
				self.gridName.get()
			)
		else:
			volumeParams = None
			
		from ESP import colorEsp
		for surf in self.surfListBox.getvalue():
			colorEsp(surf, colors, values,
					dielectric=self.dielectric.get(),
					distDep=self.distDep.get(),
					surfDist=self.surfDist.get(),
					hisScheme=hisScheme,
					volumeParams=volumeParams)

		if not getattr(self, '_sceneSaving', False):
			# only save state in scene once we've done something
			from chimera import triggers, SCENE_TOOL_SAVE
			triggers.addHandler(SCENE_TOOL_SAVE, self._sceneSave, None)
			self._sceneSaving = True

	def _colorKeyCB(self):
		for entry in self.values:
			entry.invoke()
		from Ilabel.gui import IlabelDialog
		from chimera import dialogs
		d = dialogs.display(IlabelDialog.name)
		d.keyConfigure(zip([w.rgba for w in self.wells],
					[e.getvalue() for e in self.values]))

	def _createGridChangeCB(self):
		if self.createGridVar.get():
			self._ngwFrame.grid(row=self._numericGridWidgetsRow, column=0,
				columnspan=2, sticky="ew")
			self._gnFrame.grid(row=self._gridNameRow, column=0, columnspan=2,
				sticky='ew')
		else:
			self._ngwFrame.grid_forget()
			self._gnFrame.grid_forget()

	def _menuCB(self, val):
		newNum = int(val)
		oldSettings = []
		for well, entry in zip(self.wells, self.values):
			entry.invoke()
			oldSettings.append((well.rgba, float(entry.getvalue())))
			well.grid_forget()
			well.destroy()
			entry.grid_forget()
			entry.destroy()
		import Pmw
		from CGLtk.color.ColorWell import ColorWell
		self.wells = []
		self.values = []
		scale = (len(oldSettings) - 1.0) / (newNum - 1.0)
		f = self.interpFrame
		for i in range(newNum):
			index = i * scale
			if index == int(index) \
			or int(index) >= len(oldSettings):
				color, value = oldSettings[int(index)]
			else:
				lowc, lowv = oldSettings[int(index)]
				highc, highv = oldSettings[int(index)+1]
				frac = index - int(index)
				color = []
				for lowcomp, highcomp in zip(lowc, highc):
					color.append((1.0 - frac) * lowcomp
							+ frac * highcomp)
				value = (1.0 - frac) * lowv + frac * highv
			well = ColorWell(f, color=color)
			well.grid(row=0, column=len(self.wells))
			self.wells.append(well)
			entry = Pmw.EntryField(f, value=str(value),
							**self._entryOpts)
			entry.grid(row=1, column=len(self.values))
			self.values.append(entry)

	def _sceneSave(self, trigName, myData, scene):
		info = {}
		scene.tool_settings[self.name] = (1, info)
		info['colors'] = [w.rgba for w in self.wells]
		info['values'] = [e.getvalue() for e in self.values]
		info['dist dep'] = self.distDep.get()
		info['dielectric constant'] = self.dielectric.get()
		info['surf dist'] = self.surfDist.get()
		info['his prot'] = hisProt = self.hisProtVar.get()
		if hisProt == "name":
			info['his default'] = self.hisDefault.getvalue()
		else:
			from Animate.Tools import sceneID
			info['his settings'] = hs = {}
			for r, settings in self._vars.items():
				hs[sceneID(r)] = [v.get() for v in settings]
		info['compute grid'] = self.createGridVar.get()

	def _sceneRestore(self, trigName, myData, scene):
		sceneInfo = scene.tool_settings.get(self.name, None)
		if not sceneInfo:
			return
		version, info = sceneInfo
		self.numValues.setvalue(len(info['colors']))
		self.numValues.invoke()
		for well, rgba in zip(self.wells, info['colors']):
			well.showColor(rgba, doCallback=False)
		for entry, value in zip(self.values, info['values']):
			entry.setvalue(value)
		self.distDep.set(info['dist dep'])
		self.dielectric.set(info['dielectric constant'])
		self.surfDist.set(info['surf dist'])
		prev = self.hisProtVar.get()
		if prev != info['his prot']:
			self.hisProtVar.set(info['his prot'])
			self.hisHandling.invoke()
		if self.hisProtVar.get() == "name":
			self.hisDefault.setvalue(info['his default'])
		else:
			from Animate.Tools import idLookup
			for sceneID, settings in info['his settings'].items():
				r = idLookup(sceneID)
				if r not in self._vars:
					continue
				for var, setting in zip(self._vars[r], settings):
					var.set(setting)
		self.createGridVar.set(info['compute grid'])

	def _selSurfCB(self):
		if self.surfListBox.getvalue():
			state = 'normal'
		else:
			state = 'disabled'
		self.buttonWidgets['OK']['state'] = state
		self.buttonWidgets['Apply']['state'] = state

		self._updateHisListing()

	def _select(self, hisType):
		for r, vars in self._vars.items():
			dv, ev = vars
			if hisType == "delta":
				dv.set(True)
				ev.set(False)
				self.hisListingData[r] = "HID"
			elif hisType == "epsilon":
				dv.set(False)
				ev.set(True)
				self.hisListingData[r] = "HIE"
			else:
				dv.set(True)
				ev.set(True)
				self.hisListingData[r] = "HIP"

	def _switchHisList(self):
		if not hasattr(self, 'hisListing'):
			if self.hisProtVar.get() != "pick":
				return
			self.hisListingData = {}
			import Tix, Tkinter
			self.hisFrame = Tkinter.Frame(self.hisGroup.interior())
			self.hisListing = Tix.ScrolledHList(self.hisFrame,
						width="3i",
						options="""hlist.columns 4
						hlist.header 1
						hlist.indicator 1""")
			self.hisListing.hlist.configure(
				selectbackground=self.hisListing['background'],
				selectborderwidth=0)
			self.hisListing.grid(row=0, column=0, columnspan=3,
								sticky="nsew")
			self.hisFrame.rowconfigure(1, weight=1)
			self.hisFrame.columnconfigure(0, weight=1)
			self.hisFrame.columnconfigure(1, weight=1)
			hlist = self.hisListing.hlist
			hlist.header_create(0, itemtype="text", text="Model")
			hlist.header_create(1, itemtype="text", text="Residue")
			hlist.header_create(2, itemtype="text", text="Delta")
			hlist.header_create(3, itemtype="text", text="Epsilon")
			self._checkButtonStyle = Tix.DisplayStyle("window",
				background=hlist['background'],
				refwindow=self.hisListing, anchor='center')
			self._updateHisListing()

			Tkinter.Button(self.hisFrame, text="All Delta",
				pady=0, highlightthickness=0,
				command=lambda p="delta": self._select(p)
				).grid(row=1, column=0)
			Tkinter.Button(self.hisFrame, text="All Epsilon",
				pady=0, highlightthickness=0,
				command=lambda p="epsilon": self._select(p)
				).grid(row=1, column=1)
			Tkinter.Button(self.hisFrame, text="All Both",
				pady=0, highlightthickness=0,
				command=lambda p="both": self._select(p)
				).grid(row=1, column=2)

		if self.hisProtVar.get() == "pick":
			self._pickText.set("Specified individually:")
			self.hisFrame.grid(row=4, sticky="nsew")
			interior = self.hisGroup.interior()
			interior.rowconfigure(4, weight=1)
			self.uiMaster().rowconfigure(6, weight=4)
		else:
			self._pickText.set("Specified individually...")
			self.hisFrame.grid_forget()
			interior = self.hisGroup.interior()
			interior.rowconfigure(4, weight=0)
			self.uiMaster().rowconfigure(6, weight=0)

	def _toggleDelta(self, res):
		old = self.hisListingData[res]
		if old == "HIS":
			new = "HID"
		elif old == "HID":
			new = "HIS"
		elif old == "HIE":
			new = "HIP"
		else:
			new = "HIE"
		self.hisListingData[res] = new

	def _toggleEpsilon(self, res):
		old = self.hisListingData[res]
		if old == "HIS":
			new = "HIE"
		elif old == "HID":
			new = "HIP"
		elif old == "HIE":
			new = "HIS"
		else:
			new = "HID"
		self.hisListingData[res] = new

	def _updateHisListing(self):
		if not hasattr(self, 'hisListing'):
			return
		self._updateHisListingData()
		hlist = self.hisListing.hlist
		on = self.hisListing.tk.call('tix', 'getimage', 'ck_on')
		off = self.hisListing.tk.call('tix', 'getimage', 'ck_off')
		hlist.delete_all()
		import Tkinter
		row = 0
		self._vars = {}
		for m in [s.molecule for s in self.surfListBox.getvalue()]:
			for r in m.residues:
				try:
					hisType = self.hisListingData[r]
				except KeyError:
					continue
				hlist.add(row, itemtype="text", text="%s (%s)"
						% (m.name, m.oslIdent()))
				hlist.item_create(row, 1, itemtype="text",
						text=r.oslIdent(
						start=chimera.SelResidue))
				var = Tkinter.IntVar(hlist)
				var.set(hisType in ["HID", "HIP"])
				cmd = lambda r=r: self._toggleDelta(r)
				self._vars[r] = [var]
				toggle = Tkinter.Checkbutton(hlist, command=cmd,
					variable=var, image=off, selectimage=on,
					selectcolor="", indicatoron=False,
					borderwidth=0)
				hlist.item_create(row, 2, itemtype="window",
					window=toggle,
					style=self._checkButtonStyle)
				var = Tkinter.IntVar(hlist)
				var.set(hisType in ["HIE", "HIP"])
				cmd = lambda r=r: self._toggleEpsilon(r)
				self._vars[r].append(var)
				toggle = Tkinter.Checkbutton(hlist, command=cmd,
					variable=var, image=off, selectimage=on,
					selectcolor="", indicatoron=False,
					borderwidth=0)
				hlist.item_create(row, 3, itemtype="window",
					window=toggle,
					style=self._checkButtonStyle)
				row += 1

	def _updateHisListingData(self):
		newData = {}
		default = {
			'delta': 'HID',
			'epsilon': 'HIE',
			'both': 'HIP',
			self.HB: 'HID'
		}[self.hisDefault.getvalue()]
		for m in [s.molecule for s in self.surfListBox.getvalue()]:
			for r in m.residues:
				if r.type not in ["HIS", "HIE", "HIP", "HID"]:
					continue
				try:
					newData[r] = self.hisListingData[r]
				except KeyError:
					if r.type == 'HIS':
						newData[r] = default
					else:
						newData[r] = r.type
		self.hisListingData = newData


from chimera import dialogs
dialogs.register(EspDialog.name, EspDialog)
