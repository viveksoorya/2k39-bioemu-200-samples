# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: Axes.py 41770 2018-06-26 22:24:27Z pett $

import chimera
from chimera import replyobj, selection, Point, Vector
from prefs import prefs, AXIS_RADIUS

from Geometry import Geometry, GeometrySubmanager
class Axis(Geometry):
	plural = 'axes'

	def __init__(self, number, name, color, radius,
						sameAs, center, vec, extents):
		Geometry.__init__(self, number)
		self.name = name
		self.radius = radius
		self.extents = extents
		self.center = center
		self.direction = vec
		kw = {'hidden': True}
		if sameAs:
			kw['sameAs'] = sameAs
		else:
			kw['shareXform'] = False
		if hasattr(color, 'rgba'):
			rgba = color.rgba()
		else:
			rgba = color
		from Shape.shapecmd import cylinder_shape
		defaultAxis = Vector(0.0, 0.0, 1.0)
		rotAngle = chimera.angle(defaultAxis, self.direction)
		if 0.00001 < rotAngle < 179.99999:
			rotAxis = chimera.cross(defaultAxis, self.direction)
			rotation = ",".join(["%g" % c for c in rotAxis.data()]
				) + ",%g" % rotAngle
		else:
			rotation = None
		# since extents may differ in length, need to adjust shape center...
		cyl_center = center + vec * (extents[0] + extents[1])/2.0
		self.surfacePiece = cylinder_shape(radius=radius, color=rgba,
			height=(abs(extents[0]) + abs(extents[1])),
			center=",".join(["%g" %c for c in cyl_center.data()]),
			caps=True, modelName=self.name, rotation=rotation, **kw)
		self.model = self.surfacePiece.model
		self.model.oslIdent = lambda *args: self.name

	def __str__(self):
		return self.strLegend() + ": " + self.alignedStr()

	@property
	def atoms(self):
		return axisManager.axisAtoms(self)

	def alignedStr(self, nameWidth=None, idWidth=None):
		if nameWidth == None:
			nameWidth = len(self.name)
		if idWidth == None:
			idWidth = len(self.id)
		ends = [self.direction * ext + self.center
				for ext in self.extents]
		cx, cy, cz = Point(ends)
		dx, dy, dz = self.direction
		return "%*s: %*s %6.3f (%7.3f, %7.3f, %7.3f) (%6.3f, %6.3f, %6.3f)" % (
			nameWidth, self.name, idWidth, self.id, abs(self.extents[0]
			- self.extents[1]), cx, cy, cz, dx, dy, dz)

	def destroy(self):
		chimera.openModels.close([self.model])

	def getAlignPoints(self):
		return (self.center + self.direction, self.center - self.direction)

	@property
	def length(self):
		return abs(self.extents[1] - self.extents[0])

	def pointDistances(self, target):
		if isinstance(target, Point):
			points = [target]
		else:
			points = target
		from chimera import cross, Plane
		dists = []
		minExt = min(self.extents)
		maxExt = max(self.extents)
		xfCenter = self.xformCenter()
		xfDirection = self.xformDirection()
		minPt = xfCenter + xfDirection * minExt
		maxPt = xfCenter + xfDirection * maxExt
		for pt in points:
			v = pt - xfCenter
			c1 = cross(v, xfDirection)
			if c1.length == 0.0:
				# colinear
				inPlane = pt
			else:
				plane = Plane(xfCenter, cross(c1, xfDirection))
				inPlane = plane.nearest(pt)
			ptExt = (inPlane - xfCenter) * xfDirection
			if ptExt < minExt:
				measurePt = minPt
			elif ptExt > maxExt:
				measurePt = maxPt
			else:
				measurePt = inPlane
			dists.append(pt.distance(measurePt))
		return dists

	@property
	def selectables(self):
		return axisManager.axisSelectables(self)

	@staticmethod
	def strLegend():
		return "axis name, ID, length, center, direction"

	def xformCenter(self):
		return self.model.openState.xform.apply(self.center)

	def xformDirection(self):
		return self.model.openState.xform.apply(self.direction)

	def _axisDistance(self, axis, infinite=False):
		from chimera import angle, cross, Plane
		# shortest distance between lines is perpendicular to both...
		sDir = self.xformDirection()
		aDir = axis.xformDirection()
		if angle(sDir, aDir) in [0.0, 180.0]:
			# parallel
			return self._axisEndsDist(axis)
		shortDir = cross(sDir, aDir)
		# can use analytically shortest dist only if each axis
		# penetrates the plane formed by the other axis and the
		# perpendicular
		if not infinite:
			for a1, a2 in [(axis, self), (self, axis)]:
				normal = cross(a1.xformDirection(), shortDir)
				plane = Plane(a1.xformCenter(), normal)
				d1 = plane.distance(a2.xformCenter()
					+ a2.xformDirection() * a2.extents[0])
				d2 = plane.distance(a2.xformCenter()
					+ a2.xformDirection() * a2.extents[1])
				if cmp(d1, 0.0) == cmp(d2, 0.0):
					# both ends on same side of plane
					return self._axisEndsDist(axis)
		# D is perpendicular distance to origin
		d1 = Plane(self.xformCenter(), shortDir).equation()[3]
		d2 = Plane(axis.xformCenter(), shortDir).equation()[3]
		return abs(d1 - d2)

	def _axisEndsDist(self, axis):
		return min(
			min(self.pointDistances([axis.xformCenter() +
						axis.xformDirection() * ext
						for ext in axis.extents])),
			min(axis.pointDistances([self.xformCenter() +
						self.xformDirection() * ext
						for ext in self.extents]))
		)

