from chimera.mplDialog import MPLDialog

class RamachandranPlot(MPLDialog):

	help = "ContributedSoftware/ramachandran/ramachandran.html"
	buttons = ( "Assign Residue Probabilities", "Close" )

	def __init__(self, m, assign=False):
		self.title = "Ramachandran Plot for %s" % m.name
		self.mol = m
		self.phi = []
		self.psi = []
		self.residues = []
		for r in m.residues:
			if r.phi is None or r.psi is None:
				continue
			self.phi.append(r.phi)
			self.psi.append(r.psi)
			self.residues.append(r)
		if assign:
			import contour
			contour.assignProb(m)
		self.closeHandler = None
		self.selHandler = None
		if len(self.residues) == 0:
			from chimera import UserError
			raise UserError("Molecule %s has no phi/psi angles"
					% m.name)
		MPLDialog.__init__(self)
		self.selectedIndices = []
		ax = self.add_subplot(1,1,1)
		self.subplot = ax
		self._displayData()
		self.registerPickHandler(self.onPick)

		import chimera
		self.closeHandler = chimera.openModels.addRemoveHandler(
						self._molClosed, None)

		from chimera import triggers
		self.selHandler = triggers.addHandler("selection changed",
						self._selectionChangedCB,
						None)
		self._selectionChangedCB(None, None, None)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		from contour import ContourInfo, DefaultContour
		self.contour = DefaultContour
		names = ContourInfo.keys()
		names.sort()
		names.insert(0, "None")
		self.contourOption = Pmw.OptionMenu(parent,
						labelpos="w",
						label_text="Show region for",
						initialitem=self.contour,
						items=names,
						command=self._changeContour)
		self.contourOption.pack()
		f = Tkinter.Frame(parent)
		f.pack(fill="both", expand=True)
		MPLDialog.fillInUI(self, f)

	def _displayData(self):
		colors = ['b'] * len(self.phi)
		for n in self.selectedIndices:
			colors[n] = 'r'
		ax = self.subplot
		ax.clear()
		self._showRegion(ax)
		ax.scatter(self.phi, self.psi, c=colors, picker=True)
		ax.set_xlabel("phi")
		ax.set_xlim(-180, 180)
		ax.set_xticks(range(-180, 181, 60))
		ax.set_ylabel("psi")
		ax.set_ylim(-180, 180)
		ax.set_yticks(range(-180, 181, 60))
		ax.grid(True)
		self.draw()

	def _showRegion(self, ax):
		if self.contour == "None":
			return
		from contour import getContourInfo
		z, levels = getContourInfo(self.contour)
		import numpy
		angles = numpy.arange(-179.0, 180.0, 2.0)
		lList = [ float(l) for l in levels ]
		colors = ( (0.2, 0.8, 0.2), (0.65, 0.9, 0.65), )
		cs = ax.contour(angles, angles, z, lList, colors=colors)
		fmt = dict(zip(lList, levels))
		ax.clabel(cs, lList, colors=colors, fmt=fmt, fontsize=8,
				inline_spacing=0, use_clabeltext=True)

	def onPick(self, event):
		residues = [ self.residues[i] for i in event.ind ]
		from chimera import selection
		sel = selection.ItemizedSelection(residues)
		selection.setCurrent(sel)

	def _selectionChangedCB(self, trigger, userData, ignore):
		from chimera import selection
		residues = selection.currentResidues()
		self.selectedIndices = []
		for r in residues:
			try:
				n = self.residues.index(r)
			except ValueError:
				pass
			else:
				self.selectedIndices.append(n)
		self._displayData()

	def _changeContour(self, desc):
		if desc != self.contour:
			self.contour = desc
			self._displayData()

	def _molClosed(self, trigger, myData, closed):
		if self.mol in closed:
			self.destroy()
			self.mol = None

	def destroy(self):
		if self.selHandler:
			from chimera import triggers
			triggers.deleteHandler("selection changed",
							self.selHandler)
			self.selHandler = None
		if self.closeHandler:
			import chimera
			chimera.openModels.deleteRemoveHandler(
							self.closeHandler)
			self.closeHandler = None
		MPLDialog.destroy(self)

	def AssignResidueProbabilities(self):
		if not self.mol:
			return
		import contour
		contour.assignProb(self.mol)
		try:
			from ShowAttr import ShowAttrDialog
		except ImportError:
			# No "render by attribute", just ignore
			return
		from chimera import dialogs
		d = dialogs.display(ShowAttrDialog.name)
		d.configure(models=[ self.mol ], attrsOf="residues",
							attrName=None)
		d.refreshAttrs()
		d.configure(models=[ self.mol ], attrsOf="residues",
							attrName = "ramaProb")

def cmdLine(cmdName, args):
	args = args.strip()
	from Commands import doExtensionFunc
	parts = args.split(None, 1)
	if len(parts) > 1:
		subcmd, remainder = parts
	else:
		subcmd = args
		remainder = ""
	func = modelPanel
	if "assign".startswith(subcmd):
		func = modelAssign
		args = remainder
	if not args:
		args = "#"
	doExtensionFunc(func, args,
				specInfo=[("modelSpec", "models", "models"),])

def modelPanel(models):
	import chimera
	for m in models:
		if isinstance(m, chimera.Molecule):
			RamachandranPlot(m, False)

def modelAssign(models):
	import chimera
	for m in models:
		if not isinstance(m, chimera.Molecule):
			continue
		if chimera.nogui:
			from contour import assignProb
			assignProb(m)
		else:
			RamachandranPlot(m, True)
