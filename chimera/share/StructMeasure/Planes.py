# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: Axes.py 28652 2009-08-24 23:21:53Z pett $

import chimera
from chimera import replyobj, selection, Point, Vector
from prefs import prefs, defaults, PLANE_THICKNESS

from Geometry import Geometry, GeometrySubmanager
class Plane(Geometry):
	def __init__(self, number, name, color, radius, thickness, sameAs, plane):
		Geometry.__init__(self, number)
		self.name = name
		self.radius = radius
		self.thickness = thickness
		self.plane = plane
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
		rotAngle = chimera.angle(defaultAxis, plane.normal)
		if 0.00001 < rotAngle < 179.99999:
			rotAxis = chimera.cross(defaultAxis, plane.normal)
			rotation = ",".join(["%g" % c for c in rotAxis.data()]) + ",%g" % rotAngle
		else:
			rotation = None
		self.surfacePiece = cylinder_shape(radius=radius, color=rgba,
			height=thickness,
			center=",".join(["%g" %c for c in plane.origin.data()]),
			caps=True, modelName=self.name, rotation=rotation, **kw)
		self.model = self.surfacePiece.model
		self.model.oslIdent = lambda *args: self.name

	def __str__(self):
		return self.strLegend() + ": " + self.alignedStr()

	def alignedStr(self, nameWidth=None, idWidth=None):
		if nameWidth == None:
			nameWidth = len(self.name)
		if idWidth == None:
			idWidth = len(self.id)
		ox, oy, oz = self.plane.origin
		nx, ny, nz = self.plane.normal
		return "%*s: %*s (%7.3f, %7.3f, %7.3f)" \
			" (%6.3f, %6.3f, %6.3f) %.3f"  % (nameWidth, self.name,
			idWidth, self.id, ox, oy, oz, nx, ny, nz, self.radius)

	@property
	def atoms(self):
		return planeManager.planeAtoms(self)

	selectables = atoms

	def destroy(self):
		chimera.openModels.close([self.model])

	def getAlignPoints(self):
		return (self.plane.origin + self.plane.normal, self.plane.origin)

	def pointDistances(self, target, signed=False):
		if isinstance(target, Point):
			points = [target]
		else:
			points = target
		measurePlane = chimera.Plane(self.xformOrigin(), self.xformNormal())
		if signed:
			return [measurePlane.distance(pt) for pt in points]
		return [abs(measurePlane.distance(pt)) for pt in points]

	@staticmethod
	def strLegend():
		return "plane name, ID, center, normal, radius"

	def xformOrigin(self):
		return self.model.openState.xform.apply(self.plane.origin)

	def xformNormal(self):
		return self.model.openState.xform.apply(self.plane.normal)

