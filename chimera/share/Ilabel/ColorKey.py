# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: ColorKey.py 42329 2021-09-02 16:35:56Z pett $

import chimera

_keyModel = None
def getKeyModel(create=True):
	global _keyModel
	if not _keyModel:
		if not create:
			return None
		_keyModel = KeyModel()
	return _keyModel

from PythonModel.PythonModel import PythonModel
class KeyModel(PythonModel):
	colorTreatmentValues = ("blended", "distinct")
	justificationValues = ("left", "decimal point", "right")
	labelSideValues = ("left/top", "right/bottom")
	numLabelSpacingValues = ("proportional to value", "equal")
	def __init__(self):
		PythonModel.__init__(self)
		self.gui = None
		self.reset()
		chimera.openModels.add([self], baseId=-1, hidden=True)
		from SimpleSession import SAVE_SESSION, BEGIN_RESTORE_SESSION
		self._handlerIDs = {}
		for trigName, handler in [(SAVE_SESSION, self._saveSession),
				(chimera.CLOSE_SESSION, self.destroy),
				(BEGIN_RESTORE_SESSION, self.destroy),
				(chimera.SCENE_TOOL_SAVE, self._saveScene),
				(chimera.SCENE_TOOL_RESTORE, self._restoreScene)]:
			self._handlerIDs[trigName] = chimera.triggers.addHandler(
				trigName, handler, None)

	def computeBounds(self, sphere, bbox):
		return False

	def destroy(self, *args):
		global _keyModel
		_keyModel = None
		for trigName, handlerID in self._handlerIDs.items():
			chimera.triggers.deleteHandler(trigName, handlerID)
		PythonModel.destroy(self, True)

	def draw(self, lens, viewer, passType):
		if passType != chimera.LensViewer.Overlay2d:
			return
		self._draw("opengl", viewer)

	# if adding attr here, also add it to the command version
	for attrName in ("borderColor", "borderWidth", "colorTreatment", "fontSize",
			"fontStyle", "fontTypeface", "justification", "keyPosition",
			"labelColor", "labelOffset", "labelSide", "numLabelSpacing",
			"rgbasAndLabels", "tickLength", "tickMarks", "tickThickness"):
		guiHasCB = repr(bool(attrName != "keyPosition"))
		upped = attrName[0].upper() + attrName[1:]
		exec("def get" + upped + "(self): return self._baseGet('"
			+ attrName + "')")
		exec("def set" + upped + "(self, val, fromGui=False): "
			"self._baseSet('" + attrName + "', val, fromGui, "
			+ guiHasCB +")")

	def reset(self, updateGui=False):
		if updateGui:
			def setter(attr, val):
				funcName = 'set' + attr[0].upper() + attr[1:]
				getattr(self, funcName)(val)
		else:
			def setter(attr, val):
				setattr(self, '_' + attr, val)
		from Ilabel import FONT_TYPEFACE_VALUES, contrastWithBG
		for attr, val in [
				("borderColor", contrastWithBG() + (1.0,)),
				("borderWidth", 2),
				("colorTreatment", "blended"),
				("fontSize", 24),
				("fontStyle", chimera.OGLFont.normal),
				("fontTypeface", FONT_TYPEFACE_VALUES[0]),
				("justification", "decimal point"),
				("keyPosition", None),
				("labelColor", contrastWithBG()),
				("labelOffset", 0),
				("labelSide", "right/bottom"),
				("numLabelSpacing", "proportional to value"),
				("rgbasAndLabels", [((0,0,1,1), "min"), ((1,1,1,1), ""),
					((1,0,0,1), "max")]),
				("tickLength", 10),
				("tickMarks", False),
				("tickThickness", 4)]:
			setter(attr, val)

	def validXform(self):
		return False

	def _baseGet(self, attrName):
		privateAN = "_" + attrName
		val = getattr(self, privateAN)
		if type(val) in [tuple, list, dict, set]:
			from copy import deepcopy
			return deepcopy(val)
		return val

	def _baseSet(self, attrName, val, fromGui, guiHasCB):
		privateAN = "_" + attrName
		prevVal = getattr(self, privateAN)
		if val == prevVal:
			return
		setattr(self, privateAN, val)
		if guiHasCB and self.gui and not fromGui:
			guiAttr = "_setKey" + attrName[0].upper() + attrName[1:]
			getattr(self.gui, guiAttr)(val)
		self.setMajorChange()

	def _draw(self, mode, viewer):
		if not self._keyPosition or len(self._keyPosition) < 2 \
		or len(self._rgbasAndLabels) < 2:
			return

		w, h = viewer.windowSize

		openGL = mode == "opengl"
		if openGL:
			from OpenGL import GL
		else:
			# X3D mostly cribbed from ILabelModel's x3dWrite
			prefix = self.x3dPrefix
			output = self.x3dOutput
			FONTDEF = "<FontStyle DEF='ColorKey' family='%s' size='%s' style='%s'>\n"
			ENDFONTDEF = "</FontStyle>\n"
			FONTUSE = "<FontStyle USE='ColorKey'/>\n"
			FILENAME = "<MetadataString value='\"%s\"' name='filename'/>\n"
			TEXT = "<Text string='%s'>\n"
			ENDTEXT = "</Text>\n"
			TRANS = "<Transform translation='%g %g %g'>\n"
			TRANSCALE = "<Transform translation='%g %g %g' scale='%g %g %g'>\n"
			ENDTRANS = "</Transform>\n"
			SHAPE = "<Shape>\n"
			ENDSHAPE = "</Shape>\n"
			APPEAR = "<Appearance>\n"
			ENDAPPEAR = "</Appearance>\n"
			MAT = "<Material ambientIntensity='0' diffuseColor='0 0 0' shininess='0' emissiveColor='%g %g %g'/>\n"
			MATTRANS = "<Material ambientIntensity='0' diffuseColor='0 0 0' shininess='0' emissiveColor='%g %g %g' transparency='%g'/>\n"
			OVERLAY = "<MetadataString value='\"2D overlay\"' name='model type'/>\n"
			# translate to hither plane and scale to match pixels
			cam = viewer.camera
			view = 0
			eyePos = cam.eyePos(view)
			left, right, bottom, top, hither, yon, focal = \
							cam.window(view)
			scale = (right - left) / w
			xlate_scale = (eyePos[0] + left, eyePos[1] + bottom,
					eyePos[2] - hither, scale, scale, 1)
			output.extend([ prefix, OVERLAY,
					prefix, TRANSCALE % xlate_scale ])
		x1, x2 = w * self._keyPosition[0][0], w * self._keyPosition[1][0]
		y1, y2 = h * self._keyPosition[0][1], h * self._keyPosition[1][1]
		minX, maxX = min(x1, x2), max(x1, x2)
		minY, maxY = min(y1, y2), max(y1, y2)
		if maxX - minX > maxY - minY:
			layout = "horizontal"
			shortMin, shortMax = minY, maxY
			longMin, longMax = minX, maxX
		else:
			layout = "vertical"
			shortMin, shortMax = minX, maxX
			longMin, longMax = minY, maxY
		rectPositions = self._rectPositions(longMin, longMax,
				self._colorTreatment, [ral[1] for ral in self._rgbasAndLabels])
		rgbas = [rl[0] for rl in self._rgbasAndLabels]
		if layout == "vertical":
			rectPositions = [minY + (maxY - rp) for rp in rectPositions]

		if self._colorTreatment == "blended":
			labelPositions = rectPositions
		else:
			labelPositions = [
				(rectPositions[i] + rectPositions[i+1]) / 2
					for i in range(len(rectPositions)-1)]

		if openGL:
			GL.glPushMatrix()
		if self._borderColor != None:
			bd = self._borderWidth
			# increase linewidth when printing
			bd *= chimera.LODControl.get().fontAdjust()
			# for raytracing, needs to be slightly behind key
			self._layoutRect(openGL, layout,
					shortMin-bd, shortMax+bd,
					longMin-bd, longMax+bd,
					self._borderColor, self._borderColor, z=-0.001)
		else:
			bd = 0
		labelColor = self._labelColor
		for i in range(len(rectPositions) - 1):
			color1 = rgbas[i]
			if len(rectPositions) == len(rgbas):
				color2 = rgbas[i+1]
			else:
				color2 = color1
			self._layoutRect(openGL, layout, shortMin, shortMax,
				rectPositions[i], rectPositions[i+1],
				color1, color2)
		if self._tickMarks:
			tickSize = self._tickLength
			tickSize *= chimera.LODControl.get().fontAdjust()
			tickThickness = self._tickThickness
			tickThickness *= chimera.LODControl.get().fontAdjust()
		else:
			tickSize = 0
		side = self._labelSide
		if (side == "right/bottom" and layout == "vertical") or (side
				== "left/top" and layout == "horizontal"):
			keyEdge = shortMax + bd
			tickTip = keyEdge + tickSize
			labelOffset = 5
		else:
			keyEdge = shortMin - bd
			tickTip = keyEdge - tickSize
			labelOffset = -5
		labelInfo = []
		for i, lp in enumerate(labelPositions):
			corr = 0
			if self._tickMarks:
				if self._colorTreatment == "blended":
					if lp == labelPositions[0]:
						corr = max(0,
							tickThickness/2 - bd)
						if layout == "vertical":
							corr = -corr
					elif lp == labelPositions[-1]:
						corr = max(0,
							tickThickness/2 - bd)
						if layout == "horizontal":
							corr = -corr
				if bd == 0:
					color = rgbas[i]
				else:
					color = self._borderColor
				self._layoutRect(openGL, layout, keyEdge,
					tickTip, lp-tickThickness/2+corr,
					lp+tickThickness/2+corr, color, color)
			text = self._rgbasAndLabels[i][1]
			if layout == "vertical":
				lx = tickTip + labelOffset
				ly = lp + corr
			else:
				lx = lp + corr
				ly = tickTip + labelOffset
			rgba = self._labelColor
			if rgba == None:
				rgba = rgbas[i]
			labelInfo.append((lx, ly, text, rgba))
		font = chimera.OGLFont(self._fontTypeface,
				self._fontSize, self._fontStyle)
		font.setup()
		# determine justification offsets
		if layout == "vertical":
			widths = []
			fieldWidth = 0
			justification = self._justification
			for x, y, text, rgba in labelInfo:
				if side == "right/bottom":
					if justification == "decimal point":
						try:
							dp = text.rindex('.')
						except ValueError:
							dp = len(text)
						width = font.width(text[:dp])
					elif justification == "right":
						width = font.width(text)
					else:
						width = 0
				else:
					if justification == "decimal point":
						try:
							dp = text.rindex('.')
						except ValueError:
							dp = -1
						width = font.width(text[dp+1:])
					elif justification == "left":
						width = font.width(text)
					else:
						width = 0
				widths.append(width)
				fieldWidth = max(fieldWidth, width)
			justifyOffsets = [(fieldWidth - w) for w in widths]
		else:
			justifyOffsets = [0] * len(labelInfo)
			pushDown = max([font.height(info[2])[0] for info in labelInfo])
		if not openGL:
			firstFont = True
		labelOffset = self._labelOffset
		for li, jo in zip(labelInfo, justifyOffsets):
			x, y, text, rgba = li
			if not text:
				continue
			if layout == "vertical":
				y -= font.height(text)[0] / 2
				if side == "left/top":
					x -= font.width(text) + jo + labelOffset
				else:
					x += jo + labelOffset
			else:
				import sys
				x -= font.width(text) / 2
				if side == "right/bottom":
					y -= pushDown + labelOffset
				else:
					y += labelOffset
			if openGL:
				GL.glPushMatrix()
				GL.glTranslatef(x, y, 0.0)
				font.setColor(*rgba)
				font.draw(text)
				GL.glPopMatrix()
			else:
				output.extend([prefix, ' ', TRANS % (x, y, 0)])
				output.extend([prefix, '  ', SHAPE])
				output.extend([prefix, '   ', APPEAR])
				if len(rgba) > 3 and rgba[3] != 1:
					rgbt = rgba[0:3] + (1 - rgba[3],)
					output.extend([prefix, '   ',
							MATTRANS % rgbt])
				else:
					output.extend([prefix, '   ',
							MAT % rgba[0:3]])
				output.extend([prefix, '   ', ENDAPPEAR])
				output.extend([prefix, '   ',
						TEXT % chimera.xml_quote(text)])
				if firstFont:
					output.extend([prefix, '    ',
						FONTDEF % (font.x3dFamily(),
						font.size(), font.x3dStyle()),
						prefix, '     ',
						FILENAME % font.filename(),
						prefix, '    ', ENDFONTDEF])
				else:
					output.extend([prefix, '    ',
								FONTUSE])
				output.extend([prefix, '   ', ENDTEXT])
				output.extend([prefix, '  ', ENDSHAPE])
				output.extend([prefix, ' ', ENDTRANS])
				firstFont = False
		font.cleanup()
		if openGL:
			GL.glPopMatrix()
		else:
			output.extend([prefix, ENDTRANS])

	def x3dNeeds(self, scene):
		if not self._keyPosition or len(self._keyPosition) < 2:
			return

		# for FontStyle, Text
		scene.needComponent(chimera.X3DScene.Text, 1)
		# for TriangleStripSet
		#scene.needComponent(chimera.X3DScene.Rendering, 3)
		# for ColorRGBA
		scene.needComponent(chimera.X3DScene.Rendering, 4)

	def x3dWrite(self, indent, scene):
		if not self._keyPosition or len(self._keyPosition) < 2:
			return

		self.x3dPrefix = " " * indent
		self.x3dOutput = []
		self._draw("x3d", chimera.viewer)
		return ''.join(self.x3dOutput)

	def _layoutLine(self, layout, fixedMin, fixedMax, var, color):
		if layout == "vertical":
			x1, x2, y1, y2 = fixedMin, fixedMax, var, var
		else:
			x1, x2, y1, y2 = var, var, fixedMin, fixedMax
		
		from OpenGL import GL
		GL.glColor4f(*tuple(color))
		GL.glBegin(GL.GL_LINES)
		GL.glVertex2f(x1, y1)
		GL.glVertex2f(x2, y2)
		GL.glEnd()

	def _layoutRect(self, openGL, layout, fixedMin, fixedMax,
					varMin, varMax, color1, color2, z=0):
		if layout == "vertical":
			x1, x2, y1, y2 = fixedMin, fixedMax, varMin, varMax
			colors = [color1, color1, color2, color2]
		else:
			x1, x2, y1, y2 = varMin, varMax, fixedMin, fixedMax
			colors = [color1, color2, color2, color1]
		
		if openGL:
			from OpenGL import GL
			GL.glBegin(GL.GL_QUADS)
			GL.glColor4f(*tuple(colors[0]))
			GL.glVertex2f(x1, y1)
			GL.glColor4f(*tuple(colors[1]))
			GL.glVertex2f(x2, y1)
			GL.glColor4f(*tuple(colors[2]))
			GL.glVertex2f(x2, y2)
			GL.glColor4f(*tuple(colors[3]))
			GL.glVertex2f(x1, y2)
			GL.glEnd()
			# to sidestep backface culling, draw another quad
			# in the other order
			GL.glBegin(GL.GL_QUADS)
			GL.glColor4f(*tuple(colors[3]))
			GL.glVertex2f(x1, y2)
			GL.glColor4f(*tuple(colors[2]))
			GL.glVertex2f(x2, y2)
			GL.glColor4f(*tuple(colors[1]))
			GL.glVertex2f(x2, y1)
			GL.glColor4f(*tuple(colors[0]))
			GL.glVertex2f(x1, y1)
			GL.glEnd()
		else:
			output = self.x3dOutput
			prefix = self.x3dPrefix
			SHAPE = "<Shape>\n"
			ENDSHAPE = "</Shape>\n"
			APPEAR = "<Appearance>\n"
			ENDAPPEAR = "</Appearance>\n"
			TRIANGLESTRIP = "<TriangleStripSet solid='false' stripCount='4'>\n"
			ENDTRIANGLESTRIP = "</TriangleStripSet>\n"
			COLOR = "<ColorRGBA color='"
			ENDCOLOR = "'/>\n"
			COORD = "<Coordinate point='"
			ENDCOORD = "'/>\n"
			MAT = "<Material ambientIntensity='0' diffuseColor='0 0 0' shininess='0'/>\n"
			output.extend([
				prefix, ' ', SHAPE,
				prefix, '  ', APPEAR,
				prefix, '   ', MAT,
				prefix, '  ', ENDAPPEAR])
			output.extend([prefix, '   ', TRIANGLESTRIP])
			output.extend([prefix, '    ', COLOR])
			for color in [colors[0], colors[1], colors[3],
								colors[2]]:
				output.extend(["%g " % c for c in color])
			output.extend([prefix, '    ', ENDCOLOR])
			output.extend([prefix, '    ', COORD])
			output.extend(["%g " % c for c in [x1, y1, z, x2, y1, z,
							x1, y2, z, x2, y2, z]])
			output.extend([prefix, '    ', ENDCOORD])
			output.extend([prefix, '   ', ENDTRIANGLESTRIP])
			output.extend([prefix, ' ', ENDSHAPE])


	def _layoutTriangle(self, layout, fixedMin, fixedMax, varMin, varMax,
								color):
		if layout == "vertical":
			xs = [fixedMin, fixedMax, fixedMin]
			ys = [varMin, (varMin+varMax)/2.0, varMax]
		else:
			xs = [varMin, (varMin+varMax)/2.0, varMax]
			ys = [fixedMin, fixedMax, fixedMin]
		
		from OpenGL import GL
		GL.glColor4f(*tuple(color))
		GL.glBegin(GL.GL_TRIANGLES)
		for x, y in zip(xs, ys):
			GL.glVertex2f(x, y)
		GL.glEnd()
		# to sidestep backface culling, draw another quad in the other
		# order
		xs.reverse()
		ys.reverse()
		GL.glBegin(GL.GL_TRIANGLES)
		for x, y in zip(xs, ys):
			GL.glVertex2f(x, y)
		GL.glEnd()

	def _rectPositions(self, longMin, longMax, colorTreatment, texts):
		proportional = False
		if self._numLabelSpacing == "proportional to value":
			try:
				values = [float(t) for t in texts]
			except ValueError:
				pass
			else:
				if values == sorted(values):
					proportional = True
				values.reverse()
				if values == sorted(values):
					proportional = True
				values.reverse()
				if proportional and values[0] == values[-1]:
					proportional = False
		if not proportional:
			values = range(len(texts))
		longSize = longMax - longMin
		if colorTreatment == "blended":
			valSize = abs(values[0] - values[-1])
			rectPositions = [longMin + longSize * abs(v - values[0])/valSize
								for v in values]
		else:
			v0 = values[0] - (values[1] - values[0])/2.0
			vN = values[-1] + (values[-1] - values[-2])/2.0
			valSize = abs(vN-v0)
			positions = [longMin + longSize * abs(v-v0) / valSize for v in values]
			rectPositions = [longMin] + [(positions[i] + positions[i+1])/2.0
				for i in range(len(values)-1)] + [longMax]
		return rectPositions

	def _restoreScene(self, trigName, myData, scene):
		if 'color key' in scene.tool_settings:
			self._restoreSession(scene.tool_settings['color key'])

	def _restoreSession(self, info):
		self.setKeyPosition(info["key position"])
		self.setColorTreatment(info["color depiction"])
		self.setLabelSide(info["label positions"])
		self.setLabelColor(info["label color"])
		self.setJustification(info["label justification"])
		self.setLabelOffset(info["label offset"])
		self.setNumLabelSpacing(info["label spacing"])
		self.setFontSize(info["font size"])
		self.setFontStyle(info["font typeface"])
		self.setFontTypeface(info["font name"])
		self.setBorderColor(info["border color"])
		self.setBorderWidth(info["border width"])
		self.setTickMarks(info["show ticks"])
		self.setTickLength(info["tick length"])
		self.setTickThickness(info["tick thickness"])
		self.setRgbasAndLabels(info["colors/labels"])

	def _saveScene(self, trigName, myData, scene):
		scene.tool_settings['color key'] = self._sessionInfo()

	def _sessionInfo(self):
		info = {}
		info["key position"] = self._keyPosition
		info["colors/labels"] = self._rgbasAndLabels
		info["color depiction"] = self._colorTreatment
		info["label positions"] = self._labelSide
		info["label color"] = self._labelColor
		info["label justification"] = self._justification
		info["label offset"] = self._labelOffset
		info["label spacing"] = self._numLabelSpacing
		info["font size"] = self._fontSize
		info["font typeface"] = self._fontStyle
		info["font name"] = self._fontTypeface
		info["border color"] = self._borderColor
		info["border width"] = self._borderWidth
		info["show ticks"] = self._tickMarks
		info["tick length"] = self._tickLength
		info["tick thickness"] = self._tickThickness
		return info

	def _saveSession(self, triggerName, myData, sessionFile):
		print>>sessionFile, """
try:
	from Ilabel.ColorKey import getKeyModel
	getKeyModel()._restoreSession(%s)
except:
	reportRestoreError("Error restoring color key")

""" % repr(self._sessionInfo())
