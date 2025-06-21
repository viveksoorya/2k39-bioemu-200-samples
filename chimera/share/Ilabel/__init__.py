# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42344 2021-11-18 00:42:03Z pett $

from OpenGL import GL
from PythonModel.PythonModel import PythonModel
import chimera
from SimpleSession import SAVE_SESSION

import threading
_uidLock = threading.RLock()

from Label import Label

_ilabelModel = None
def LabelsModel(create=True):
	global _ilabelModel
	if not _ilabelModel:
		if not create:
			return None
		IlabelModel()
	return _ilabelModel

AUTO_ID_PREFIX = "label2d_id_"
class IlabelModel(PythonModel):
	def __init__(self):
		# setting _ilabelModel has to be here instead of in
		# LabelsModel() for backwards compatibility with old sessions
		global _ilabelModel
		if _ilabelModel:
			raise RuntimeError("Attempt to create second"
				" IlabelModel instance")
		_ilabelModel = self
		PythonModel.__init__(self)
		self.labels = []
		self.labelMap    = {}
		self._UID        = 0
		self.curLabel = None
		chimera.openModels.add([self], baseId=-1, hidden=True)
		self._handlerIDs = {}
		for trigName, handler in [(SAVE_SESSION, self._saveSession),
				(chimera.SCENE_TOOL_SAVE, self._saveScene),
				(chimera.SCENE_TOOL_RESTORE, self._restoreScene),
				(chimera.ANIMATION_TRANSITION_START, self._animStart),
				(chimera.ANIMATION_TRANSITION_FINISH, self._animFinish)]:
			self._handlerIDs[trigName] = chimera.triggers.addHandler(trigName, handler, None)

	def destroy(self, *args):
		for label in self.labels:
			label.destroy()
		for trigName, handlerID in self._handlerIDs.items():
			chimera.triggers.deleteHandler(trigName, handlerID)
		PythonModel.destroy(self, True)
		global _ilabelModel
		_ilabelModel = None

	def computeBounds(self, sphere, bbox):
		return False

	def validXform(self):
		return False

	def draw(self, lens, viewer, passType):
		if passType != chimera.LensViewer.Overlay2d:
			return

		w, h = viewer.windowSize
		scale = chimera.LODControl.get().fontAdjust()
		curFont = None
		for label in self.labels:
			# TODO: handle justify
			# style (justify is only left/center/right)

			# any changes here need to mirror in pickLabel
			# and x3dWrite
			if not unicode(label).strip() or not label.shown:
				continue
			labelLines = label.lines[:]
			while labelLines and not labelLines[0]:
				labelLines.pop(0)
			while labelLines and not labelLines[-1]:
				labelLines.pop()
			if not labelLines:
				continue
			maxWidth = 0.0
			textTop, textBottom = None, None
			baseX, baseY = label.pos[0]*w, label.pos[1]*h
			# looks less fuzzy on integer boundaries
			baseX = int(baseX + 0.5)
			baseY = int(baseY + 0.5)
			for line in labelLines:
				width = 0.0
				for c in line:
					# font setup/teardown is expensive
					# so minimize it as much as possible
					if curFont is None or c.font != curFont:
						if curFont is not None:
							curFont.cleanup()
						curFont = c.font
						curFont.setup()
					text = unicode(c)
					width += curFont.width(text)
					if label.background:
						if line == labelLines[0]:
							u, d = curFont.height(text)
							if textTop is None or baseY + u > textTop:
								textTop = baseY + u
						if line == labelLines[-1]:
							u, d = curFont.height(text)
							if textBottom is None or baseY + d < textBottom:
								textBottom = baseY + d
				if curFont:
					fsize = curFont.size()
				else:
					fsize = 24
				baseY -= fsize * scale
				maxWidth = max(maxWidth, width)
			if label.background:
				scaledMargin = label.margin * scale
				x1 = baseX - scaledMargin
				x2 = baseX + maxWidth + scaledMargin
				y1 = textBottom - scaledMargin
				y2 = textTop + scaledMargin
				bkgrdColor = label.background[:3] + (label.background[3] * label.opacity,)
				if label.outline > 0:
					outlineColor = contrastWith(bkgrdColor)[:3] + (label.opacity,)
					scaledOutline = label.outline * scale
					ox1 = x1 - scaledOutline
					ox2 = x2 + scaledOutline
					oy1 = y1 - scaledOutline
					oy2 = y2 + scaledOutline
					GL.glPushMatrix()
					GL.glBegin(GL.GL_QUADS)
					GL.glColor4f(*outlineColor)
					#top
					GL.glVertex2f(ox1, oy2)
					GL.glVertex2f(x1, y2)
					GL.glVertex2f(x2, y2)
					GL.glVertex2f(ox2, oy2)
					# right
					GL.glVertex2f(x2, y2)
					GL.glVertex2f(ox2, oy2)
					GL.glVertex2f(ox2, oy1)
					GL.glVertex2f(x2, y1)
					# bottom
					GL.glVertex2f(ox1, oy1)
					GL.glVertex2f(x1, y1)
					GL.glVertex2f(x2, y1)
					GL.glVertex2f(ox2, oy1)
					# left
					GL.glVertex2f(ox1, oy1)
					GL.glVertex2f(x1, y1)
					GL.glVertex2f(x1, y2)
					GL.glVertex2f(ox1, oy2)
					GL.glEnd()
					# to sidestep backface culling, draw another quad
					# in the other order
					GL.glBegin(GL.GL_QUADS)
					GL.glColor4f(*outlineColor)
					#top
					GL.glVertex2f(ox2, oy2)
					GL.glVertex2f(x2, y2)
					GL.glVertex2f(x1, y2)
					GL.glVertex2f(ox1, oy2)
					# right
					GL.glVertex2f(x2, y1)
					GL.glVertex2f(ox2, oy1)
					GL.glVertex2f(ox2, oy2)
					GL.glVertex2f(x2, y2)
					# bottom
					GL.glVertex2f(ox2, oy1)
					GL.glVertex2f(x2, y1)
					GL.glVertex2f(x1, y1)
					GL.glVertex2f(ox1, oy1)
					# left
					GL.glVertex2f(ox1, oy2)
					GL.glVertex2f(x1, y2)
					GL.glVertex2f(x1, y1)
					GL.glVertex2f(ox1, oy1)
					GL.glEnd()
					GL.glPopMatrix()
				GL.glPushMatrix()
				GL.glBegin(GL.GL_QUADS)
				GL.glColor4f(*bkgrdColor)
				GL.glVertex2f(x1, y1)
				GL.glVertex2f(x2, y1)
				GL.glVertex2f(x2, y2)
				GL.glVertex2f(x1, y2)
				GL.glEnd()
				# to sidestep backface culling, draw another quad
				# in the other order
				GL.glBegin(GL.GL_QUADS)
				GL.glColor4f(*bkgrdColor)
				GL.glVertex2f(x1, y2)
				GL.glVertex2f(x2, y2)
				GL.glVertex2f(x2, y1)
				GL.glVertex2f(x1, y1)
				GL.glEnd()
				GL.glPopMatrix()
			baseX, baseY = label.pos[0]*w, label.pos[1]*h
			# looks less fuzzy on integer boundaries
			baseX = int(baseX + 0.5)
			baseY = int(baseY + 0.5)
			for line in labelLines:
				width = 0.0
				for c in line:
					GL.glPushMatrix()
					GL.glTranslatef(baseX + width, baseY, 0.0)
					# font setup/teardown is expensive
					# so minimize it as much as possible
					if curFont is None or c.font != curFont:
						if curFont is not None:
							curFont.cleanup()
						curFont = c.font
						curFont.setup()
					if label.opacity < 1.0:
						rgba = c.rgba[:3] + (label.opacity * c.rgba[3],)
					else:
						rgba = c.rgba
					curFont.setColor(*rgba)
					text = unicode(c)
					curFont.draw(text)
					width += curFont.width(text)
					GL.glPopMatrix()
				if curFont:
					fsize = curFont.size()
				else:
					fsize = 24
				baseY -= fsize * scale

		if curFont is not None:
			curFont.cleanup()

	def x3dNeeds(self, scene):
		if not self.labels:
			return

		scene.needComponent(chimera.X3DScene.Text, 1)
		for label in self.labels:
			if label.background:
				# for ColorRGBA
				scene.needComponent(chimera.X3DScene.Rendering, 4)
				break

	def x3dWrite(self, indent, scene):
		if not self.labels:
			return

		# repeat draw code, but output x3d
		w, h = chimera.viewer.windowSize
		prefix = ' ' * indent
		curFont = None
		fontCount = 0
		output = []
		FONTDEF = "<FontStyle DEF='ILabel%s' family='%s' size='%s' style='%s'>\n"
		ENDFONTDEF = "</FontStyle>\n"
		FONTUSE = "<FontStyle USE='ILabel%s'/>\n"
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
		cam = chimera.viewer.camera
		view = 0
		eyePos = cam.eyePos(view)
		left, right, bottom, top, hither, yon, focal = cam.window(view)
		scale = (right - left) / w
		xlate_scale = (eyePos[0] + left, eyePos[1] + bottom, eyePos[2] - hither, scale, scale, 1)
		output.extend([
			prefix, OVERLAY,
			prefix, TRANSCALE % xlate_scale
			])
		hasLabels = False
		for label in self.labels:
			if not unicode(label) or not label.shown:
				continue
			labelLines = label.lines[:]
			while labelLines and not labelLines[0]:
				labelLines.pop(0)
			while labelLines and not labelLines[-1]:
				labelLines.pop()
			if not labelLines:
				continue
			hasLabels = True
			maxWidth = 0.0
			textTop, textBottom = None, None
			baseX, baseY = label.pos[0]*w, label.pos[1]*h
			# looks less fuzzy on integer boundaries
			baseX = int(baseX + 0.5)
			baseY = int(baseY + 0.5)
			for line in labelLines:
				width = 0.0
				for c in line:
					# font setup/teardown is expensive
					# so minimize it as much as possible
					if curFont is None or c.font != curFont:
						if curFont is not None:
							curFont.cleanup()
						curFont = c.font
						curFont.setup()
					curFont.setColor(*c.rgba)
					text = unicode(c)
					##curFont.draw(text)
					width += curFont.width(text)
					if label.background:
						if line == labelLines[0]:
							u, d = curFont.height(text)
							if textTop is None or baseY + u > textTop:
								textTop = baseY + u
						if line == labelLines[-1]:
							u, d = curFont.height(text)
							if textBottom is None or baseY + d < textBottom:
								textBottom = baseY + d
				if curFont:
					fsize = curFont.size()
				else:
					fsize = 24
				baseY -= fsize
				maxWidth = max(maxWidth, width)
			if curFont is not None:
				curFont.cleanup()
				curFont = None
			if label.background:
				x1 = baseX - label.margin
				x2 = baseX + maxWidth + label.margin
				y1 = textBottom - label.margin
				y2 = textTop + label.margin
				bkgrdColor = label.background[:3] + (label.background[3] * label.opacity,)
				self.x3dRect(output, prefix, bkgrdColor,
						x1, y1, x2, y1, x2, y2, x1, y2)
				# to sidestep backface culling, draw another quad
				# in the other order
				self.x3dRect(output, prefix, bkgrdColor,
						x1, y2, x2, y2, x2, y1, x1, y1)
				if label.outline > 0:
					outlineColor = contrastWith(bkgrdColor)[:3] + (label.opacity,)
					ox1 = x1 - label.outline
					ox2 = x2 + label.outline
					oy1 = y1 - label.outline
					oy2 = y2 + label.outline
					#top
					self.x3dRect(output, prefix, outlineColor,
							ox1, oy2, x1, y2, x2, y2, ox2, oy2)
					# right
					self.x3dRect(output, prefix, outlineColor,
							x2, y2, ox2, oy2, ox2, oy1, x2, y1)
					# bottom
					self.x3dRect(output, prefix, outlineColor,
							ox1, oy1, x1, y1, x2, y1, ox2, oy1)
					# left
					self.x3dRect(output, prefix, outlineColor,
							ox1, oy1, x1, y1, x1, y2, ox1, oy2)
					# to sidestep backface culling, draw another quad
					# in the other order
					#top
					self.x3dRect(output, prefix, outlineColor,
							ox2, oy2, x2, y2, x1, y2, ox1, oy2)
					# right
					self.x3dRect(output, prefix, outlineColor,
							x2, y1, ox2, oy1, ox2, oy2, x2, y2)
					# bottom
					self.x3dRect(output, prefix, outlineColor,
							ox2, oy1, x2, y1, x1, y1, ox1, oy1)
					# left
					self.x3dRect(output, prefix, outlineColor,
							ox1, oy2, x1, y2, x1, y1, ox1, oy1)
			baseX, baseY = label.pos[0]*w, label.pos[1]*h
			# looks less fuzzy on integer boundaries
			baseX = int(baseX + 0.5)
			baseY = int(baseY + 0.5)
			for line in label.lines:
				width = 0.0
				for c in line:
					output.extend([prefix, ' ',
						TRANS % (baseX + width, baseY,
									0)])
					output.extend([prefix, '  ', SHAPE])
					output.extend([prefix, '   ', APPEAR])
					if c.rgba[3] != 1:
						rgbt = c.rgba[0:3] + (1 - c.rgba[3],)
						output.extend([prefix, '   ',
							MATTRANS % rgbt])
					else:
						output.extend([prefix, '   ',
							MAT % c.rgba[0:3]])
					output.extend([prefix, '   ',
								ENDAPPEAR])
					text = unicode(c)
					output.extend([prefix, '   ',
						TEXT % chimera.xml_quote(text)])
					if curFont is None or c.font != curFont:
						fontCount += 1
						curFont = c.font
						output.extend([
							prefix, '    ', FONTDEF
							% (fontCount,
							curFont.x3dFamily(),
							curFont.size(),
							curFont.x3dStyle()),
							prefix, '     ',
							FILENAME %
							curFont.filename(),
							prefix, '    ',
							ENDFONTDEF
							])
					else:
						output.extend([prefix, '    ',
							FONTUSE % fontCount])
					width += curFont.width(text)
					output.extend([prefix, '   ', ENDTEXT])
					output.extend([prefix, '  ', ENDSHAPE])
					output.extend([prefix, ' ', ENDTRANS])
				baseY -= curFont.size()
		output.extend([prefix, ENDTRANS])
		if not hasLabels:
			return ""
		return ''.join(output)

	def x3dRect(self, output, prefix, color, *coords):
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
		for i in range(4):
			output.extend(["%g " % c for c in color])
		output.extend([prefix, '    ', ENDCOLOR])
		output.extend([prefix, '    ', COORD])
		p1, p2, p3, p4 = [(coords[i], coords[i+1]) for i in range(0, 8, 2)]
		for p in (p2, p1, p3, p4):
			output.append("%g %g 0.0 " % p)
		output.extend([prefix, '    ', ENDCOORD])
		output.extend([prefix, '   ', ENDTRIANGLESTRIP])
		output.extend([prefix, ' ', ENDSHAPE])

	def changeLabel(self, newText):
		self.curLabel.set(newText)
		self.setMajorChange()

	def changeToLabel(self, nextLabel):
		self.curLabel = nextLabel

	def moveLabel(self, pos):
		self.curLabel.pos = pos
		self.setMajorChange()

	def _getLabelID(self):
		## start critical section
		_uidLock.acquire()
		id = self._UID
		self._UID += 1
		_uidLock.release()
		## end critical section
		
		return AUTO_ID_PREFIX + "%s" % id
		
	def newLabel(self, pos, labelID=None):
		
		if labelID:
			if labelID in self.labelMap.keys():
				raise RuntimeError("Already have a label " \
						   "with ID '%s'" % labelID
						   )
			else:
				l_id = labelID
		else:
			l_id = self._getLabelID()

		newLabel = Label(pos, self)
		self.labels.append(newLabel)

		self.labelMap[l_id] = newLabel

		return newLabel

	def pickLabel(self, pos, w, h):
		slop = 2
		targetX, targetY = pos[0]*w, pos[1]*h
		for label in self.labels:
			if not unicode(label) or not label.shown:
				continue
			if label.background:
				extra = max(label.margin + label.outline, 0) + slop
			else:
				extra = slop
			baseX, baseY = label.pos[0]*w, label.pos[1]*h
			font = None
			for line in label.lines:
				width = 0.0
				for c in line:
					font = c.font
					lx = baseX + width - extra
					text = unicode(c)
					width += font.width(text)
					rx = baseX + width + extra
					above, below = font.height(text)
					uy = baseY + above + extra
					ly = baseY + below - extra
					if targetX >= lx and targetX <= rx \
					and targetY >= ly and targetY <= uy:
						moveOffset = (
							targetX - baseX,
							targetY - label.pos[1]*h
						)
						break
				else:
					if font:
						baseY -= font.size()
					else:
						baseY -= 24
					continue
				break
			else:
				continue
			break
		else:
			label = None
			moveOffset = (0, 0)
		return label, moveOffset

	def removeLabel(self, label):
		self.labels.remove(label)

		for k,v in self.labelMap.items():
			if v == label:
				del self.labelMap[k]
				break
			
		if label == self.curLabel:
			self.curLabel = None
		if unicode(label):
			self.setMajorChange()
		label.destroy()

	def _animStart(self, trigName, myData, transition):
		if transition.scene().saveStateVer == 1:
			# labels restored by Animate
			return
		# deregister from scene-restore trigger while animation
		# ongoing to avoid duplicative state restoration
		tn = chimera.SCENE_TOOL_RESTORE
		chimera.triggers.deleteHandler(tn, self._handlerIDs[tn])
		del self._handlerIDs[tn]

		from Arrows import ArrowsModel
		self._handlerIDs[chimera.ANIMATION_TRANSITION_STEP] = chimera.triggers.addHandler(
				chimera.ANIMATION_TRANSITION_STEP, self._animStep,
				(self.sessionInfo(), ArrowsModel().getRestoreInfo()))
		self._alphasCached = False
		ArrowsModel()._animStart(transition)

	def _animStep(self, trigName, startData, transition):
		labelStartData, arrowStartData = startData
		animMapping = self._establishAnimMapping(labelStartData, transition)
		where = transition.frameCount / float(transition.frames)
		endData = transition.scene().tool_settings.get("2D Labels (labels)", None)
		for label, change in animMapping.items():
			start, end = change
			if start is not None:
				start = labelStartData['labels'][labelStartData['labelIDs'].index(start)]
			if end is not None:
				end = endData['labels'][endData['labelIDs'].index(end)]
			label.animInterp(start, where, end)
		if self.labels:
			self.setMajorChange()
		from Arrows import ArrowsModel
		ArrowsModel()._animStep(arrowStartData, transition)

	def _animFinish(self, trigName, myData, transition):
		if transition.scene().saveStateVer == 1:
			# labels restored by Animate
			return
		endData = transition.scene().tool_settings.get("2D Labels (labels)", None)
		if endData:
			endIDs = set(endData['labelIDs'])
		else:
			endIDs = set()
		removals = []
		for labelID, label in self.labelMap.items():
			if labelID not in endIDs:
				removals.append(label)
		for label in removals:
			self.removeLabel(label)
		if endData:
			endDataMap = dict(zip(endData['labelIDs'], endData['labels']))
			for labelID, label in self.labelMap.items():
				labelEndData = endDataMap[labelID]
				label.shown = labelEndData["shown"]
				label.opacity = labelEndData["opacity"]
		from Arrows import ArrowsModel
		ArrowsModel()._animFinish(transition)
		tn = chimera.ANIMATION_TRANSITION_STEP
		chimera.triggers.deleteHandler(tn, self._handlerIDs[tn])
		del self._handlerIDs[tn]

		self._handlerIDs[chimera.SCENE_TOOL_RESTORE] = chimera.triggers.addHandler(
				chimera.SCENE_TOOL_RESTORE, self._restoreScene, None)
		if not chimera.nogui:
			updateGUI()

	def _establishAnimMapping(self, startData, transition):
		animMapping = startData.setdefault('animMapping', {})
		startIDs = dict(zip(startData['labelIDs'], startData['labels']))
		endData = transition.scene().tool_settings.get("2D Labels (labels)", None)
		if endData:
			endIDs = dict(zip(endData['labelIDs'], endData['labels']))
		else:
			endIDs = {}
		deletions = []
		for curID, curLabel in self.labelMap.items():
			if curID not in startIDs and curID not in endIDs:
				deletions.append(curLabel)
		for delLabel in deletions:
			self.removeLabel(delLabel)
		nearStart = transition.frameCount < 0.5 * transition.frames
		for startID, labelData in startIDs.items():
			if startID in endIDs:
				change = (startID, startID)
			else:
				change = (startID, None)
			try:
				label = self.labelMap[startID]
			except KeyError:
				label = self.newLabel(*labelData["args"], labelID=startID)
				if nearStart or startID not in endIDs:
					label.restoreSession(labelData)
				else:
					label.restoreSession(endIDs[startID])
			animMapping[label] = change
		for endID, labelData in endIDs.items():
			if endID in startIDs:
				continue
			try:
				label = self.labelMap[endID]
			except KeyError:
				label = self.newLabel(*labelData["args"], labelID=endID)
				label._restoreSession(labelData)
			animMapping[label] = (None, endID)

		return animMapping

	def _restoreScene(self, trigName, myData, scene):
		if scene.saveStateVer == 1:
			# labels restored by Animate
			return
		self.destroy()
		il = LabelsModel()
		il.restoreSession(scene.tool_settings.get('2D Labels (labels)', None))
		from Arrows import ArrowsModel
		ArrowsModel()._restoreScene(scene)
		if chimera.nogui:
			return
		updateGUI()
		from chimera import dialogs, openModels
		from gui import IlabelDialog
		if '2D Labels (gui)' in scene.tool_settings:
			dlg = dialogs.display(IlabelDialog.name)
			dlg._restoreScene(None, None, scene)
		else:
			dlg = dialogs.find(IlabelDialog.name)
			if dlg:
				openModels.close([dlg.keyModel])
				dlg.Close()
				dlg.destroy()

	def restoreSession(self, info):
		if info is None:
			# scene with no labels
			return

		for labelInfo in info["labels"]:
			new_label = Label(*(labelInfo["args"] + (self,)), **labelInfo.get('kw', {}))
			self.labels.append(new_label)
			self.labels[-1]._restoreSession(labelInfo)

		if info.has_key("labelUID"):
			self._UID = info["labelUID"]

		for idx,label in enumerate(self.labels):
			if info.has_key("labelIDs"):
				uid = info["labelIDs"][idx]
			else:
				uid = self._getLabelID()
			self.labelMap[uid] = label

		if info["curLabel"] is None:
			self.curLabel = None
		else:
			self.curLabel = self.labels[info["curLabel"]]
	# backwards compatibility...
	_restoreSession = restoreSession

	def _saveScene(self, trigName, myData, scene):
		scene.tool_settings['2D Labels (labels)'] = self.sessionInfo()

	def _saveSession(self, triggerName, myData, sessionFile):
		print>>sessionFile, """
try:
	import Ilabel
	il = Ilabel.LabelsModel(create=False)
	if il:
		il.destroy()
	il = Ilabel.LabelsModel()
	il.restoreSession(%s)
	del Ilabel, il
except:
	reportRestoreError("Error restoring IlabelModel instance in session")
""" % repr(self.sessionInfo())

	def sessionInfo(self):
		info = {}
		info["labels"]   = [l._sessionInfo() for l in self.labels]

		id_list = []
		for l in self.labels:
			## try to find the label as a value in the labelMap,
			## and add the key to id_list
			for k,v in self.labelMap.items():
				if v == l:
					id_list.append(k)
					break
			## this case should never happen, but if labelMap
			## somehow became corrupted, come up with a new
			## id for this label, and add append it to id_list
			else:
				id_list.append(self._getLabelID()) 

		info["labelIDs"] = id_list

		info["labelUID"] = self._UID
		
		if self.curLabel:
			info["curLabel"] = self.labels.index(self.curLabel)
		else:
			info["curLabel"] = None
		
		return info



