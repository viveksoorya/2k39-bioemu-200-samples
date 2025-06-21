# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

import Tkinter, Pmw
from chimera.baseDialog import ModelessDialog
import chimera
from chimera import UserError, tkgui, selection

class PlotsDialog(ModelessDialog):
	provideStatus = True
	statusPosition = "left"
	buttons = ("Close", "Dump Values")
	help = "ContributedSoftware/movie/movie.html#plotting"
	title = "MD Plots"

	def __init__(self, movie):
		self.movie = movie
		self.movie.subdialogs.append(self)
		from prefs import prefs, PLOTS_LAST_USE
		last = prefs[PLOTS_LAST_USE]
		from time import time
		now = prefs[PLOTS_LAST_USE] = time()
		if last is None or now - last > 777700: # about 3 months
			self.shownTitle = "Shown"
		else:
			self.shownTitle = "S"
		ModelessDialog.__init__(self)

	def Close(self):
		while self.dependentDialogs:
			self.dependentDialogs[0].Close()
		ModelessDialog.Close(self)

	def destroy(self):
		while self.dependentDialogs:
			self.dependentDialogs[0].Close()
		self.movie = None
		# calling ModelessDialog.Close causes recursion
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		from chimera import selection, UserError
		self.dependentDialogs = []
		self.plotPanels = {}

	def DumpValues(self):
		from OpenSave import SaveModeless
		SaveModeless(command=self._dvCB, title="Dump MD Measurement Values",
			dialogKw={'oneshot': True})

	def showPlot(self, plotName):
		totalFrames = self.movie.endFrame - self.movie.startFrame + 1
		if not self.plotPanels:
			if len(self.movie.model.coordSets) < totalFrames:
				self.dependentDialogs.append(LoadFramesDialog(self))
		else:
			self.enter()
			if len(self.movie.model.coordSets) < totalFrames:
				for dd in self.dependentDialogs:
					if isinstance(dd, LoadFramesDialog):
						dd.enter()

		if plotName not in self.plotPanels:
			self._createPlotPanel(plotName)
		self.plotPanels[plotName].panel_shown_variable.set(True)

	def _createPlotPanel(self, plotName):
		self.plotPanels[plotName] = PlotPanel(plotName, self)

	def _dvCB(self, okay, dialog):
		if not okay:
			return
		for plotPanel in self.plotPanels.values():
			if not plotPanel.panel_shown_variable.get():
				continue
			for plottable in plotPanel.plottables:
				if plottable.shown:
					break
			else:
				continue
			break
		else:
			from chimera import UserError
			UserError("No plots being shown!")
		path = dialog.getPaths()[0]
		from OpenSave import osOpen
		f = osOpen(path, 'w')
		first = True
		csMap = self.movie.model.coordSets
		xs = csMap.keys()
		xs.sort()
		addOne = xs[0] == 0
		for plotName, plotPanel in self.plotPanels.items():
			if not plotPanel.panel_shown_variable.get():
				continue
			precision = self.movie.plotPrecisions[self.movie.plotNames.index(plotName)]
			if callable(precision):
				precision = precision()
			titleWritten = False
			for plottable in plotPanel.plottables:
				if not plottable.shown:
					continue
				if not titleWritten:
					if first:
						first = False
					else:
						print>>f, ""
					print>>f, plotName
					titleWritten = True
				if plotPanel.numAtoms is None:
					if plottable.plotType != plotName:
						print>>f, plottable.plotType
				elif plotPanel.numAtoms > 0:
					print>>f, " <-> ".join([str(a) for a in plottable.atoms])
				else:
					print>>f, "Frame %d (%d atoms)" % (plottable.frameNum, len(plottable.atoms))
				vc = plotPanel.valCaches[plottable]
				for x in xs:
					y = vc[x]
					if addOne:
						x += 1
					if y is None:
						print>>f, "%d\tno value" % (x,)
					else:
						print>>f, "%d\t%8.*f" % (x, precision, y)

		f.close()
		self.status("Values written to file")

