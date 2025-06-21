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
from prefs import prefs, defaults, CENTROID_RADIUS

from Geometry import Geometry, GeometrySubmanager
class Centroid(Geometry):
	def __init__(self, number, name, color, radius, sameAs, center):
		Geometry.__init__(self, number)
		self.name = name
		self.radius = radius
		self.center = center
		kw = {'hidden': True}
		if sameAs:
			kw['sameAs'] = sameAs
		else:
			kw['shareXform'] = False
		if hasattr(color, 'rgba'):
			rgba = color.rgba()
		else:
			rgba = color
		from Shape.shapecmd import sphere_shape
		self.surfacePiece = sphere_shape(radius=radius, color=rgba,
			center=",".join(["%g" %c for c in center.data()]),
			modelName=self.name, **kw)
		self.model = self.surfacePiece.model
		self.model.oslIdent = lambda *args: self.name

	def __str__(self):
		return self.strLegend() + ": " + self.alignedStr()

	def alignedStr(self, nameWidth=None, idWidth=None):
		if nameWidth == None:
			nameWidth = len(self.name)
		if idWidth == None:
			idWidth = len(self.id)
		cx, cy, cz = self.center
		return "%*s: %*s (%7.3f, %7.3f, %7.3f)"  % (
			nameWidth, self.name, idWidth, self.id, cx, cy, cz)

	@property
	def atoms(self):
		return centroidManager.centroidAtoms(self)

	selectables = atoms

	def destroy(self):
		chimera.openModels.close([self.model])

	def pointDistances(self, target):
		if isinstance(target, Point):
			points = [target]
		else:
			points = target
		xformed = self.xformCenter()
		return [xformed.distance(pt) for pt in points]

	@staticmethod
	def strLegend():
		return "centroid name, ID, center"

	def xformCenter(self):
		return self.model.openState.xform.apply(self.center)

class CentroidManager(GeometrySubmanager):
	restoreOrder = 1  # Axes can depend on Centroids

	def __init__(self):
		self.centroidData = {}
		self.centroidOrdinal = 0
		from Geometry import geomManager
		geomManager.registerManager(self, Centroid)

	@property
	def centroids(self):
		centroids = self.centroidData.keys()
		return centroids
	items = centroids

	def centroidAtoms(self, centroid):
		return self.centroidData[centroid].atoms()

	def createCentroid(self, name, atoms, number=None, massWeighting=False,
				radius=defaults[CENTROID_RADIUS], color=None, legend=True):
		numbers = dict([(cntd.number, cntd) for cntd in self.centroids])
		if number == None:
			if numbers:
				number = max(numbers.keys()) + 1
			else:
				number = 1
		elif number in numbers:
			self.removeCentroids([numbers[number]])

		if color == None:
			from StructMeasure import matchStructureColor
			color = matchStructureColor(atoms)
		from StructMeasure import GeometricItems
		sourceModel, coords, weights = self._getRefInfo(GeometricItems(atoms, []),
										massWeighting=massWeighting)
		import StructMeasure
		center = StructMeasure.centroid(coords, weights=weights)
		self.centroidOrdinal += 1
		centroid = self._instantiateCentroid(number, name, self.centroidOrdinal,
			color, radius, sourceModel, atoms, center)
		if legend:
			replyobj.status(str(centroid), log=True, secondary=True)
		else:
			replyobj.status(centroid.alignedStr(), log=True, secondary=True)
		return centroid

	def removeCentroids(self, centroids):
		for centroid in centroids:
			del self.centroidData[centroid]
			centroid.destroy()
		if not self.centroidData:
			self.centroidOrdinal = 0
		from Geometry import geomManager
		geomManager.removeInterfaceItems(centroids)
	removeItems = removeCentroids

	def _instantiateCentroid(self, number, name, cmpVal, color, radius,
			sourceModel, atoms, center):
		centroid = Centroid(number, name, color, radius, sourceModel, center)
		from chimera.selection import ItemizedSelection
		sel = ItemizedSelection(selChangedCB=lambda cntrd=centroid:
				self.removeCentroids([cntrd]))
		sel.add(atoms)
		self.centroidData[centroid] = sel

		from Geometry import geomManager
		geomManager.addInterfaceItems([centroid])
		return centroid

	def _restoreSession(self, centroidData, fromGeom=False, scene=False):
		if scene:
			from Animate.Tools import getColor, idLookup
		else:
			from SimpleSession import getColor, idLookup
		maxNumber = 0
		for data, atomIDs in centroidData.items():
			try:
				version, number, name, cmpVal, radius, colorID, center, \
					display = data
			except ValueError:
				try:
					version, number, name, cmpVal, radius, colorID, \
						center = data
				except ValueError:
					number, name, cmpVal, radius, colorID, center = data
					version = 1
			atoms = [idLookup(a) for a in atomIDs]
			if version == 1:
				sourceModel = self._getSourceModel(atoms)
			else:
				from StructMeasure import GeometricItems
				sourceModel = self._getRefInfo(GeometricItems(atoms, []),
					modelOnly=True)
			if version < 3:
				colorValue = getColor(colorID)
			else:
				colorValue = colorID
			centroid = self._instantiateCentroid(number, name,
				self.centroidOrdinal + number, colorValue, radius,
				sourceModel, atoms, Point(*center))
			if version >= 4:
				centroid.model.display = display
			maxNumber = max(number, maxNumber)
		self.centroidOrdinal += maxNumber

	def _sessionData(self, scene=False):
		if scene:
			from Animate.Tools import sceneID as saveID, colorID
		else:
			from SimpleSession import sessionID as saveID, colorID
		centroidData = {}
		for centroid, sel in self.centroidData.items():
			centroidData[(
				4, # version number
				centroid.number,
				centroid.name,
				0, # used to be cmpVal
				centroid.radius,
				centroid.surfacePiece.color,
				centroid.center.data(),
				centroid.model.display
			)] = [saveID(a) for a in sel.atoms()]
		return centroidData