def processLabel2DCmd(action, itemID, text=None, color=None, size=None,
	style=None, typeface=None, xpos=None, ypos=None, visibility=None, frames=None,
	start=None, end=None, weight=None, head=None, bgColor=False, outline=None, margin=None):

	from Midas import MidasError

	if itemID == "*":
		# operate on all existing
		import inspect
		argNames, varargName, varKwName, vals = inspect.getargvalues(inspect.currentframe())
		recurseKw = dict([(n, vals[n]) for n in argNames if n not in ('action', 'itemID')])
		if action[0] == "a":
			from Arrows import ArrowsModel, Arrow
			aModel = ArrowsModel()
			itemIDs = aModel.arrows
		else:
			model = LabelsModel() # create if necessary
			itemIDs = model.labelMap.keys()
		for itemID in itemIDs[:]:
			processLabel2DCmd(action, itemID, **recurseKw)
		return

	if action[0] == "a":
		from Arrows import ArrowsModel, Arrow
		aModel = ArrowsModel()
	else:
		if type(xpos) == list or type(ypos) == list:
			raise MidasError("Multiple occurances of 'xpos' or 'ypos' keywords")

		try:
			if xpos: xpos + 0
			if ypos: ypos + 0
		except:
			raise MidasError("xpos/ypos values must be numeric")

		model = LabelsModel() # create if necessary

		if text is not None:
			if isinstance(text, basestring):
				if not isinstance(text, unicode):
					# text directly from command line will be
					# unicode, but text from a script file
					# may be UTF-8 (if non-ASCII label)
					text = text.decode('utf8')
			else:
				# text might have evaluated as an integer or something
				text = unicode(text)

			# backslash interpretation...
			if '\\' in text:
				if '"' not in text:
					text = eval('u"' + text + '"')
				elif "'" not in text:
					text = eval("u'" + text + "'")

		if bgColor not in (False, None):
			bgColor = bgColor.rgba()
		labelKw = {}
		if bgColor is not False:
			labelKw['background'] = bgColor
		if margin is not None:
			labelKw['margin'] = margin
		if outline is not None:
			labelKw['outline'] = outline

	if action == "create":
		## get the position
		if xpos==None:
			xpos = .5
		if ypos==None:
			ypos = .5

		if not color:
			color = chimera.Color.lookup('white')
		
		if not size:
			size = 24

		if not style:
			style = "normal"
			
		if not typeface:
			typeface = "sans serif"

		## make a new label
		try:
			label = model.newLabel( (xpos,ypos), itemID )
		except RuntimeError, what:
			raise MidasError, what
		
		## set it's content
		label.set(text or '')

		## color and size the characters
		label.changeAttrs(size, color, styleLookup(style),
						typefaceLookup(typeface), **labelKw)

		if visibility == "hide":
			label.shown = False
		if not chimera.nogui:
			from chimera.tkgui import app
			app.rapidAccess.shown = False

	elif action == "change":
		if not model.labelMap.has_key(itemID):
			raise MidasError, "No such label with ID '%s'" % itemID

		label = model.labelMap[itemID]

		if text!=None:
			cur_size  = None
			cur_color = None
			cur_style = None
			cur_typeface = None
			
			if (len(label.lines) > 0) and \
			   (len(label.lines[0]) > 0):
				c = label.lines[0][0]
				cur_color = c.rgba
				cur_size  = c.size
				cur_style = c.style
				cur_typeface = c.fontName

			label.set(text)

			if cur_color:
				cur_color = chimera.MaterialColor(*cur_color)

			label.changeAttrs(cur_size, cur_color, cur_style,
								cur_typeface, **labelKw)

		if color or size or style or typeface or labelKw:
			if style:
				style = styleLookup(style)
			if typeface:
				typeface = typefaceLookup(typeface)
			label.changeAttrs(size, color, style, typeface, **labelKw)

		if (xpos!=None) or (ypos!=None):
			cur_xpos, cur_ypos = label.pos
			if xpos==None: xpos = cur_xpos
			if ypos==None: ypos = cur_ypos
			label.pos = (xpos, ypos)

		if visibility:
			from Midas import _addMotionHandler

			global _tickMotionHandler
			from Midas import _tickMotionHandler
			
			
			param = {'command':'fade','label':label,
				'frames':frames}
			## need step, frames

			if visibility == 'show':
				if not frames:
					label.shown = True
				else:
					## should show start from 0?  Is wierd
					## when someone 'shows' a label that is
					## already shown
					label.changeAttrs(opacity=0.0)
					label.shown = True
					step = 1.0 / frames
					param['step'] = step
					_addMotionHandler(_fade, param)
					
			elif visibility == 'hide':
				if not frames:
					label.shown = False
					#label.changeAttrs(opacity=0.0)
				else:
					step = 1.0 / frames
					param['step'] = -(step)
					_addMotionHandler(_fade, param)
			else:
				raise MidasError, "No such visibility mode '%s'" % visibility

	elif action == "delete":
		if not model.labelMap.has_key(itemID):
			raise MidasError, "No such label with ID '%s'" % itemID

		label = model.labelMap[itemID]
		model.removeLabel(label)

	elif action == "read":
		readFiles([itemID])

	elif action == "write":
		writeFile(itemID)

	elif action in ["acreate", "arrowcreate"]:
		if isinstance(itemID, Arrow):
			raise MidasError("Cannot use '*' as ID in arrowcreate")
		if itemID in [a.ident for a in aModel.arrows]:
			raise MidasError("Arrow with ID %s already exists!" % itemID)
		kw = {'ident': itemID}
		args = []
		for arg in ("start", "end"):
			args.append(_getArrowStartEnd(eval(arg)))

		if not color:
			color = chimera.Color.lookup('white')
		kw['color'] = color

		if weight is not None:
			try:
				weight = float(weight)
			except ValueError:
				raise MidasError("Weight value must be numeric")
			kw['weight'] = weight

		if head is not None:
			if head not in Arrow.headStyles:
				raise MidasError("Arrowhead style must be one of: %s"
					", ".join(Arrow.headStyles))
			kw['head'] = head

		if visibility == 'hide':
			kw['shown'] = False

		aModel.addArrow(*args, **kw)
		if not chimera.nogui:
			from chimera.tkgui import app
			app.rapidAccess.shown = False

	elif action in ["achange", "arrowchange"]:
		if isinstance(itemID, Arrow):
			arrow = itemID
		else:
			for arrow in aModel.arrows:
				if arrow.ident == itemID:
					break
			else:
				raise MidasError("No such arrow with ID '%s'" % itemID)

		if color:
			try:
				arrow.color = color
			except ValueError, v:
				raise MidasError(str(v))

		if weight is not None:
			try:
				arrow.weight = weight
			except ValueError, v:
				raise MidasError(str(v))

		if head is not None:
			try:
				arrow.head = head
			except ValueError, v:
				raise MidasError(str(v))

		if start is not None:
			arrow.start = _getArrowStartEnd(start)
		if end is not None:
			arrow.end = _getArrowStartEnd(end)

		if visibility:
			from Midas import _addMotionHandler

			global _tickMotionHandler
			from Midas import _tickMotionHandler

			param = {'command': 'fade', 'arrow': arrow, 'frames': frames}
			## need step

			if visibility == 'show':
				if not frames:
					arrow.shown = True
				else:
					## should show start from 0?  Is wierd
					## when someone 'shows' an arrow that is
					## already shown
					arrow.opacity = 0.0
					arrow.shown = True
					step = 1.0 / frames
					param['step'] = step
					_addMotionHandler(_fadeArrow, param)

			elif visibility == 'hide':
				if not frames:
					arrow.shown = False
				else:
					step = 1.0 / frames
					param['step'] = -(step)
					_addMotionHandler(_fadeArrow, param)
			else:
				raise MidasError("No such visibility mode '%s'" % visibility)
	elif action in ["adelete", "arrowdelete"]:
		if isinstance(itemID, Arrow):
			arrow = itemID
		else:
			for arrow in aModel.arrows:
				if arrow.ident == itemID:
					break
			else:
				raise MidasError("No such arrow with ID '%s'" % itemID)

		aModel.removeArrow(arrow)

	else:
		raise MidasError("Unknown 2dlabels action '%s'" % action)

	if action[0] != "a":
		model.setMajorChange()
	if not chimera.nogui:
		updateGUI()

