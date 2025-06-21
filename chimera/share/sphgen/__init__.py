_needModelPanelButton = True

#
# Read sphgen output file into "molecule"
#
def openSphgen(path):
	"Open sphgen output file and construct a molecular model"

	try:
		with open(path) as f:
			header, colorTable, clusterTable = _parseSphgen(f)
	except IOError, e:
		from chimera import UserError
		raise UserError("cannot open file \"%s\": %s" % (path, str(e)))
	mlist = _makeModels(path, header, colorTable, clusterTable)
	import chimera
	if not chimera.nogui:
		global _needModelPanelButton
		if _needModelPanelButton:
			import ModelPanel
			ModelPanel.addButton("save sphgen", _saveSphgenCB)
			_needModelPanelButton = False
	return mlist

def _nextLine(f, lineno, eofOkay):
	line = f.readline()
	if not line and not eofOkay:
		raise IOError("unexpected EOF")
	return (line, lineno + 1)

def _syntaxError(lineno):
	raise IOError("syntax error, line %d" % lineno)

def _parseSphgen(f):
	state = "header"
	colorTable = dict()
	clusterTable = dict()
	line, lineno = _nextLine(f, 0, False)
	while line:
		if state == "sphere":
			s = _getSphere(line, lineno)
			clusterTable[clusterIndex].append(s)
			numSpheres -= 1
			if numSpheres > 0:
				line, lineno = _nextLine(f, lineno, False)
			else:
				line, lineno = _nextLine(f, lineno, True)
				state = "cluster"
		elif state == "cluster":
			clusterIndex, numSpheres = _getCluster(line, lineno)
			clusterTable[clusterIndex] = list()
			line, lineno = _nextLine(f, lineno, False)
			state = "sphere"
		elif state == "color":
			if line.startswith("color"):
				name, index = _getColor(line, lineno)
				colorTable[index] = name
				line, lineno = _nextLine(f, lineno, False)
			elif line.startswith("cluster"):
				state = "cluster"
			else:
				_syntaxError(lineno)
		elif state == "header":
			if line.strip() != "DOCK 3.5 receptor_spheres":
				from chimera import replyobj
				replyobj.message("non-standard sph header\n")
			if line.startswith("color"):
				header = None
				state = "color"
			elif line.startswith("cluster"):
				header = None
				state = "cluster"
			else:
				header = line
				line, lineno = _nextLine(f, lineno, False)
				state = "color"
	return header, colorTable, clusterTable

def _getSphere(line, lineno):
	ni = int(line[0:5])
	x = float(line[5:15])
	y = float(line[15:25])
	z = float(line[25:35])
	r = float(line[35:43])
	nj = int(line[43:48])
	try:
		clusterIndex = int(line[48:50])
	except (ValueError, IndexError):
		clusterIndex = 0
	try:
		colorIndex = int(line[50:53])
	except (ValueError, IndexError):
		colorIndex = 0
	return (ni, x, y, z, r, nj, clusterIndex, colorIndex)

import re
_ClusterPat = re.compile("cluster +(?P<index>\\d+)   number of spheres "
				"in cluster +(?P<count>\\d+)")
def _getCluster(line, lineno):
	m = _ClusterPat.match(line)
	if m is None:
		_syntaxError(lineno)
	return (int(m.group("index")), int(m.group("count")))

def _getColor(line, lineno):
	fields = line.strip().split()
	if fields[0] != "color":
		_syntaxError(lineno)
	return fields[1], int(fields[2])