class PlaneManager(GeometrySubmanager):
	restoreOrder = 2  # Axes (normals) can depend on Planes

	def __init__(self):
		self.planeData = {}
		self.planeOrdinal = 0
		from Geometry import geomManager
		geomManager.registerManager(self, Plane)

	@property
	def planes(self):
		planes = self.planeData.keys()
		return planes
	items = planes

	def planeAtoms(self, plane):
		return self.planeData[plane].atoms()

	def createPlane(self, name, atoms, number=None, radius=None,
				radiusOffset=0.0, color=None,
				thickness=defaults[PLANE_THICKNESS], legend=True):
		if len(atoms) < 3:
			raise ValueError("Need at least 3 atoms to define plane")
		numbers = dict([(pl.number, pl) for pl in self.planes])
		if number == None:
			if numbers:
				number = max(numbers.keys()) + 1
			else:
				number = 1
		elif number in numbers:
			self.removePlanes([numbers[number]])

		if color == None:
			from StructMeasure import matchStructureColor
			color = matchStructureColor(atoms)
		from StructMeasure import GeometricItems
		sourceModel, coords, weights = self._getRefInfo(
				GeometricItems(atoms, []), massWeighting=False)
		from numpy import array
		crds = array(coords)
		import StructMeasure
		if radius == None:
			plane, proj, radius = StructMeasure.plane(crds, findBounds=True)
			radius += radiusOffset
		else:
			plane = StructMeasure.plane(crds, findBounds=False)
		self.planeOrdinal += 1
		p = self._instantiatePlane(number, name, self.planeOrdinal, color,
				radius, thickness, sourceModel, atoms, plane)
		if legend:
			replyobj.status(str(p), log=True, secondary=True)
		else:
			replyobj.status(p.alignedStr(), log=True, secondary=True)

	def removePlanes(self, planes):
		for plane in planes:
			del self.planeData[plane]
			plane.destroy()
		if not self.planeData:
			self.planeOrdinal = 0
		from Geometry import geomManager
		geomManager.removeInterfaceItems(planes)
	removeItems = removePlanes

	def _instantiatePlane(self, number, name, cmpVal, color, radius,
			thickness, sourceModel, atoms, chimeraPlane):
		plane = Plane(number, name, color, radius,
					thickness, sourceModel, chimeraPlane)
		from chimera.selection import ItemizedSelection
		sel = ItemizedSelection(selChangedCB=lambda pl=plane:
				self.removePlanes([pl]))
		sel.add(atoms)
		self.planeData[plane] = sel

		from Geometry import geomManager
		geomManager.addInterfaceItems([plane])
		return plane

	def _restoreSession(self, planeData, fromGeom=False, scene=False):
		if scene:
			from Animate.Tools import getColor, idLookup
		else:
			from SimpleSession import getColor, idLookup
		maxNumber = 0
		for data, atomIDs in planeData.items():
			try:
				version, number, name, cmpVal, radius, thickness, colorID, \
					origin, normal, display = data
			except ValueError:
				try:
					version, number, name, cmpVal, radius, thickness, colorID, \
						origin, normal = data
				except ValueError:
					number, name, cmpVal, radius, thickness, colorID, origin, \
						normal = data
					version = 1
			if version < 3:
				colorValue = getColor(colorID)
			else:
				colorValue = colorID
			atoms = [idLookup(a) for a in atomIDs]
			if version == 1:
				sourceModel = self._getSourceModel(atoms)
			else:
				from StructMeasure import GeometricItems
				sourceModel = self._getRefInfo(GeometricItems(atoms, []),
					modelOnly=True)
			plane = self._instantiatePlane(number, name, self.planeOrdinal
				+ number, colorValue, radius, thickness, sourceModel, atoms,
				chimera.Plane(Point(*origin), Vector(*normal)))
			if version >= 4:
				plane.model.display = display
			maxNumber = max(number, maxNumber)
		self.planeOrdinal += maxNumber

	def _sessionData(self, scene=False):
		if scene:
			from Animate.Tools import sceneID as saveID, colorID
		else:
			from SimpleSession import sessionID as saveID, colorID
		planeData = {}
		for plane, sel in self.planeData.items():
			planeData[(
				4, # version number
				plane.number,
				plane.name,
				0, # used to be cmpVal
				plane.radius,
				plane.thickness,
				plane.surfacePiece.color,
				plane.plane.origin.data(),
				plane.plane.normal.data(),
				plane.model.display
			)] = [saveID(a) for a in sel.atoms()]
		return planeData

planeManager = PlaneManager()

from chimera.baseDialog import ModelessDialog
class CreatePlaneDialog(ModelessDialog):
	title = "Define Plane"
	help = "ContributedSoftware/structuremeas/structuremeas.html#define-plane"
	provideStatus = True
	statusPosition = "above"

	def fillInUI(self, parent):
		import Pmw, Tkinter
		row = 0
		Tkinter.Label(parent, text="Create plane for selected atoms...").grid(
							row=row, columnspan=2)
		row += 1

		from chimera.tkoptions import StringOption, BooleanOption
		self.nameOpt = StringOption(parent, row, "Plane name", "plane", None)
		row += 1

		self.replaceExistingOpt = BooleanOption(parent, row,
										"Replace existing planes", False, None)
		row += 1

		from chimera.tkoptions import ColorOption, FloatOption
		self.colorOpt = ColorOption(parent, row, "Color", None, None,
			balloon="Plane color.  If No Color, then the plane"
			" will be colored to match the structure")
		row += 1

		self.autoRadiusOpt = BooleanOption(parent, row,
			"Set disk size to enclose atom projections", True, self._radCB)
		row += 1
		self.radRow = row
		self.radOffsetOpt = FloatOption(parent, row, "Extra radius"
			" (padding)", 0.0, None)
		self.radiusOpt = FloatOption(parent, row, "Fixed radius", 10.0, None)
		self.radiusOpt.forget()
		row += 1

		self.thicknessOpt = FloatOption(parent, row, "Disk thickness",
										prefs[PLANE_THICKNESS], None)

	def Apply(self):
		from chimera import UserError
		if self.replaceExistingOpt.get():
			planeManager.removePlanes(planeManager.planes)
		kw = {
			'color': self.colorOpt.get(),
			'thickness': self.thicknessOpt.get()
		}
		prefs[PLANE_THICKNESS] = kw['thickness']
		if self.autoRadiusOpt.get():
			kw['radiusOffset'] = self.radOffsetOpt.get()
		else:
			kw['radius'] = self.radiusOpt.get()

		replyobj.info("Creating plane\n")
		selAtoms = selection.currentAtoms()
		if len(selAtoms) < 3:
			self.enter()
			raise UserError("Need to select at least three"
					" atoms to define a plane")
		planeManager.createPlane(self.nameOpt.get().strip(), selAtoms, **kw)
		from Geometry import geomManager
		geomManager.showInterface()

	def _radCB(self, opt):
		if opt.get():
			self.radiusOpt.forget()
			self.radOffsetOpt.manage()
		else:
			self.radOffsetOpt.forget()
			self.radiusOpt.manage()