def _getArrowStartEnd(arg):
	rawVal = arg
	if rawVal.count(',') != 1:
		raise MidasError("start/end values must be two comma-separated"
			" numbers (with no spaces)")
	try:
		x, y = [float(v) for v in rawVal.split(',')]
	except:
		raise MidasError("start/end values must be two comma-separated"
			" numbers (with no spaces)")
	return (x,y)

def updateGUI():
	from gui import IlabelDialog
	from chimera import dialogs
	dlg = dialogs.find(IlabelDialog.name)
	if dlg:
		dlg.updateGUI("command")

def contrastWith(rgb):
	if rgb[0]*0.59 + rgb[1] < 0.826:
		return (1, 1, 1)
	else:
		return (0, 0, 0)

def contrastWithBG():
	bg = chimera.viewer.background
	if bg:
		bgColor = bg.rgba()
	else:
		bgColor = (0, 0, 0)
	return contrastWith(bgColor)

def readFiles(fileNames, clear=True):
	from Arrows import _arrowsModel, ArrowsModel, Arrow
	if clear:

		lm = LabelsModel(create=False)
		if lm:
			for label in lm.labels[:]:
				lm.removeLabel(label)
			lm.setMajorChange()
		am = ArrowsModel(create=False)
		if am:
			for arrow in am.arrows[:]:
				am.removeArrow(arrow)
	from chimera import UserError
	for fileName in fileNames:
		from OpenSave import osOpen
		f = osOpen(fileName)
		for ln, line in enumerate(f):
			lineNum = ln + 1
			if not line.strip() or line.strip().startswith('#'):
				# skip blank lines / comments
				continue
			if line.lower().startswith("label"):
				labelID = line[5:].strip()
				LabelsModel().setMajorChange()
				text = label = None
				itemType = "label"
				continue
			if line.lower().startswith("arrow"):
				arrowArgs = []
				arrowKw = {}
				arrowID = line[5:].strip()
				if arrowID:
					arrowKw['ident'] = arrowID
				itemType = "arrow"
				continue
			if line[0] != '\t':
				f.close()
				raise UserError("%s, line %d: line must start with 'Label',"
					" 'Arrow', or tab" % (fileName, lineNum))
			try:
				semi = line.index(':')
			except ValueError:
				f.close()
				raise UserError("%s, line %d: line must have semi-colon"
					% (fileName, lineNum))
			name = line[1:semi].lower()
			value = line[semi+1:].strip()
			if itemType == "label":
				if not label and name != "(x,y)":
					f.close()
					raise UserError("%s, line %d: xy position must immediately"
						" follow 'Label' line" % (fileName, lineNum))
				if label and text is None and name != "text":
					f.close()
					raise UserError("%s, line %d: text must immediately"
						" follow xy position" % (fileName, lineNum))
				if name == "(x,y)":
					text = None
					try:
						pos = eval(value)
					except:
						f.close()
						raise UserError("%s, line %d: could not parse xy value"
							% (fileName, lineNum))
					if labelID:
						label = LabelsModel().newLabel(pos, labelID=labelID)
					else:
						label = LabelsModel().newLabel(pos)
				elif name == "text":
					try:
						text = eval(value)
					except:
						f.close()
						LabelsModel().removeLabel(label)
						raise UserError("%s, line %d: could not parse 'text' value"
							% (fileName, lineNum))
					label.set(text)
				elif name == "shown":
					if name == "shown":
						try:
							label.shown = eval(value.capitalize())
						except:
							f.close()
							LabelsModel().removeLabel(label)
							raise UserError("%s, line %d: could not parse 'shown'"
								" value" % (fileName, lineNum))
				else:
					chars = []
					for l in label.lines:
						chars.extend(l)
					if '),' in value:
						values = value.split('),')
						for i, v in enumerate(values[:-1]):
							values[i] = v + ')'
					elif ',' in value and not value.strip().startswith('('):
						values = value.split(',')
					else:
						values = [value] * len(chars)
					if len(values) != len(chars):
						f.close()
						raise UserError("%s, line %d: number of values not equal"
							" to numbers of characters in text (and not a single"
							" value)" % (fileName, lineNum))
					if name.startswith("font size"):
						try:
							values = [eval(v) for v in values]
						except:
							f.close()
							LabelsModel().removeLabel(label)
							raise UserError("%s, line %d: could not parse"
								" 'font size' value(s)" % (fileName, lineNum))
						for c, v in zip(chars, values):
							c.size = v
					elif name.startswith("font style"):
						for c, v in zip(chars, values):
							try:
								c.style = styleLookup(v.strip().lower())
							except:
								f.close()
								LabelsModel().removeLabel(label)
								raise UserError("%s, line %d: could not parse"
									" 'font style' value(s)" % (fileName, lineNum))
					elif name.startswith("font typeface"):
						for c, v in zip(chars, values):
							try:
								c.fontName = typefaceLookup(v.strip().lower())
							except:
								f.close()
								LabelsModel().removeLabel(label)
								raise UserError("%s, line %d: could not parse"
									" 'font typeface' value(s)" %
									(fileName, lineNum))
					elif name.startswith("color"):
						try:
							values = [eval(v) for v in values]
						except:
							f.close()
							LabelsModel().removeLabel(label)
							raise UserError("%s, line %d: could not parse"
								" 'color' value(s)" % (fileName, lineNum))
						for c, v in zip(chars, values):
							c.rgba = v
					else:
						LabelsModel().removeLabel(label)
						raise UserError("%s, line %d: unknown label attribute '%s'"
							% (fileName, lineNum, name))
			else: # arrow
				if name in ["start", "end"]:
					if len(arrowArgs) > 1:
						raise UserError("%s, line %d: start/end values already"
						" given for this arrow" % (fileName, lineNum))
					try:
						x, y = [float(v) for v in eval(value)]
					except:
						raise UserError("%s, line %d: could not parse"
							" %s xy value" % (fileName, lineNum, name))
					if name == "start":
						if arrowArgs:
							raise UserError("%s, line %d: start value already"
							" given for this arrow" % (fileName, lineNum))
						arrowArgs.append((x,y))
					else:
						if not arrowArgs:
							raise UserError("%s, line %d: no start value yet"
							" given for this arrow" % (fileName, lineNum))
						arrowArgs.append((x,y))
						arrow = ArrowsModel().addArrow(*arrowArgs, **arrowKw)
				else:
					if len(arrowArgs) != 2:
						raise UserError("%s, line %d: start/end values not yet"
						" both given for this arrow" % (fileName, lineNum))
					if name == "shown":
						try:
							shown = eval(value.capitalize())
						except:
							raise UserError("%s, line %d: could not parse %s value"
								% (fileName, lineNum, name))
						arrow.shown = shown
					elif name == "weight":
						try:
							weight = float(value)
						except ValueError:
							raise UserError("%s, line %d: value for weight ('%s')"
								" for arrow %s must be numeric." %
								(fileName, lineNum, value, name))
						arrow.weight = weight
					elif name == "head":
						if value not in Arrow.headStyles:
							raise UserError("%s, line %d: value for head style"
								" ('%s') for arrow %s must be one of %s." %
								(fileName, lineNum, value, name,
								", ".join(Arrow.headStyles)))
						arrow.head = value
					elif name == "color":
						try:
							r,g,b,a = [float(v) for v in eval(value)]
						except:
							raise UserError("%s, line %d: could not parse"
								" %s value" % (fileName, lineNum, name))
						arrow.color = (r,g,b,a)
					else:
						raise UserError("%s, line %d: unknown arrow attribute '%s'"
							% (fileName, lineNum, name))
		f.close()
	if chimera.nogui:
		dlg = None
	else:
		from gui import IlabelDialog
		from chimera import dialogs
		dlg = dialogs.find(IlabelDialog.name)
	if dlg:
		dlg.updateGUI("file")

