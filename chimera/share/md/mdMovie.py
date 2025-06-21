from Movie.gui import MovieDialog
import Pmw, Tkinter

class mdMovieDialog(MovieDialog):
	
	def __init__(self, ensemble, biomet_parm = None, biomet_version = None, *args, **kw):
		self.sessionHandler = None
		self.parm = biomet_parm
		self.title = "Molecular Dynamics: %s" % ensemble.name
		self.ensemble = ensemble
		plotInfo = []
		potEnergy=[]
		kinEnergy=[]
		temp=[]
		for a in biomet_parm:
			potEnergy.append(float(a[0]))
			kinEnergy.append(float(a[1]))
			temp.append(float(a[2]))

		for name, values in [("Potential Energy", potEnergy),("Kinetic Energy",kinEnergy),("Temperature",temp)]:
			plotInfo.append([name, None, [(
					name, lambda i, values=values: values[i-1])
				], "%.3f", 3])

		kw['additionalPlotTypes'] = kw.get('additionalPlotTypes', []) + plotInfo
		MovieDialog.__init__(self, ensemble, *args, **kw)

	def fillInUI(self,parent):
		mainFrame = Tkinter.Frame(parent)
		mainFrame.grid(row=0, column=0, sticky="nsew")
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(0, weight=1)
		MovieDialog.fillInUI(self, mainFrame)
		self.__intPlot = Tkinter.IntVar(parent)
		self.__intPlot.set(False)

		self.__intGroup = Pmw.Group(mainFrame,
				tag_text='Interactions Plotting')
		self.__intGroup.grid(column=0, row=5, sticky = 'nsew')
		self.__intGroup.grid_remove()
		self.molButton = Pmw.ButtonBox(self.__intGroup.interior(),
				labelpos = 'n',
				label_text = 'Set the two atom collections')
		self.molButton.grid(column=0,row=0,sticky='nsew',columnspan=3)
		self.molButton.add('Set collection 1', command=self._collection1)
		self.molButton.add('Set collection 2', command=self._collection2)
		self.selectCalc = Pmw.RadioSelect(self.__intGroup.interior(),
				buttontype = 'radiobutton',
				command = self._selectPlotProc,
				orient = 'vertical')
		self.selectCalc.grid(column = 0, rowspan = 3, row = 2, sticky = 'nsew')
		for text in ('Every ', 'From frame '):
			self.selectCalc.add(text)
		self.entryPlot1 = Pmw.EntryField(self.__intGroup.interior(),
				labelpos = 'e',
				value = 1,
				label_text = ' frames',
				validate = {'validator' : 'real'})
		self.entryPlot1.grid(column = 1, row = 2, sticky = 'nsew')
		self.entryPlot2 = Pmw.EntryField(self.__intGroup.interior(),
				labelpos = 'e',
				value = 'first',
				label_text = 'to frame')
		self.entryPlot2.grid(column = 1, row = 4, sticky = 'nsew')
		self.entryPlot3 = Pmw.EntryField(self.__intGroup.interior(),
				value = 'last')
		self.entryPlot3.grid(column = 3, row = 4, sticky = 'nsew')
		self.plotButton = Tkinter.Button(self.__intGroup.interior(),
				text="Plot",
				command=self.__plot)
		self.plotButton.grid(column=1, columnspan = 2, row=6, sticky = 'nsew')
		
		self.analysisMenu.add_checkbutton(label="Plot Interactions",
				variable=self.__intPlot, command=self.__interactions)

	def _selectPlotProc(self, tag):
		if tag == 'Every ':
			self.plotProc = self.entryPlot1.getvalue()
		else:
			self.plotProc = (self.entryPlot2.getvalue(), self.entryPlot3.getvalue())

	def __interactions(self):
		state = self.__intPlot.get()
	
		import chimera	
		if state:
			self.__intGroup.grid()
			self.selectCalc.invoke('Every ')
		else:
			self.__intGroup.grid_remove()

	def _collection1(self):
		import chimera
		self.col1 = [a for a in chimera.selection.currentAtoms()]
		for a in self.col1:
			a.drawMode=1
			for b in a.bonds:
				b.drawMode = 1
				b.radius = 0.1
		chimera.selection.clearCurrent()		

	def _collection2(self):
		import chimera
		self.col2 = [a for a in chimera.selection.currentAtoms()]
		for a in self.col2:
			a.drawMode=1
			for b in a.bonds:
				b.drawMode = 1
				b.radius = 0.1
		chimera.selection.clearCurrent()
	
	def __plot(self):
		import energyMMTKinter
		import chimera
		from chimera import Point
		if not hasattr(self, 'col1') or not hasattr(self, 'col2'):
			from chimera import UserError
			raise UserError("Must set collections 1 and 2 before plotting")
		csNumbers = self.model.coordSets.keys()
		csNumbers.sort()
		energyList=list()
		lista = list()
		lista.append(self.model._mol)
		en = energyMMTKinter.energyMMTKinter(lista,self.col1,self.col2,prep=False)
		en.loadMMTKCoordinates()
		min = 1
		max = len(csNumbers)
		if len(self.plotProc) == 2:
			self.plotProc = (self.entryPlot2.getvalue(), self.entryPlot3.getvalue())
			if self.plotProc[0] == 'first':
				min=1
			else:
				min = self.plotProc[0]
			if self.plotProc[1] == 'last':
				max = int(len(csNumbers))
			else:
				max = int(self.plotProc[1])
			i = int(min)
			while i != max:
				cs = self.model.coordSets[i]
				energy = en.energyEvaluator(cs)
				energyList.append(energy)
				i += 1
		else:
			self.plotProc = self.entryPlot1.getvalue()
			csn = 1
			while csn < len(csNumbers):
				cs = self.model.coordSets[csn]
				energy = en.energyEvaluator(cs)
				energyList.append(energy)
				csn += int(self.plotProc)
				

		self.enPlots = intPlot(energyList, self, title="Interactions")
		self.subdialogs.append(self.enPlots)
	
		#
		# Code for restoring the session
		#

	def sesSave_gatherData(self):
		from SimpleSession import sessionID
		sesData = MovieDialog.sesSave_gatherData(self)
		sesData["biomet_info"] = (1, self.parm)
		return sesData

	def sesSave_writeCode(self, sesData, sessionFile):
		from SimpleSession import sesRepr
		print >> sessionFile, "mdData=%s" % sesRepr(sesData)
		print >> sessionFile, """
try:
	from Movie import restoreSession
	from md.mdMovie import mdMovieDialog
	version, parm = mdData.pop("biomet_info")
	kw={"biomet_parm":parm, "biomet_version":version}
	mdMovie = restoreSession(mdData, mdDialog=mdMovieDialog,**kw)
except:
	reportRestoreError("Error restoring Molecular Dynamics Trajectory")
"""