from CGLtk.Hybrid import Popup_Panel
class PlotPanel(object, Popup_Panel):
	def __init__(self, plotName, plotsDialog):
		self.plotsDialog = plotsDialog
		self.movie = plotsDialog.movie
		parent = plotsDialog.uiMaster()
		Popup_Panel.__init__(self, parent)
		row = len(plotsDialog.plotPanels)
		self.frame.grid(row=row, column=0, sticky="nsew")
		parent.rowconfigure(row, weight=1)
		parent.columnconfigure(0, weight=1)

		titleFrame = Tkinter.Frame(self.frame)
		titleFrame.grid(row=0, column=0, columnspan=2, sticky="ew")
		title = Tkinter.Label(titleFrame, text=plotName)
		from CGLtk.Font import shrinkFont
		shrinkFont(title)
		title.grid(row=0, column=0)
		titleFrame.columnconfigure(0, weight=1)

		cb = self.make_close_button(titleFrame)
		cb.grid(row=0, column=1)

		self.frame.rowconfigure(1, weight=1)
		self.frame.columnconfigure(0, weight=1)
		self.frame.config(bd=1, relief="solid")

		tableFrame = Tkinter.Frame(self.frame)
		tableFrame.grid(row=1, column=1, sticky='nsew')

		index = self.movie.plotNames.index(plotName)
		self.numAtoms = numAtoms = self.movie.plotAtoms[index]
		if numAtoms is None:
			self.term = term = plotName.lower()
		elif numAtoms > 0:
			self.term = term = plotName.lower()[:-1]
		else:
			self.term = term = plotName
		from CGLtk.Table import SortableTable
		self.table = table = SortableTable(tableFrame)
		table.addColumn("", "rgb", format=(False, False))
		table.addColumn(plotsDialog.shownTitle, "shown", format=bool)
		def getTableVal(plt, s=self):
			if hasattr(s, '_tableValRefreshPending'):
				return None
			return s.valCaches[plt].get(s.movie.model.activeCoordSet.id, None)
		table.addColumn(term.capitalize(), getTableVal, format=self.movie.plotFormats[index])

		self._plottables = []
		plottables = []
		self.plotValFunc = self.movie.plotValFuncs[index]
		if numAtoms is None:
			if len(self.plotValFunc) > 1 or self.plotValFunc[0][0] != plotName:
				table.addColumn("Type", lambda v: v.plotType)
			for plotType, plotValFunc in self.plotValFunc:
				plottable = self._genPlottable(ScalarPlottable, plotType, plottables=plottables)
				plottable.plotValFunc = plotValFunc
				plottables.append(plottable)
			self.plotValFunc = None
		elif numAtoms > 0:
			for i in range(numAtoms):
				table.addColumn("Atom %d" % (i+1), lambda v, i=i: str(v.atoms[i]))
		else:
			table.addColumn("Frame #", lambda v: v.frameNum)
			table.addColumn("# atoms", lambda v: len(v.atoms))

		table.setData(self._plottables)
		table.launch(browseCmd=self._tableBrowseCB)
		table.grid(row=0, column=0, sticky="nsew")
		tableFrame.rowconfigure(0, weight=1)
		tableFrame.columnconfigure(0, weight=1)
		if numAtoms is not None:
			f = Tkinter.Frame(tableFrame)
			f.grid(row=1, column=0)
			Tkinter.Button(f, text="Plot", command=self.plot).grid(row=0, column=0)
			if numAtoms > 0:
				Tkinter.Label(f, text="%s from %d selected atoms" % (term, numAtoms)
					).grid(row=0, column=1)
			else:
				Tkinter.Label(f, text="%s from selected atoms, if any" % (term,)
					).grid(row=0, column=1)
				optionsFrame = Tkinter.Frame(f)
				optionsFrame.grid(row=1, column=0, columnspan=2)
				from chimera.tkoptions import IntOption, BooleanOption
				self.frameNumOpt = IntOption(optionsFrame, 0, "vs. frame",
					self.movie.startFrame, None, min=self.movie.startFrame,
					max=self.movie.endFrame)
				self.ignoreSolventIonsOpt = BooleanOption(optionsFrame, 1,
					"Ignore solvent and non-metal ions", True, None)
				self.ignoreHydrogensOpt = BooleanOption(optionsFrame, 2,
					"Ignore hydrogens", True, None)
				from gui import IgnoreMetalIonsOption as IMIO
				self.metalIonsOpt = IMIO(optionsFrame, 4, IMIO.defaultLabel,
					IMIO.defaultValue, None)

			f = Tkinter.Frame(tableFrame)
			f.grid(row=2, column=0)
			Tkinter.Button(f, text="Delete", command=self.deletePlot,
				).grid(row=0, column=0)
			Tkinter.Label(f, text="chosen %ss" % term).grid(row=0, column=1)

			if term[0] in "aeiou":
				mod = "n"
			else:
				mod = ""
			self.mod = mod
			if self.numAtoms > 0:
				self.hint = Tkinter.Label(self.frame, text="Select %d atoms and click\n"
					"'Plot' to plot a%s %s" % (numAtoms, mod, term))
				self.hint.grid(row=1, column=0)
			else:
				self.hint = None

		from matplotlib.figure import Figure
		mpFigure = Figure()
		self.timeLine = mpFigure.add_subplot(111)
		from matplotlib.backends.backend_tkagg \
			import FigureCanvasTkAgg, NavigationToolbar2TkAgg
		self.mpFrame = mpFrame = Tkinter.Frame(self.frame)
		mpFrame.grid(row=1, column=0, sticky="nsew")
		mpFrame.grid_remove()
		figFrame = Tkinter.Frame(mpFrame)
		figFrame.grid(row=0, column=0, sticky="nsew")
		figFrame.bind('<Configure>', lambda e, s=self, f=figFrame:
			f.after_idle(lambda s=s: s.plottables and
			hasattr(s, 'timeLineBackground') and
			s.drawTimeLine()))
		mpFrame.columnconfigure(0, weight=1)
		mpFrame.rowconfigure(0, weight=1)
		self.mpFigureCanvas = mpFigureCanvas = FigureCanvasTkAgg(mpFigure,
												master=figFrame)
		mpFigureCanvas.get_tk_widget().pack(side="top", fill="both", expand=True)
		tbFrame = Tkinter.Frame(mpFrame)
		tbFrame.grid(row=1, column=0, sticky='w')
		NavigationToolbar2TkAgg(mpFigureCanvas, tbFrame)
		for event in ['button_press', 'motion_notify']:
			mpFigure.canvas.mpl_connect(event+'_event', self._mouseHandler)

		self.triggerInfo = {}
		self.valCaches = {}

		self.plottables = plottables

	def deletePlot(self):
		plottables = self.plottables
		for pa in self.table.selected():
			plottables.remove(pa)
		self.plottables = plottables

	def drawFrameIndicator(self, fn):
		tl = self.timeLine
		if not hasattr(self, 'frameIndicator'):
			self.frameIndicator = tl.plot([fn, fn], [self.ymin, self.ymax],
				color=(0,0,0), animated=True)[0]
		canvas = tl.figure.canvas
		canvas.restore_region(self.timeLineBackground)
		self.frameIndicator.set_xdata([fn, fn])
		self.frameIndicator.set_ydata([self.ymin, self.ymax])
		tl.draw_artist(self.frameIndicator)
		canvas.blit(tl.bbox)

	def drawTimeLine(self):
		tl = self.timeLine
		tl.clear()

		csMap = self.movie.model.coordSets
		xs = csMap.keys()
		xs.sort()
		if xs and xs[0] == 0:
			offset = 1
		else:
			offset = 0

		if self.numAtoms is None:
			ymax = ymin = None
		elif self.numAtoms > 2:
			ymax = None
		else:
			ymax = 0.0
		for plottable in self.plottables:
			if not plottable.shown:
				continue
			valCache = self.valCaches.setdefault(plottable, {})
			pvf = self.plotValFunc
			if pvf is None:
				pvf = plottable.plotValFunc
			if self.numAtoms == 0:
				baseCS = csMap[plottable.frameNum - offset]
			ys = []
			for i in xs:
				try:
					val = valCache[i]
				except KeyError:
					if self.numAtoms is None:
						val = valCache[i] = pvf(i+offset)
					elif self.numAtoms > 0:
						val = valCache[i] = pvf(*[a.coord(csMap[i])
											for a in plottable.atoms])
					else:
						val = valCache[i] = pvf(baseCS, csMap[i], plottable.atoms)
				ys.append(val)
				if self.numAtoms is None:
					if val is not None:
						if ymax is None:
							ymin = ymax = val
						else:
							ymin = min(ymin, val)
							ymax = max(ymax, val)
				elif ymax is not None:
					if val is None:
						if 'ymax' not in valCache:
							valCache['ymax'] = None
					else:
						valCache['ymax'] = max(valCache.get('ymax', 0.0), val)

			if xs and xs[0] == 0:
				offsetXs = [x+1 for x in xs]
			else:
				offsetXs = xs
			if self.numAtoms is not None and self.numAtoms > 2:
				for wxs, wys in self.wrapAngleValues(offsetXs, ys):
					tl.plot(wxs, wys, color=plottable.rgb)
			else:
				tl.plot(offsetXs, ys, color=plottable.rgb)
			if ymax is not None and self.numAtoms is not None:
				ymax = max(ymax, valCache['ymax'])
		if self.numAtoms is None:
			if ymax is not None:
				mag = ymax - ymin
				unit = 1
				if unit < mag:
					while unit * 50 < mag:
						unit *= 10
				else:
					while unit * 5 > mag:
						unit /= 10.0
				from math import floor
				unitMin = floor(ymin/unit) * unit - unit
				if unitMin < 0.0 and ymin >= 0.0:
					unitMin = 0.0
				unitMax = floor(ymax/unit) * unit + unit
				if unitMax > 0.0 and ymax <= 0.0:
					unitMax = 0.0
				self.ymin, self.ymax = unitMin, unitMax
		elif self.numAtoms > 2:
			self.ymin, self.ymax = -180.0, 180.0
		else:
			unit = 1
			if unit < ymax:
				while unit * 50 < ymax:
					unit *= 10
			unitMax = int(ymax/unit) * unit + unit
			self.ymin, self.ymax = 0.0, unitMax
		from matplotlib.ticker import ScalarFormatter
		tl.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
		tl.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
		tl.xaxis.set_minor_formatter(ScalarFormatter(useOffset=False))
		tl.yaxis.set_minor_formatter(ScalarFormatter(useOffset=False))
		tl.set_ylim(ymin=self.ymin, ymax=self.ymax)
		tl.set_xlim(xmin=self.movie.startFrame, xmax=self.movie.endFrame)
		self.mpFigureCanvas.show()

		self.timeLineBackground = tl.figure.canvas.copy_from_bbox(tl.bbox)
		self.drawFrameIndicator(self.movie.currentFrame.get())

	def plot(self):
		kw = {}
		if self.numAtoms > 0:
			atoms = selection.currentAtoms(ordered=True)
			if len(atoms) != self.numAtoms:
				self.plotsDialog.status("Must select exactly %d atoms\n"
					"to plot a%s %s" % (self.numAtoms, self.mod, self.term), color="red")
				return
		elif self.numAtoms == 0:
			from analysis import analysisAtoms, AnalysisError
			try:
				atoms = analysisAtoms(self.movie.model.Molecule(), True,
						self.ignoreSolventIonsOpt.get(), self.ignoreHydrogensOpt.get(),
						self.metalIonsOpt.get())
			except AnalysisError, v:
				raise UserError(unicode(v))
			kw['frameNum'] = self.frameNumOpt.get()
		self.plotsDialog.status("")
		self.plottables += [self._genPlottable(AtomsPlottable, atoms, **kw)]

	def getPlottables(self):
		return self._plottables[:]

	def setPlottables(self, plottables):
		prevPlottables = set(self._plottables)
		newPlottables = set(plottables)
		if newPlottables == prevPlottables:
			return
		self._plottables = plottables

		if not prevPlottables:
			# enable triggers
			if self.numAtoms is not None:
				if self.hint:
					self.hint.grid_remove()
			self.mpFrame.grid()
			self.triggerInfo[(chimera.triggers, 'Atom')] = \
				chimera.triggers.addHandler('Atom', self._atomsChangeCB, None)
			self.triggerInfo[(chimera.triggers, 'CoordSet')] = \
				chimera.triggers.addHandler('CoordSet', self._coordsetChangeCB, None)
			self.triggerInfo[(self.movie.triggers, self.movie.NEW_FRAME_NUMBER)] = \
				self.movie.triggers.addHandler(self.movie.NEW_FRAME_NUMBER,
					self._newFrameCB, None)
		if newPlottables:
			self.drawTimeLine()
		else:
			# disable triggers
			self.mpFrame.grid_remove()
			if self.numAtoms is not None:
				if self.hint:
					self.hint.grid()
			for info, handler in self.triggerInfo.items():
				triggers, trigName = info
				triggers.deleteHandler(trigName, handler)
			self.triggerInfo = {}

		self.table.setData(plottables)
		self.table.requestFullWidth()

	plottables = property(getPlottables, setPlottables)

	def wrapAngleValues(self, xs, ys):
		prevX, prevY = None, None
		newXs = []
		newYs = []
		xys = [(newXs, newYs)]
		for x, y in zip(xs, ys):
			if prevY is not None:
				if y is not None:
					if abs(y - prevY) > 180.0:
						if prevY < 0.0:
							v1 = 180.0 + prevY
							v2 = 180.0 - y
							y1, y2 = -180.0, 180.0
						else:
							v1 = 180.0 - prevY
							v2 = 180.0 + y
							y1, y2 = 180.0, -180.0
						xcross = prevX + (x - prevX) * v1 / (v1 + v2)
						newXs.append(xcross)
						newYs.append(y1)
						newXs = [xcross]
						newYs = [y2]
						xys.append((newXs, newYs))
			prevX, prevY = x, y
			newXs.append(x)
			newYs.append(y)
		return xys

	def _atomsChangeCB(self, trigName, myData, trigData):
		if trigData.deleted:
			newPlottables = []
			for plottable in self.plottables:
				if not isinstance(plottable, AtomsPlottable):
					newPlottables.append(plottable)
					continue
				for a in plottable.atoms:
					if a in trigData.deleted:
						break
				else:
					newPlottables.append(plottable)
			self.plottables = newPlottables

	def _coordsetChangeCB(self, trigName, myData, trigData):
		if trigData.created:
			relevant = trigData.created & set(self.movie.model.coordSets.values())
			if relevant:
				self.drawTimeLine()

	def _depictionCB(self, plottable):
		self.drawTimeLine()

	def _genPlottable(self, klass, *args, **kw):
		from CGLtk.color import distinguishFrom
		used = [(0,0,0), (1,1,1)] # distinguish from background and time indicator
		used.extend([p.rgb for p in kw.pop('plottables', self.plottables)])
		rgb = distinguishFrom(used, numCandidates=5)
		return klass(rgb, self._depictionCB, *args, **kw)

	def _mouseHandler(self, event):
		if type(event.button) != int or event.xdata == None:
			return
		fn = min(max(self.movie.startFrame, int(event.xdata+0.5)),
				self.movie.endFrame)
		self.movie.LoadFrame(fn)

	def _newFrameCB(self, trigName, myData, frameNumber):
		self.drawFrameIndicator(frameNumber)
		hadattr = hasattr(self, '_tableValRefreshPending')
		if hadattr:
			self.frame.after_cancel(self._tableValRefreshPending)
		def refreshTableVals(s=self):
			delattr(self, '_tableValRefreshPending')
			s.table.refresh()
		self._tableValRefreshPending = self.frame.after(200, refreshTableVals)
		if not hadattr:
			self.table.refresh()

	def _tableBrowseCB(self, plottables):
		selAtoms = []
		for plottable in plottables:
			selAtoms.extend(getattr(plottable, 'atoms', []))
		if selAtoms:
			selection.setCurrent(selAtoms)