FONT_STYLE_LABELS = ["normal", "italic", "bold", "bold italic"]
oglFont = chimera.OGLFont
FONT_STYLE_VALUES = [oglFont.normal, oglFont.italic, oglFont.bold,
					oglFont.bold | oglFont.italic]
def styleLookup(label):
	try:
		return FONT_STYLE_VALUES[FONT_STYLE_LABELS.index(label)]
	except ValueError:
		from Midas import MidasError
		raise MidasError("No known font style '%s'; choices are: %s" %
			(label, ", ".join(FONT_STYLE_LABELS)))

FONT_TYPEFACE_LABELS = ["sans serif", "serif", "fixed"]
FONT_TYPEFACE_VALUES = ["Sans Serif", "Serif", "Fixed"]
def typefaceLookup(label):
	try:
		return FONT_TYPEFACE_VALUES[FONT_TYPEFACE_LABELS.index(label)]
	except ValueError:
		from Midas import MidasError
		raise MidasError("No known font typeface '%s'; choices are: %s"
			% (label, ", ".join(FONT_TYPEFACE_LABELS)))

def writeFile(fileName):
	from OpenSave import osOpen
	f = osOpen(fileName, 'w')
	lm = LabelsModel(create=False)
	if lm:
		labelIDs = lm.labelMap.keys()
		labelIDs.sort()
		for labelID in labelIDs:
			if labelID.startswith(AUTO_ID_PREFIX):
				print>>f, "Label"
			else:
				print>>f, "Label %s" % labelID
			label = lm.labelMap[labelID]
			print>>f, "\t(x,y): %s" % repr(label.pos)
			print>>f, "\ttext: %s" % repr(unicode(label))
			print>>f, "\tshown: %s" % label.shown
			print>>f, "\tfont size(s): %s" % _valuesString([str(c.size)
									for l in label.lines for c in l])
			print>>f, "\tfont style(s): %s" % _valuesString([
				FONT_STYLE_LABELS[FONT_STYLE_VALUES.index(c.style)]
									for l in label.lines for c in l])
			print>>f, "\tfont typeface(s): %s" % _valuesString([
				FONT_TYPEFACE_LABELS[FONT_TYPEFACE_VALUES.index(c.fontName)]
									for l in label.lines for c in l])
			print>>f, "\tcolor(s): %s" % _valuesString([repr(c.rgba)
									for l in label.lines for c in l])
	from Arrows import _arrowsModel, ArrowsModel
	if _arrowsModel:
		for arrow in ArrowsModel().arrows:
			if arrow.ident:
				print>>f, "Arrow %s" % arrow.ident
			else:
				print>>f, "Arrow"
			print>>f, "\tstart: %s" % repr(arrow.start)
			print>>f, "\tend: %s" % repr(arrow.end)
			print>>f, "\tshown: %s" % arrow.shown
			print>>f, "\tweight: %g" % arrow.weight
			print>>f, "\thead: %s" % arrow.head
			print>>f, "\tcolor: %s" % repr(arrow.color)
	f.close()

