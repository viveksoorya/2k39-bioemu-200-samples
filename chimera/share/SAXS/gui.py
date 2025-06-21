# -----------------------------------------------------------------------------
# Dialog for computing small-angle x-ray scattering profile.
#

# -----------------------------------------------------------------------------
#
from chimera.baseDialog import ModelessDialog
import os.path
class SAXS_Dialog(ModelessDialog):

	title = 'Small-angle X-ray Profile 2.0'
	name = 'small-angle x-ray profile 2.0'
	buttons = ('Calculate Profile', 'Options', 'Close',)
	help = 'ContributedSoftware/saxs/saxs.html'
	
	def fillInUI(self, parent):

		import Tkinter, Pmw
		from CGLtk import Hybrid
		from chimera.tkoptions import OutputFileOption, InputFileOption

		self.plot = None
		self.expHistory = ""
		self.expDup = False

		t = parent.winfo_toplevel()
		self.toplevel_widget = t
		t.withdraw()

		parent.columnconfigure(0, weight = 0)
		parent.columnconfigure(1, weight = 1)
		row = 0

		from chimera.preferences import addCategory, HiddenCategory
		prefs = addCategory("SAXS", HiddenCategory,
						optDict = {'saxs executable': '', 'temp output folder':''})
		self.preferences = prefs


		from chimera import widgets as w
		mm = w.ExtendedMoleculeOptionMenu(parent, label_text = 'Molecule: ',
										labelpos = 'w',
										labels = ['selected atoms','all molecules'])
		mm.grid(row = row, column = 0, columnspan=2, sticky = 'w')
		row += 1
		self.molecule_menu = mm
		
		# Experimental profile 
		balloonText = 'Please optionally specify the experimental SAXS profle data.\n'\
					'The fitting chi value will be shown in the Reply Log.'
		self.experimental_profile = InputFileOption(parent, row,
							'Experimental profile (optional)', 
							None, self._expDataExistCB,
							balloon = balloonText)
		row += 1
		
		#ep = Hybrid.Entry(parent, 'Experimental profile (optional) ', 25, browse = True)
		#ep.frame.grid(row = row, column = 0, sticky = 'ew')
		#self.experimental_profile = ep.variable

		op = Hybrid.Popup_Panel(parent)
		opf = op.frame
		opf.grid(row = row, column = 0, columnspan= 2, sticky = 'news')
		opf.grid_remove()
		opf.columnconfigure(0, weight=0)
		opf.columnconfigure(1, weight=1)
		self.options_panel = op.panel_shown_variable
		row += 1
		orow = 0

		cb = op.make_close_button(opf)
		cb.grid(row = orow, column = 2, sticky = 'e')
		orow += 1

#-- Advanced Options: Excluded Volume Adjustment (exvo) -e
		self.exvoLabel = Tkinter.Label(opf, 
					text='Excluded volume adjustment: ',
					state='disabled')
		self.exvoLabel.grid(row=orow, column =0, sticky='e')
		self.exvoVar = Tkinter.IntVar(opf)
		self.exvoVar.set(1)
		self.exvoCheckButton = Tkinter.Checkbutton(opf,
				variable=self.exvoVar,
				state='disabled')
		self.exvoCheckButton.grid(row=orow, column=1, sticky='w')
		balloonText = 'Adjust the protein excluded volume to improve fitting. \n'\
					'Disabled if no experimental profile data provided.'
		Pmw.Balloon(opf).bind(self.exvoCheckButton, balloonText)
		Pmw.Balloon(opf).bind(self.exvoLabel, balloonText)
		orow += 1

#-- Advanced Options: Water layer (water)	-w
		self.waterLabel = Tkinter.Label(opf, 
					text='Hydration (water) layer: ',
					state='disabled')
		self.waterLabel.grid(row=orow, column =0, sticky='e')
		self.waterVar = Tkinter.IntVar(opf)
		self.waterVar.set(1)
		self.waterCheckButton = Tkinter.Checkbutton(opf,
				variable = self.waterVar,
				state='disabled')
		self.waterCheckButton.grid(row=orow, column=1, sticky='w')
		balloonText = 'Use Hydration layer for improved fitting. \n'\
					'Disabled if no experimental profile data provided.'
		Pmw.Balloon(opf).bind(self.waterCheckButton, balloonText)
		Pmw.Balloon(opf).bind(self.waterLabel, balloonText)

		orow += 1

