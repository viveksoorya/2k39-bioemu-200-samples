from chimera.baseDialog import ModelessDialog

def profile(func):
	def wrapper(*args, **kw):
		import cProfile, pstats
		prof = cProfile.Profile()
		v = prof.runcall(func, *args, **kw)
		print func.__name__
		s = pstats.Stats(prof)
		s.sort_stats("cum", "time").print_callers(40)
		return v
	return wrapper

#
# Mixin for displaying RMF hierarchy
#
class RMFHierarchy:

	#
	# Must be supplied by derived class
	#
	def getFrame(self):
		raise NotImplementedError("RMFHierarchy.getFrame")

	def setFrame(self, frame):
		raise NotImplementedError("RMFHierarchy.setFrame")

	#
	# Update display to "frame"
	#
	def updateHierarchy(self, frame):
		if frame == self._hierarchyFrame:
			return
		self._hierarchyFrame = frame
		self.rmf.redisplayFrame(frame)
		self.setFrame(frame)

	#
	# GUI and methods for displaying and updating resolution
	#
	def setupHierarchyUI(self, master):
		from chimera.widgets import DisclosureFrame
		pane = DisclosureFrame(master, text="Hierarchy",
							collapsed=False)
		pane.pack(expand=True, fill="both")
		parent = pane.frame

		from CGLtk import Hybrid
		try:
			maxResolution = self.rmf.resolutions[-1]
		except IndexError:
			self.logScale = None
		else:
			import math
			bound = math.pow(10, math.ceil(math.log10(maxResolution)))
			if bound <= 1:
				bound = 2
			self.logScale = Hybrid.Logarithmic_Scale(parent,
						u"Resolution (\u212B)", 1, bound, 1)
			self.logScale.frame.pack(side="top", fill="x")
			self.logScale.callback(self._resolutionCB)
			self.currentResolutionIndex = -1
		import Tkinter, Pmw
		sf = Tkinter.Frame(parent)
		sf.pack(expand=True, fill="both")
		f = Tkinter.Frame(sf)
		f.pack(side="right", fill="y")
		self.cmdBox = Pmw.ButtonBox(f,
					orient="vertical",
					padx=0,
					pady=0,
					labelpos="n",
					label_text="Graphics")
		self.cmdBox.pack()
		self.cmdBox.add("Select", command=self._selectCB)
		self.cmdBox.add("Show", command=self._showCB)
		self.cmdBox.add("Show children", command=self._showChildrenCB)
		self.cmdBox.add("Show leaves", command=self._showLeavesCB)
		self.cmdBox.add("Hide", command=self._hideCB)
		self._makeTree(sf)
		self._hierarchyFrame = -1

	def quitHierarchyUI(self):
		pass

	def _makeTree(self, master):
		from TreeTable import TreeTable
		self.hierarchyMap = dict()
		self.hierarchyTable = TreeTable(master, "Data Hierarchy",
						command=self._selectHierarchy,
						header=False,
						selectMode="extended")
		row = self._addHierarchyRows(self.rmf.rootComponent)
		self.hierarchyTable.pack(expand=True, fill="both")
		self.hierarchyTable.launch()
		self.hierarchyTable.openRow(row)
		self._hierarchyNodeMap = None
		self._selectingHierarchy = False
		self._selectedHierarchyRows = list()

	def _addHierarchyRows(self, c, cRow=None):
		row = self.hierarchyTable.addRow(c.name, parentRow=cRow)
		self.hierarchyMap[row] = c
		for sc in c.components:
			if sc.showInGUI:
				self._addHierarchyRows(sc, row)
		return row

	def selectedComponents(self):
		return [ self.hierarchyMap[row]
			for row in self.hierarchyTable.selectedRows() ]

	def _selectHierarchy(self, ignoreEntryPath=None):
		rows = self.hierarchyTable.selectedRows()
		if rows == self._selectedHierarchyRows:
			return
		self._selectCB()
		self._selectedHierarchyRows = rows

	def updateResolution(self):
		rmf = self.rmf
		frame = self.getFrame()
		if not self.logScale:
			rmf.displayAtResolution(frame, 0)
			return
		resolution = self.logScale.value()
		for i, r in enumerate(self.rmf.resolutions):
			if resolution < r:
				ri = i
				break
		else:
			ri = len(self.rmf.resolutions)
		if ri == self.currentResolutionIndex:
			return
		self.currentResolutionIndex = ri
		rmf.displayAtResolution(frame, resolution)

	def _resolutionCB(self):
		self.updateResolution()

	def _showAtomsCB(self):
		sel = self._selectedAtoms()
		for a in sel.atoms():
			a.display = True

	def _showRibbonCB(self):
		sel = self._selectedAtoms()
		for r in sel.residues():
			r.ribbonDisplay = True

	def _hideAtomsCB(self):
		sel = self._selectedAtoms()
		for a in sel.atoms():
			a.display = False

	def _hideRibbonCB(self):
		sel = self._selectedAtoms()
		for r in sel.residues():
			r.ribbonDisplay = False

	def _showCB(self):
		self._openDisplayedAncestors()
		for c in self.selectedComponents():
			c.showGraphics(True)

	def _showChildrenCB(self):
		self._openDisplayedAncestors()
		for c in self.selectedComponents():
			if c.components:
				c.showGraphics(False, hideChildren=False)
				for sc in c.components:
					sc.showGraphics(True)

	def _showLeavesCB(self):
		self._openDisplayedAncestors()
		for c in self.selectedComponents():
			self._showLeaf(c)

	def _showLeaf(self, c):
		if c.isReprLeaf() or not c.components:
			c.showGraphics(True, hideChildren=False)
		else:
			c.showGraphics(False, hideChildren=False)
		for sc in c.components:
			self._showLeaf(sc)

	def _openDisplayedAncestors(self):
		# When we show a node, if an ancestor node is being
		# shown as a bounding sphere, then we want to hide
		# the bounding sphere and show all the other child
		# nodes that do not lead the currently selected nodes.
		# For example, if a molecule is shown as a single
		# bounding sphere and we choose to display an atom
		# in a residue, then we not only show the selected atom
		# but we need to hide the molecule bounding sphere;
		# all residues not containing the selected atom should
		# be displayed as bounding spheres; the residue containing
		# the selected atom should display all its atoms and not
		# its bounding sphere.
		items = self.selectedComponents()
		skip = set(items)

		# construct set of components that need to display
		# their children
		needToOpen = set()
		for c in items:
			parents = list()
			while c.parent is not None:
				pc = c.parent
				shown = pc.isShown
				if not shown:
					parents.add(pc)
					c = pc
				else:
					needToOpen.update(parents)
					break

		# for each saved component, display each child unless
		# it is (a) a saved component, or (b) a selected component.
		# The latter two cases will be taken care of either
		# by this loop (case a) or by the caller (case b)
		# so we do not need to do anything.
		for c in needToOpen:
			for sc in c.components:
				if sc in needToOpen or sc in skip:
					continue
				sc.showGraphics(True)

	def _hideCB(self):
		for c in self.selectedComponents():
			c.showGraphics(False, hideChildren=True)

	def _selectCB(self):
		self._selectingHierarchy = True
		sel = self._selectedAtoms()
		from chimera import selection
		selection.setCurrent(sel)

	def _selectedAtoms(self):
		selectedItems = set()
		for c in self.selectedComponents():
			c.addChimeraObjects(selectedItems)
		from chimera import selection
		return selection.ItemizedSelection(selectedItems)

	def updateHierarchySelection(self, selected):
		if self._selectingHierarchy:
			self._selectingHierarchy = False
			return
		if self._hierarchyNodeMap is None:
			import weakref
			self._hierarchyNodeMap = weakref.WeakKeyDictionary()
			for row, c in self.hierarchyMap.iteritems():
				if not c.isReprLeaf():
					continue
				sel = set()
				c.addChimeraObjects(sel)
				for o in sel:
					self._hierarchyNodeMap[o] = row
		rows = set()
		for a in (selected.atoms() + selected.bonds()
						+ selected.molecules()):
			try:
				rows.add(self._hierarchyNodeMap[a])
			except KeyError:
				pass
		if not rows:
			return
		table = self.hierarchyTable
		table.clearHighlights()
		for row in rows:
			table.displayRow(row)
			table.highlightRow(row, True, deselect=False)
		table.makeVisible(iter(rows).next())
		self._selectedHierarchyRows = rows

	def _dumpSelected(self, node):
		if node.selected:
			print " selected", node
		else:
			print " not selected", node
		print " children", node.children
		for c in node.children:
			self._dumpSelected(c)