class AxisManager(GeometrySubmanager):
	def __init__(self):
		self.axisData = {}
		from Geometry import geomManager
		geomManager.registerManager(self, Axis)

	@property
	def axes(self):
		axes = self.axisData.keys()
		return axes
	items = axes

	def axisAtoms(self, axis):
		return self.axisData[axis].atoms()

	def axisSelectables(self, axis):
		sel = self.axisData[axis]
		return sel.vertices()

	def createAxis(self, name, atoms=[], centroids=[], plane=None,
				number=None, radius=None, color=None,
				helicalCorrection=True, massWeighting=False, legend=True):
		if plane:
			if color == None:
				color = plane.surfacePiece.color
			if radius == None:
				radius = plane.radius / 25.0
			sourceModel = plane.model
			items = plane
			pt = plane.plane.origin
			vec = plane.plane.normal
			b2 = plane.radius / 2.0
			b1 = -b2
		else:
			from StructMeasure import GeometricItems
			items = GeometricItems(atoms, centroids)
			if len(items) < 2:
				raise ValueError("Need at least 2 atoms/centroids"
					" to define axis")
			if len(items) < 3:
				helicalCorrection = False
				if radius == None:
					radius = prefs[AXIS_RADIUS]
			sourceModel, coords, weights = self._getRefInfo(items,
											massWeighting=massWeighting)
			if color == None:
				color = items.color
			axisKw = {}
			from numpy import array
			if massWeighting:
				axisKw['weights'] = array(weights)
			crds = array(coords)
			import StructMeasure
			if radius == None:
				pt, vec, b1, b2, radius = StructMeasure.axis(crds,
					findBounds=True, findRadius=True,
					iterate=helicalCorrection, **axisKw)
			else:
				pt, vec, b1, b2 = StructMeasure.axis(crds,
					findBounds=True, findRadius=False,
					iterate=helicalCorrection, **axisKw)
		numbers = dict([(a.number, a) for a in self.axes])
		if number == None:
			if numbers:
				number = max(numbers.keys()) + 1
			else:
				number = 1
		elif number in numbers:
			self.removeAxes([numbers[number]])

		axis = self._instantiateAxis(number, name, color,
				radius, sourceModel, items, pt, vec, (b1, b2))
		if legend:
			replyobj.status(str(axis), log=True, secondary=True)
		else:
			replyobj.status(axis.alignedStr(), log=True, secondary=True)
		return axis

	def removeAxes(self, axes):
		for axis in axes:
			del self.axisData[axis]
			axis.destroy()
		from Geometry import geomManager
		geomManager.removeInterfaceItems(axes)
	removeItems = removeAxes

	def _instantiateAxis(self, number, name, color, radius, sourceModel,
						items, center, vec, extents):
		axis = Axis(number, name, color, radius,
					sourceModel, center, vec, extents)
		from chimera.selection import ItemizedSelection
		sel = ItemizedSelection(selChangedCB=lambda a=axis:
				self.removeAxes([a]))
		if hasattr(items, 'selectables'):
			sel.add(items.selectables)
		else:
			sel.add(items)
		self.axisData[axis] = sel

		from Geometry import geomManager
		geomManager.addInterfaceItems([axis])
		return axis

	def _restoreSession(self, axisData, fromGeom=False, scene=False):
		if scene:
			from Animate.Tools import getColor, idLookup
		else:
			from SimpleSession import getColor, idLookup
		for i, data in enumerate(axisData.keys()):
			try:
				version, number, name, cmpVal, radius, colorID, extents, \
					center, direction, display = data
			except ValueError:
				try:
					version, number, name, cmpVal, radius, colorID, extents, \
						center, direction = data
				except ValueError:
					try:
						number, name, cmpVal, radius, colorID, extents, center,\
							direction = data
						version = 2
					except ValueError:
						number = i + 1
						name, cmpVal, radius, colorID, extents, center,\
							direction = data
						version = 1
			if version < 5:
				atomIDs = axisData[data]
				centroidIDs = []
			elif version < 7:
				atomIDs, centroidIDs = axisData[data]
				planeID = None
			else:
				atomIDs, centroidIDs, planeID = axisData[data]
			atoms = [idLookup(a) for a in atomIDs]
			from Centroids import centroidManager
			centroids = []
			for cid in centroidIDs:
				centroids.extend([c for c in centroidManager.centroids
					if c.id == cid])
			if planeID is None:
				plane = None
			else:
				from Planes import planeManager
				for p in planeManager.planes:
					if p.id == planeID:
						plane = p
						break
			from StructMeasure import GeometricItems
			if version <= 2:
				sourceModel = self._getSourceModel(atoms)
				items = GeometricItems(atoms, [])
			elif version <= 6 or plane == None:
				items = GeometricItems(atoms, centroids)
				sourceModel = self._getRefInfo(items, modelOnly=True)
			else:
				items = plane
				sourceModel = plane.model
			if version < 4:
				colorValue = getColor(colorID)
			else:
				colorValue = colorID
			axis = self._instantiateAxis(number, name, colorValue, radius,
				sourceModel, items, Point(*center), Vector(*direction), extents)
			if version >= 6:
				axis.model.display = display

	def _sessionData(self, scene=False):
		if scene:
			from Animate.Tools import sceneID as saveID, colorID
		else:
			from SimpleSession import sessionID as saveID, colorID
		axisData = {}
		from Centroids import centroidManager
		centroids = centroidManager.centroids
		from Planes import planeManager
		planes = planeManager.planes
		for axis, sel in self.axisData.items():
			atoms = set(sel.atoms())
			geomModels = [v.model for v in sel.vertices() if v not in atoms]
			centroidIDs = []
			planeID = None
			for gm in geomModels:
				for c in centroids:
					if c.model == gm:
						centroidIDs.append(c.id)
						break
				else:
					for p in planes:
						if p.model == gm:
							planeID = p.id
							break
					else:
						raise AssertionError(
							"No centroid/plane matches Axis data")
			axisData[(
				7, # version number
				axis.number,
				axis.name,
				0, # used to be cmpVal
				axis.radius,
				axis.surfacePiece.color,
				axis.extents,
				axis.center.data(),
				axis.direction.data(),
				axis.model.display
			)] = ([saveID(a) for a in atoms], centroidIDs, planeID)
		return axisData

