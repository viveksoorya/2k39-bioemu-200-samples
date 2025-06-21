# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: Cluster.py 35794 2012-03-09 01:26:57Z pett $

import Tkinter, Pmw
from chimera.baseDialog import ModelessDialog
from chimera import UserError
from CGLtk.color import colorRange, rgba2tk

class ClusterStarter(ModelessDialog):
	title = "Get Clustering Parameters"
	help = "ContributedSoftware/movie/movie.html#clustering"

	def __init__(self, movie):
		self.movie = movie
		movie.subdialogs.append(self)
		ModelessDialog.__init__(self)

	def destroy(self):
		self.movie = None
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		from chimera.tkoptions import IntOption, BooleanOption, \
							FloatOption
		Tkinter.Label(parent, text="Cluster trajectory",
				relief="ridge", bd=4).grid(row=0,
				column=0, columnspan=2, sticky="ew")

		startFrame = self.movie.startFrame
		endFrame = self.movie.endFrame
		self.startFrame = IntOption(parent, 1, "Starting frame",
			startFrame, None, min=startFrame, max=endFrame, width=6)

		numFrames = endFrame - startFrame + 1
		defStride = 1 + int(numFrames/300)
		self.stride = IntOption(parent, 2, "Step size", defStride,
			None, min=1, max=numFrames, width=3)

		self.endFrame = IntOption(parent, 3, "Ending frame", endFrame,
			None, min=startFrame, max=endFrame, width=6)

		self.useSel = BooleanOption(parent, 4, "Cluster based on "
				"current selection, if any", True, None)

		self.ignoreBulk = BooleanOption(parent, 5, "Ignore solvent and "
							"non-metal ions", True, None)
		self.ignoreHyds = BooleanOption(parent, 6, "Ignore hydrogens",
							True, None)
		from gui import IgnoreMetalIonsOption as IMIO
		self.metalIons = IMIO(parent, 7, IMIO.defaultLabel, IMIO.defaultValue, None)

	def Apply(self):
		startFrame = self.startFrame.get()
		stride = self.stride.get()
		endFrame = self.endFrame.get()
		if endFrame <= startFrame:
			self.enter()
			raise UserError("Start frame must be less"
							" than end frame")
		if startFrame < self.movie.startFrame \
		or endFrame > self.movie.endFrame:
			self.enter()
			raise UserError("Start or end frame outside"
							" of trajectory")
		ClusterDialog(self.movie, startFrame, self.stride.get(),
			endFrame, self.useSel.get(), self.ignoreBulk.get(),
			self.ignoreHyds.get(), self.metalIons.get())