#-- Advanced Options: Background adjustment (bgad)	-b 
		self.bgadLabel = Tkinter.Label(opf, 
					text='Experimental background adjustment: ',
					state='disabled')
		self.bgadLabel.grid(row=orow, column =0, sticky='e')
		self.bgadVar = Tkinter.IntVar(opf)
		self.bgadVar.set(0)
		self.bgadCheckButton = Tkinter.Checkbutton(opf,
				variable = self.bgadVar,
				state='disabled')
		self.bgadCheckButton.grid(row=orow, column=1, sticky='w')
		balloonText = 'Adjust the background of the experimental profile.\n'\
					'Disabled if no experimental profile data provided.'
		Pmw.Balloon(opf).bind(self.bgadCheckButton, balloonText)
		Pmw.Balloon(opf).bind(self.bgadLabel, balloonText)
		orow += 1


#-- Advanced Options: Maximal q value(maxq) -q 
		maxqLabel = Tkinter.Label(opf, text='Maximal q value: ')
		maxqLabel.grid(row=orow, column =0, sticky='e')
		self.maxqEntry = Pmw.EntryField(opf,
				value = 0.5,
				validate = {'validator' : 'real'},
				entry_width = 12 )
		self.maxqEntry.grid(row=orow, column=1, sticky='w')
		balloonText = "Maximal q value"
		Pmw.Balloon(opf).bind(self.maxqEntry, balloonText)
		Pmw.Balloon(opf).bind(maxqLabel, balloonText)
		orow += 1
		
#-- Advanced Options: Profile size (pfsz) -s
		pfszLabel = Tkinter.Label(opf, text='Profile size: ')
		pfszLabel.grid(row=orow, column =0, sticky='e')
		self.pfszEntry = Pmw.EntryField(opf,
				value = 500,
				validate = {'validator' : 'numeric',
						'min' : '100', 'max' : '1000',
						'minstrict' : 0, 'maxstrict' : 0},
				entry_width = 12 )
		self.pfszEntry.grid(row=orow, column=1, sticky='w')
		balloonText = "Number of points in the computed profile.(100-1000)"
		Pmw.Balloon(opf).bind(self.pfszEntry, balloonText)
		Pmw.Balloon(opf).bind(pfszLabel, balloonText)
		orow += 1


#-- Advanced Options Hydrogens: hydrogen (dydrogen) -h
		hydrogenLabel = Tkinter.Label(opf, text='Implicit hydrogens: ')
		hydrogenLabel.grid(row=orow, column =0, sticky='e')
		self.hydrogenVar = Tkinter.IntVar(opf)
		self.hydrogenVar.set(1)
		hydrogenCheckButton = Tkinter.Checkbutton(opf,
				variable = self.hydrogenVar)
		hydrogenCheckButton.grid(row=orow, column=1, sticky='w')
		balloonText = 'Implicitly consider hydrogens in PDB files'
		Pmw.Balloon(opf).bind(hydrogenCheckButton, balloonText)
		Pmw.Balloon(opf).bind(hydrogenLabel, balloonText)
		orow += 1



		
		"""
		bgadLabel = Tkinter.Label(opf, text='Background adjustment: ')
		bgadLabel.grid(row=orow, column =0, sticky='e')
		self.bgadVar = Tkinter.IntVar(opf)
		self.bgadVar.set(0)
		frame = Pmw.Group(opf, tag_pyclass = None)
		bgadCheckButton = Tkinter.Checkbutton(frame.interior(),
				variable = self.bgadVar,
				command = self._bgadEnableEntry)
		bgadCheckButton.grid(row=0, column=1, sticky='w')
		balloonText = 'Adjust the background of the experimental profile'
		Pmw.Balloon(opf).bind(bgadCheckButton, balloonText)
		self.bgadEntry = Pmw.EntryField(frame.interior(),
				value = 0.2,
				validate = {'validator' : 'real'},
				entry_width = 8)
		self.bgadEntry.grid(row=0, column=2, sticky='w')
		frame.grid(row=orow, column=1, sticky='w')
		self._bgadEnableEntry()
		balloonText = 'If enabled, recommended q value is 0.2.'
		Pmw.Balloon(opf).bind(self.bgadEntry, balloonText)
		orow += 1
		
#-- Advanced Options: use offset in fitting (offset) -o
		offsetLabel = Tkinter.Label(opf, text='Use offset in fitting: ')
		offsetLabel.grid(row=orow, column =0, sticky='e')
		self.offsetVar = Tkinter.IntVar(opf)
		self.offsetVar.set(0)
		frame = Pmw.Group(opf, tag_pyclass = None)
		offsetCheckButton = Tkinter.Checkbutton(frame.interior(),
				variable = self.offsetVar,
				command = self._offsetEnableEntry)
		offsetCheckButton.grid(row=0, column=1, sticky='w')
		balloonText = 'Use offset in fitting'
		Pmw.Balloon(opf).bind(offsetCheckButton, balloonText)
		self.offsetEntry = Pmw.EntryField(frame.interior(),
				value = 0.0,
				validate = {'validator' : 'real'},
				entry_width = 8)
		self.offsetEntry.grid(row=0, column=2, sticky='w')
		frame.grid(row=orow, column=1, sticky='w')
		self._offsetEnableEntry()
		balloonText = 'e.g. input 10.0, offset the curve 10.0 left?' #TODO
		Pmw.Balloon(opf).bind(self.offsetEntry, balloonText)
		orow += 1
		"""