axisManager = AxisManager()

from chimera.baseDialog import ModelessDialog
class CreateAxesDialog(ModelessDialog):
	title = "Define Axes"
	help = "ContributedSoftware/structuremeas/structuremeas.html#define-axes"
	provideStatus = True
	statusPosition = "above"

	MODE_HELICES, MODE_SELECTION, MODE_PLANE_NORMAL = range(3)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		row = 0
		Tkinter.Label(parent, text="Create axis for...").grid(
							row=row, sticky='w')
		row += 1

		self.modeVar = Tkinter.IntVar(parent)
		self.modeVar.set(self.MODE_HELICES)
		f = Tkinter.Frame(parent)
		f.grid(row=row, sticky='nsew')
		Tkinter.Radiobutton(f, text="Each helix in:",
				command=self._helixCB, variable=self.modeVar,
				value=self.MODE_HELICES).grid(row=0, column=0)
		from chimera.widgets import MoleculeScrolledListBox
		self.molList = MoleculeScrolledListBox(f,
						listbox_selectmode='extended')
		self.molList.grid(row=0, column=1, sticky="nsew")
		parent.rowconfigure(1, weight=1)
		parent.columnconfigure(0, weight=1)
		f.rowconfigure(0, weight=1)
		f.columnconfigure(1, weight=1)
		row += 1

		f = Tkinter.Frame(parent)
		f.grid(row=row, sticky='ew')
		Tkinter.Radiobutton(f, text="Selected atoms/centroids (axis name:",
				command=self._selCB, variable=self.modeVar,
				value=self.MODE_SELECTION).grid(row=0, column=0)
		self.axisNameVar = Tkinter.StringVar(parent)
		self.axisNameVar.set("axis")
		Tkinter.Entry(f, textvariable=self.axisNameVar, width=10
				).grid(row=0, column=1)
		Tkinter.Label(f, text=")").grid(row=0, column=2)
		row += 1

		f = Tkinter.Frame(parent)
		f.grid(row=row, sticky='ew')
		Tkinter.Radiobutton(f, text="Plane normals:",
				command=self._planeNormalCB, variable=self.modeVar,
				value=self.MODE_PLANE_NORMAL).grid(row=0, column=0)
		row += 1

		parent.columnconfigure(1, pad=10)
		self.paramGroup = paramGroup = Pmw.Group(parent, tag_text="Axis Parameters")
		paramGroup.grid(row=0, column=1, rowspan=row)
		paramFrame = paramGroup.interior()
		prow = 0

		butFrame = Tkinter.Frame(paramFrame)
		butFrame.grid(row=prow, column=0, columnspan=3)
		prow += 1

		self.massWeighting = Tkinter.IntVar(parent)
		self.massWeighting.set(False)
		self._mwButton = Tkinter.Checkbutton(butFrame,
				command=self._mwCB, text="Mass weighting",
				variable=self.massWeighting)
		self._mwButton.grid(row=0, column=0, sticky='w')
		self._mwButton.grid_remove()

		self.helixCorrection = Tkinter.IntVar(parent)
		self.helixCorrection.set(True)
		Tkinter.Checkbutton(butFrame, text="Use helical correction",
			command=self._hcCB, variable=self.helixCorrection).grid(
			row=1, column=0, sticky='w')

		self.replaceExisting = Tkinter.IntVar(parent)
		self.replaceExisting.set(True)
		Tkinter.Checkbutton(butFrame, text="Replace existing axes",
				variable=self.replaceExisting).grid(
				row=2, column=0, sticky='w')

		f = Tkinter.Frame(paramFrame)
		f.grid(row=prow, column=0, columnspan=3)
		prow += 1
		from chimera.tkoptions import ColorOption, FloatOption
		self.colorOpt = ColorOption(f, prow, "Color", None,
			None, balloon="Axis color.  If No Color, then the axis"
			" will be colored to match the structure")

		Tkinter.Label(paramFrame, text="Radius:").grid(
						row=prow, column=0, rowspan=2)
		self.fixedRadiusVar = Tkinter.IntVar(parent)
		self.fixedRadiusVar.set(False)
		Tkinter.Radiobutton(paramFrame, variable=self.fixedRadiusVar,
			padx=0, value=False).grid(row=prow, column=1)
		Tkinter.Label(paramFrame, text="average axis-atom distance"
					).grid(row=prow, column=2, sticky='w')
		Tkinter.Radiobutton(paramFrame, variable=self.fixedRadiusVar,
			padx=0, value=True).grid(row=prow+1, column=1)
		f = Tkinter.Frame(paramFrame)
		f.grid(row=prow+1, column=2, sticky='w')
		self.radiusOpt = FloatOption(f, 0, "angstroms",
					prefs[AXIS_RADIUS], None, min=0.01)

		from Planes import planeManager
		self.planeList = Pmw.ScrolledListBox(parent, labelpos='nw',
			label_text="Planes", listbox_selectmode="extended",
			items=[p.id for p in planeManager.planes])
		if len(planeManager.planes) == 1:
			self.planeList.setvalue(planeManager.planes[0].id)
		self.planeList.grid(row=0, column=1, rowspan=row, sticky='ns')
		self.planeList.grid_remove()

	def Apply(self):
		from chimera import UserError
		from Geometry import geomManager
		if self.modeVar.get() == self.MODE_PLANE_NORMAL:
			planeIDs = self.planeList.getvalue()
			if not planeIDs:
				raise UserError("No plane selected in list")
			for planeID in planeIDs:
				from Planes import planeManager
				for plane in planeManager.planes:
					if plane.id == planeID:
						break
				axisManager.createAxis(planeID + " normal", plane=plane)
			geomManager.showInterface()
			return
		if self.replaceExisting.get():
			axisManager.removeAxes(axisManager.axes)
		kw = {}
		kw['color'] = self.colorOpt.get()
		if self.fixedRadiusVar.get():
			kw['radius'] = prefs[AXIS_RADIUS] = self.radiusOpt.get()
		kw['massWeighting'] = self.massWeighting.get() \
				and self.modeVar.get() == self.MODE_SELECTION
		kw['helicalCorrection'] = self.helixCorrection.get() \
				and not kw['massWeighting']
		if kw['helicalCorrection']:
			replyobj.info("Creating axes with helical correction\n")
		elif kw['massWeighting']:
			replyobj.info("Creating axes with mass weighting\n")
		else:
			replyobj.info("Creating axes\n")
		if self.modeVar.get() == self.MODE_HELICES:
			mols = self.molList.getvalue()
			if not mols:
				self.enter()
				raise UserError("No molecules chosen")
			for m in mols:
				createHelices(m, **kw)
		else:
			selAtoms = selection.currentAtoms()
			from Centroids import Centroid
			selCentroids = [item for item in geomManager.selectedItems
				if isinstance(item, Centroid)]
			if len(selAtoms) + len(selCentroids) < 2:
				self.enter()
				raise UserError("Need to select at least two"
						" atoms/centroids to define an axis")
			axisManager.createAxis(self.axisNameVar.get().strip(),
						atoms=selAtoms, centroids=selCentroids, **kw)
		geomManager.showInterface()

	def addItems(self, items):
		from Planes import Plane, planeManager
		if [p for p in items if isinstance(p, Plane)]:
			self.planeList.setlist([p.id for p in planeManager.planes])
			if len(planeManager.planes) == 1:
				self.planeList.setvalue(planeManager.planes[0].id)

	removeItems = addItems

	def _helixCB(self):
		self._mwButton.grid_remove()
		self.helixCorrection.set(True)
		self.planeList.grid_remove()
		self.paramGroup.grid()

	def _hcCB(self):
		if self.helixCorrection.get() and self.massWeighting.get():
			self.massWeighting.set(False)

	def _mwCB(self):
		if self.massWeighting.get() and self.helixCorrection.get():
			self.helixCorrection.set(False)

	def _planeNormalCB(self):
		self.paramGroup.grid_remove()
		self.planeList.grid()

	def _selCB(self):
		self._mwButton.grid()
		self.helixCorrection.set(False)
		self.planeList.grid_remove()
		self.paramGroup.grid()