def _fade(trigger, param, triggerData):
	
	if trigger:
		_tickMotionHandler(param)

	step  = param['step']
	label = param['label']

	label.changeAttrs(opacity=label.opacity+step)
	LabelsModel().setMajorChange()

	if param['frames'] == 0:
		if step < 0:
			## means this is the last iteration of a fade to black
			## after you fade it, need to set it back to former opacity !!
			label.shown = False
			label.opacity = 1.0
		if not chimera.nogui:
			updateGUI()

def _fadeArrow(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)

	step  = param['step']
	arrow = param['arrow']

	arrow.opacity += step
	if step < 0 and param['frames'] == 0:
		arrow.shown = False
		arrow.opacity = 1.0
		# change GUI shown status also
		from gui import IlabelDialog
		from chimera import dialogs
		dlg = dialogs.find(IlabelDialog.name)
		if dlg:
			dlg.arrowTable.refresh()

def _valuesString(values):
	if len(set(values)) == 1:
		return values[0]
	return ", ".join(values)

def keyCmd(cmdName, args):
	# syntax: makekey llx,lly urx,ury kw1 val1 kw2 val2 ... label1 color1 label2 color2 ...
	from Midas import MidasError, convertColor
	from Midas.midas_text import parseColorName
	from ColorKey import KeyModel
	from ColorKey import getKeyModel
	km = getKeyModel()
	if cmdName.startswith("un"):
		# remove key
		km.setKeyPosition(None)
		return
	try:
		xy1, xy2, args = args.split(None, 2)
	except ValueError:
		raise MidasError("Not enough arguments; type 'help %s' for more info"
			% cmdName)
	xys = []
	for xy in [xy1, xy2]:
		try:
			x, y = xy.split(',')
		except ValueError:
			raise MidasError("Key corner positions must be specified as x,y"
				" with no space after comma")
		try:
			x, y = float(x), float(y)
		except ValueError:
			raise MidasError("Key corner xy positions must be numeric")
		if not (0 <= x <= 1 and 0 <= y <= 1):
			raise MidasError("Key corner xy positions must be in the range 0-1")
		xys.append((x,y))
	keyAttrInfo = []
	while args:
		try:
			kw, valPlusArgs = args.split(None, 1)
		except ValueError:
			raise MidasError("Not enough arguments;"
				" type 'help %s' for more info" % cmdName)
		origKw = kw
		kw = kw.lower()
		attrNames = ("borderColor", "borderWidth", "colorTreatment",
			"fontSize", "fontStyle", "fontTypeface", "justification",
			"labelColor", "labelOffset", "labelSide", "numLabelSpacing",
			"tickLength", "tickMarks", "tickThickness")
		colorAttrs = set(["borderColor", "labelColor"])
		intAttrs = set(["borderWidth", "fontSize", "labelOffset", "tickLength",
			"tickThickness"])
		boolAttrs = set(["tickMarks"])
		enumAttrs = {
			"colorTreatment":
				(KeyModel.colorTreatmentValues, KeyModel.colorTreatmentValues),
			"fontStyle": (FONT_STYLE_LABELS, FONT_STYLE_VALUES),
			"fontTypeface": (FONT_TYPEFACE_LABELS, FONT_TYPEFACE_VALUES),
			"justification":
				(KeyModel.justificationValues, KeyModel.justificationValues),
			"labelSide": (KeyModel.labelSideValues, KeyModel.labelSideValues),
			"numLabelSpacing":
				(KeyModel.numLabelSpacingValues, KeyModel.numLabelSpacingValues)
		}
		matches = []
		for attrName in attrNames:
			if attrName.lower().startswith(kw):
				matches.append(attrName)
		if not matches:
			break
		elif len(matches) > 1:
			raise MidasError("Keyword '" + origKw + "' not long enough;"
				" could be either " + ", ".join(matches[:-1]) + " or "
				+ matches[-1])
		kw = matches[0]
		if kw in colorAttrs:
			cn, args = parseColorName(valPlusArgs)
			val = convertColor(cn)
			if val:
				val = val.rgba()
		elif kw in intAttrs:
			try:
				iv, args = valPlusArgs.split(None, 1)
			except ValueError:
				raise MidasError("No labels/colors given for key")
			try:
				val = int(iv)
			except ValueError:
				raise MidasError("Value for %s keyword must be an integer" % kw)
		elif kw in boolAttrs:
			try:
				bv, args = valPlusArgs.split(None, 1)
			except ValueError:
				raise MidasError("No labels/colors given for key")
			if bv.lower() not in ["true", "false"]:
				raise MidasError("Value for '" + kw + "' keyword must be"
					" 'true' or 'false'")
			val = eval(bv.capitalize())
		elif kw in enumAttrs:
			labels, values = enumAttrs[kw]
			try:
				fv, args = valPlusArgs.split(None, 1)
			except ValueError:
				raise MidasError("No labels/colors given for key")
			for label, val in zip(labels, values):
				undashed = fv.replace('-', ' ')
				if undashed == label:
					break
			else:
				raise MidasError("No such value for " + kw + " keyword '"
					+ kw + "';" + " choices are: " + ", ".join(
					[l.replace(' ', '-') for l in labels]))
		else:
			raise AssertionError("Unexpected non-match for keyword '%s'" % kw)
		keyAttrInfo.append((kw, val))

	if not args:
		raise MidasError("No labels/colors given for key")
	from Midas.midas_text import parseColorName, findQuoted
	from Midas import convertColor
	rgbasLabels = []
	while args:
		if args[0] in ['"', "'"]:
			label, args = findQuoted(args)
			label = label[1:-1]
			if not args:
				raise MidasError("No color specified for label '%s'" % label)
		else:
			try:
				label, args = args.split(None, 1)
			except ValueError:
				raise MidasError("No color specified for label '%s'" % args)
		cn, args = parseColorName(args)
		color = convertColor(cn, noneOkay=False)
		rgbasLabels.append((color.rgba(), label))
	if len(rgbasLabels) < 2:
		raise MidasError("Must provide at least two labels and corresponding"
			" colors")

	km.reset()
	for kw, val in keyAttrInfo:
		setFunc = 'set' + kw[0].upper() + kw[1:]
		getattr(km, setFunc)(val)
	km.setRgbasAndLabels(rgbasLabels)
	km.setKeyPosition(xys)