def _makeModels(path, header, colorTable, clusterTable):
	import os.path
	modelName = os.path.basename(path)

	from chimera import MaterialColor
	colors = dict()
	for colorIndex, colorName in colorTable.iteritems():
		c = MaterialColor.lookup(colorName)
		if c is None:
			c = MaterialColor(0.5, 0.8, 1.0, 0.5)
			c.save(colorName)
		colors[colorIndex] = c

	# Generate unique per-model colors
	from chimera import openModels
	used = [ m.color for m in openModels.list() if m.color is not None ]
	from chimera import viewer
	if viewer.background is None:
		from chimera.colorTable import getColorByName
		bgColor = getColorByName("black")
	else:
		bgColor = viewer.background
	used.append(bgColor)
	used.append(viewer.highlightColor)
	rgbs = [ c.rgba()[:3] for c in used if c ]

	# Convert each cluster into a residue, and each
	# sphere into an atom
	models = list()
	from chimera import Molecule, Element, Atom, Coord
	LP = Element("LonePair")
	from CGLtk.color import distinguishFrom
	for clusterIndex, sphereList in clusterTable.iteritems():
		# Each cluster is a submodel
		m = Molecule()
		models.append(m)
		# Have to use noprefs=True because we want all
		# our spheres to remain spheres, but now we have
		# to manually set our colors
		m.noprefs = True
		m.isRealMolecule = False
		m.name = "Cluster %d - %s" % (clusterIndex, modelName)
		m.display = clusterIndex != 0
		# Cache color table so colors are retained even if they
		# are not used
		m.sphgenHeader = header
		m.sphgenColorTable = colorTable
		m.sphgenColors = colors
		m.sphgenCluster = clusterIndex
		rgb = distinguishFrom(rgbs, seed=14, numCandidates=7)
		m.color = MaterialColor(*rgb)
		rgbs.append(rgb)

		residue = m.newResidue("CLU", " ", clusterIndex, '')
		print "Cluster %d - %d spheres" % (clusterIndex, len(sphereList))
		for s in sphereList:
			ni, x, y, z, r, nj, ci, coi = s
			atom = m.newAtom("SPH", LP)
			atom.setCoord(Coord(x, y, z))
			atom.color = colors.get(coi, None)
			atom.radius = r
			atom.drawMode = Atom.Sphere
			atom.sphgenNi = ni
			atom.sphgenNj = nj
			atom.sphgenClusterIndex = ci
			atom.sphgenColorIndex = coi
			residue.addAtom(atom)

	return models

#
# Generate sphgen output file from molecule
#
_Header = "DOCK 3.5 receptor_spheres\n"
_CFmt = "cluster %5d   number of spheres in cluster %5d"
_SFmt = "%5d%10.5f%10.5f%10.5f%8.3f%5d%2d%3d"

def writeSphgen(mList, xform, f, displayedOnly=False, selectedOnly=False):
	if selectedOnly:
		from chimera import selection
		selectedSet = set(selection.currentAtoms())
	else:
		selectedSet = None

	header = getattr(mList[0], "sphgenHeader", _Header)
	if header:
		f.write(header)
	colorTable = dict()
	cluster0 = None
	for m in mList:
		try:
			colorTable.update(m.sphgenColorTable)
		except AttributeError:
			pass
		try:
			if m.sphgenCluster == 0:
				cluster0 = m
		except AttributeError:
			pass
	for colorIndex, colorName in colorTable.iteritems():
		print >> f, "color %s %d" % (colorName, colorIndex)
	for m in mList:
		if m is not cluster0:
			_writeSphgenMol(m, xform, f, displayedOnly, selectedSet)
	if cluster0:
		_writeSphgenMol(cluster0, xform, f, displayedOnly, selectedSet)

def _writeSphgenMol(m, xform, f, displayedOnly, selectedSet):
	if displayedOnly and not m.display:
		return
	for r in m.residues:
		keep = [ a for a in r.atoms
				if ((not selectedSet or a in selectedSet) and 
					(not displayedOnly or a.display)) ]
		if not keep:
			continue
		print >> f, _CFmt % (r.id.position, len(keep))
		for a in keep:
			ni = getattr(a, "sphgenNi", 0)
			nj = getattr(a, "sphgenNj", 0)
			cl = getattr(a, "sphgenClusterIndex", 0)
			co = getattr(a, "sphgenColorIndex", 0)
			r = a.radius
			c = xform.apply(a.coord())
			print >> f, _SFmt % (ni, c.x, c.y, c.z, r, nj, cl, co)

#
# Callback for ModelPanel button
#
def _saveSphgenCB(models):
	from chimera import dialogs
	dialogs.display(WriteSphgenDialog.name).configure(models, selOnly=False)


