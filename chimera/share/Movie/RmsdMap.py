# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: RmsdMap.py 40894 2016-02-22 19:45:26Z pett $

import Tkinter, Pmw
from chimera.baseDialog import ModelessDialog, AskYesNoDialog
from prefs import prefs, RMSD_MIN, RMSD_MAX, RMSD_AUTOCOLOR
from chimera import UserError, tkgui

class RmsdStarter(ModelessDialog):
	title = "Get RMSD Map Parameters"
	help = "ContributedSoftware/movie/movie.html#rmsd"

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
		Tkinter.Label(parent, text="Create RMSD map of trajectory "
			"against itself", relief="ridge", bd=4).grid(row=0,
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

		self.minRmsd = FloatOption(parent, 4, "Lower RMSD threshold"
				" (white)", prefs[RMSD_MIN], None, width=6)
		self.maxRmsd = FloatOption(parent, 5, "Upper RMSD threshold"
				" (black)", prefs[RMSD_MAX], None, width=6)

		self.useSel = BooleanOption(parent, 6, "Restrict map to "
				"current selection, if any", True, None)

		self.ignoreBulk = BooleanOption(parent, 7, "Ignore solvent and"
							" non-metal ions", True, None)
		self.ignoreHyds = BooleanOption(parent, 8, "Ignore hydrogens",
							True, None)
		from gui import IgnoreMetalIonsOption as IMIO
		self.metalIons = IMIO(parent, 9, IMIO.defaultLabel, IMIO.defaultValue, None)
		self.recolor = BooleanOption(parent, 10, "Auto-recolor for"
				" contrast", prefs[RMSD_AUTOCOLOR], None)
	def Apply(self):
		startFrame = self.startFrame.get()
		stride = self.stride.get()
		if (len(self.movie.ensemble) - (startFrame-1)) / stride > 1000:
			dlg = AskYesNoDialog("RMSD map will be %d pixels wide"
				" and tall. Okay?")
			if dlg.run(self.uiMaster()) == "no":
				self.enter()
				return
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
		prefs[RMSD_MIN] = self.minRmsd.get()
		prefs[RMSD_MAX] = self.maxRmsd.get()
		prefs[RMSD_AUTOCOLOR] = self.recolor.get()
		RmsdMapDialog(self.movie, startFrame, self.stride.get(),
			endFrame, self.useSel.get(), prefs[RMSD_MIN],
			prefs[RMSD_MAX], self.ignoreBulk.get(),
			self.ignoreHyds.get(), self.metalIons.get(), prefs[RMSD_AUTOCOLOR])

class RmsdMapDialog(ModelessDialog):
	oneshot = True
	provideStatus = True
	buttons = ("Close","Save RMSDs")
	help = "ContributedSoftware/movie/movie.html#rmsd"

	titleFmt = "%g-%g RMSD Map"

	def __init__(self, movie, startFrame, stride, endFrame, useSel, minRmsd,
				maxRmsd, ignoreBulk, ignoreHyds, metalIons, recolor):
		self.movie = movie
		self.movie.subdialogs.append(self)
		self.startFrame = startFrame
		self.stride = stride
		self.endFrame = endFrame
		self.useSel = useSel
		self.minRmsd = minRmsd
		self.maxRmsd = maxRmsd
		self.ignoreBulk = ignoreBulk
		self.ignoreHyds = ignoreHyds
		self.metalIons = metalIons
		self.recolor = recolor
		self.title = self.titleFmt % (minRmsd, maxRmsd)
		ModelessDialog.__init__(self)

	def Close(self):
		if self._computing:
			self._abort = True
			return
		self.movie.subdialogs.remove(self)
		while self.dependentDialogs:
			self.dependentDialogs[0].Close()
		ModelessDialog.Close(self)
	
	def SaveRMSDs(self):
		SaveRmsdMap(self.rmsdMatrix,self.dim)

	def destroy(self):
		while self.dependentDialogs:
			self.dependentDialogs[0].Close()
		# calling ModelessDialog.Close causes recursion
		self.movie = None
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		from chimera.match import matchPositions
		from chimera import numpyArrayFromAtoms
		from chimera import selection, UserError

		self.buttonWidgets['Save RMSDs'].configure(state="disabled")
		self._computing = False
		top = parent.winfo_toplevel()
		menuBar = Tkinter.Menu(top, type="menubar", tearoff=False)
		top.config(menu=menuBar)

		self.dependentDialogs = []
		rmsdMenu = Tkinter.Menu(menuBar)
		menuBar.add_cascade(label="RMSD", menu=rmsdMenu)
		rmsdMenu.add_command(label="Change thresholds...",
					command=self.launchRmsdBoundsDialog)

		numFrames = self.endFrame - self.startFrame + 1
		# load needed coord sets...
		for frameNum in range(self.startFrame, self.endFrame+1,
								self.stride):
			if not self.movie.findCoordSet(frameNum):
				self.status("loading frame %d" % frameNum)
				self.movie._LoadFrame(frameNum,
							makeCurrent=False)

		from chimera.tkgui import aquaMenuBar
		aquaMenuBar(menuBar, parent, row=0, columnspan=2)

		self.widgets = []
		width = max(len(str(self.endFrame)), 6)
		kw = {}
		if tkgui.windowSystem != 'aqua':
			kw['padx'] = kw['pady'] = 0
		for i in range(2):
			entryFrame = Tkinter.Frame(parent)
			entryFrame.grid(row=2, column=i)
			entry = Pmw.EntryField(entryFrame, labelpos='w',
					entry_width=width, label_text="Frame",
					validate='numeric')
			entry.configure(command=lambda ent=entry:
							self.entryCB(ent))
			entry.grid(row=0, column=0)
			self.widgets.append(entry)
			goBut = Tkinter.Button(entryFrame, text="Go",
				command=lambda ent=entry: self.entryCB(ent), **kw)
			goBut.grid(row=0, column=1)
			self.widgets.append(goBut)
		self.widgets[0].insert(0, "Click")
		self.widgets[2].insert(0, "on map")
		for widget in self.widgets:
			if isinstance(widget, Pmw.EntryField):
				widget = widget.component('entry')
			widget.config(state='disabled')

		self.mplFrame = Tkinter.Frame(parent)
		self.mplFrame.grid(row=1, column=0, columnspan=2, sticky="nsew")
		parent.rowconfigure(1, weight=1)
		parent.columnconfigure(0, weight=1)
		parent.columnconfigure(1, weight=1)

		# compute RMSD/image canvas
		from analysis import analysisAtoms, AnalysisError
		try:
			atoms = analysisAtoms(self.movie.model.Molecule(), self.useSel,
					self.ignoreBulk, self.ignoreHyds, self.metalIons)
		except AnalysisError, v:
			self.Close()
			raise UserError(unicode(v))

		self.buttonWidgets['Close'].configure(text="Abort")
		self.rects = {}
		numpyArrays = {}
		if self.recolor:
			rmsds = []
		minRmsd = maxRmsd = None
		# added for printing rmsd 
		self.dim = len(range(self.startFrame, self.endFrame+1, self.stride))
		from numpy import zeros, ones
		import numpy.ma
		self.rmsdMatrix = numpy.ma.array(zeros((self.dim,self.dim), float),
			mask=ones((self.dim,self.dim), bool))
		# use a color map so that not-yet-computed areas can be
		# shown in blue
		from matplotlib.colors import LinearSegmentedColormap as LSColormap
		cmDict = {
			'red': ((0.0, 1.0, 1.0),
					(1.0, 0.0, 0.0)),
			'green': ((0.0, 1.0, 1.0),
					(1.0, 0.0, 0.0)),
			'blue': ((0.0, 1.0, 1.0),
					(1.0, 0.0, 0.0)),
		}
		cmap = LSColormap('computing', cmDict, 256)
		cmap.set_bad(color='blue')
		cmap.set_under(color='white')
		cmap.set_over(color='black')
		from matplotlib.figure import Figure
		fig = Figure()
		ax = self.mplAxes = fig.add_subplot(111)
		ax.tick_params(direction='out')
		from matplotlib.backends.backend_tkagg \
			import FigureCanvasTkAgg, NavigationToolbar2TkAgg
		self.mplFigCanvas = figCanvas = FigureCanvasTkAgg(fig,
					master=self.mplFrame)
		# matplotlib uses pack...
		figCanvas.get_tk_widget().pack(side="top", fill="both", expand=True)
		self.navTB = nt = NavigationToolbar2TkAgg(figCanvas, self.mplFrame)
		nt.__set_message = nt.set_message
		nt.set_message = self._mpl2status
		nt.update()
		for event in ['button_press', 'motion_notify']:
			fig.canvas.mpl_connect(event + '_event',
											self._mouse_handler)
		last = self.startFrame + int((self.endFrame - self.startFrame) /
			self.stride) * self.stride
		self.fixedMplKw = {
			'cmap': cmap,
			'origin': 'lower',
			'extent': (self.startFrame, last, self.startFrame, last)
		}
		im = ax.imshow(self.rmsdMatrix, vmin=self.minRmsd, vmax=self.maxRmsd,
						**self.fixedMplKw)
		figCanvas.draw()

		for step1, frame1 in enumerate(range(self.startFrame,
						self.endFrame+1, self.stride)):
			self.status("compute/show RMSDs for frame %d" % frame1)
			try:
				na1 = numpyArrays[frame1]
			except KeyError:
				na1 = numpyArrayFromAtoms(atoms,
					self.movie.findCoordSet(frame1))
				numpyArrays[frame1] = na1
			for step2, frame2 in enumerate(range(frame1,
						self.endFrame+1, self.stride)):
				try:
					na2 = numpyArrays[frame2]
				except KeyError:
					na2 = numpyArrayFromAtoms(atoms,
						self.movie.findCoordSet(frame2))
					numpyArrays[frame2] = na2
				rmsd = matchPositions(na1, na2)[1]
				if self.recolor:
					rmsds.append(rmsd)
				self.rmsdMatrix[step1,step1+step2] = rmsd
				self.rmsdMatrix[step1+step2,step1] = rmsd
				if frame1 != frame2:
					if minRmsd is None:
						minRmsd = maxRmsd = rmsd
					elif rmsd < minRmsd:
						minRmsd = rmsd
					elif rmsd > maxRmsd:
						maxRmsd = rmsd
			self._computing = True
			self._abort = False
			im.set_data(self.rmsdMatrix)
			figCanvas.draw()
			parent.update() # show each line and allow quit
			self._computing = False
			if self._abort:
				parent.after_idle(self.Close)
				return
		self.buttonWidgets['Close'].configure(text="Close")
		self.buttonWidgets['Save RMSDs'].configure(state="normal")
		if self.recolor:
			self.status("Calculating recoloring thresholds")
			rmsds.sort()
			newMin = float("%.1f" % rmsds[int(len(rmsds)/3)])
			newMax = float("%.1f" % rmsds[int(2*len(rmsds)/3)])
			if newMin == newMax:
				if newMin > 0:
					newMin -= 0.1
				else:
					newMax += 0.1
			self.newMinMax(newMin, newMax)
		self.status("Calculated RMSD varies from %.3f to %.3f\n"
						% (minRmsd, maxRmsd), log=True)

	def entryCB(self, entry):
		self.movie.currentFrame.set(entry.get())
		self.movie.LoadFrame()

	def launchRmsdBoundsDialog(self):
		self.dependentDialogs.append(BoundsChangeDialog(self))

	def newMinMax(self, newMin, newMax):
		prefs[RMSD_MIN] = self.minRmsd = newMin
		prefs[RMSD_MAX] = self.maxRmsd = newMax
		self.status("recoloring map...", blankAfter=0)
		self.mplAxes.cla()
		self.mplAxes.imshow(self.rmsdMatrix, vmin=self.minRmsd,
			vmax=self.maxRmsd, **self.fixedMplKw)
		self.mplFigCanvas.draw()
		self.status("map recolored")
		self.uiMaster().winfo_toplevel().title(self.titleFmt
							% (newMin, newMax))

	def _mouse_handler(self, event):
		if event.xdata == None:
			return
		frames = self._mplCoords2Frames((event.xdata, event.ydata))
		if not frames:
			return
		if type(event.button) == int:
			for i, frame in enumerate(frames):
				self.widgets[i*2].component('entry').configure(
									state='normal')
				self.widgets[i*2+1].configure(state='normal')
				self.widgets[i*2].setvalue(str(frame))
		"""
		else:
			self.status("RMSD: %.3f" % self.rmsdMatrix[
				(frames[0] - self.startFrame) / self.stride,
				(frames[1] - self.startFrame) / self.stride])
		"""

	def _mplCoords2Frames(self, coords):
		last = self.startFrame + int((self.endFrame - self.startFrame)
			/ self.stride) * self.stride
		for crd in coords:
			if crd < self.startFrame or crd > last:
				return None
		return [int((crd - self.startFrame) / float(self.stride)
			+ 0.5) * self.stride + self.startFrame for crd in coords]

	def _mpl2status(self, msg):
		for i in range(len(msg)):
			if msg[i:i+2] == "x=":
				coords = [float(mpl[2:])
					for mpl in msg[i:].strip().split()]
				strideFrames = self._mplCoords2Frames(coords)
				if not strideFrames:
					self.navTB.__set_message(msg[:i])
					return
				self.navTB.__set_message("%s frames %d/%d: RMSD %.3f"
					% (msg[:i], strideFrames[0], strideFrames[1],
					self.rmsdMatrix[
					(strideFrames[0] - self.startFrame) / self.stride,
					(strideFrames[1] - self.startFrame) / self.stride]))
				return
		self.navTB.__set_message(msg)

class BoundsChangeDialog(ModelessDialog):
	title = "Change RMSD Thresholds"
	oneshot = True
	default = "OK"
	help = "ContributedSoftware/movie/movie.html#changethresh"

	def __init__(self, rmsdDialog):
		self.rmsdDialog = rmsdDialog
		ModelessDialog.__init__(self)

	def Apply(self):
		prefs[RMSD_MIN] = self.newMin.get()
		prefs[RMSD_MAX] = self.newMax.get()
		self.rmsdDialog.newMinMax(prefs[RMSD_MIN], prefs[RMSD_MAX])

	def destroy(self):
		# Apply/OK needs access to rmsdDialog, so can't do this in Close
		self.rmsdDialog.dependentDialogs.remove(self)
		self.rmsdDialog = None

	def fillInUI(self, parent):
		from chimera.tkoptions import FloatOption
		self.newMin = FloatOption(parent, 0,
					"New lower RMSD threshold (white)",
					prefs[RMSD_MIN], None)
		self.newMax = FloatOption(parent, 1,
					"New upper RMSD threshold (black)",
					prefs[RMSD_MAX], None)

from OpenSave import SaveModeless
from chimera import replyobj

class SaveRmsdMap(SaveModeless):
	keepShown = SaveModeless.default
	title = "Write RMSD Map"
	#help = "UsersGuide/savemodel.html#mol2"
	oneshot = True

	def __init__(self,rmsdMatrix,dim):
		SaveModeless.__init__(self)
		self.rmsdMatrix=rmsdMatrix
		self.dim=dim

	def Apply(self):
		paths = self.getPaths()
		if not paths:
			replyobj.error('No save location chosen.\n')
			return
		path = paths[0]
		from OpenSave import osOpen
		f = osOpen(path, "w")

		for i in range(self.dim):
			for j in range(self.dim):
				print >>f, "%6.3f" % self.rmsdMatrix[i,j],
			print >>f

		print>>f, "End of File"

		f.close()



