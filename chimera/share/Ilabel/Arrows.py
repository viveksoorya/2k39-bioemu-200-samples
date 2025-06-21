# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: ColorKey.py 29408 2009-11-23 19:54:11Z gregc $

import chimera
from math import sqrt
from SimpleSession import SAVE_SESSION

class Arrow(object):
	HEAD_SOLID = "solid"
	HEAD_POINTY = "pointy"
	HEAD_BLOCKY = "blocky"
	HEAD_POINTER = "pointer"
	headStyles = [HEAD_SOLID, HEAD_POINTY, HEAD_BLOCKY, HEAD_POINTER]

	HEAD, MIDDLE, TAIL = range(3)

	STD_HALF_WIDTH = 0.01

	def __init__(self, start, end, color="white", weight=1.0, head=HEAD_SOLID,
			shown=True, ident=None):
		self._start = start
		self._end = end
		self.ident = ident
		self._shown = shown
		self._weight = weight
		self._head = head
		if isinstance(color, basestring):
			try:
				color = chimera.Color.lookup(color)
			except KeyError:
				raise chimera.UserError("No such color: '%s'" % color)
		self.color = color
		self._opacity = 1.0

	def getRestoreInfo(self):
		return (self.start, self.end), {
			'ident': self.ident,
			'shown': self.shown,
			'weight': self.weight,
			'head': self.head,
			'color': self.color
		}

	def __str__(self):
		return u"%.2f,%.2f \N{RIGHTWARDS ARROW} %.2f,%.2f" % (
			self.start[0], self.start[1], self.end[0], self.end[1])

	posString = property(__str__)

	def getColor(self):
		return self.rgba

	def setColor(self, color):
		if hasattr(color, 'rgba'):
			rgba = color.rgba()
		else:
			rgba = color
		if len(rgba) == 3:
			rgba = rgba + (1.0,)
		self.rgba = rgba
		ArrowsModel().setMajorChange()

	color = property(getColor, setColor)

	def getEnd(self):
		return self._end

	def setEnd(self, end):
		if self._end == end:
			return
		self._end = end
		ArrowsModel().setMajorChange()

	end = property(getEnd, setEnd)

	def getHead(self):
		return self._head

	def setHead(self, head):
		if head == self._head:
			return
		if head not in self.headStyles:
			raise ValueError("Arrowhead style must be one of: %s"
								% ", ".join(self.headStyles))
		self._head = head
		ArrowsModel().setMajorChange()

	head = property(getHead, setHead)

	def getOpacity(self):
		return self._opacity

	def setOpacity(self, opacity):
		if opacity == self._opacity:
			return
		self._opacity = opacity
		ArrowsModel().setMajorChange()

	opacity = property(getOpacity, setOpacity)

	def getShown(self):
		return self._shown

	def setShown(self, shown):
		if self._shown == shown:
			return
		self._shown = shown
		ArrowsModel().setMajorChange()

	shown = property(getShown, setShown)

	def getStart(self):
		return self._start

	def setStart(self, start):
		if self._start == start:
			return
		self._start = start
		ArrowsModel().setMajorChange()

	start = property(getStart, setStart)

	def getWeight(self):
		return self._weight

	def setWeight(self, weight):
		try:
			weight = float(weight)
		except ValueError:
			raise ValueError("Arrow weight must be numeric")

		if weight == self._weight:
			return
		self._weight = weight
		ArrowsModel().setMajorChange()

	weight = property(getWeight, setWeight)

	def animInterp(self, startData, where, endData):
		if startData is None:
			ekw = endData[-1]
			self.opacity = where
			self.shown = ekw["shown"] and not where == 0.0
			return
		if endData is None:
			skw = startData[-1]
			self.opacity = (1.0 - where)
			self.shown = skw["shown"] and not where == 1.0
			return
		sargs, skw = startData
		eargs, ekw = endData
		self.shown = skw["shown"] or ekw["shown"]
		if not self.shown:
			return
		sopacity = eopacity = 1.0
		if not skw["shown"]:
			sopacity = 0.0
		if not ekw["shown"]:
			eopacity = 0.0
		self.opacity = sopacity + where * (eopacity - sopacity)
		sstart, send = sargs
		estart, eend = eargs
		self.start = tuple([sstart[i] + where * (estart[i] - sstart[i])
				for i in range(2)])
		self.end = tuple([send[i] + where * (eend[i] - send[i])
				for i in range(2)])
		if where < 0.5:
			self.head = skw["head"]
		else:
			self.head = ekw["head"]
		if where < 0.5:
			self.weight = skw["weight"]
		else:
			self.weight = ekw["weight"]

	def triangleStrips(self, width, height):
		start, end = self.start, self.end
		sx, sy = start[0] * width, start[1] * height
		ex, ey = end[0] * width, end[1] * height
		scaleFactor = min(width, height)
		v = (ex - sx, ey - sy)
		arrowLen2 = v[0] * v[0] + v[1] * v[1]
		arrowLen = sqrt(arrowLen2)
		nv = (v[0]/arrowLen, v[1]/arrowLen)
		perpv = (nv[1], -nv[0])

		# half base
		halfWidth = scaleFactor * self.STD_HALF_WIDTH * self.weight
		ext1, ext2 = perpv[0] * halfWidth, perpv[1] * halfWidth
		base1, base2 = (sx + ext1, sy + ext2), (sx - ext1, sy - ext2)

		# inside arrowhead
		x1, y1 = base1
		arrowHeadWidth = 4 * halfWidth
		cutBack = arrowLen - 2 * halfWidth
		extx, exty = nv[0] * cutBack, nv[1] * cutBack
		x2, y2 = base2
		inside1, inside2 = (x1 + extx, y1 + exty), (x2 + extx, y2 + exty)

		# arrowhead edge
		backLen = arrowLen - arrowHeadWidth
		ext1, ext2 = perpv[0] * arrowHeadWidth, perpv[1] * arrowHeadWidth
		base = sx + nv[0] * backLen, sy + nv[1] * backLen
		edge1, edge2 = (base[0] + ext1, base[1] + ext2), (base[0] - ext1, base[1] - ext2)

		# tip
		tip = (ex, ey)

		# avoid overlapping triangles for "solid" arrowhead
		proj = nv[0] * (edge1[0] - base1[0]) + nv[1] * (edge1[1] - base1[1])
		solidInside1 = (base1[0] + proj * nv[0], base1[1] + proj * nv[1])
		solidInside2 = (base2[0] + proj * nv[0], base2[1] + proj * nv[1])

		# clockwise vs. anti-clockwise order matters
		if self.head == self.HEAD_SOLID:
			return [[solidInside1, solidInside2, base1, base2],
					[tip, edge2, edge1]]
		elif self.head == self.HEAD_POINTY:
			return [[edge1, tip, inside1, inside2, base1, base2],
					[tip, edge2, inside2]]
		elif self.head == self.HEAD_POINTER:
			return [[inside1, inside2, base1, base2],
					[tip, inside2, inside1]]
		# HEAD_BLOCKY
		# avoid triangle overlaps so that fading looks good...
		root2 = sqrt(2.0)
		flangeWidth = 1.5 * halfWidth
		fwRoot2 = flangeWidth / root2
		v1 = (fwRoot2 * (-nv[0] - perpv[0]), fwRoot2 * (-nv[1] - perpv[1]))
		v2 = (fwRoot2 * (perpv[0] - nv[0]), fwRoot2 * (perpv[1] - nv[1]))
		innerTip = (tip[0] - 2 * fwRoot2 * nv[0], tip[1] - 2 * fwRoot2 * nv[1])
		flange1 = edge1[0] + v1[0], edge1[1] + v1[1]
		flange2 = edge2[0] + v2[0], edge2[1] + v2[1]
		innerFlange1 = (innerTip[0] + halfWidth * (-nv[0] + perpv[0]),
						innerTip[1] + halfWidth * (-nv[1] + perpv[1]))
		innerFlange2 = (innerTip[0] + halfWidth * (-nv[0] - perpv[0]),
						innerTip[1] + halfWidth * (-nv[1] - perpv[1]))
		return [[innerTip, innerFlange2, innerFlange1, base2, base1],
				[innerTip, flange1, tip, edge1],
				[innerTip, tip, flange2, edge2]]

	def within(self, pos, slop):
		def dot(a, b):
			return a[0]*b[0] + a[1]*b[1]
		def distSq(a, b):
			dx = a[0] - b[0]
			dy = a[1] - b[1]
			return dx*dx + dy*dy
		def diff(x, y):
			return (x[0]-y[0], x[1]-y[1])
		# solve for nearest point on arrow in parameterized form
		v = diff(self.end, self.start)
		if v == (0, 0):
			if distSq(pos, self.start) < slop * slop:
				return True, self.HEAD, diff(self.end, pos)
			return False, None, None
		near = dot(v, diff(pos, self.start)) / dot(v, v)
		if near > 1:
			if distSq(pos, self.end) < slop * slop:
				return True, self.HEAD, diff(self.end, pos)
			return False, None, None
		if near < 0:
			if distSq(pos, self.start) < slop * slop:
				return True, self.TAIL, diff(self.start, pos)
			return False, None, None
		nearPt = (self.start[0] + near*v[0], self.start[1] + near*v[1])
		testWidth = self.weight * self.STD_HALF_WIDTH + slop
		if distSq(pos, nearPt) < testWidth * testWidth:
			if near <= 0.25:
				return True, self.TAIL, diff(self.start, pos)
			if near >= 0.75:
				return True, self.HEAD, diff(self.start, pos)
			return True, self.MIDDLE, diff((self.start[0]+self.end[0]/2.0,
										self.start[1]+self.end[1]/2.0), pos)
		return False, None, None