def createHelices(m, **kw):
	from chimera.specifier import evalSpec
	sel = evalSpec(":/isHelix & backbone.minimal", models=[m])
	residues = sel.residues()
	if not residues:
		return []
	from chimera.misc import oslCmp
	residues.sort(lambda r1, r2: oslCmp(r1.oslIdent(), r2.oslIdent()))
	from chimera import bondsBetween
	from chimera.selection import INTERSECT, ItemizedSelection
	if 'legend' not in kw:
		kw['legend'] = False
		replyobj.status(Axis.strLegend(), log=True, secondary=True)
	created = 0
	curHelix = []
	axes = []
	from Geometry import geomManager
	geomManager.suspendUpdates()
	while residues:
		if not curHelix:
			r = residues.pop(0)
			curHelix.append(r)
			helixNum = r.ssId
			continue
		if helixNum > -1:
			if helixNum == residues[0].ssId:
				curHelix.append(residues.pop(0))
				continue
		elif bondsBetween(curHelix[-1], residues[0], True):
			curHelix.append(residues.pop(0))
			continue
		resSel = ItemizedSelection()
		resSel.add(curHelix)
		resSel.merge(INTERSECT, sel)
		atoms = resSel.atoms()
		if helixNum < 0:
			created += 1
			helixNum = created
		hname = "%s H%d" % (m.name, helixNum)
		axes.append(axisManager.createAxis(hname, atoms, **kw))
		curHelix = []
	if curHelix:
		resSel = ItemizedSelection()
		resSel.add(curHelix)
		resSel.merge(INTERSECT, sel)
		atoms = resSel.atoms()
		if helixNum < 0:
			created += 1
			helixNum = created
		hname = "%s H%d" % (m.name, helixNum)
		axes.append(axisManager.createAxis(hname, atoms, **kw))
	geomManager.enableUpdates()
	return axes
