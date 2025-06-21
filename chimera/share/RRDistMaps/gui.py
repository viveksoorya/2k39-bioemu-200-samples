# --- UCSF Chimera Copyright ---

# Copyright (c) 2014 Regents of the University of California.
# All rights reserved. This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use. This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera
import numpy as np
import matplotlib.pyplot as plt
from chimera.mplDialog import MPLDialog
from chimera import widgets

MODE_DISTANCE = 0
MODE_AVG_DIST = 1
MODE_STD_DEV = 2
MODE_COMBINED = 3
MODE_DIFFERENCE = 4

class RRDistanceMapsDialog(MPLDialog):
	"""Dialog for interactive RR Distance Maps"""

	name = 'RR Distance Maps'
	title = 'RR Distance Maps'
	buttons = ('Options...', 'Export...', 'Close')
	provideStatus = True
	help = "ContributedSoftware/rrdistmaps/rrdistmaps.html"

	def __init__(self, sessionData = None, *args, **kw):
		"""Constructor"""
		self.optionsDialog = None
		self.closeHandler = None
		import colormap
		self._colors = (colormap.comboColors, colormap.noColor)
		self._diffColors = colormap.diffColors
		self._resolutions = (16, 16)
		MPLDialog.__init__(self)

                # Initialze some commonly used attributes
                self.dMatrix = None
                self.sdMatrix = None
                self.diffMatrix = None

		# Register Dialog in tools menu
		from chimera.extension import manager
		manager.registerInstance(self)

		# Handle Session Saving and closing
		chimera.extension.manager.registerInstance(self)
		self._closeSesHandler = chimera.triggers.addHandler(
						chimera.CLOSE_SESSION,
						self.emQuit, None)

	def destroy(self):
		"""Delete handlers for session closing"""
		if self._closeSesHandler:
			chimera.triggers.deleteHandler(chimera.CLOSE_SESSION,
							self._closeSesHandler)
			self._closeSesHandler = None

		from chimera.extension import manager
		# Deregister instance from extension manager
		manager.deregisterInstance(self)
		MPLDialog.destroy(self)


	def fillInUI(self, parent):
		"""Fill in UI in parent frame"""
		import Pmw, Tkinter

		# MoleculeChainScrolledListBox listing opened chains
		g = Pmw.Group(parent, hull_padx=2, tag_text='Chains')
		g.pack(fill='both', expand=True)
		gi = g.interior()
		from chimera.widgets import MoleculeChainScrolledListBox
		self.RRdmMolBox = MoleculeChainScrolledListBox(gi,
						autoselect='single',
						listbox_height=4,
						listbox_selectmode='extended')
		self.RRdmMolBox.pack(fill='both', expand=True)
		self.RRdmMolBox.component("listbox").bind(
						"<<ListboxSelect>>",
						self._chainSelectCB)
		self.calcButton = Tkinter.Button(gi, text="Calculate Map",
						command=self._calcCB)
		self.calcButton.pack()

		# Option menu for map type
		self.mapChains = []
		self.mapTypeOption = Pmw.RadioSelect(parent,
						labelpos='w',
						label_text='Display: ',
						buttontype="radiobutton",
						command=self._mapModeCB)
		self.mapTypeOption.add("Distance")
		self.mapTypeOption.add("Std Dev")
		self.mapTypeOption.add("Both")
		self.mapTypeOption.add("Difference")
		self.mapTypeOption.setvalue("Distance")
		self.mapTypeOption.pack()
		self.mapMode = MODE_DISTANCE

		# Finish up with matplotlib frame
		from chimera import mplDialog
		self.RRdmMPL = mplDialog.MPLFrame(parent)
		self.RRdmMPL.mpl_connect('button_press_event', self.onPress)
		self.RRdmMPL.mpl_connect('button_release_event', self.onRelease)
		self.RRdmMPL.mpl_connect('motion_notify_event', self.onMotion)
		self.dragStart = None
		self.rectangle = None
		self.distmap = None
		self.img = None
		self.legend = None
		self.colormap = None
		self.lastPress = None
		self.chainsChanged = True
		self._chainSelectCB(None)

	def _calcCB(self):
		"""Update distance map"""
		self.mapChains = self.RRdmMolBox.getvalue()[:]
		self.needAlignment = True
		self._chainSelectCB(None)
		mapType = self.mapTypeOption.getvalue()
		button = self.mapTypeOption.button(mapType)
		if button.cget("state") == "disabled":
			# Current map mode is not compatible with
			# the number of selected chains
			mapType = "Distance"
		self.mapTypeOption.invoke(mapType)

	def _chainSelectCB(self, event):
		"""Update available map type options"""
		chosen = self.RRdmMolBox.getvalue()
		self.chainsChanged = self.mapChains != chosen
		numChains = len(chosen)
		exportButton = self.buttonWidgets["Export..."]
		if numChains == 0 or self.chainsChanged:
			self.mapTypeOption.button(0).config(state="disabled")
			self.mapTypeOption.button(1).config(state="disabled")
			self.mapTypeOption.button(2).config(state="disabled")
			self.mapTypeOption.button(3).config(state="disabled")
			exportButton.config(state="disabled")
		elif numChains == 1:
			self.mapTypeOption.button(0).config(state="normal")
			self.mapTypeOption.button(1).config(state="disabled")
			self.mapTypeOption.button(2).config(state="disabled")
			self.mapTypeOption.button(3).config(state="disabled")
			exportButton.config(state="normal")
		elif numChains == 2:
			self.mapTypeOption.button(0).config(state="normal")
			self.mapTypeOption.button(1).config(state="normal")
			self.mapTypeOption.button(2).config(state="normal")
			self.mapTypeOption.button(3).config(state="normal")
			exportButton.config(state="normal")
		else:
			self.mapTypeOption.button(0).config(state="normal")
			self.mapTypeOption.button(1).config(state="normal")
			self.mapTypeOption.button(2).config(state="normal")
			self.mapTypeOption.button(3).config(state="disabled")
			exportButton.config(state="normal")
                name = self.mapTypeOption.getvalue()
		if self.chainsChanged and numChains > 0:
			self.calcButton.config(state="normal")
		else:
			self.calcButton.config(state="disabled")

	def _mapModeCB(self, value):
		if self.chainsChanged:
			return
		numChains = len(self.mapChains)
		if numChains == 0:
			from chimera import UserError
			raise UserError('No chains chosen')
		elif numChains == 1:
			self.mapMode = MODE_DISTANCE
			self.status("Computing map...")
			self.perChain()
			self.status("Creating plot...")
			self.plot()
			self.status('')
		else:
			mapType = self.mapTypeOption.getvalue()
			if mapType == "Distance":
				self.mapMode = MODE_AVG_DIST
			elif mapType == "Std Dev":
				self.mapMode = MODE_STD_DEV
			elif mapType == "Both":
				self.mapMode = MODE_COMBINED
			else:
				self.mapMode = MODE_DIFFERENCE
			if not self.needAlignment:
				self.plot()
			elif numChains == 2:
				# Use NW
				self.status('Aligning chains using '
						'Needleman-Wunsch...')
				self.chainAlignTwo()
				self.needAlignment = False
			else:
				# Use multiple sequence alignment
				self.status('Aligning chains using '
						'MUSCLE web service...')
				self.chainAlignMult()
				self.needAlignment = False

	def _atomOf(self, r):
		return r.atomsMap['CA'][0]

	def _coordOf(self, r):
		return self._atomOf(r).coord()

	def perChain(self):
		"""Displays residue distances within chain"""
		coordlist = []
		resList = []
		for r in self.mapChains[0].residues:
			if r is None or r.__destroyed__:
				continue
			try:
				c = self._coordOf(r)
			except KeyError:
				pass
			else:
				resList.append(r)
				coordlist.append(c)
		if len(resList) == 0:
			from chimera import UserError
			raise UserError("No usable residues found.  "
					"RR Distance Maps currently "
					"only works for proteins.")
		self.rLL = [ resList ]
		self.coord = [ coordlist ]
		self._computeDistance()

	def chainAlignTwo(self):
		"""Uses Needleman-Wunsch for alignment
		- Returns a list of two lists of indices
		"""
		if len(self.mapChains) != 2:
			from chimera import UserError
			raise UserError('Please choose two target chains.')
		chain1, chain2 = self.mapChains

		# Align Chains using Needleman/Wunsch
		from chimera import replyobj
		from NeedlemanWunsch import nw
		score, nwSeqs = nw(chain1, chain2, returnSeqs = True)
		score, matchList = nw(chain1, chain2)

		# Write fasta file for display with MAV
		from MultAlignViewer.formatters.saveFASTA import save
		from OpenSave import osTemporaryFile, osOpen
		self.file = osTemporaryFile(suffix='.fa')
		f = open(self.file, 'w')
		save(f, None, nwSeqs, None)
		f.close()

		self._alignPlot(matchList, self.mapChains, True)

	def chainAlignMult(self):
		"""Call MUSCLE web service giving input ungapped sequences"""
		from AlignSeq import RunAlignWS
		from chimera.Sequence import Sequence
		inputSeqs = []
		for seq in self.mapChains:
			inputSeq = Sequence(seq.fullName())
			inputSeq[:] = seq.ungapped()
			inputSeqs.append(inputSeq)

		# Add MUSCLE job, run _finishAlignJob to begin plotting process
		ws = RunAlignWS(None, self._finishAlignJob,
				self._finishAlignJob, seqs=inputSeqs)

	def _finishAlignJob(self, ws, results):
		"""Finish MUSCLE Job, feed results into AlignPlot"""
		self.file = ws.file	# Save for displaying in MAV
		# Create a dictionary mapping residue indices
		# and the residues themselves"""
		maps = [ dict(enumerate(sso.residues))
				for sso in self.mapChains ]
		self._alignPlot(maps, results, False)

	def _alignPlot(self, listdex, selSeqList, nw):
		"""Default plotting program for multiple chain selections
		Calls Matrix generating functions,
		plots and activates interactivity
		"""
		self.status("Finding corresponding residues...")
		self._alignObj(selSeqList, listdex, nw)
		self.status("Computing map...")
		self._computeDistanceAndSD()
		self.status("Creating plot...")
		self.plot()
		self.status("Displaying alignment...")
		title = "Distance Map: " + ", ".join([seq.fullName()
						for seq in self.mapChains ])
		from MultAlignViewer.MAViewer import MAViewer
		mav = MAViewer(self.file, autoAssociate=False, title=title)
		for i, seq in enumerate(self.mapChains):
			mav.associate(seq, seq=mav.seqs[i])
		self.status('')

	def _alignObj(self, seqList, listdex, nw):
		"""Compute residue correspondences and residue coordinates"""
		from Alignment import Alignment
		alignment = Alignment(self, seqList, listdex, nw)
		self.status(alignment.statsMessage())
		if len(alignment.resListList[0]) == 0:
			self.rLL = alignment.resListList
			self.coord = alignment.coordListList
			from chimera import UserError
			raise UserError("No usable residues found.  "
					"RR Distance Maps currently "
					"only works for proteins.")
		if len(alignment.resListList[0]) < 20:
			self.rLL = alignment.resListList
			self.coord = alignment.coordListList
		else:
			# Remove a few end Residues because they
			# tend to be noisy (screwing up SD)
			strip = 2
			self.rLL = [ l[strip:-strip]
					for l in alignment.resListList ]
			self.coord = [ l[strip:-strip]
					for l in alignment.coordListList ]

	def _computeDM(self, l, numCoords):
		dm = np.empty((numCoords, numCoords), dtype=float)
		for row in range(numCoords):
			rrow = l[row]
			dm[row, row] = 0
			for col in range(row + 1, numCoords):
				rcol = l[col]
				d = rrow.distance(rcol)
				dm[row, col] = d
				dm[col, row] = d
		return dm

	def _computeDistance(self):
		"""Compute avg distances for residue pairs between chains"""
		# This function is present to minimize memory usage
		# when SD is not needed.
		# Fill list of RR distance matrices
		numCoords = len(self.coord[0])
		self.dMatrix = np.zeros((numCoords, numCoords))
		for l in self.coord:
			self.dMatrix += self._computeDM(l, numCoords)
		self.dMatrix /= len(self.coord)
		self.sdMatrix = None

	def _computeDistanceAndSD(self):
		"""Compute distance and SD for residue pairs between chains"""
		# Fill list of RR distance matrices
		numCoords = len(self.coord[0])
		sddmList = []
		for l in self.coord:
			sddmList.append(self._computeDM(l, numCoords))

		# Masks matrices and calculates standard deviation
		# Find mean/avg distance
		numChains = len(self.coord)
		self.dMatrix = np.zeros((numCoords, numCoords))
		for m in sddmList:
			self.dMatrix += m
		self.dMatrix /= numChains

		# Calculate difference matrix if exactly two chains
		if numChains != 2:
			self.diffMatrix = None
		else:
			self.diffMatrix = sddmList[0] - sddmList[1]

		# Calculate variance and square root
		# for sample standard deviation
		varMatr = np.zeros((numCoords, numCoords))
		for m in sddmList:
			varMatr += np.square(m - self.dMatrix)
		varMatr /= numChains - 1
		self.sdMatrix = np.sqrt(varMatr)

	def plot(self):
		"""Create subplot for data"""
		if len(self.rLL[0]) == 0:
			from chimera import UserError
			raise UserError("No usable residues found.  "
					"RR Distance Maps currently "
					"only works for proteins.")
		if self.distmap:
			self.RRdmMPL.delaxes(self.distmap)
			self.img = None
			self.rectangle = None
		if self.legend:
			self.RRdmMPL.delaxes(self.legend)
			self.colormap = None

		# Split the plot into two spaces for graphs
		import matplotlib.gridspec as gridspec
		if self.mapMode != MODE_COMBINED:
			gs = gridspec.GridSpec(1, 2, width_ratios=[19,1])
		else:
			gs = gridspec.GridSpec(1, 2, width_ratios=[22,3])

		# Create distance map axes
		title = ", ".join([ c.fullName() for c in self.mapChains ])
		numCoords = len(self.coord[0])
		xExtent = [ 0, numCoords ]
		yExtent = [ numCoords, 0 ]
		labels = [ '\n'.join([ resList[0].oslIdent()
					for resList in self.rLL ]),
				'\n'.join([ resList[-1].oslIdent()
					for resList in self.rLL ]) ]
		self.distmap = self.RRdmMPL.add_subplot(gs[0], title=title,
					xlim=xExtent, ylim=yExtent,
					xticks=[0,numCoords], yticks=[],
					xticklabels=labels)
                self.distmap.format_coord = lambda x, y: ""

		# Create legend axes
		self.legend = self.RRdmMPL.add_subplot(gs[1],
					xlabel='', ylabel='',
					xticks=[], yticks=[])
                self.legend.format_coord = lambda x, y: ""

		# Construct Color maps and legend first
		# so that we can use it for lookups from the data
		# rectangular for Combined and colorbar for the rest
		if self.mapMode == MODE_COMBINED:
			xRange = (np.amin(self.sdMatrix),
					np.amax(self.sdMatrix))
			yRange = (np.amin(self.dMatrix),
					np.amax(self.dMatrix))
			xr, yr = self._resolutions
			from colormap import ColorMap2D
			self.colormap = ColorMap2D(self.RRdmMPL, self.legend,
							self._colors[0],
							xRange, yRange,
							xResolution=xr,
							yResolution=yr,
							bg=self._colors[1],
							cb=self._recolor)
			image = self._plotFillCombined(self.colormap)
			self.legend.set_xlabel('SD')
			self.legend.set_ylabel('Avg Dist')
		else:
			if self.mapMode == MODE_DISTANCE:
				colors = (self._colors[0][0],
						self._colors[0][2])
				m = self.dMatrix
				self.legend.set_ylabel('Distance')
				from colormap import ColorMap as cm
			elif self.mapMode == MODE_AVG_DIST:
				colors = (self._colors[0][0],
						self._colors[0][2])
				m = self.dMatrix
				self.legend.set_ylabel('Avg Dist')
				from colormap import ColorMap as cm
			elif self.mapMode == MODE_STD_DEV:
				colors = (self._colors[0][0],
						self._colors[0][1])
				m = self.sdMatrix
				self.legend.set_ylabel('SD')
				from colormap import ColorMap as cm
			else:
				# Difference
				colors = self._diffColors
				m = self.diffMatrix
				self.legend.set_ylabel('Difference')
				from colormap import ColorMapDifference as cm
			dataRange = (np.amin(m), np.amax(m))
			r = self._resolutions[1]
			self.colormap = cm(self.RRdmMPL, self.legend,
						colors, dataRange,
						resolution=r,
						bg=self._colors[1],
						cb=self._recolor)
			image = self._plotFillSingle(m, self.colormap)
		self._updateImage(image)

	def _recolor(self, *args):
		cm = self.colormap
		if self.mapMode == MODE_COMBINED:
			self._updateImage(self._plotFillCombined(cm))
		else:
			if self.mapMode == MODE_DISTANCE:
				m = self.dMatrix
			elif self.mapMode == MODE_AVG_DIST:
				m = self.dMatrix
			elif self.mapMode == MODE_STD_DEV:
				m = self.sdMatrix
			else:
				# Difference
				m = self.diffMatrix
			self._updateImage(self._plotFillSingle(m, cm))

	def _updateImage(self, image):
		if self.img:
			self.img.remove()
			#self.distmap.remove(self.img)
		self.img = self.distmap.imshow(image, interpolation='nearest',
						origin='lower',
						extent=(0, image.shape[1],
							0, image.shape[0]))
		self.RRdmMPL.draw()

	def _plotFillSingle(self, matrix, cm):
		"""Heat map by color map lookup."""
		numCoords = len(self.coord[0])
		dmin, dmax = cm.minmax
		drange = (dmin == dmax) and 1.0 or (dmax - dmin)
		# ci = color index
		ci = np.around((matrix - dmin) /
				(drange / cm.resolution)).astype(int)
		return cm.makeImage(ci)

	def _plotFillCombined(self, cm):
		"""Displays a fused average distance and standard deviation
		map for residue pairs among chosen chains"""

		# Grab Distance and SD Data
		numCoords = len(self.coord[0])
		dmin, dmax = cm.yminmax
		drange = (dmin == dmax) and 1.0 or (dmax - dmin)
		di = np.around((self.dMatrix - dmin)
				/ (drange / cm.yResolution)).astype(int)
		sdmin, sdmax = cm.xminmax
		sdrange = (sdmin == sdmax) and 1.0 or (sdmax - sdmin)
		sdi = np.around((self.sdMatrix - sdmin)
				/ (sdrange / cm.xResolution)).astype(int)
		return cm.makeImage(di, sdi)

	def _getIndex(self, c, numCoords):
		return max(min(int(c), numCoords - 1), 0)

	def _getSelected(self, x, y, highlight):
		# Get indices of interest
		if x is None or y is None:
			return ([], [])
		numCoords = len(self.coord[0])
		xIndex = self._getIndex(x, numCoords)
		yIndex = self._getIndex(y, numCoords)

		# Find selected atoms
		selected = []
		for resList in self.rLL:
			try:
				xRes = resList[xIndex]
				yRes = resList[yIndex]
			except IndexError:
				continue
			if xRes is None or xRes.__destroyed__:
				continue
			if yRes is None or yRes.__destroyed__:
				continue
			selected.append((xRes, yRes))

		# Find values of interest
		values = []
		mode = self.mapMode
		if mode == MODE_DISTANCE:
			values.append(("Distance", self.dMatrix[xIndex,yIndex]))
		elif mode == MODE_AVG_DIST:
			values.append(("Avg Dist", self.dMatrix[xIndex,yIndex]))
		elif mode == MODE_STD_DEV:
			values.append(("SD", self.sdMatrix[xIndex,yIndex]))
		elif mode == MODE_COMBINED:
			values.append(("Avg Dist", self.dMatrix[xIndex,yIndex]))
			values.append(("SD", self.sdMatrix[xIndex,yIndex]))
		else:
			# Difference
			values.append(("Difference",
					self.diffMatrix[xIndex,yIndex]))
		if highlight:
			self._highlightRegion(xIndex, yIndex, xIndex, yIndex)
		return selected, values

	def _getSwept(self, x, y):
		sx, sy = self.dragStart
		numCoords = len(self.coord[0])
		sxIndex = self._getIndex(sx, numCoords)
		syIndex = self._getIndex(sy, numCoords)
		exIndex = self._getIndex(x, numCoords)
		eyIndex = self._getIndex(y, numCoords)
		if exIndex < sxIndex:
			sxIndex, exIndex = exIndex, sxIndex
		if eyIndex < syIndex:
			syIndex, eyIndex = eyIndex, syIndex

		selected = []
		for xIndex in range(sxIndex, exIndex + 1):
			for yIndex in range(syIndex, eyIndex + 1):
				for resList in self.rLL:
					xRes = resList[xIndex]
					if xRes is None or xRes.__destroyed__:
						continue
					yRes = resList[yIndex]
					if yRes is None or yRes.__destroyed__:
						continue
					selected.append((xRes, yRes))
		self._highlightRegion(sxIndex, syIndex, exIndex, eyIndex)
		return selected

	def _highlightRegion(self, xmin, ymin, xmax, ymax):
		xy = (xmin, ymin)
		w = xmax - xmin + 1
		h = ymax - ymin + 1
		if self.rectangle is None:
			from matplotlib.patches import Rectangle
			self.rectangle = self.distmap.add_patch(
						Rectangle(xy, w, h,
							fc='none',
							ec=(0, 1, 0, 1)))
		else:
			self.rectangle.set_xy(xy)
			self.rectangle.set_width(w)
			self.rectangle.set_height(h)
		self.RRdmMPL.draw()

	def _selectResidues(self, residues):
		if not residues:
			return
		from chimera import selection
		atoms = []
		for r0, r1 in residues:
			atoms.append(self._atomOf(r0))
			atoms.append(self._atomOf(r1))
		selection.setCurrent(atoms)

	def _composeMessage(self, residues, values):
		messages = []
		for value in values:
			messages.append("%s:%.3f" % value)
		for r0, r1 in residues:
			messages.append("%s/%s" % (r0.oslIdent(),
							r1.oslIdent()))
		return ", ".join(messages)

	def _onPressDistanceMap(self, event):
		# Button press over distance map.
		# Select residue and keep track as possible start of drag
		residues, values = self._getSelected(event.xdata, event.ydata,
								True)
		self._selectResidues(residues)
		self.status("Selection: " +
				self._composeMessage(residues, values))
		self.dragStart = event.xdata, event.ydata

	def _onMotionDistanceMap(self, event):
		if not self.dragStart:
			# Motion but not drag
			# Display residue we are over
			from chimera import selection
			residues, values = self._getSelected(event.xdata,
								event.ydata,
								False)
			self.status(self._composeMessage(residues, values))
		else:
			# Drag out swept area
			residues = self._getSwept(event.xdata, event.ydata)
			self._selectResidues(residues)
			numPairs = len(residues) / len(self.mapChains)
			self.status("%d pairs selected" % numPairs)

	def _onReleaseDistanceMap(self, event):
		self.dragStart = None

	def onPress(self, event):
		"""Responds to mouse left-click press."""
		if event.inaxes is self.distmap:
			self._onPressDistanceMap(event)
			self.lastPress = event.inaxes
		elif event.inaxes is self.legend:
			self.colormap.onPress(event)
			self.lastPress = event.inaxes

	def onMotion(self, event):
		"""Responds to mouse motion."""
		if event.inaxes is self.distmap:
			self._onMotionDistanceMap(event)
		elif event.inaxes is self.legend:
			self.colormap.onMotion(event)

	def onRelease(self, event):
		"""Responds to mouse left-click release."""
		self.dragStart = None
		if event.inaxes in [ self.distmap, self.legend ]:
			target = event.inaxes
		else:
			target = self.lastPress
		self.lastPress = None
		if not target:
			return
		elif target is self.distmap:
			self._onReleaseDistanceMap(event)
		elif target is self.legend:
			self.colormap.onRelease(event)

	def Options(self):
		if self.optionsDialog:
			self.optionsDialog.enter()
		else:
			self.optionsDialog = OptionsDialog(self)

	def Export(self):
		from OpenSave import SaveModal
		tsv = "tab-separated values"
		csv = "comma-separated values"
		sep = { tsv: "\t", csv: "," }
		d = SaveModal(title="Export RRDistMaps Matrix",
				filters=[(tsv, "*.tsv", ".tsv"),
					 (csv, "*.csv", ".csv")])
		paths = d.run(self.uiMaster())
		if paths is None:
			# cancelled by user
			return
		# Expecting exactly one entry of (path, type)
		path = paths[0][0]
		delim = sep[paths[0][1]]
		import numpy
		with open(path, "w") as f:
			if self.mapChains:
				names = numpy.array([c.fullName()
							for c in self.mapChains]
							).reshape((-1,1))
				numpy.savetxt(f, names,
						fmt="%s", delimiter=delim,
						header="Chains",
						footer="End Chains")
			if self.dMatrix is not None:
				numpy.savetxt(f, self.dMatrix,
						fmt="%.4f", delimiter=delim,
						header="Distance",
						footer="End Matrix")
			if self.sdMatrix is not None:
				numpy.savetxt(f, self.sdMatrix,
						fmt="%.4f", delimiter=delim,
						header="Std Dev",
						footer="End Matrix")
			if self.diffMatrix is not None:
				numpy.savetxt(f, self.diffMatrix,
						fmt="%.4f", delimiter=delim,
						header="Difference",
						footer="End Matrix")

	def getResolutions(self):
		return self._resolutions

	def getColors(self):
		return self._colors

	def getDiffColors(self):
		return self._diffColors

	def optionsCB(self, od):
		# od = optionsDialog
		self._colors = od.getColors()
		self._diffColors = od.getDiffColors()
		self._resolutions = od.getResolutions()
		self.mapTypeOption.invoke(self.mapTypeOption.getvalue())

	"""Extension Manager callback functions toggle
	options at the bottom of the tool menu:
	Raise, Hide, Quit
	"""
	def emName(self):
		return self.title

	def emRaise(self):
		self.enter()

	def emHide(self):
		self.Close()

	def emQuit(self, *args):
		self.destroy()