from PythonModel.PythonModel import PythonModel
class _ArrowsModel(PythonModel):
	def __init__(self):
		PythonModel.__init__(self)
		self.arrows = []
		chimera.openModels.add([self], baseId=-1, hidden=True)
		self._handlerIDs = {}
		for trigName, handler in [(SAVE_SESSION, self._saveSession),
				(chimera.SCENE_TOOL_SAVE, self._saveScene)]:
			self._handlerIDs[trigName] = chimera.triggers.addHandler(trigName, handler, None)

	def addArrow(self, *args, **kw):
		if kw.get('ident', None) is None:
			idents = set([a.ident for a in self.arrows])
			num = 1
			while ("anon_arrow_%d" % num) in idents:
				num += 1
			from copy import copy
			kw = copy(kw)
			kw['ident'] = "anon_arrow_%d" % num
		self.arrows.append(Arrow(*args, **kw))
		self.setMajorChange()
		return self.arrows[-1]

	def removeArrow(self, arrow):
		self.arrows.remove(arrow)
		self.setMajorChange()

	def getRestoreInfo(self):
		return {'arrows': [a.getRestoreInfo() for a in self.arrows]}

	def restore(self, info):
		self.arrows = []
		if info is not None:
			for args, kw in info['arrows']:
				if isinstance(kw.get('weight', 1.0), basestring):
					kw['weight'] = {
						'thin': 0.5,
						'medium': 1.0,
						'thick': 1.5
					}.get(kw['weight'], 1.0)
				self.addArrow(*args, **kw)
		self.setMajorChange()

	def destroy(self, *args):
		for trigName, handlerID in self._handlerIDs.items():
			chimera.triggers.deleteHandler(trigName, handlerID)
		PythonModel.destroy(self, True)
		global _arrowsModel
		_arrowsModel = None

	def pickArrow(self, pos, w, h):
		for arrow in self.arrows:
			if not arrow.shown:
				continue
			within, part, delta = arrow.within(pos, 0.005)
			if within:
				break
		else:
			arrow = None
			delta = (0, 0)
			part = Arrow.HEAD
		return arrow, part, delta

	def computeBounds(self, sphere, bbox):
		return False

	def validXform(self):
		return False

	def draw(self, lens, viewer, passType):
		if passType != chimera.LensViewer.Overlay2d:
			return
		self._draw("opengl", viewer)

	def _draw(self, mode, viewer):
		w, h = viewer.windowSize

		openGL = mode == "opengl"
		if openGL:
			from OpenGL import GL
		else:
			# X3D mostly cribbed from ILabelModel's x3dWrite
			prefix = self.x3dPrefix
			output = self.x3dOutput
			TRANSCALE = "<Transform translation='%g %g %g' scale='%g %g %g'>\n"
			ENDTRANS = "</Transform>\n"
			OVERLAY = "<MetadataString value='\"2D overlay\"' name='model type'/>\n"
			# translate to hither plane and scale to match pixels
			cam = viewer.camera
			view = 0
			eyePos = cam.eyePos(view)
			left, right, bottom, top, hither, yon, focal = \
							cam.window(view)
			scale = (right - left) / w
			xlate_scale = (eyePos[0] + left, eyePos[1] + bottom,
					eyePos[2] - hither - 0.0001, scale, scale, 1)
			output.extend([ prefix, OVERLAY,
					prefix, TRANSCALE % xlate_scale ])
		if openGL:
			GL.glPushMatrix()
		for arrow in self.arrows:
			if arrow.shown:
				if arrow.opacity < 1.0:
					color = arrow.color[:3] + (arrow.opacity * arrow.color[3],)
				else:
					color = arrow.color
				try:
					self._layoutTriangleStrips(openGL, arrow.triangleStrips(w, h), color)
				except ZeroDivisionError:
					# zero-length arrow
					pass
		if openGL:
			GL.glPopMatrix()
		else:
			output.extend([prefix, ENDTRANS])

	def x3dNeeds(self, scene):
		if not self.arrows:
			return

		# for TriangleStripSet
		scene.needComponent(chimera.X3DScene.Rendering, 3)
		# for ColorRGBA
		scene.needComponent(chimera.X3DScene.Rendering, 4)

	def x3dWrite(self, indent, scene):
		if not self.arrows:
			return

		self.x3dPrefix = " " * indent
		self.x3dOutput = []
		self._draw("x3d", chimera.viewer)
		return ''.join(self.x3dOutput)

	def _animStart(self, transition):
		pass

	def _animStep(self, startData, transition):
		animMapping, startIDs, endIDs = self._establishAnimMapping(startData, transition)
		where = transition.frameCount / float(transition.frames)
		endData = transition.scene().tool_settings.get("2D Labels (arrows)", None)
		for arrow, change in animMapping.items():
			start, end = change
			if start is not None:
				start = startIDs[start]
			if end is not None:
				end = endIDs[end]
			arrow.animInterp(start, where, end)

	def _animFinish(self, transition):
		endData = transition.scene().tool_settings.get("2D Labels (arrows)", None)
		if endData:
			endIDs = set(self._setupAnimIDs(endData["arrows"]).keys())
			removals = []
			for arrow in self.arrows:
				if arrow.ident not in endIDs:
					removals.append(arrow)
			for arrow in removals:
				self.removeArrow(arrow)
		for arrow in self.arrows:
			arrow.opacity = 1.0

	def _establishAnimMapping(self, startData, transition):
		animMapping = startData.setdefault('animMapping', {})
		# arrows in old scenes can have ID None; allow for that
		startIDs = self._setupAnimIDs(startData["arrows"])
		endData = transition.scene().tool_settings.get("2D Labels (arrows)", None)
		if endData:
			endIDs = self._setupAnimIDs(endData["arrows"])
		else:
			endIDs = {}
		if None in startIDs or None in endIDs:
			startIDs, endIDs = self._rectifyForIDNone(startData["arrows"], endData["arrows"])
		deletions = []
		for arrow in self.arrows:
			if arrow.ident not in startIDs and arrow.ident not in endIDs:
				deletions.append(arrow)
		for arrow in deletions:
			self.removeArrow(arrow)
		nearStart = transition.frameCount < 0.5 * transition.frames
		arrowMap = dict([(a.ident, a) for a in self.arrows])
		for startID, arrowData in startIDs.items():
			if startID in endIDs:
				change = (startID, startID)
			else:
				change = (startID, None)
			try:
				arrow = arrowMap[startID]
			except KeyError:
				if startID in endIDs and not nearStart:
					arrowData = endIDs[startID]
				args, kw = arrowData
				arrow = Arrow(*args, **kw)
				self.arrows.append(arrow)
			animMapping[arrow] = change
		for endID, arrowData in endIDs.items():
			if endID in startIDs:
				continue
			try:
				arrow = arrowMap[endID]
			except KeyError:
				args, kw = arrowData
				arrow = Arrow(*args, **kw)
				self.arrows.append(arrow)
			animMapping[arrow] = (None, endID)

		return animMapping, startIDs, endIDs

	def _layoutTriangleStrips(self, openGL, triangleStrips, color):
		if openGL:
			from OpenGL import GL
			GL.glColor4f(*tuple(color))
			for ts in triangleStrips:
				GL.glBegin(GL.GL_TRIANGLE_STRIP)
				for x, y in ts:
					GL.glVertex2f(x, y)
				GL.glEnd()
		else:
			output = self.x3dOutput
			prefix = self.x3dPrefix
			SHAPE = "<Shape>\n"
			ENDSHAPE = "</Shape>\n"
			APPEAR = "<Appearance>\n"
			ENDAPPEAR = "</Appearance>\n"
			TRIANGLESTRIP = "<TriangleStripSet solid='false' stripCount='%s'>\n"
			ENDTRIANGLESTRIP = "</TriangleStripSet>\n"
			COORD = "<Coordinate point='"
			ENDCOORD = "'/>\n"
			MATTRANS = "<Material ambientIntensity='0' diffuseColor='0 0 0' shininess='0' emissiveColor='%g %g %g' transparency='%g'/>\n"
			rgbt = color[0:3] + (1 - color[3],)
			output.extend([
				prefix, ' ', SHAPE,
				prefix, '  ', APPEAR,
				prefix, '   ', MATTRANS % rgbt,
				prefix, '  ', ENDAPPEAR])
			vertices = []
			for ts in triangleStrips:
				vertices.extend(list(ts))
			output.extend([prefix, '   ', TRIANGLESTRIP % " ".join(
				[str(len(ts)) for ts in triangleStrips])])
			output.extend([prefix, '    ', COORD])
			for x, y in vertices:
				output.extend(["%g " % c for c in [x, y, 0]])
			output.extend([prefix, '    ', ENDCOORD])
			output.extend([prefix, '   ', ENDTRIANGLESTRIP])
			output.extend([prefix, ' ', ENDSHAPE])

	def _restoreScene(self, scene):
		self.restore(scene.tool_settings.get('2D Labels (arrows)', None))

	def _saveScene(self, trigName, myData, scene):
		scene.tool_settings['2D Labels (arrows)'] = self.getRestoreInfo()

	def _saveSession(self, triggerName, myData, sessionFile):
		print>>sessionFile, """
try:
	from Ilabel.Arrows import ArrowsModel
	ArrowsModel().restore(%s)
except:
	reportRestoreError("Error restoring 2D arrows in session")

""" % repr(self.getRestoreInfo())

	def _setupAnimIDs(self, arrowData):
		mapping = {}
		num = 1
		for args, kw in arrowData:
			if kw['ident'] is None:
				start, end = args
				from copy import copy
				kw = copy(kw)
				for a in self.arrows:
					if a.start == start and a.end == end:
						kw['ident'] = a.ident
						break
				else:
					kw['ident'] = 'anim_%d_%d' % (num, id(arrowData))
					num += 1
			mapping[kw['ident']] = (args, kw)
		return mapping

_arrowsModel = None
def ArrowsModel(create=True):
	global _arrowsModel
	if not _arrowsModel:
		if not create:
			return None
		_arrowsModel = _ArrowsModel()
	return _arrowsModel