class ClusterDialog(ModelessDialog):
	oneshot = True
	provideStatus = True
	buttons = ("Save", "Close",)
	title = "Clustering"
	help = "ContributedSoftware/movie/movie.html#clusterdialog"

	def __init__(self, movie, startFrame, stride, endFrame, useSel,
						ignoreBulk, ignoreHyds, metalIons):
		self.movie = movie
		self.movie.subdialogs.append(self)
		self.startFrame = startFrame
		self.stride = stride
		self.endFrame = endFrame
		self.useSel = useSel
		self.ignoreBulk = ignoreBulk
		self.ignoreHyds = ignoreHyds
		self.metalIons = metalIons
		ModelessDialog.__init__(self)

	def Close(self):
		if self._computing:
			self._abort = True
			return
		self.movie.subdialogs.remove(self)
		ModelessDialog.Close(self)

	def Save(self):
		if not hasattr(self, '_saveDialog'):
			self._saveDialog = _SaveClusteringInfo(self,
				title="Save Clustering Information")
		self._saveDialog.enter()

	def destroy(self):
		# calling ModelessDialog.Close causes recursion
		if hasattr(self, '_newFrameHandler'):
			self.movie.triggers.deleteHandler(self.movie.NEW_FRAME_NUMBER,
											self._newFrameHandler)
		if hasattr(self, '_saveDialog'):
			self._saveDialog.destroy()
			delattr(self, '_saveDialog')
		self.movie = None
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		from chimera import UserError

		self._computing = False

		# load needed coord sets...
		frameNums = range(self.startFrame, self.endFrame+1, self.stride)
		for frameNum in frameNums:
			if not self.movie.findCoordSet(frameNum):
				self.status("loading frame %d" % frameNum)
				self.movie._LoadFrame(frameNum,
							makeCurrent=False)

		# compute RMSDs
		from analysis import analysisAtoms, AnalysisError
		try:
			atoms = analysisAtoms(self.movie.model.Molecule(), self.useSel,
					self.ignoreBulk, self.ignoreHyds, self.metalIons)
		except AnalysisError, v:
			self.Close()
			raise UserError(unicode(v))

		self.buttonWidgets['Close'].configure(text="Abort")
		self.buttonWidgets['Save'].configure(state="disabled")
		frameAdjust = 0
		if self.movie.findCoordSet(self.startFrame).id != self.startFrame:
			frameNums = [fn-1 for fn in frameNums]
			frameAdjust = 1
		from cluster import cluster, ClusterError
		from chimera import CancelOperation
		try:
			clustering, reducedFrameNums, sameAs = cluster(self.movie.model.Molecule(), atoms,
				frameNums, testAbort=self._testAbort, status=self.status)
		except CancelOperation:
			parent.after_idle(self.Close)
			return
		except ClusterError, v:
			self.Close()
			raise UserError(unicode(v))
		# sameAs map can map to clusters that are _also_ keys
		# in the sameAs map; make them map to their final
		# cluster...
		finalSA = {}
		for k, v in sameAs.items():
			while v in sameAs:
				v = sameAs[v]
			finalSA[k] = v
		sameAs = finalSA
		self.buttonWidgets['Close'].configure(text="Close")
		self.clusterMap = {}
		self.representatives = []
		self.clusters = []
		unsortedClusters = [(c, clustering.representative(c))
						for c in clustering.clusters]
		# sort the clusters so that the coloring is reproducible
		# while trying to avoid using adjacent colors for
		# adjacent clusters
		clusters = [unsortedClusters.pop()]
		while unsortedClusters:
			bestCluster = bestVal = None
			for uc in unsortedClusters:
				val = abs(uc[-1] - clusters[-1][-1])
				if len(clusters) > 1:
					val += 0.5 * abs(uc[-1]
							- clusters[-2][-1])
				if len(clusters) > 2:
					val += 0.25 * abs(uc[-1]
							- clusters[-3][-1])
				if bestVal == None or val > bestVal:
					bestCluster = uc
					bestVal = val
			unsortedClusters.remove(bestCluster)
			clusters.append(bestCluster)
		colors = colorRange(len(clusters))
		for c, rep in clusters:
			cluster = Cluster()
			cluster.color = colors.pop()
			self.clusters.append(cluster)
			cluster.representative = reducedFrameNums[rep] + frameAdjust
			cluster.members = []
			for m in c.members():
				f = reducedFrameNums[m] + frameAdjust
				self.clusterMap[f] = cluster
				cluster.members.append(f)
		for dup, base in sameAs.items():
			c = self.clusterMap[base]
			self.clusterMap[dup+frameAdjust] = c
			c.members.append(dup+frameAdjust)
		self.status("%d clusters" % len(self.clusters))
		self.buttonWidgets['Save'].configure(state="normal")

		from CGLtk.Table import SortableTable
		self.table = SortableTable(parent)
		self.table.addColumn("Color", "color", format=(False, False),
							titleDisplay=False)
		membersCol = self.table.addColumn("Members",
				"lambda c: len(c.members)", format="%d")
		self.table.addColumn("Representative Frame", "representative",
								format="%d")
		self.table.setData(self.clusters)
		self.table.launch(browseCmd=self.showRep)
		self.table.sortBy(membersCol)
		self.table.sortBy(membersCol) # to get descending order
		self.table.grid(sticky="nsew")

		self.averageButton = Tkinter.Button(parent, state="disabled", pady=0,
			text="Generate average structure for cluster", command=self._genAverage)
		self.averageButton.grid(row=1, column=0)

		self.resNetButton = Tkinter.Button(parent, state="disabled", pady=0,
			text="Generate residue-interaction network for cluster",
			command=self._genNetwork)
		self.resNetButton.grid(row=2, column=0)

		self.resNetDiffButton = Tkinter.Button(parent, state="disabled", pady=0,
			text="Generate residue-interaction difference network for cluster pair",
			command=self._genDiffNetwork)
		self.resNetDiffButton.grid(row=3, column=0)

		from matplotlib.figure import Figure
		self.mpFigure = Figure(figsize=(4,1))
		self.timeLine = self.mpFigure.add_subplot(111, axisbg='0.75')
		from matplotlib.backends.backend_tkagg \
			import FigureCanvasTkAgg, NavigationToolbar2TkAgg
		mpFrame = Tkinter.Frame(parent) # matplotlib uses pack...
		mpFrame.grid(row=4, column=0, sticky="nsew")
		self.mpFigureCanvas = FigureCanvasTkAgg(self.mpFigure, master=mpFrame)
		self.mpFigureCanvas.get_tk_widget().pack(side="top", fill="both", expand=True)
		nt = NavigationToolbar2TkAgg(self.mpFigureCanvas, mpFrame)
		nt.set_message = self._mp2status
		nt.update()
		for event in ['button_press', 'motion_notify']:
			self.mpFigure.canvas.mpl_connect(event + '_event',
											self._mouse_handler)
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(0, weight=1)
		self.drawTimeLine()

		self._newFrameHandler = self.movie.triggers.addHandler(
					self.movie.NEW_FRAME_NUMBER, self._newFrameCB, None)

	def drawFrameIndicator(self, fn):
		tl = self.timeLine
		cluster = self.clusterMap.get(fn)
		if cluster:
			mfc = 'w'
		else:
			mfc = 'y'
		if not hasattr(self, "frameMarker"):
			self.frameMarker = tl.plot([fn], [2.0],
						marker='v', mfc=mfc, mec='k', ms=18, animated=True)[0]
		canvas = tl.figure.canvas
		canvas.restore_region(self.timeLineBackground)
		self.frameMarker.set_xdata(fn)
		self.frameMarker.set_mfc(mfc)
		tl.draw_artist(self.frameMarker)
		canvas.blit(tl.bbox)

	def drawTimeLine(self):
		tl = self.timeLine
		tl.clear()
		cluster = None
		edges = []
		items = []
		clusters = []
		selectedClusters = self.table.selected()
		frameNums = range(self.startFrame, self.endFrame+1, self.stride)
		for fn in frameNums:
			c = self.clusterMap[fn]
			if c == cluster:
				continue
			cluster = c
			items.append(fn)
			if cluster in selectedClusters:
				items.append(fn)
			edges.append(fn - 0.5)
			clusters.append(cluster)
			cluster.patches = []
		edges.append(self.endFrame + 0.5)
		n, bins, patches = tl.hist(items, bins=edges)
		for patch, cluster in zip(patches, clusters):
			cluster.patches.append(patch)
			# force patch to get color...
			# while preventing redraw from color setting
			cluster.canvas = None
			cluster.color = cluster.color
			cluster.canvas = self.mpFigure.canvas
		for tick in tl.yaxis.get_major_ticks():
			tick.label1On = tick.label2On = tick.tick1On = tick.tick2On = False
		tl.set_ylim(ymax=2.0)
		tl.set_xlim(self.startFrame-0.5, self.endFrame+0.5)
		if not selectedClusters:
			tl.text((self.endFrame + self.startFrame)/2.0, 1.5,
				"Choose in above table to show cluster",
				ha="center", va="center", size="small")
		self.mpFigureCanvas.show()
		self.timeLineBackground = tl.figure.canvas.copy_from_bbox(tl.bbox)
		self.drawFrameIndicator(self.movie.currentFrame.get())

	def showRep(self, clusters):
		if clusters:
			self.movie.currentFrame.set(clusters[0].representative)
			self.movie.LoadFrame()
		state = "normal" if len(clusters) == 1 else "disabled"
		self.averageButton.config(state=state)
		self.resNetButton.config(state=state)
		state = "normal" if len(clusters) == 2 else "disabled"
		self.resNetDiffButton.config(state=state)
		self.drawTimeLine()

	def _genAverage(self):
		cluster = self.table.selected()[0]
		frameOffset = self.movie.findCoordSet(self.startFrame).id - self.startFrame
		from AverageDialog import AverageDialog
		AverageDialog(self.movie, ([f + frameOffset for f in cluster.members],
			cluster.representative + frameOffset))

	def _genDiffNetwork(self):
		clusters = self.table.selected()
		frameOffset = self.movie.findCoordSet(self.startFrame).id - self.startFrame
		from ResInteraction import ResInteractionStarter
		ResInteractionStarter(self.movie, [([f + frameOffset for f in cluster.members],
			cluster.representative + frameOffset) for cluster in clusters],
			differenceNetwork=True)

	def _genNetwork(self):
		cluster = self.table.selected()[0]
		frameOffset = self.movie.findCoordSet(self.startFrame).id - self.startFrame
		from ResInteraction import ResInteractionStarter
		ResInteractionStarter(self.movie, ([f + frameOffset for f in cluster.members],
			cluster.representative + frameOffset))

	def _newFrameCB(self, trigName, myData, frameNumber):
			self.drawFrameIndicator(frameNumber)

	def _mouse_handler(self, event):
		if type(event.button) != int or event.xdata == None:
			return
		fn = min(max(self.startFrame, int(event.xdata+0.5)), self.endFrame)
		self.movie.LoadFrame(fn)

	def _mp2status(self, msg):
		for i in range(len(msg)):
			if msg[i:i+2] == "x=":
				frame = int(float(msg[i+2:].split()[0])+0.5)
				if self.startFrame <= frame <= self.endFrame:
					self.status("frame %d" % frame)
				return
		self.status(msg)

	def _testAbort(self):
		self._computing = True
		self._abort = False
		from chimera.update import processWidgetEvents
		processWidgetEvents(self.buttonWidgets['Close'])
		# nowadays the line below is __slow___; use the above instead
		#self.uiMaster().update() # allow Abort button to function
		self._computing = False
		return self._abort

class Cluster(object):
	def getColor(self):
		return self.__color
	def setColor(self, color):
		self.__color = color
		if hasattr(self, 'patches'):
			for patch in self.patches:
				patch.set_facecolor(color)
				patch.set_edgecolor(color)
			if self.canvas:
				self.canvas.draw()
	color = property(getColor, setColor)

from OpenSave import SaveModeless
class _SaveClusteringInfo(SaveModeless):
	def __init__(self, clusterDialog, **kw):
		self.clusterDialog = clusterDialog
		SaveModeless.__init__(self, **kw)

	def Apply(self):
		clusters = self.clusterDialog.clusters[:]
		clusters.sort(lambda c1, c2: cmp(len(c2.members), len(c1.members)) \
				or cmp(min(c1.members), min(c2.members)))
		from OpenSave import osOpen
		saveFile = osOpen(self.getPaths()[0], 'w')
		print>>saveFile, "# one cluster per line; first frame on each line is representative"
		for cluster in clusters:
			print>>saveFile, cluster.representative,
			for member in sorted(cluster.members):
				if member == cluster.representative:
					continue
				print>>saveFile, member,
			print>>saveFile, ""
		saveFile.close()

	def destroy(self):
		self.clusterDialog = None
		SaveModeless.destroy(self)