#-- Advanced Options perform fast coarse grained profile :  calculation (coarsegrained) -r
		coarsegrainedLabel = Tkinter.Label(opf, text='Fast coarse-grained profile: ')
		coarsegrainedLabel.grid(row=orow, column =0, sticky='e')
		self.coarsegrainedVar = Tkinter.IntVar(opf)
		self.coarsegrainedVar.set(0)
		coarsegrainedCheckButton = Tkinter.Checkbutton(opf,
				variable = self.coarsegrainedVar)
		coarsegrainedCheckButton.grid(row=orow, column=1, sticky='w')
		balloonText = 'Compute the fast coarse-grained profile using CA atoms only'
		Pmw.Balloon(opf).bind(coarsegrainedCheckButton, balloonText)
		Pmw.Balloon(opf).bind(coarsegrainedLabel, balloonText)
		orow += 1

#-- Advanced Options: Use new plot window (newp)
		newpLabel = Tkinter.Label(opf, text='Use new plot window: ')
		newpLabel.grid(row=orow, column =0, sticky='e')
		self.newpVar = Tkinter.IntVar(opf)
		self.newpVar.set(0)
		newpCheckButton = Tkinter.Checkbutton(opf,
				variable = self.newpVar)
		newpCheckButton.grid(row=orow, column=1, sticky='w')
		balloonText = 'Open a new plot window to display the results'
		Pmw.Balloon(opf).bind(newpCheckButton, balloonText)
		Pmw.Balloon(opf).bind(newpLabel, balloonText)

		orow += 1

		""" Advanced Options: template
		#-- Advanced Options: xxxx (_xXx_) -X
		_xXx_Label = Tkinter.Label(opf, text='BLABLA: ')
		_xXx_Label.grid(row=orow, column =0, sticky='e')
		self._xXx_Var = Tkinter.IntVar(opf)
		self._xXx_Var.set(0)
		_xXx_CheckButton = Tkinter.Checkbutton(opf,
				variable = self._xXx_Var)
		_xXx_CheckButton.grid(row=orow, column=1, sticky='w')
		balloonText = 'BLABLABLA'
		Pmw.Balloon(opf).bind(_xXx_CheckButton, balloonText)
		orow += 1
		"""
#-- Advanced Options: Executable file (if run on local)
		#sPathLabel = Tkinter.Label(opf, text='Executable file (optional, if run on local): ')
		#sPathLabel.grid(row=orow, column =0, sticky='e')

		balloonText = "If choose to calculate the SAXS profile by a local version of \n" \
					"executable file, please specify the executable file."
		self.saxsPath = InputFileOption(opf, orow,
							'Local executable file (optional)', 
							prefs['saxs executable'], None,
							balloon = balloonText, dirsOnly=False)
		orow += 1

#-- Advanced Options: Output files location (optional)

		balloonText = "If specify the output files location, the calculation output files \n" \
					"and temp PDB files will be stored there."
		self.outputfilePath = OutputFileOption(opf, orow,
							'Output file location (optional)', 
							prefs['temp output folder'], None,
							balloon = balloonText, dirsOnly=True)
		orow += 1



#-- Advanced Options: citation
		from CGLtk.Citation import Citation
		Citation(opf, "D. Schneidman-Duhovny, M. Hammel, and A. Sali. FoXS: A Web server for\n"
					"Rapid Computation and Fitting of SAXS Profiles. NAR 2010.38 Suppl:W540-4",
					prefix= "Publications should cite:",
					url='https://www.ncbi.nlm.nih.gov/pubmed/20507903' ).grid(
					row = orow, column = 0, columnspan=2)
		