class AtomsPlottable(object):
	def __init__(self, rgb, depictionCB, atoms, frameNum=None):
		self.atoms = atoms
		self._rgb = rgb
		self._shown = True
		self._depictionCB = depictionCB
		if frameNum is not None:
			self.frameNum = frameNum

	def getRGB(self):
		return self._rgb

	def setRGB(self, rgb):
		if rgb == self._rgb:
			return
		self._rgb = rgb
		self._depictionCB(self)

	rgb = property(getRGB, setRGB)

	def getShown(self):
		return self._shown

	def setShown(self, shown):
		if shown == self._shown:
			return
		self._shown = shown
		self._depictionCB(self)

	shown = property(getShown, setShown)

class ScalarPlottable(object):
	def __init__(self, rgb, depictionCB, plotType):
		self._rgb = rgb
		self._shown = True
		self._depictionCB = depictionCB
		self.plotType = plotType

	def getRGB(self):
		return self._rgb

	def setRGB(self, rgb):
		if rgb == self._rgb:
			return
		self._rgb = rgb
		self._depictionCB(self)

	rgb = property(getRGB, setRGB)

	def getShown(self):
		return self._shown

	def setShown(self, shown):
		if shown == self._shown:
			return
		self._shown = shown
		self._depictionCB(self)

	shown = property(getShown, setShown)