from plotdialog import PlotDialog
class intPlot(PlotDialog):
	"""Display -energy vs step semilog plot.  It's -energy
	because energy values are always negative."""

	# TODO There should be some code for cleaning up the variable
	# monitoring on exit.  We should also exit if the movie dialog
	# goes away.
	oneshot = True

	def __init__(self, var, movieDialog, **kw):
		PlotDialog.__init__(self, **kw)
		self.movieDialog = movieDialog
		# X axis is step number
		self.steps = range(1, len(var) + 1)
		# Y axis is -energy
		try:
			self.var = []
			self.var2 = []
			for inf in var:
				self.var.append(inf[0])
				self.var2.append(inf[1])
			self.dual = True
		except:
			self.var = var
			self.dual = False

		self.subplot = self.add_subplot(1,1,1)
		self._displayData()
		# Register plot picking function so we can jump to the
		# corresponding frame of the trajectory
		# Monitor the movie dialog frame counter (Tk) variable
		# so that we highlight the currently displayed step
		#self.handlerID = movieDialog.triggers.addHandler(movieDialog.NEW_FRAME_NUMBER,
		#				self._update, None)

	def _displayData(self):
		ax = self.subplot
		ax.clear()
		# "markevery" is used to put a single marker on the
		# currently displayed step.  The two arguments are
		# which point to start adding markers and how often
		# to add markers.  We set the latter to a large number
		# so that only one marker is added.
		step = self.movieDialog.currentFrame.get()
		#every = (self.steps.index(step), len(self.steps))
		lines = ax.plot(self.steps, self.var,
					c='r', picker=False)
					#arker='o', markevery=every, mfc='r')
		self.line = lines[0]
		# Save the created line so we can update it in _update.
		ax.set_xlabel("Step")
		ax.set_ylabel("%s" % self.movieDialog.name)
		ax.set_title("%s vs. Time Step" % self.movieDialog.name)
		ax.grid(True)
		self.draw()


	def Close(self):
		#mvDlg = self.movieDialog
		#del mvDlg.enPlots[self.title]
		#curChecked = list(mvDlg.options.getvalue())
		#curChecked.remove(self.title)
		#mvDlg.options.setvalue(curChecked)
		PlotDialog.Close(self)

	#def destroy(self):
	#	self.movieDialog.triggers.deleteHandler(self.movieDialog.NEW_FRAME_NUMBER,
	#					self.handlerID)
	#	PlotDialog.destroy(self)