#
# Mixin for displaying RMF features
#
class RMFFeatures:

	#
	# Must be supplied by derived class
	#
	def getFrame(self):
		raise NotImplementedError("RMFFeatures.getFrame")

	def setFrame(self, frame):
		raise NotImplementedError("RMFFeatures.setFrame")

	#
	# Update features to current frame
	#
	def updateFeatures(self):
		if not self.featureTable:
			return
		frame = self.getFrame()
		if self._featureFrame != -1:
			self.rmf.setCurrentFrame(self._featureFrame)
			for row in self._selectedFeatureRows:
				f = self.featureMap[row]
				f.showLeaves(False)
			self.rmf.setCurrentFrame(frame)
		self._featureFrame = frame
		for row in self._selectedFeatureRows:
			f = self.featureMap[row]
			f.showLeaves(True)
		for row, f in self.featureMap.iteritems():
			try:
				score = f.getScore()
			except KeyError:
				label = "-"
			else:
				label = "%g" % score
			self.featureTable.setCellText(row, self._valueColumn,
									label)
		if self.mplBackground:
			self._updatePlotFrame(frame)

	#
	# Methods for drawing and updating plot
	#
	MarkerColors = [
		(	'o',	'b'	),	# circle blue
		(	'o',	'g'	),	# circle green
		(	'o',	'r'	),	# circle red
		(	'o',	'c'	),	# circle cyan
		(	'o',	'm'	),	# circle magenta
						# skip yellow, hard to see
		(	's',	'b'	),	# square blue
		(	's',	'g'	),	# square green
		(	's',	'r'	),	# square red
		(	's',	'c'	),	# square cyan
		(	's',	'm'	),	# square magenta
	]

	def _drawPlot(self, event=None):
		self.mplAxes.clear()
		from matplotlib.ticker import FixedLocator
		loc = FixedLocator([self.offset,
				self.rmf.frameCount - 1 + self.offset])
		self.mplAxes.get_xaxis().set_major_locator(loc)
		pad = int((self.rmf.frameCount - 1) / 20)
		loc.set_bounds(self.offset - pad,
				self.rmf.frameCount - 1 + self.offset + pad)
		anyRow = False
		mc = 0
		rows = self.featureTable.selectedRows()
		if not rows:
			return
		#from math import isinf, isnan
		scores = self.rmf.getAllScores(self._toplevel,
				[ self.featureMap[row] for row in rows ])
		featureCount, frameCount = scores.shape
		import numpy
		x = numpy.arange(self.offset, self.offset + frameCount)
		for f in range(featureCount):
			y = scores[f]
			mask = numpy.isfinite(y)
			if not numpy.any(mask):
				continue
			#for frame in range(frameCount):
			#	score = scores[f, frame]
			#	if score is not None and not isinf(score):
			#		x.append(frame + self.offset)
			#		y.append(score)
			#if not x:
			#	#from numpy.random import randn
			#	#x = range(1, self.rmf.frameCount + 1)
			#	#y = randn(self.rmf.frameCount)
			#	continue
			marker, color = self.MarkerColors[mc]
			mc = (mc + 1) % len(self.MarkerColors)
			self.mplAxes.scatter(x[mask], y[mask], label=row.text,
						c=color, marker=marker,
						s=12, picker=8)
			anyRow = True
		if not anyRow:
			self.mplAxes.set_title("no scores to display",
						fontproperties=self.mplFontProp)
		else:
			#self.mplAxes.grid(True)
			self.mplAxes.set_title("scores",
						fontproperties=self.mplFontProp)
			self.mplAxes.legend(prop=self.mplFontProp)
		self.mplFrame.draw()
		canvas = self.mplFrame.figureCanvas
		self.mplBackground = canvas.copy_from_bbox(
						self.mplAxes.bbox)
		self._updatePlotFrame(self.getFrame())

	def _updatePlotFrame(self, frame):
		canvas = self.mplFrame.figureCanvas
		canvas.restore_region(self.mplBackground)
		self.mplCurrentFrame.set_xdata([ frame + self.offset ])
		self.mplAxes.draw_artist(self.mplCurrentFrame)
		canvas.blit(self.mplAxes.bbox)

	#
	# GUI and methods for displaying features
	#
	def setupFeatureUI(self, master):
		if not self.rmf.rootFeature.features:
			# No features ?!
			self.featureTable = None
			return

		from chimera.widgets import DisclosureFrame
		pane = DisclosureFrame(master, text="Features", collapsed=False)
		pane.pack(expand=True, fill="both")
		parent = pane.frame

		self._selectedFeatureRows = set()
		from TreeTable import TreeTable
		self.featureMap = dict()
		self.featureTable = TreeTable(parent, "Feature",
						browsecmd=self._selectFeature,
						header=True,
						width=30,
						selectMode="extended")
		self._valueColumn = self.featureTable.addColumn("Value")
		row = self._addFeatureRows(self.rmf.rootFeature)
		self.featureTable.pack(side="left", expand=True, fill="both")
		self.featureTable.launch()
		self.featureTable.openRow(row)

		import Tkinter
		f = Tkinter.Frame(parent)
		f.pack(side="right", expand=True, fill="both")
		b = Tkinter.Button(f, text="Update Plot",
						command=self._drawPlot)
		b.pack(side="bottom")
		from chimera.mplDialog import MPLFrame
		self.mplBackground = None
		self.mplFrame = MPLFrame(f, showToolbar=False)
		self.mplAxes = self.mplFrame.add_subplot(1, 1, 1)
		self.mplCurrentFrame = self.mplAxes.axvline(x=1,
					ls='--', c='k', animated=True)
		fcf = self.mplFrame.figureCanvas.get_tk_widget()
		fcf.config(width=200, height=200)
		fcf.pack(expand=True, fill="both")
		from matplotlib.font_manager import FontProperties
		self.mplFontProp = FontProperties(size="x-small")

		self.mplMotion = None
		if self.rmf.frameCount > 1:
			self.mplFrame.mpl_connect("button_press_event",
							self._onButtonPress)
			self.mplFrame.mpl_connect("button_release_event",
							self._onButtonRelease)
		#self.mplFrame.mpl_connect("resize_event", self._drawPlot)
		self._featureFrame = -1
		self._selectingFeature = False
		self._featureNodeMap = None

	def quitFeatureUI(self):
		pass

	def _addFeatureRows(self, parent, parentRow=None):
		row = self.featureTable.addRow(parent.name,
						parentRow=parentRow,
						sortable=True)
		self.featureTable.addCell(row, self._valueColumn, "-")
		self.featureMap[row] = parent
		for f in parent.features:
			self._addFeatureRows(f, row)
		return row

	def _selectFeature(self, ignoreEntryPath=None):
		self._selectingFeature = True
		table = self.featureTable
		rows = set(table.selectedRows())
		if rows == self._selectedFeatureRows:
			return
		for row in self._selectedFeatureRows - rows:
			f = self.featureMap[row]
			f.showLeaves(False)
		for row in rows - self._selectedFeatureRows:
			f = self.featureMap[row]
			f.showLeaves(True)
		sel = set()
		for row in rows:
			f = self.featureMap[row]
			f.addChimeraObjects(sel)
		if sel:
			from chimera.selection \
				import ItemizedSelection, setCurrent
			setCurrent(ItemizedSelection(sel))
		self._selectedFeatureRows = rows
		#self._drawPlot()

	def _onButtonPress(self, event):
		if event.xdata is None:
			return
		try:
			self.setFrame(int(event.xdata))
		except ValueError:
			pass
		if not self.mplMotion:
			self.mplMotion = self.mplFrame.mpl_connect(
						"motion_notify_event",
						self._onButtonPress)

	def _onButtonRelease(self, event):
		if self.mplMotion:
			self.mplFrame.mpl_disconnect(self.mplMotion)
			self.mplMotion = None

	def updateFeaturesSelection(self, selected):
		if self.featureTable is None:
			# No features, no update
			return
		if self._selectingFeature:
			self._selectingFeature = False
			return
		if self._featureNodeMap is None:
			import weakref
			self._featureNodeMap = weakref.WeakKeyDictionary()
			for row, f in self.featureMap.iteritems():
				if f.features:
					# Skip container features when
					# checking graphical selection
					continue
				sel = set()
				f.addChimeraObjects(sel)
				for o in sel:
					try:
						self._featureNodeMap[o].append(row)
					except KeyError:
						self._featureNodeMap[o] = [row]
		rows = set()
		for o in (selected.atoms() + selected.bonds()
						+ selected.molecules()):
			try:
				rows.update(self._featureNodeMap[o])
			except KeyError:
				pass
		if not rows:
			return
		for row in self._selectedFeatureRows - rows:
			f = self.featureMap[row]
			f.showLeaves(False)
		for row in rows - self._selectedFeatureRows:
			f = self.featureMap[row]
			f.showLeaves(True)
		table = self.featureTable
		table.clearHighlights()
		for row in rows:
			table.displayRow(row)
			table.highlightRow(row, True, deselect=False)
		table.makeVisible(iter(rows).next())
		self._selectedFeatureRows = rows
		#self._drawPlot()