from chimera.baseDialog import ModelessDialog
class OptionsDialog(ModelessDialog):

	title = "RRDM Colormap Options"
	buttons = ( "Apply", "Reset", "Cancel" )
	help = "ContributedSoftware/rrdistmaps/rrdistmaps.html#rrmap-color"

	def __init__(self, rrdm, *args, **kw):
		# Use weakref to avoid reference loop
		import weakref
		self.rrdm = weakref.ref(rrdm)
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		rrdm = self.rrdm()
		hRes, vRes = self._res = rrdm.getResolutions()
		(loLo, loHi, hiLo, hiHi), noColor = self._col = rrdm.getColors()
		nDiff, zDiff, pDiff = rrdm.getDiffColors()
		from chimera.tkoptions import IntOption, ColorOption
		row = 0
		self.vResOption = IntOption(parent, row,
					"Vertical resolution",
					vRes, self._resCB)
		row += 1
		self.hResOption = IntOption(parent, row,
					"Horizontal resolution",
					hRes, self._resCB)
		row += 1
		self.loLoColorOption = ColorOption(parent, row,
					"Low D, low SD color",
					tuple(loLo), self._colorCB)
		row += 1
		self.hiLoColorOption = ColorOption(parent, row,
					"High D, low SD color",
					tuple(hiLo), self._colorCB)
		row += 1
		self.loHiColorOption = ColorOption(parent, row,
					"Low D, high SD color",
					tuple(loHi), self._colorCB)
		row += 1
		self.hiHiColorOption = ColorOption(parent, row,
					"High D, high SD color",
					tuple(hiHi), self._colorCB)
		row += 1
		self.excColorOption = ColorOption(parent, row,
					"Excluded color",
					tuple(noColor), self._colorCB)
		row += 1
		self.nDiffColorOption = ColorOption(parent, row,
					"Negative difference color",
					tuple(nDiff), self._colorCB)
		row += 1
		self.zDiffColorOption = ColorOption(parent, row,
					"Zero difference color",
					tuple(zDiff), self._colorCB)
		row += 1
		self.pDiffColorOption = ColorOption(parent, row,
					"Positive difference color",
					tuple(pDiff), self._colorCB)

	def _resCB(self, opt):
		pass

	def _colorCB(self, opt):
		pass

	def _getColor(self, opt):
		from numpy import array
		return array(opt.get().rgba()[:3])

	def getColors(self):
		return ((self._getColor(self.loLoColorOption),
				self._getColor(self.loHiColorOption),
				self._getColor(self.hiLoColorOption),
				self._getColor(self.hiHiColorOption)),
			self._getColor(self.excColorOption))

	def getDiffColors(self):
		return (self._getColor(self.nDiffColorOption),
				self._getColor(self.zDiffColorOption),
				self._getColor(self.pDiffColorOption))

	def getResolutions(self):
		return (self.hResOption.get(),
			self.vResOption.get())

	def Apply(self):
		rrdm = self.rrdm()
		if rrdm:
			rrdm.optionsCB(self)

	def Reset(self):
		hRes, vRes = self._res
		self.vResOption.set(vRes)
		self.hResOption.set(hRes)
		(loLo, loHi, hiLo, hiHi), noColor = self._col
		self.loLoColorOption.set(tuple(loLo))
		self.hiLoColorOption.set(tuple(hiLo))
		self.loHiColorOption.set(tuple(loHi))
		self.hiHiColorOption.set(tuple(hiHi))
		self.excColorOption.set(tuple(noColor))

from chimera import dialogs
dialogs.register(RRDistanceMapsDialog.name, RRDistanceMapsDialog)
def display():
	dialogs.display(RRDistanceMapsDialog.name)
def hide():
	d = dialogs.find(RRDistanceMapsDialog.name)
	if d:
		d.emHide()
