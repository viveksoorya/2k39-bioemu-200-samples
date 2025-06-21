class ServiceLocation:

	def __init__(self, parent, extensionName, defaults):
		self._master = parent
		self.extensionName = extensionName
		self.defaults = defaults
		import Tkinter
		parent.columnconfigure(1, weight=1)
		self._typeVar = Tkinter.StringVar(parent)
		row = 0
		firstType = None
		self._widgets = dict()
		import prefs
		d = dict()
		for backend, param in self.defaults:
			attr = "_%sSetup" % backend
			try:
				f = getattr(self, attr)
			except AttributeError:
				continue
			prefParam = prefs.getServicePrefs(self.extensionName,
									backend)
			if param[0] is not None and prefParam[0] is None:
				prefs.setServicePrefs(self.extensionName,
							backend, *param)
			row, widgets = f(parent, row)
			self._widgets[backend] = widgets
			d[backend] = param
			if firstType is None:
				firstType = backend
		prefs.prefs.changeDefault(self.extensionName, d)

		import prefs
		curType = prefs.getSelectedPrefs(self.extensionName)
		if curType is None or curType not in d:
			curType = firstType
		self._saveType = curType
		self._typeVar.set(curType)
		self._changeType()

	def _changeType(self):
		curType = self._typeVar.get()
		for backend, widgets in self._widgets.iteritems():
			if backend == curType:
				state = "normal"
			else:
				state = "disabled"
			for w in widgets:
				w.config(state=state)
		if self._saveType != curType:
			import prefs
			prefs.setSelectedPrefs(self.extensionName, curType)
			self._saveType = curType

	def _showValue(self, w, backend):
		import prefs
		service, server = prefs.getServicePrefs(self.extensionName,
								backend)
		if service is None:
			s = ""
		else:
			s = prefs.service2display(backend, service, server)
		w.delete(0, "end")
		w.insert(0, s)

	def _setValue(self, backend, s):
		import prefs
		try:
			service, server = prefs.display2service(backend, s)
		except:
			from chimera import replyobj
			replyobj.warning("mangled %s value" % backend)
		else:
			prefs.setServicePrefs(self.extensionName, backend,
							service, server)

	def _opalSetup(self, parent, row):
		import Tkinter
		self._opalRadio = Tkinter.Radiobutton(parent,
						text="Opal web service",
						value="opal",
						variable=self._typeVar,
						command=self._changeType)
		self._opalRadio.grid(row=row, column=0,
						columnspan=3, sticky="w")
		self._opalServerLabel = Tkinter.Label(parent,
						text="Server:")
		row += 1
		self._opalServerLabel.grid(row=row, column=0, sticky="e")
		self._opalServer = Tkinter.Entry(parent)
		self._opalServer.grid(row=1, column=1, sticky="ew")
		self._opalServerReset = Tkinter.Button(parent,
						text="Reset",
						command=self._opalResetServer)
		self._opalServerReset.grid(row=row, column=2, sticky="ew")
		self._opalServer.bind("<Return>", self._opalSet)
		self._opalServer.bind("<FocusOut>", self._opalSet)
		row += 1
		self._showValue(self._opalServer, "opal")
		return row, [ self._opalServerLabel, self._opalServer,
						self._opalServerReset ]

	def _opalResetServer(self):
		import prefs
		d = prefs.prefs.getDefault(self.extensionName)
		service, server = d["opal"]
		s = prefs.service2display("opal", service, server)
		self._opalServer.delete(0, "end")
		self._opalServer.insert(0, s)

	def _opalSet(self, event=None):
		self._setValue("opal", self._opalServer.get())
		return "break"

	def _localSetup(self, parent, row):
		import Tkinter
		self._localRadio = Tkinter.Radiobutton(parent,
						text="Local",
						value="local",
						variable=self._typeVar,
						command=self._changeType)
		self._localRadio.grid(row=row, column=0,
						columnspan=3, sticky="w")
		row += 1
		self._localPathLabel = Tkinter.Label(parent,
						text="Path:")
		self._localPathLabel.grid(row=row, column=0, sticky="e")
		self._localPath = Tkinter.Entry(parent)
		self._localPath.grid(row=row, column=1, sticky="ew")
		self._localBrowse = Tkinter.Button(parent,
						text="Browse...",
						command=self._localBrowse)
		self._localBrowse.grid(row=row, column=2, sticky="ew")
		self._localPath.bind("<Return>", self._localSet)
		self._localPath.bind("<FocusOut>", self._localSet)
		row += 1
		self._showValue(self._localPath, "local")
		self.browseDialog = None
		return row, [ self._localPathLabel, self._localPath,
						self._localBrowse ]

	def _localBrowse(self):
		if self.browseDialog is None:
			from OpenSave import OpenModeless
			dialogKw = {
				"master": self._master
			}
			self.browseDialog = OpenModeless(multiple=False,
						command=self._localUpdatePath,
						dialogKw=dialogKw)
		self.browseDialog.enter()

	def _localUpdatePath(self, okOrApply, dialog):
		if not okOrApply:
			return
		paths = dialog.getPaths()
		if not paths:
			return
		path = paths[0]
		self._localPath.delete(0, "end")
		self._localPath.insert(0, path)
		self._localSet()

	def _localSet(self, event=None):
		self._setValue("local", self._localPath.get())
		return "break"

	def getLocation(self):
		backend = self._typeVar.get()
		import prefs
		service, server = prefs.getServicePrefs(self.extensionName,
								backend)
		return backend, service, server

def addServiceSelector(parent, extensionName, defaults, title=None):
	if title is None:
		title = "Executable location"
	from chimera.widgets import DisclosureFrame
	df = DisclosureFrame(parent, text=title)
	sl = ServiceLocation(df.frame, extensionName, defaults)
	return df, sl