#
# Class for simple extension manager callbacks
#
class EMCallbacks:
	def emName(self):
		return self.title
	def emRaise(self):
		self.enter()
	def emHide(self):
		self.Cancel()
	Hide = emHide
	def emQuit(self):
		self.Quit()

#
# Classes for movie-style interface
#
class RMFTraj:
	"""RMF trajectory class for MovieDialog"""
	def __len__(self):
		return len(self.molecule.coordSets)
	def __getitem__(self, key):
		return None

from Movie.gui import MovieDialog
class RMFTrajDialog(MovieDialog, RMFHierarchy, RMFFeatures, EMCallbacks):

	def __init__(self, rmf, **kw):
		# displayed frame vs index offset
		# MovieDialog uses 1-based indexing, we use 0-based
		self.offset = 1
		self.rmf = rmf
		import os.path
		head, tail = os.path.split(rmf.filename)
		if head:
			title = "%s - %s" % (tail, head)
		else:
			title = tail
		self.title = "RMF: %s" % title
		self._rmfUpdateHandler = None
		self._rmfModels = self.rmf.getModels()
		ensemble = RMFTraj()
		ensemble.name = rmf.filename
		# MovieDialog uses 1-based indexing
		ensemble.startFrame = 1
		ensemble.endFrame = rmf.frameCount
		ensemble.molecule = self._rmfModels[0]
		kw["externalEnsemble"] = True
		MovieDialog.__init__(self, ensemble, shareXform=False, **kw)
		self._rmfUpdateHandler = self.triggers.addHandler(
						self.NEW_FRAME_NUMBER,
						self._rmfUpdateCB, None)
		# We do not need to register with manager because
		# MovieDialog has already done so

	def destroy(self):
		if self._rmfUpdateHandler:
			self.triggers.deleteHandler(self.NEW_FRAME_NUMBER,
							self._rmfUpdateHandler)
			self._rmfUpdateHandler = None
		MovieDialog.destroy(self)

	def _rmfUpdateCB(self, triggerName, ignore, frame):
		# MovieDialog uses 1-based indexing, we use 0-based
		frame -= 1
		self.rmf.loadFrame(frame)
		self.updateHierarchy(frame)
		self.updateFeatures()

	def getFrame(self):
		# MovieDialog uses 1-based indexing, we use 0-based
		return self.currentFrame.get() - 1

	def setFrame(self, frame):
		if frame == self.getFrame():
			return
		self.rmf.loadFrame(frame)

	def fillInUI(self, parent):
		from chimera.widgets import DisclosureFrame
		moviePane = DisclosureFrame(parent, text="Frames",
					collapsed=self.rmf.frameCount<=1)
		moviePane.pack(expand=False, fill="x")
		MovieDialog.fillInUI(self, moviePane.frame)
		self.setupFeatureUI(parent)
		self.setupHierarchyUI(parent)

		self.currentFrame.set(1)
		self.updateResolution()
		self._rmfUpdateCB("internal", None, 1)
		parent.winfo_toplevel().protocol('WM_DELETE_WINDOW',
							self.emHide)

	def Quit(self):
		self.destroy()