centroidManager = CentroidManager()

from chimera.baseDialog import ModelessDialog
class CreateCentroidDialog(ModelessDialog):
	title = "Define Centroid"
	help = "ContributedSoftware/structuremeas/structuremeas.html#define-centroid"
	provideStatus = True
	statusPosition = "above"

	def fillInUI(self, parent):
		import Pmw, Tkinter
		row = 0
		Tkinter.Label(parent, text="Create centroid for selected atoms..."
			).grid(row=row, columnspan=2)
		row += 1

		from chimera.tkoptions import StringOption, BooleanOption
		self.nameOpt = StringOption(parent, row, "Centroid name",
									"centroid", None)
		row += 1

		self.massWeightingOpt = BooleanOption(parent, row, "Mass weighting",
			False, None)
		row += 1

		self.replaceExistingOpt = BooleanOption(parent, row,
									"Replace existing centroids", False, None)
		row += 1

		from chimera.tkoptions import ColorOption, FloatOption
		self.colorOpt = ColorOption(parent, row, "Color", None, None,
			balloon="Centroid color.  If No Color, then the centroid"
			" will be colored to match the structure")
		row += 1

		self.radiusOpt = FloatOption(parent, row, "Radius",
										prefs[CENTROID_RADIUS], None)
		row += 1

	def Apply(self):
		from chimera import UserError
		if self.replaceExistingOpt.get():
			centroidManager.removeCentroids(centroidManager.centroids)
		kw = {
			'color': self.colorOpt.get(),
		}
		kw['radius'] = self.radiusOpt.get()
		prefs[CENTROID_RADIUS] = kw['radius']

		kw['massWeighting'] = self.massWeightingOpt.get()

		replyobj.info("Creating centroid\n")
		selAtoms = selection.currentAtoms()
		if len(selAtoms) < 1:
			self.enter()
			raise UserError("Need to select at least one atom")
		centroidManager.createCentroid(self.nameOpt.get().strip(),
										selAtoms, **kw)
		from Geometry import geomManager
		geomManager.showInterface()
