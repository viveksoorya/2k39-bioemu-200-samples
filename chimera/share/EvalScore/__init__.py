# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

def openScores(path):
	# Expecting file content with comment lines that start with
	# '#' and data lines of
	#   reference/solution<TAB>score1<TAB>score2
	errorCount = 0
	vList = list()
	from chimera import replyobj
	with open(path) as f:
		for line in f:
			line = line.strip()
			if line[0] == '#':
				continue
			values = line.split('\t')
			try:
				if len(values) != 3:
					raise ValueError("expected 3 values and got %d" %
								len(values))
				reference, solution = values[0].split('/')
				score1 = float(values[1])
				score2 = float(values[2])
			except ValueError, e:
				errorCount += 1
				replyobj.error("%s: %s\n" % (e, line))
			else:
				vList.append((score1, score2,
							reference, solution))
	if errorCount:
		from chimera import UserError
		raise UserError("%s: %d errors found\n" % (path, errorCount))
	else:
		import os.path
		EvalScoreDialog(os.path.dirname(path), vList)
		from chimera import runCommand
		runCommand("set bg_color dim gray")

from chimera.mplDialog import MPLDialog
class EvalScoreDialog(MPLDialog):

	title = "Evaluate structure scores"
	help = "UsersGuide/evalscore.html"

	def __init__(self, dirPath, values, **kw):
		self.dirPath = dirPath
		self.values = values
		self.shown = list()
		self.currentReference = None
		self.currentSolution = None
		self.selected = None
		MPLDialog.__init__(self, **kw)
		import chimera
		self._closeSesHandler = chimera.triggers.addHandler(
						chimera.CLOSE_SESSION,
						self.destroy, None)

	def destroy(self, *args):
		# Delete handlers for session closing
		if self._closeSesHandler:
			import chimera
			chimera.triggers.deleteHandler(chimera.CLOSE_SESSION,
							self._closeSesHandler)
			self._closeSesHandler = None
		# Destroy dialog
		MPLDialog.destroy(self)

	def fillInUI(self, parent):
		MPLDialog.fillInUI(self, parent)
		# matplotlib picker seems a bit off so we do our own picking
		#self.registerPickHandler(self.onPick)
		self.mpl_connect("button_release_event", self.onRelease)
		self.ax = self.add_subplot(1, 1, 1)
		self.redraw()

	def redraw(self, keepBounds=False):
		values = self.shown + self.values
		x = [ v[0] for v in values ]
		y = [ v[1] for v in values ]
		c = len(self.shown) * ['b'] + len(self.values) * ['r']
		if keepBounds:
			xbound = self.ax.get_xbound()
			ybound = self.ax.get_ybound()
		self.ax.clear()
		self.ax.scatter(x, y, c=c, picker=True)
		self.ax.set_xlabel("score 1")
		self.ax.set_ylabel("score 2")
		if self.selected is not None:
			v = values[self.selected]
			label = "%s, %s\n%g, %g" % (v[2], v[3], v[0], v[1])
			self.ax.annotate(label,
					(x[self.selected], y[self.selected]),
					xytext=(0.02, 1.02),
					textcoords="axes fraction",
					arrowprops=dict(
					  arrowstyle="wedge,tail_width=0.7",
					  fc="0.6", ec="none",
					  connectionstyle="arc3,rad=-0.3",
					))
		self.ax.grid(True)
		if keepBounds:
			self.ax.set_xbound(*xbound)
			self.ax.set_ybound(*ybound)
		self.draw()

	def onPick(self, event):
		self.selected = event.ind[-1]
		if self.selected < len(self.shown):
			v = self.shown[self.selected]
		else:
			v = self.values.pop(self.selected - len(self.shown))
			self.shown.append(v)
			self.selected = len(self.shown) - 1
		self._showPick(v)

	def _showPick(self, v):
		self.openReference(v[2])
		self.openSolution(v[3])
		r = self.currentReference and self.currentReference()
		s = self.currentSolution and self.currentSolution()
		if r and s:
			from chimera import runCommand
			runCommand("mm %s %s ssFraction false computeSS false ;"
					"move x 50 model %s; focus"
					% (str(r), str(s), str(s)))
			copyColor(r, s)
		self.redraw(keepBounds=True)

	def onRelease(self, event):
		try:
			ax = event.inaxes
		except AttributeError:
			return
		if ax != self.ax:
			return
		selected = None
		selDsq = None
		values = self.shown + self.values
		for n, v in enumerate(values):
			px, py = ax.transData.transform((v[0], v[1]))
			dx = px - event.x
			dy = py - event.y
			dsq = dx * dx + dy * dy
			if dsq > 3.5 ** 2:	# allow some slop in picking
				continue
			if selDsq is None or dsq < selDsq:
				selDsq = dsq
				selected = n
		if selected is None:
			return
		if selected < len(self.shown):
			v = self.shown[selected]
			self.selected = selected
		else:
			v = self.values.pop(selected - len(self.shown))
			self.shown.append(v)
			self.selected = len(self.shown) - 1
		self._showPick(v)

	def openReference(self, reference):
		from chimera import openModels
		baseId = openModels.Default
		m = self.currentReference and self.currentReference()
		if m:
			if reference == m.name:
				return
			baseId = m.id
			openModels.close([ m ])
#			p = self.pnpReference and self.pnpReference()
#			if p:
#				openModels.close([ p ])
		self.currentReference = None
#		self.pnpReference = None
		import os.path
		filename = self._getPDB(reference)
		mList = openModels.open(filename, type="PDB", baseId=baseId,
					identifyAs=reference)
		from chimera.colorTable import getColorByName
		c = getColorByName("light gray")
		for m in mList:
			m.color = c
			orient(m)
			ssColor(m)
		import weakref
		self.currentReference = weakref.ref(mList[0], self._refCB)