class LoadFramesDialog(ModelessDialog):
	title = "Load Frames"
	buttons = ('OK',)
	help = "ContributedSoftware/movie/movie.html#plotload"
	oneshot = True
	default = 'OK'

	def __init__(self, plotsDialog):
		self.plotsDialog = plotsDialog
		self.movie = plotsDialog.movie
		ModelessDialog.__init__(self, master=plotsDialog.uiMaster())

	def destroy(self):
		self.movie = None
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		self.actionVar = Tkinter.StringVar(parent)
		self.actionVar.set("load all")

		Tkinter.Label(parent, text="Not all frames are loaded.\n"
			"What would you like to do?").grid(column=0)
		Tkinter.Radiobutton(parent, text="load all frames", value="load all",
			variable=self.actionVar).grid(column=0, sticky='w')
		f = Tkinter.Frame(parent)
		f.grid(column=0, sticky='w')
		Tkinter.Radiobutton(f, text="load every nth frame, n=", value="stride",
			variable=self.actionVar).grid(row=0, column=0)
		self.strideEntry = Tkinter.Entry(f, width=2)
		self.strideEntry.grid(row=0, column=1)
		Tkinter.Radiobutton(parent, text="plot currently-loaded frames (plot will"
			" update as more frames are played/loaded)", value="as is",
			variable=self.actionVar).grid(column=0)

	def Apply(self):
		action = self.actionVar.get()
		if action == "as is":
			return
		if action == "load all":
			stride = 1
		else:
			try:
				stride = int(self.strideEntry.get().strip())
			except ValueError:
				return

		# if a lot of frames, don't update status every frame...
		import math
		digits = int(math.log10(self.movie.endFrame-self.movie.startFrame)+0.5)
		if digits <= 2:
			updateRate = 1
		else:
			updateRate = 10 ** (digits-2)
		updateAt = None
		# load needed coord sets...
		for frameNum in range(self.movie.startFrame, self.movie.endFrame+1, stride):
			if not self.movie.findCoordSet(frameNum):
				if updateAt is None:
					updateAt = frameNum
				if updateAt == frameNum:
					self.plotsDialog.status("loading frame %d" % frameNum)
					updateAt += updateRate
				self.movie._LoadFrame(frameNum, makeCurrent=False)
		self.plotsDialog.status("Requested frames loaded")

	def Close(self):
		self.plotsDialog.dependentDialogs.remove(self)
		ModelessDialog.Close(self)