# Legend label
		self.legendLabel = []

	"""
	def _exvoEnableEntry(self):
		if self.exvoVar.get():
			self.exvoEntry.component('entry').config(state='normal')
		else:
			self.exvoEntry.component('entry').config(state='disabled')
		return
	def _bgadEnableEntry(self):
		if self.bgadVar.get():
			self.bgadEntry.component('entry').config(state='normal')
		else:
			self.bgadEntry.component('entry').config(state='disabled')
		return
	def _offsetEnableEntry(self):
		if self.offsetVar.get():
			self.offsetEntry.component('entry').config(state='normal')
		else:
			self.offsetEntry.component('entry').config(state='disabled')
		return
	"""

	def _expDataExistCB(self, expData):
		expath = expData.get()
		if expath and os.path.isfile(expath):
			self.bgadLabel.config(state='normal')
			self.bgadCheckButton.config(state='normal')
			self.exvoLabel.config(state='normal')
			self.exvoCheckButton.config(state='normal')
			self.waterLabel.config(state='normal')
			self.waterCheckButton.config(state='normal')
		else:
			self.bgadLabel.config(state='disabled')
			self.bgadCheckButton.config(state='disabled')
			self.exvoLabel.config(state='disabled')
			self.exvoCheckButton.config(state='disabled')
			self.waterLabel.config(state='disabled')
			self.waterCheckButton.config(state='disabled')
		return
		
	# ---------------------------------------------------------------------------
	#
	def CalculateProfile(self):

		self.compute_profile()

	# ---------------------------------------------------------------------------
	#
	def compute_profile(self):

		from chimera.replyobj import warning
		import os.path

		molecules, selected_only = self.chosen_atoms()
		if len(molecules) == 0:
			warning('No atoms selected for SAXS profile computation.\n')
			return

		expath = self.experimental_profile.get()
		from os.path import isfile
		if expath and not isfile(expath):
			warning('Experimental profile "%s" does not exist\n' % expath)
			expath = ''
		if expath: 
			if expath != self.expHistory: 
				self.expDup = False
				self.expHistory = expath
			else:
				self.expDup = True

		epath = self.executable_path()
		
		if len(self.outputfilePath.get()) > 0: 
			if os.path.exists(self.outputfilePath.get()):
				self.preferences['temp output folder'] = self.outputfilePath.get()
			else:
				warning('The specified Output files location "%s" does not exist!\n' 
						%self.outputfilePath.get())
		else:
			self.preferences['temp output folder'] = ''
			
#-- Advanced Options:
		AdvOpt = ""	 
		AdvOpt += "-q %s " %self.maxqEntry.getvalue() 	
		AdvOpt += "-s %s " %self.pfszEntry.getvalue() 
		
		if not self.waterVar.get():
			AdvOpt += "-w "
		if not self.hydrogenVar.get():
			AdvOpt += "-h "
		if self.coarsegrainedVar.get():
			AdvOpt += "-r "

		if not self.exvoVar.get():
			AdvOpt += "-e 1.0 " 
		
		if self.bgadVar.get():
			AdvOpt += "-b 0.2 "
		
		"""
		if self.offsetVar.get():
			AdvOpt += "-o %s " %self.offsetEntry.getvalue()
		"""

		p = None if self.newpVar.get() else self.plot
		if self.newpVar.get():
			self.legendLabel = []
			self.expDup = False
			self.expHistory = expath

		print "Executable file path: ", epath
		print "Experimental data: ", expath
		print "Temp folder path: ", self.outputfilePath.get()
		print "Options pass to foxs: ",  AdvOpt
		print "duplicated experimental data: ", self.expDup
		

	
		import saxs
		p = saxs.show_saxs_profile(molecules, selected_only, epath, expath, AdvOpt,
						expDup = self.expDup,
						legendLabel = self.legendLabel,
						tempFolder = self.outputfilePath.get(), 
						dialog = p)
		if p:
			self.plot = p
			p.raiseWindow()

	# ---------------------------------------------------------------------------
	#
	def executable_path(self):

		epath = self.saxsPath.get()
		if len(epath) == 0:
			self.preferences['saxs executable'] = ''
			from CGLutil.findExecutable import findExecutable
			epath = findExecutable('profile')
			if epath is None:
				return None
		else:
			from os.path import isfile
			if not isfile(epath):
				return None
			self.preferences['saxs executable'] = epath

		return epath

	# ---------------------------------------------------------------------------
	#
	def chosen_atoms(self):

		m = self.molecule_menu.getvalue()
		from chimera import Molecule, openModels, selection
		if isinstance(m, Molecule):
			return [m], False
		elif m == 'selected atoms':
			mlist = list(set([a.molecule for a in selection.currentAtoms()]))
			return mlist, True
		elif m == 'all molecules':
			mlist = openModels.list(modelTypes = [Molecule])
			return mlist, False
		return [], False
			
	# ---------------------------------------------------------------------------
	#
	def Options(self):

		self.options_panel.set(not self.options_panel.get())

# -----------------------------------------------------------------------------
#
def saxs_dialog(create = False):

	from chimera import dialogs
	return dialogs.find(SAXS_Dialog.name, create=create)
	
# -----------------------------------------------------------------------------
#
def show_saxs_dialog():

	from chimera import dialogs
	return dialogs.display(SAXS_Dialog.name)

# -----------------------------------------------------------------------------
#
from chimera import dialogs
dialogs.register(SAXS_Dialog.name, SAXS_Dialog, replace = True)