#		mList[0].display = False
#		from PipesAndPlanks import makePandP
#		self.pnpReference = weakref.ref(makePandP(mList[0]), self._refCB)

	def _getPDB(self, name):
		import os.path
		filename = os.path.join(self.dirPath, name)
		if os.path.exists(filename):
			return filename
		if not filename.endswith(".pdb"):
			filename += ".pdb"
		return filename

	def openSolution(self, solution):
		from chimera import openModels
		baseId = openModels.Default
		m = self.currentSolution and self.currentSolution()
		if m:
			if solution == m.name:
				return
			baseId = m.id
			openModels.close([ m ])
#			p = self.pnpSolution and self.pnpSolution()
#			if p:
#				openModels.close([ p ])
		self.currentSolution = None
#		self.pnpSolution = None
		import os.path
		filename = self._getPDB(solution)
		mList = openModels.open(filename, type="PDB", baseId=baseId,
					identifyAs=solution)
		from chimera.colorTable import getColorByName
		c = getColorByName("light gray")
		for m in mList:
			m.color = c
			orient(m)
		import weakref
		self.currentSolution = weakref.ref(mList[0], self._refCB)
#		mList[0].display = False
#		from PipesAndPlanks import makePandP
#		self.pnpSolution = weakref.ref(makePandP(mList[0]), self._refCB)

	def _refCB(self, obj):
		if obj is self.currentReference:
			self.currentReference = None
		elif obj is self.currentSolution:
			self.currentSolution = None
		elif obj is self.pnpReference:
			self.pnpReference = None
		elif obj is self.pnpSolution:
			self.pnpSolution = None

def orient(mol):
	from chimera import openModels, Molecule, UserError, numpyArrayFromAtoms
	coords = numpyArrayFromAtoms(mol.atoms, xformed=True)
	from StructMeasure import bestLine
	centroidPt, majorVec, centroidArray, majorArray, centered, vals, vecs = \
			bestLine(coords)
	sortableVecs = zip(vals, vecs)
	sortableVecs.sort()
	sortableVecs.reverse()

	from chimera import Xform, Point, cross, angle, Vector
	openState = mol.openState
	toOrigin = Point() - centroidPt
	sv1, sv2 = sortableVecs[0][1], sortableVecs[1][1]
	v1 = Vector(*sv1)
	v2 = Vector(*sv2)
	openState.globalXform(Xform.translation(toOrigin))
	# major axis onto Y
	y_axis = Vector(0.0, 1.0, 0.0)
	delta = angle(y_axis, v1)
	if abs(delta) > 0.001 and abs(180.0 - delta) > 0.001:
		rotAxis = cross(y_axis, v1)
		rot = Xform.rotation(rotAxis, -delta)
		openState.globalXform(rot)
		rv2 = rot.apply(v2)
	else:
		rv2 = v2

	# second axis onto X
	x_axis = Vector(1.0, 0.0, 0.0)
	delta = angle(x_axis, rv2)
	if abs(delta) > 0.001 and abs(180.0 - delta) > 0.001:
		rotAxis = cross(x_axis, rv2)
		rot = Xform.rotation(rotAxis, -delta)
		openState.globalXform(rot)
	openState.globalXform(Xform.translation(-toOrigin))

colors = [ # values are (red, green, blue) in the range 0-1
	(0.0, 0.0, 1.0), # blue
	(0.0, 1.0, 1.0), # cyan
	(0.0, 1.0, 0.0), # green
	(1.0, 1.0, 0.0), # yellow
	(1.0, 0.0, 0.0)  # red
]

def ssColor(mol):
	from chimera import runCommand
	runCommand("color light gray %s" % str(mol))
	last_ss_id = None
	runs = []
	cur_run = None
	for r in mol.residues:
		if r.isHelix:
			ss_id = ('H', r.ssId)
		elif r.isStrand:
			ss_id = ('S', r.ssId)
		else:
			ss_id = None

		if last_ss_id:
			if ss_id == last_ss_id:
				cur_run.append(r)
			elif ss_id:
				runs.append(cur_run)
				cur_run = [r]
			else:
				runs.append(cur_run)
				cur_run = None
		elif ss_id:
			cur_run = [r]
		last_ss_id = ss_id
	if cur_run:
		runs.append(cur_run)

	from math import floor
	from chimera import MaterialColor
	for i, run in enumerate(runs):
		if len(runs) == 1:
			fract = 0.5
		else:
			fract = i / float(len(runs)-1)
		cfract = fract * (len(colors)-1)
		below = int(floor(cfract))
		rem = cfract - below
		if abs(rem) < 0.0001:
			rgb = colors[below]
		else:
			brgb = colors[below]
			argb = colors[below+1]
			rgb = tuple([ b*(1.0-rem) + a*rem
					for b, a in zip(brgb, argb) ])
		c = MaterialColor(*rgb)
		for r in run:
			_setColor(r, c)

def _setColor(r, c):
	r.ribbonColor = c
	r.fillColor = c
	r.labelColor = c
	for a in r.atoms:
		a.color = c
		a.labelColor = c
		a.vdwColor = c
		a.surfaceColor = c

def copyColor(r, s):
	rr = r.residues
	sr = s.residues
	ri = 0
	si = 0
	while ri < len(rr) and si < len(sr):
		rri = rr[ri]
		sri = sr[si]
		if (rri.id.position == sri.id.position
		and rri.id.insertionCode == sri.id.insertionCode):
			_setColor(sri, rri.ribbonColor)
			ri += 1
			si += 1
		elif rri.id.position < sri.id.position:
			ri += 1
		elif rri.id.position > sri.id.position:
			si += 1
		elif rri.id.insertionCode == ' ':
			ri += 1
		else:
			si += 1