#
# class that manages frame updates itself instead of using trajectory support
#
class RMFViewerDialog(ModelessDialog, RMFHierarchy, RMFFeatures, EMCallbacks):

	buttons = ( "Hide", "Quit" )
	help = "UsersGuide/rmfviewer.html"

	def __init__(self, rmf, **kw):
		# displayed frame vs index offset
		# We use 0-base for both, so no offset
		self.offset = 0
		self.rmf = rmf
		import os.path
		head, tail = os.path.split(rmf.filename)
		if head:
			title = "%s - %s" % (tail, head)
		else:
			title = tail
		self.title = "RMF: %s" % title
		ModelessDialog.__init__(self, **kw)
		from chimera.extension import manager
		manager.registerInstance(self)
		import chimera
		self._quitHandler = chimera.triggers.addHandler(
					chimera.APPQUIT, self._quitCB, None)
		self._selHandler = chimera.triggers.addHandler(
					"selection changed", self._selCB, None)
		self._removeHandler = chimera.openModels.addRemoveHandler(
					self._removeCB, None)

	def destroy(self):
		import chimera
		if self._removeHandler:
			chimera.openModels.deleteRemoveHandler(
						self._removeHandler)
			self._removeHandler = None
		if self._selHandler:
			chimera.triggers.deleteHandler("selection changed",
							self._selHandler)
			self._selHandler = None
		if self._quitHandler:
			chimera.triggers.deleteHandler(chimera.APPQUIT,
							self._quitHandler)
			self._quitHandler = None
		if self.rmf:
			self.rmf.destroy()
			self.rmf = None
			from chimera.extension import manager
			manager.deregisterInstance(self)
			ModelessDialog.destroy(self)

	def getFrame(self):
		# MovieDialog uses 1-based indexing, we use 0-based
		if self.playback:
			return self.playback.getFrame()
		else:
			return 0

	def setFrame(self, frame):
		if frame < 0 or frame >= self.rmf.frameCount:
			if self.rmf.frameCount > 0:
				raise ValueError("frame out of range (%d of %d)"
						% (frame, self.rmf.frameCount))
		if self.playback:
			self.playback.setFrame(frame)
		self.frameName.config(text=self.rmf.getFrameName(frame))

	def _loadFrame(self, frame):
		self.rmf.loadFrame(frame)
		self.updateHierarchy(frame)
		self.updateFeatures()

	def prevFrame(self):
		frame = self.currentFrame.get() - 1
		if frame < 0:
			if not self.loopVar.get():
				self.pause()
				return
			frame = self.rmf.frameCount - 1
		self.setFrame(frame)

	def fillInUI(self, parent):
		if self.rmf.frameCount > 1:
			#from chimera.widgets import DisclosureFrame
			#moviePane = DisclosureFrame(parent, text="Frames",
			#				collapsed=False)
			#moviePane.pack(expand=False, fill="x")
			from PlaybackFrame import PlaybackFrame
			#self.playback = PlaybackFrame(moviePane.frame, 0,
			#				self.rmf.frameCount - 1,
			#				self._loadFrame)
			self.playback = PlaybackFrame(parent, 0,
							self.rmf.frameCount - 1,
							self._loadFrame)
			self.playback.pack(fill="x")
		else:
			self.playback = None
		import Tkinter
		self.frameName = Tkinter.Label(parent, anchor="w",
						text=self.rmf.getFrameName(0))
		self.frameName.pack(fill="x")
		self.setupFeatureUI(parent)
		self.setupHierarchyUI(parent)
		self._loadFrame(0)
		self.updateResolution()
		parent.winfo_toplevel().protocol('WM_DELETE_WINDOW',
							self.emHide)

	def Hide(self):
		self.Close()

	def Quit(self):
		if self.playback:
			self.playback.cleanup()
		self.quitFeatureUI()
		self.quitHierarchyUI()
		self.destroy()

	def _quitCB(self, triggerName, ignore, frame):
		self.Quit()

	def _selCB(self, triggerName, ignore, selected):
		self.updateHierarchySelection(selected)
		self.updateFeaturesSelection(selected)

	def _removeCB(self, triggerName, ignore, models):
		myModels = set(self.rmf.getModels())
		shouldQuit = False
		for m in models:
			if m in myModels:
				shouldQuit = True
		if shouldQuit:
			import chimera
			chimera.openModels.deleteRemoveHandler(
						self._removeHandler)
			self._removeHandler = None
			self.Quit()

def getIconButton(parent, filename, cb):
	import os.path
	import Movie
	iconPath = os.path.join(Movie.__path__[0], "Icons", filename)
	from Movie.gui import GenImage
	imtk = GenImage(iconPath, parent)
	from Tkinter import Button
	b = Button(parent, command=cb, image=imtk)
	b._image = imtk
	return b