from OpenSave import SaveModeless
class WriteSphgenDialog(SaveModeless):
	keepShown = SaveModeless.default
	help = "UsersGuide/modelpanel.html#savesph"
	name = "write sphgen"
	fileformat = "sph"
	filters=[("Sphgen spheres", "*.sph", ".sph")]

	def __init__(self):
		SaveModeless.__init__(self, clientPos='s', clientSticky='ewns',
			filters=self.filters)
		from chimera import openModels
		openModels.addAddHandler(self._modelsChange, None),
		openModels.addRemoveHandler(self._modelsChange, None)
		self._modelsChange()

	def configure(self, models=None, refreshList=True, selOnly=None):
		if models is not None:
			if len(models) > 1:
				name = "Multiple Models "
			elif models:
				name = models[0].name + " "
			else:
				name = ""
			self._toplevel.title("Save %sas %s File" %
							(name, self.fileformat))
			if refreshList:
				self.modelList.setvalue(models)
		if selOnly is not None:
			self.selOnlyVar.set(selOnly)

	def fillInUI(self, parent):
		SaveModeless.fillInUI(self, parent)
		row = 0

		from chimera.widgets import ModelScrolledListBox, ModelOptionMenu
		self.modelList = ModelScrolledListBox(self.clientArea,
			labelpos='w', label_text="Save models:",
			listbox_selectmode='extended',
			filtFunc=lambda m: hasattr(m, 'sphgenHeader'),
			selectioncommand=lambda: self.configure(
			self.modelList.getvalue(), refreshList=False))
		self.modelList.grid(row=row, column=0, sticky='nsew')
		self.clientArea.rowconfigure(row, weight=1)
		self.clientArea.columnconfigure(0, weight=1)
		row += 1

		import Tkinter, Pmw
		self.dispOnlyVar = Tkinter.IntVar(parent)
		self.dispOnlyVar.set(False)
		Tkinter.Checkbutton(self.clientArea, variable=self.dispOnlyVar,
			text="Save displayed atoms only").grid(row=row,
			column=0, sticky='w')
		row += 1

		self.selOnlyVar = Tkinter.IntVar(parent)
		self.selOnlyVar.set(False)
		Tkinter.Checkbutton(self.clientArea, variable=self.selOnlyVar,
			text="Save selected atoms only").grid(row=row,
			column=0, sticky='w')
		row += 1

		self.saveRelativeVar = Tkinter.IntVar(parent)
		self.saveRelativeVar.set(False)
		self.relativeFrame = f = Tkinter.Frame(self.clientArea)
		Tkinter.Checkbutton(f, variable=self.saveRelativeVar,
			text="Save relative to model:"
			).grid(row=0, column=0, sticky='e')
		self.relModelMenu = ModelOptionMenu(f)
		self.relModelMenu.grid(row=0, column=1, sticky='w')
		self.saveUntransformedVar = Tkinter.IntVar(parent)
		self.saveUntransformedVar.set(True)
		self.untransformedButton = Tkinter.Checkbutton(self.clientArea,
					variable=self.saveUntransformedVar,
					text="Use untransformed coordinates")
		self._rfRow = row
		row += 1

		# not always shown; remember row number
		self._fsRow = row
		row += 1

	def Apply(self):
		from chimera import replyobj
		paths = self.getPaths()
		if not paths:
			replyobj.error('No save location chosen.\n')
			return
		path = paths[0]
		models = self.modelList.getvalue()
		if not models:
			replyobj.error("No models chosen to save.\n")
			return
		from chimera import openModels
		if len(openModels.listIds()) > 1:
			if self.saveRelativeVar.get():
				relModel = self.relModelMenu.getvalue()
			else:
				relModel = None
		else:
			if self.saveUntransformedVar.get():
				relModel = models[0]
			else:
				relModel = None

		import os
		# path will be encoded if the OS doesn't support Unicode
		# file names, so decode before printing
		if os.path.supports_unicode_filenames:
			printablePath = path
		else:
			printablePath = path.decode('utf8')
		import Midas
		replyobj.status("Writing %s to %s" %
						(models[0].name, printablePath))
		Midas.write(models, relModel, path,
				dispOnly=self.dispOnlyVar.get(),
				selOnly=self.selOnlyVar.get(),
				format=self.fileformat)
		replyobj.status("Wrote %s to %s" %
						(models[0].name, printablePath))

	def _modelsChange(self, *args):
		# can't query listbox, since it hangs off of same trigger
		from chimera import openModels
		if len(openModels.listIds()) > 1:
			self.untransformedButton.grid_forget()
			self.relativeFrame.grid(row=self._rfRow,
						column=0, sticky='w')
		else:
			self.relativeFrame.grid_forget()
			self.untransformedButton.grid(row=self._rfRow,
						column=0, sticky='w')

from chimera import dialogs
dialogs.register(WriteSphgenDialog.name, WriteSphgenDialog)
