# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import Pmw
import chimera
from chimera.baseDialog import ModelessDialog
import Tkinter
from Tkinter import *
from chimera.widgets import MoleculeScrolledListBox
import chimera.dialogs
from DockPrep.gui import DockPrepDialog
from Solvate.gui import SolvateDialog
from AddCharge.gui import AddChargesDialog
from Addions.gui import AddionsDialog
from MMMD.gui import mmmdDialog
from chimera import selection, replyobj, UserError
from chimera.selection import ItemizedSelection
from StructMeasure.DistMonitor import distanceMonitor, addDistance, removeDistance, \
	precision, setPrecision, showUnits
from StructMeasure.prefs import prefs, ROT_LABEL, ROT_DIAL_SIZE, ANGLE_PRECISION, \
				TORSION_PRECISION, SHOW_DEGREE_SYMBOL
from OpenSave import SaveModeless
from chimera import tkoptions
from OpenSave import tildeExpand

SOLVATE = "Solvation"
CONS = "Constraints Etc."
#RUNOPT = "Running"
#FF = "ForceField"
PREP = "Prep Structure"
SETUP = "Run Parameters"

pageNames = [PREP,SOLVATE,CONS,SETUP]

class MolecularDynamicsDialog(ModelessDialog):
	title = "Molecular Dynamics Simulation"
	name = "Molecular Dynamics Simulation"
	help = "ContributedSoftware/md/md.html"
	buttons = ("Close",)
	provideStatus = True
	statusPosition = "above"

	def __init__(self):
		ModelessDialog.__init__(self)

		from SimpleSession import SAVE_SESSION
		import chimera
		self.sessionHandler = chimera.triggers.addHandler(SAVE_SESSION,
			self._sessionSaveCB, None)

	def fillInUI(self,parent):
		self.velScalerMaintain=False
		self.heating = Tkinter.IntVar(parent)
		self.heating.set(True)
		self.autoPBC = False
		self.prodRes = Tkinter.IntVar(parent)
		self.prodRes.set(False)
		self.minimization = Tkinter.IntVar(parent)
		self.minimization.set(True)
		self.pbc = Tkinter.IntVar(parent)
		self.pbc.set(False)
		self.prodBarostat = Tkinter.IntVar(parent)
		self.prodBarostat.set(False)
		self.prodVelScalerVar = False
		self.centroidList = None
		self.selfCentroidSelect=False	
		self.centroidOptionRestraint = False
		self.production = Tkinter.IntVar(parent)
		self.production.set(True)
		self.prodThermostat = Tkinter.IntVar(parent)
		self.prodThermostat.set(False)
		self.rot = Tkinter.IntVar(parent)
		self.rot.set(True)
		self.trans = Tkinter.IntVar(parent)
		self.trans.set(True)
		self.baro = Tkinter.IntVar(parent)
		self.baro.set(False)
		self.onLive = Tkinter.IntVar(parent)
		self.onLive.set(False)
		self.multi = Tkinter.IntVar(parent)
		self.multi.set(False)
		self.fixAtoms = ItemizedSelection()
		self.outside = False
		parent.columnconfigure(0, weight=1)
		parent.rowconfigure(0, weight=1)
		from chimera.widgets import MoleculeScrolledListBox
		self.molList = MoleculeScrolledListBox(parent,
						labelpos='w',
						listbox_selectmode="extended",
						label_text="Select model:")
		self.molList.grid(row=0, column=0, sticky="nsew")
		self.notebook = Pmw.NoteBook(parent) 
		self.notebook.grid(row=1, column=0, sticky="nsew")

		for pn in pageNames:
			pageID = pn
			self.notebook.add(pageID, tab_text=pn)

		#####################

		solv = self.notebook.page(SOLVATE)
		## original version that allowed for multiple solvation methods;
		## leaving it in, commented out, for possible future use in case a
		## second solvation method gets added
		"""
		self.labelSolvate = Tkinter.Label(solv, text = "Method:")
		self.labelSolvate.grid(column = 0, row = 1, sticky = 'w')
		self.SolvateMenu = Tkinter.StringVar(solv)
		self.SolvateMenu.set("Amber")
		self.SolvateMenuOptions = Tkinter.OptionMenu(solv,self.SolvateMenu,"Amber")
		self.SolvateMenuOptions.grid(column = 1, row = 1, sticky = 'nsew')
		self.SolvateButton = Tkinter.Button(solv, text = 'Solvate', command = self._solvate)
		self.SolvateButton.grid(column = 2, row = 1, sticky = 'nsew')
		self.labelion = Tkinter.Label(solv, text = "Counterions:")
		self.labelion.grid(column = 0, row = 3, sticky = 'w')
		self.ionButton = Tkinter.Button(solv, text = "Add", 
						command=lambda:chimera.dialogs.display(AddionsDialog.name))
		self.ionButton.grid(column = 1, row = 3, sticky = 'nsew')
		"""
		f = Tkinter.Frame(solv)
		f.grid(row=0, column=0, sticky='w')
		Tkinter.Button(f, text="Start Solvate tool", command=lambda ml=self.molList:
			chimera.dialogs.display(SolvateDialog.name).molList.setvalue(ml.getvalue())
			).grid(row=1, column=1)
		Tkinter.Button(f, text="Start Add Ions tool", command=lambda ml=self.molList:
			chimera.dialogs.display(AddionsDialog.name).molList.setvalue(ml.getvalue())
			).grid(row=1, column=2)
		self.pbcBox = Pmw.Group(solv, tag_text='Periodic Boundary Conditions',
					tag_pyclass=Tkinter.Checkbutton,
					tag_variable=self.pbc, tag_command=self._pbcChange)
		self.pbcBox.grid(column=0, row=1, sticky='nsew')
		
		self.pbcLabel = Pmw.Group(self.pbcBox.interior(), tag_text = "Box Size")
		self.pbcLabel.grid(column = 0, row = 1, sticky = 'w')
		self.xCoord = Pmw.EntryField(self.pbcLabel.interior(), entry_width=7,
				labelpos = 'w',
				label_text = 'X:',
				validate = {'validator':'real',
					'min':'0'},
				value = '0')
		self.xCoord.grid(column = 0, row = 0, sticky = 'w')
		self.yCoord = Pmw.EntryField(self.pbcLabel.interior(), entry_width=7,
				labelpos = 'w',
				label_text = 'Y:',
				validate = {'validator':'real',
					'min':'0'},
				value = '0')
		self.yCoord.grid(column = 1, row = 0, sticky = 'w')
		self.zCoord = Pmw.EntryField(self.pbcLabel.interior(), entry_width=7,
				labelpos = 'w',
				label_text = 'Z:',
				validate = {'validator':'real',
					'min':'0'},
				value = '0')
		self.zCoord.grid(column = 2, row = 0, sticky = 'w')
		self.autoPBCOption=Pmw.RadioSelect(self.pbcBox.interior(),
				buttontype = 'checkbutton',
				labelpos = 'w',
				label_text = 'Automatic box size:',
				command = self._autoPBC)
		self.autoPBCOption.add("")
		self.autoPBCOption.grid(column = 0, row = 2, sticky = 'nsew')
	

		###############################################3
	
		co = self.notebook.page(CONS)
		from itertools import count
		row = count()
		self.fixedAtomsVar = Tkinter.IntVar(co)
		self.fixedAtomsVar.set(False)
		self.FixGroup = Pmw.Group(co, tag_text = "Fixed Atoms",
				tag_pyclass=Tkinter.Checkbutton,
				tag_variable=self.fixedAtomsVar,
				tag_command=self._changed)
		self.FixGroup.grid(column = 0, row = row.next(), sticky='w')
		self.FixMenu = Tkinter.StringVar(self.FixGroup.interior())
		self.FixMenu.set("selected")
		self.FixMenuOptions = Tkinter.OptionMenu(self.FixGroup.interior(),self.FixMenu,"selected","unselected")
		self.FixMenuOptions.grid(column = 1, row = 0, sticky = 'nsew')
		self.FixMenuOptions.config(state = DISABLED)
		self.fixSetButton = Tkinter.Button(self.FixGroup.interior(),
                                                text = "Set", command = self._setAtoms)
		self.fixSetButton.grid(column=2, row=0, sticky='nsew')
		self.fixSetButton.config(state=DISABLED)

		#co.rowconfigure(6, weight = 1)
		#co.columnconfigure(0, weight = 1)

		transFrame = Tkinter.Frame(co)
		transFrame.grid(column=0, row=row.next(), sticky='w')
		Tkinter.Checkbutton(transFrame, text="Translation remover:",
			variable=self.trans).grid(row=0, column=0)
		self.transRemI = Pmw.EntryField(transFrame, labelpos='w',
			label_text="start", entry_width=5, value='1',
			validate={ 'validator':'numeric', 'minstrict': False,
				'maxstrict': False, 'min':'1'})
		self.transRemI.grid(row=0, column=1)
		self.transRemF = Pmw.EntryField(transFrame, labelpos='w',
			label_text="  end", entry_width=7, value='', validate=numberOrNone)
		self.transRemF.grid(row=0, column=2)
		self.transRemS = Pmw.EntryField(transFrame, labelpos='w',
			label_text="  apply every", entry_width=4, value='2',
			validate={ 'validator': 'numeric', 'minstrict': True, 'min':'1'})
		self.transRemS.grid(row=0, column=3)
		Tkinter.Label(transFrame, text="steps").grid(row=0, column=4)

		rotFrame = Tkinter.Frame(co)
		rotFrame.grid(column=0, row=row.next(), sticky='w')
		Tkinter.Checkbutton(rotFrame, text="Rotation remover:",
			variable=self.rot).grid(row=0, column=0)
		self.rotRemI = Pmw.EntryField(rotFrame, labelpos='w',
			label_text="start", entry_width=5, value='1',
			validate={ 'validator':'numeric', 'minstrict': False,
				'maxstrict': False, 'min':'1'})
		self.rotRemI.grid(row=0, column=1)
		self.rotRemF = Pmw.EntryField(rotFrame, labelpos='w',
			label_text="  end", entry_width=7, value='', validate=numberOrNone)
		self.rotRemF.grid(row=0, column=2)
		self.rotRemS = Pmw.EntryField(rotFrame, labelpos='w',
			label_text="  apply every", entry_width=4, value='2',
			validate={ 'validator': 'numeric', 'minstrict': True, 'min':'1'})
		self.rotRemS.grid(row=0, column=3)
		Tkinter.Label(rotFrame, text="steps").grid(row=0, column=4)

		self.electrostaticGroup = Pmw.Group(co, tag_text="ForceField Options")
		self.electrostaticGroup.grid(column=0, row=row.next(), sticky='nsew')
		esFrame = Tkinter.Frame(self.electrostaticGroup.interior())
		esFrame.grid(row=0, column=0, sticky='w')
		Tkinter.Label(esFrame, text='Electrostatic interaction method:').grid(
			column=0,row=0)
		self.var1=Tkinter.StringVar()
		self.var1.set('default')
		self.cutOffMenu=Pmw.OptionMenu(esFrame,
				menubutton_textvariable=self.var1, command=self._esMenuChange,
				items=['default', 'direct','cutoff','Ewald','screened'])
		self.cutOffMenu.grid(row=0,column=2)
		# disable Ewald if PBC off...
		self._pbcChange()
		self.cutOffDialog = Pmw.EntryField(esFrame,
				validate = {'validator':'real'}, entry_width=4,
				labelpos = 'e', label_text=u'\N{ANGSTROM SIGN}')
		self.cutOffDialog.grid(row=0, column=3)
		self.cutOffDialog.grid_remove()
		self.betaDialog = Pmw.EntryField(esFrame,
				validate = {'validator':'real'}, entry_width=4,
				labelpos = 'w', label_text='  beta:')
		self.betaDialog.grid(row=0, column=4)
		self.betaDialog.grid_remove()
		self.var2=Tkinter.StringVar()
		self.var2.set('default')
		ljFrame = Tkinter.Frame(self.electrostaticGroup.interior())
		ljFrame.grid(row=1, column=0, sticky='w')
		Tkinter.Label(ljFrame, text='Lennard-Jones interaction method:').grid(
			column=0,row=0)
		self.lenMenu=Pmw.OptionMenu(ljFrame,
				menubutton_textvariable=self.var2, command=self._ljMenuChange,
				items=['default', 'direct','cutoff'])
		self.lenMenu.grid(row=0,column=1)
		self.lenDialog = Pmw.EntryField(ljFrame,
				validate = {'validator':'real'}, entry_width=4,
				labelpos = 'e', label_text=u'\N{ANGSTROM SIGN}')
		self.lenDialog.grid(row=0, column=2)
		self.lenDialog.grid_remove()

		
	
		#ro.columnconfigure(4, weight = 1)

		###########################

		prep = self.notebook.page(PREP)
		self.dockPrepGroup = Pmw.Group(prep, tag_text='System Preparation')
		self.dockPrepGroup.grid(column=0, row=0, sticky='nsew')
		self.memoryType = Pmw.RadioSelect(self.dockPrepGroup.interior(), orient="vertical",
								buttontype='radiobutton', pady=0)
		self.memoryType.add("set", text="Memorize options chosen in"
			" subsequent dialogs", anchor="w", justify="left")
		self.memoryType.add("use", text="Use previously memorized options,"
			" if any", anchor="w", justify="left")
		self.memoryType.add("none", text="Neither memorize nor use memorized"
			" options", anchor="w", justify="left")
		self.memoryType.grid(row=0, column=0, columnspan=4)
		def doDockPrep(memorize, models):
			from DockPrep import memoryPrep
			from chimera import openModels, Molecule
			from AddCharge import defaultChargeModel
			d = memoryPrep("Minimize", memorize, models,
				gaffType=True, chargeModel=defaultChargeModel)
			if d:
				d.writeMol2Var.set(False)
		self.dockButton = Tkinter.Button(self.dockPrepGroup.interior(),
			text = "Start Dock Prep tool",
			command=lambda mt=self.memoryType, ml=self.molList:
				doDockPrep(mt.getvalue(), ml.getvalue()))
		self.dockButton.grid(column=0, row=3, sticky='nw')
		from DockPrep.prefs import prefs, MEMORIZED_SETTINGS
		if "Minimize" in prefs[MEMORIZED_SETTINGS]:
			self.memoryType.setvalue("use")
		else:
			self.memoryType.setvalue("set")

		###########################

		setup = self.notebook.page(SETUP)
		
		self.dynOptions = Pmw.OptionMenu(setup, command=self._dynOptions,
			items=['minimization','equilibration','production',
			'other runtime options'], labelpos='w', label_text="Settings:")
		self.dynOptions.grid(row=0, column=0)

		##Heating Options

		self.equilGroup = eg = Pmw.Group(setup, tag_text="Equilibrate",
				tag_pyclass=StepsTag, tag_variable=self.heating,
				tag_command=self._equilibrateChange)
		eg.grid(column=0, row=1, sticky = 'nsew')
		self.heatSteps = eg.component('tag').stepsEntry
		self.equilibrateWidgets = eqw = []

		heatRow = 0

		self.heatMethod = hm = Pmw.RadioSelect(eg.interior(),
			buttontype='radiobutton', command=self._heatMethodChange,
			labelpos='w', label_text="Temperature control method:",
			orient='horizontal')
		eqw.append(hm.component('label'))
		eqw.append(hm.add("heater", text="Heater"))
		eqw.append(hm.add("scaler", text="Velocity scaler"))
		hm.grid(row=heatRow, column=0)
		heatRow += 1

		self.heaterGroup = hg = Pmw.Group(eg.interior(),
			tag_text="Heater Parameters")
		eqw.append(hg.component('tag'))

		heaterFrame1 = Tkinter.Frame(hg.interior())
		heaterFrame1.grid(row=0, column=0)
		self.heaterInitialTemp = Pmw.EntryField(heaterFrame1,
				labelpos = 'w', label_text = 'temp1 (K)',
				validate = {'validator':'real', 'min':'0'},
				entry_width=3, value = '0')
		eqw.append(self.heaterInitialTemp.component('label'))
		eqw.append(self.heaterInitialTemp.component('entry'))
		self.heaterInitialTemp.grid(column = 0, row = 0, sticky = 'w')
		self.heaterFinalTemp = Pmw.EntryField(heaterFrame1,
				labelpos = 'w', label_text = '  temp2 (K)',
				validate = {'validator':'real', 'min':'0'},
				entry_width=3, value = '298')
		eqw.append(self.heaterFinalTemp.component('label'))
		eqw.append(self.heaterFinalTemp.component('entry'))
		self.heaterFinalTemp.grid(column = 1, row = 0, sticky = 'w')
		self.heaterGradient = Pmw.EntryField(heaterFrame1,
				labelpos = 'w', label_text = '  gradient (K/ps)',
				validate = {'validator':'real', 'min':'0'},
				entry_width=3, value = '10')
		eqw.append(self.heaterGradient.component('label'))
		eqw.append(self.heaterGradient.component('entry'))
		self.heaterGradient.grid(column = 2, row = 0, sticky = 'w')
		heaterFrame2 = Tkinter.Frame(hg.interior())
		heaterFrame2.grid(row=1, column=0)
		self.heaterFirstStep = Pmw.EntryField(heaterFrame2,
				labelpos = 'w', label_text = 'start',
				validate = {'validator':'numeric',
					'minstrict': False, 'maxstrict': False, 'min':'1'},
				entry_width=5, value = '1')
		eqw.append(self.heaterFirstStep.component('label'))
		eqw.append(self.heaterFirstStep.component('entry'))
		self.heaterFirstStep.grid(column = 0, row = 0, sticky = 'w')
		self.heaterLastStep = Pmw.EntryField(heaterFrame2,
				labelpos = 'w', label_text = '  end',
				validate = numberOrNone,
				entry_width=7)
		eqw.append(self.heaterLastStep.component('label'))
		eqw.append(self.heaterLastStep.component('entry'))
		self.heaterLastStep.grid(column = 1, row = 0)
		self.heaterSkip = Pmw.EntryField(heaterFrame2,
				labelpos = 'w', label_text = '  apply every',
				validate = {'validator':'numeric',
					'minstrict': False, 'maxstrict': False, 'min':'1'},
				entry_width=3, value = '2')
		stepsLabel = Tkinter.Label(heaterFrame2, text="steps")
		eqw.append(self.heaterSkip.component('label'))
		eqw.append(self.heaterSkip.component('entry'))
		eqw.append(stepsLabel)
		self.heaterSkip.grid(column = 2, row = 0, sticky = 'w')
		stepsLabel.grid(row=0, column=3)
		hg.grid(row=heatRow, column=0)
		hg.grid_remove()

		self.velScalerGroup = vsg = Pmw.Group(eg.interior(),
			tag_text="Velocity Scaler Parameters")
		eqw.append(vsg.component('tag'))

		velScalerFrame1 = Tkinter.Frame(vsg.interior())
		velScalerFrame1.grid(row=0, column=0)
		self.velScalerTemp = Pmw.EntryField(velScalerFrame1,
				labelpos = 'w', label_text = 'temp (K)',
				validate = {'validator':'real', 'min':'0'},
				entry_width=3, value = '298')
		eqw.append(self.velScalerTemp.component('label'))
		eqw.append(self.velScalerTemp.component('entry'))
		self.velScalerTemp.grid(column = 0, row = 0, sticky = 'w')
		self.velScalerTempWindow = Pmw.EntryField(velScalerFrame1,
				labelpos = 'w', label_text = '  allowed deviation',
				validate = {'validator':'real', 'min':'0'},
				entry_width=3, value = '0')
		eqw.append(self.velScalerTempWindow.component('label'))
		eqw.append(self.velScalerTempWindow.component('entry'))
		self.velScalerTempWindow.grid(column = 1, row = 0, sticky = 'w')
		velScalerFrame2 = Tkinter.Frame(vsg.interior())
		velScalerFrame2.grid(row=1, column=0)
		self.velScalerFirstStep = Pmw.EntryField(velScalerFrame2,
				labelpos = 'w', label_text = 'start',
				validate = {'validator':'numeric',
					'minstrict': False, 'maxstrict': False, 'min':'1'},
				entry_width=5, value = '1')
		eqw.append(self.velScalerFirstStep.component('label'))
		eqw.append(self.velScalerFirstStep.component('entry'))
		self.velScalerFirstStep.grid(column = 0, row = 0, sticky = 'w')
		self.velScalerLastStep = Pmw.EntryField(velScalerFrame2,
				labelpos = 'w', label_text = '  end',
				validate = numberOrNone,
				entry_width=7)
		eqw.append(self.velScalerLastStep.component('label'))
		eqw.append(self.velScalerLastStep.component('entry'))
		self.velScalerLastStep.grid(column = 1, row = 0)
		self.velScalerSkip = Pmw.EntryField(velScalerFrame2,
				labelpos = 'w', label_text = '  apply every',
				validate = {'validator':'numeric',
					'minstrict': False, 'maxstrict': False, 'min':'1'},
				entry_width=3, value = '2')
		stepsLabel = Tkinter.Label(velScalerFrame2, text="steps")
		eqw.append(self.velScalerSkip.component('label'))
		eqw.append(self.velScalerSkip.component('entry'))
		eqw.append(stepsLabel)
		self.velScalerSkip.grid(column = 2, row = 0, sticky = 'w')
		stepsLabel.grid(row=0, column=3)
		vsg.grid(row=heatRow, column=0)
		vsg.grid_remove()

		hm.invoke("heater")
		heatRow += 1
		
		baroFrame = Tkinter.Frame(eg.interior())
		baroFrame.grid(column=0, row=heatRow, sticky='w')
		eqw.append(Tkinter.Checkbutton(baroFrame, text="Barostat reset:",
			variable=self.baro))
		eqw[-1].grid(row=0, column=0)
		self.baroResFirstStep = Pmw.EntryField(baroFrame, labelpos='w',
			label_text="start", entry_width=5, value='1',
			validate={ 'validator':'numeric', 'minstrict': False,
				'maxstrict': False, 'min':'1'})
		eqw.append(self.baroResFirstStep.component('label'))
		eqw.append(self.baroResFirstStep.component('entry'))
		self.baroResFirstStep.grid(row=0, column=1)
		self.baroResLastStep = Pmw.EntryField(baroFrame, labelpos='w',
			label_text="  end", entry_width=7, value='', validate=numberOrNone)
		eqw.append(self.baroResLastStep.component('label'))
		eqw.append(self.baroResLastStep.component('entry'))
		self.baroResLastStep.grid(row=0, column=2)
		self.baroResSkip = Pmw.EntryField(baroFrame, labelpos='w',
			label_text="  apply every", entry_width=4, value='2',
			validate={ 'validator': 'numeric', 'minstrict': True, 'min':'1'})
		eqw.append(self.baroResSkip.component('label'))
		eqw.append(self.baroResSkip.component('entry'))
		self.baroResSkip.grid(row=0, column=3)
		eqw.append(Tkinter.Label(baroFrame, text="steps"))
		eqw[-1].grid(row=0, column=4)
		heatRow += 1

		self.heatIntegration = Pmw.EntryField(eg.interior(),
				labelpos = 'w',
				label_text = 'Time step (fs):',
				validate = {'validator':'numeric',
					'minstrict': False, 'maxstrict': False,
					'min':'1'},
				entry_width=3,
				value = '1')
		eqw.append(self.heatIntegration.component('label'))
		eqw.append(self.heatIntegration.component('entry'))
		self.heatIntegration.grid(column = 0, row = heatRow, sticky='w')
		heatRow += 1

		heatTrajectoryFrame = Tkinter.Frame(eg.interior())
		heatTrajectoryFrame.columnconfigure(1, weight=1)
		initialTrajFile = tildeExpand("~/Desktop/heating.nc")

		class heatTrajPathDialog(SaveModeless):
			default = 'Set Equilibration Trajectory Path'
			title = 'Select Equilibration trajectory output file'
			def SetHeatTrajPath(self):
				self.Save()

		setattr(heatTrajPathDialog, heatTrajPathDialog.default,
				heatTrajPathDialog.SetHeatTrajPath)

		heatTraj = tkoptions.OutputFileOption(heatTrajectoryFrame,
										0, 'Output trajectory file',
										initialTrajFile,
										None,
										balloon='Equilibration trajectory file save location',
										)
		eqw.append(heatTraj)
		heatTraj.dialogType = heatTrajPathDialog
		self.heatTrajFileOption=heatTraj

		heatTrajectoryFrame.grid(row=heatRow, column=0, columnspan=4, sticky='ew')
		heatRow += 1

		heatResTrajectoryFrame = Tkinter.Frame(eg.interior())
		heatResTrajectoryFrame.columnconfigure(1, weight=1)
		initialTrajFile = tildeExpand("~/Desktop/heat_res.nc")

		class heatResTrajPathDialog(SaveModeless):
			default = 'Set Restart Equilibration Trajectory Path'
			title = 'Select Restart Equilibration Trajectory output file'
			def SetHeatResTrajPath(self):
				self.Save()

		setattr(heatResTrajPathDialog, heatResTrajPathDialog.default,
				heatResTrajPathDialog.SetHeatResTrajPath)

		self.heatResVar = Tkinter.StringVar(heatResTrajectoryFrame)
		self.heatResVar.set(initialTrajFile)
		heatResTraj = tkoptions.OutputFileOption(heatResTrajectoryFrame,
				0, 'Output restart-trajectory file',
				initialTrajFile, None, entry_textvariable=self.heatResVar,
				balloon='Restart equilibration trajectory file save location')
		eqw.append(heatResTraj)
		heatResTraj.dialogType = heatResTrajPathDialog
		self.heatResTrajFileOption=heatResTraj

		heatResTrajectoryFrame.grid(column=0, row=heatRow, sticky='ew')
		heatRow += 1
		hg.grid_remove()
		if not self.heating.get():
			self._equilibrateChange()

		## Production Options

		self.prodGroup = pg = Pmw.Group(setup, tag_text="Include production phase",
				tag_pyclass=StepsTag, tag_variable=self.production,
				tag_command=self._productionChange)
		self.prodGroup.grid(row=1, column=0, sticky='nsew')
		self.prodSteps = pg.component('tag').stepsEntry
		self.productionWidgets = prodw = []

		prodRow = 0

		prodInTrajectoryFrame = Tkinter.Frame(pg.interior())
		prodInTrajectoryFrame.columnconfigure(1, weight=1)

		class prodInTrajPathDialog(SaveModeless):
			default = 'Set Prouction Input Trajectory Path'
			title = 'Select Production Trajectory input file'
			def SetProdInTrajPath(self):
				self.Save()

		setattr(prodInTrajPathDialog, prodInTrajPathDialog.default,
				prodInTrajPathDialog.SetProdInTrajPath)

		prodInTraj = tkoptions.InputFileOption(prodInTrajectoryFrame, 0,
				'Input restart-trajectory file (from previous equilibration or production)',
				initialTrajFile, None, entry_textvariable=self.heatResVar,
				balloon='Input restart trajectory file location')
		prodw.append(prodInTraj)
		prodInTraj.dialogType = prodInTrajPathDialog

		prodInTrajectoryFrame.grid(column=0, row=prodRow, sticky='ew')
		prodRow += 1

		andersenFrame = Tkinter.Frame(pg.interior())
		andersenFrame.grid(column=0, row=prodRow, sticky='w')
		prodw.append(Tkinter.Checkbutton(andersenFrame, text="Andersen barostat:",
			variable=self.prodBarostat))
		prodw[-1].grid(row=0, column=0)
		from MMTK.Units import atm, bar
		self.prodBarostatValue = Pmw.EntryField(andersenFrame, labelpos='w',
				label_text="pressure (bars)", entry_width=8,
				validate={'validator':'real', 'min':'0.0'},
				value = "%.4f" % (atm/bar))
		prodw.append(self.prodBarostatValue.component('label'))
		prodw.append(self.prodBarostatValue.component('entry'))
		self.prodBarostatValue.grid(row=0, column=1)
		self.prodBarostatRelax = Pmw.EntryField(andersenFrame, labelpos = 'w',
				label_text = '  relaxation time ', entry_width=5,
				validate = {'validator':'real', 'min':'0'},
				value = '1.5')
		prodw.append(self.prodBarostatRelax.component('label'))
		prodw.append(self.prodBarostatRelax.component('entry'))
		self.prodBarostatRelax.grid(row= 0, column=2, sticky = 'w')
		prodRow += 1

		noseFrame = Tkinter.Frame(pg.interior())
		noseFrame.grid(column=0, row=prodRow, sticky='w')
		prodw.append(Tkinter.Checkbutton(noseFrame,
			text=u'Nos\N{LATIN SMALL LETTER E WITH ACUTE} thermostat:',
			variable=self.prodThermostat))
		prodw[-1].grid(row=0, column=0)
		self.prodThermostatValue = Pmw.EntryField(noseFrame, labelpos='w',
				label_text="temperature (K)",
				validate={'validator':'numeric',
				'min':'0'},
				entry_width=3,
				value = '298')
		prodw.append(self.prodThermostatValue.component('label'))
		prodw.append(self.prodThermostatValue.component('entry'))
		self.prodThermostatValue.grid(row=0,column=1)
		self.prodThermostatRelax = Pmw.EntryField(noseFrame, labelpos = 'w',
				label_text = '  relaxation time',
				entry_width=5,
				validate = {'validator':'real', 'min':'0'},
				value = '0.2')
		prodw.append(self.prodThermostatRelax.component('label'))
		prodw.append(self.prodThermostatRelax.component('entry'))
		self.prodThermostatRelax.grid(row=0, column=2, sticky = 'w')
		prodRow += 1

		self.entryProdIntegration = Pmw.EntryField(pg.interior(), 
				labelpos='w',
				label_text='Time step (fs):',
				validate = {'validator':'numeric',
					'minstrict': False, 'maxstrict': False,
					'min':'1'},
				entry_width=3,
				value = '1')
		prodw.append(self.entryProdIntegration.component('label'))
		prodw.append(self.entryProdIntegration.component('entry'))
		self.entryProdIntegration.grid(column = 0, row = prodRow, sticky='w', padx=10)
		prodRow += 1

		prodTrajectoryFrame = Tkinter.Frame(pg.interior())
		prodTrajectoryFrame.columnconfigure(1, weight=1)
		initialTrajFile = tildeExpand("~/Desktop/prod.nc")

		class prodTrajPathDialog(SaveModeless):
			default = 'Set Production Trajectory Path'
			title = 'Select Production Trajectory output file'
			def SetProdTrajPath(self):
				self.Save()

		setattr(prodTrajPathDialog, prodTrajPathDialog.default,
				prodTrajPathDialog.SetProdTrajPath)

		prodTraj = tkoptions.OutputFileOption(prodTrajectoryFrame,
										0, 'Output trajectory file',
										initialTrajFile,
										None,
										balloon='Production trajectory file save location',
										)
		prodw.append(prodTraj)
		prodTraj.dialogType = prodTrajPathDialog
		self.prodTrajFileOption=prodTraj

		prodTrajectoryFrame.grid(row=prodRow, column=0, columnspan=8, sticky='ew')
		prodRow += 1

		prodResTrajectoryFrame = Tkinter.Frame(self.prodGroup.interior())
		prodResTrajectoryFrame.columnconfigure(2, weight=1)
		b = Tkinter.Checkbutton(prodResTrajectoryFrame, text="", variable=self.prodRes)
		b.grid(row=0, column=0)
		prodw.append(b)
		initialTrajFile = tildeExpand("~/Desktop/prod_res.nc")

		class prodResTrajPathDialog(SaveModeless):
			default = 'Set Production Restart Path'
			title = 'Select Production Restart output file'
			def SetProdResTrajPath(self):
				self.Save()

		setattr(prodResTrajPathDialog, prodResTrajPathDialog.default,
				prodResTrajPathDialog.SetProdResTrajPath)

		prodResTraj = tkoptions.OutputFileOption(prodResTrajectoryFrame,
										0, 'Output restart-trajectory file',
										initialTrajFile,
										None, startCol=1,
										balloon='Restart production trajectory file save location',
										)
		prodResTraj.dialogType = prodResTrajPathDialog
		self.prodResTrajFileOption=prodResTraj
		prodw.append(prodResTraj)

		prodRow += 1
		prodResTrajectoryFrame.grid(column=0, row=prodRow, sticky = 'ew')
					
		self.prodGroup.grid_remove()


		# Minimization 

		self.minGroup = Pmw.Group(setup,
					tag_pyclass=Tkinter.Checkbutton,
					tag_variable=self.minimization,
					tag_command=self._minimizationChange,
					tag_text='Minimize before MD')
		self.minGroup.grid(column=0, row=1)
		self.minGroup.grid_remove()
		self.minimizeEntries = []
		self.sdSteps = Pmw.EntryField(self.minGroup.interior(),
				label_text = "Steepest descent steps:",
				labelpos = 'w',
				validate = {'validator':'real',
					'minstrict': False, 'maxstrict': False,
					'min':'1'},
				entry_width=5,
				value=100)
		self.minimizeEntries.append(self.sdSteps)
		self.sdSteps.grid(column=0,row=1,sticky='nsew')
		self.sdStepSize = Pmw.EntryField(self.minGroup.interior(),
				label_text = u"Steepest descent step size (\N{ANGSTROM SIGN}):",
				labelpos = 'w',
				validate = {'validator':'real',
					'minstrict': False, 'maxstrict': False,
						'min':'0.0001',
						'max':'1.0'},
				entry_width=5,
				value=0.02)
		self.minimizeEntries.append(self.sdStepSize)
		self.sdStepSize.grid(column=0,row=2,sticky='nsew')
		self.cgSteps = Pmw.EntryField(self.minGroup.interior(),
				label_text = "Conjugate gradient steps:",
				labelpos = 'w',
				validate = {'validator':'real',
						'min':'0'},
				entry_width=5,
				value=10)
		self.minimizeEntries.append(self.cgSteps)
		self.cgSteps.grid(column=0,row=3,sticky='nsew')
		self.cgStepSize = Pmw.EntryField(self.minGroup.interior(),
				label_text = u"Conjugate gradient step size (\N{ANGSTROM SIGN}):",
				labelpos = 'w',
				validate = {'validator':'real',
					'minstrict': False, 'maxstrict': False,
						'min':'0.0001',
						'max':'1.0'},
				entry_width=5,
				value=0.02)
		self.minimizeEntries.append(self.cgStepSize)
		self.cgStepSize.grid(column=0,row=4,sticky='nsew')
		if not self.minimization.get():
			self._minimizationChange()

		# runtime options
		runRow = 0

		# comment out background computation;
		# MMTK itself needs enhancement in order to write out
		# a universe to use for the computation, and the 
		# current background-computation code has some errors
		# in it
		self.runGroup = Tkinter.Frame(setup)
		self.runGroup.grid(row=1, column=0)
		self.runGroup.grid_remove()
		"""
		self.runningOptions = Pmw.RadioSelect(self.runGroup,
				buttontype = 'radiobutton',
				labelpos = 'w',
				label_text = 'Running Options',
				command = self.changeOptions)
		self.runningOptions.grid(column=0, row=runRow, sticky='w')
		for text in ('Interactive', 'Background'):
			self.runningOptions.add(text)
		self.runIntFrame = Tkinter.Frame(self.runGroup)
		self.runIntFrame.grid(column=0, row=5)
		self.runBackFrame = Tkinter.Frame(self.runGroup)
		self.runBackFrame.grid(column=0, row=5)
		self.runBackFrame.grid_remove()
		self.runningOptions.setvalue("Interactive")
		runRow += 1
		"""



		#initialTrajFile = tildeExpand("~/Desktop/MMTK_input.py") 
		initialTrajFile = ""

		class MMTKInputPathDialog(SaveModeless):
			default = 'Set MMTK input Path'
			title = 'Select MMTK input file'
			def SetMMTKInputPath(self):
				self.Save()

		setattr(MMTKInputPathDialog, MMTKInputPathDialog.default,
				MMTKInputPathDialog.SetMMTKInputPath)

		f = Tkinter.Frame(self.runGroup)
		#f.grid(row=runRow, column=0, sticky='w')
		#runRow += 1
		MMTKInput = tkoptions.OutputFileOption(f,
										0, 'MMTK input file (optional)',
										initialTrajFile,
										None,
										balloon='MMTK Input file save location',
										)
		MMTKInput.dialogType = MMTKInputPathDialog
		self.MMTKInputFileOption=MMTKInput

		f = Tkinter.Frame(self.runGroup)
		f.grid(row=runRow, column=0, sticky='w')
		runRow += 1
		Tkinter.Checkbutton(f, text="Use multiple CPUs", variable=self.multi,
			command=self._multi).grid(row=0, column=0)
		import multiprocessing
		try:
			ncpus = str(multiprocessing.cpu_count())
		except NotImplementedError:
			ncpus = "2"
		self.nprocsDialog = Pmw.EntryField(f, entry_width=3,
				labelpos='w', label_text="  #CPUs:",
				value=ncpus, validate = {'validator':'numeric'})
		self.nprocsDialog.grid(column=1, row=0)
		self.nprocsDialog.grid_remove()
		f = Tkinter.Frame(self.runGroup)
		f.grid(row=runRow, column=0, sticky='w')
		runRow += 1
		self.framesDialog = Pmw.EntryField(f,
				validate={'validator':'numeric'}, value="10",
				entry_width=3, entry_justify="center",
				labelpos = 'w',
				label_text='Save once every')
		self.framesDialog.grid(column=0, row=0)
		Tkinter.Label(f, text="steps").grid(row=0, column=1)
		Tkinter.Checkbutton(self.runGroup, text='"Live" trajectory', variable=self.onLive,
			command=self._multi).grid(row=runRow, column=0, sticky='w')
		runRow += 1

		self.dynOptions.invoke('minimization')

		Tkinter.Button(setup, text="Run", command=self.Run).grid(row=2, column=0)

		self.teamNameInfo = Tkinter.Label(parent,
				text="Interface designed by V. Munoz-Robles and J.-D.Marechal\n"
				"The Computational Biotechnological Chemistry Team")

		self.teamNameInfo.grid(row=2, column=0)

		self.notebook.setnaturalsize()

	def _restoreSession(self, session):
		#Restoring the session

		self.memoryType.setvalue(session["memory"])

		#Solvation
		
		self.pbc.set(session["PBCcon"])

		self.xCoord.setvalue(session["PBCval"][0])
		self.yCoord.setvalue(session["PBCval"][1])
		self.zCoord.setvalue(session["PBCval"][2])
	
		self.autoPBC = session["PBCauto"]
		if self.autoPBC:
			self.autoPBCOption.invoke("")

		#MD Options
		#Minimize
		
		self.minimization.set(session["Minimize"])
		self.sdSteps.setvalue(session["sdStep"])
		self.sdStepSize.setvalue(session["sdStepSize"])
		self.cgSteps.setvalue(session["cgStep"])
		self.cgStepSize.setvalue(session["cgStepSize"])
		
		#Equilibration Options
	
		self.heating.set(session["heat"])
		self.heatSteps.setvalue(session["eqSteps"])
		self.heaterInitialTemp.setvalue(session["iTemp"])
		self.heaterFinalTemp.setvalue(session["fTemp"])
		self.heaterGradient.setvalue(session["grad"])
		self.heaterFirstStep.setvalue(session["iStep"])
		self.heaterLastStep.setvalue(session["fStep"] or "")
		self.heaterSkip.setvalue(session["skip"]+1)
		self.velScalerTemp.setvalue(session["velScalerTemp"])
		self.velScalerTempWindow.setvalue(session["velScalerTempWin"])
		self.velScalerFirstStep.setvalue(session["velScalerFirst"])
		self.velScalerLastStep.setvalue(session["velScalerLast"])
		self.velScalerSkip.setvalue(session["velScalerSkip"])+1
		self.heatIntegration.setvalue(session["eqInt"])

		#Production Options
		self.production.set(session["Production"])
		self.prodSteps.setvalue(session["prodSteps"])         
		self.entryProdIntegration.setvalue(session["prodInt"])
		self.prodBarostat.set(session["prodAndersen"])
		self.prodBarostatRelax.setvalue(session["prodBarRelax"])       
		self.prodBarostatValue.setvalue(session["prodBar"])
            
		self.prodThermostat.set(session["prodNose"])
		self.prodThermostatValue.setvalue(session["prodThermostat"])     
		self.prodThermostatRelax.setvalue(session["prodThermostatValue"])
		self.prodRes.set(session["prodRes"])

		#Restraint
	
		try:
			self.fixAtoms = ItemizedSelection()
			from chimera import runCommand as run
			for a in session['fixed']:
				run("sel @/serialNumber = %i" % a)
				self.fixAtoms.add(selection.currentAtoms())
				selection.clearCurrent()
			self._changed()
		except:
			pass

		#Miscellanea

		self.rot.set(session["rotRem"])
		self.rotRemI.setvalue(session["iRotRem"])
		self.rotRemF.setvalue(session["fRotRem"])
		if session.has_key("lastRotRem") and session["lastRotRem"]:
			self.rotRemF.setvalue("")
		self.rotRemS.setvalue(session["rotSkip"]+1)
		self.trans.set(session["transRem"])
		self.transRemI.setvalue(session["iTransRem"])
		self.transRemF.setvalue(session["fTransRem"]) 
		if session.has_key("lastTransRem") and session["lastTransRem"]:
			self.transRemF.setvalue("")
		self.transRemS.setvalue(session["transSkip"]+1) 
		self.cutOffDialog.setvalue(session["elecCutOffValue"])
		self.betaDialog.setvalue(session["elecBetaValue"])
		self.var1.set(session["elecCutOffOpt"]) 
		self.lenDialog.setvalue(session["lenVal"])
		self.var2.set(session["levOpt"]) 
		
		#Running

		self.multi.set(session["procsOpt"])
		if self.multi:
			self._multi()
		self.nprocsDialog.setvalue(session["procs"])
	 	self.framesDialog.setvalue(session["open"])
	 	self.onLive.set(session["live"])


#	def _eqBarostat(self,tag, state):
#		if state:
#			self.eqBarostat = True
#		else:
#			self.eqBarostat = False
#	def _eqVelScaler(self,tag, state):
#		if state:
#			self.eqVelScalerVar = True
#		else:
#			self.eqVelScalerVar = False
#	def _eqBarostatReset(self,tag, state):
#		if state:
#			self.eqBarostatResetVar = True
#		else:
#			self.eqBarostatResetVar = False

	def _heatMethodChange(self, butName):
		if butName == "heater":
			self.heaterGroup.grid()
			self.velScalerGroup.grid_remove()
		else:
			self.heaterGroup.grid_remove()
			self.velScalerGroup.grid()
		self.notebook.setnaturalsize()

	def _autoPBC(self, tag, state):
		if state:
			self.autoPBC = True
		else:
			self.autoPBC = False 

	def _dynOptions(self, tag):
		if tag=='minimization':
			self.minGroup.grid()
			self.equilGroup.grid_remove()
			self.prodGroup.grid_remove()
			self.runGroup.grid_remove()
		elif tag=='equilibration':
			self.minGroup.grid_remove()
			self.equilGroup.grid()
			self.prodGroup.grid_remove()
			self.runGroup.grid_remove()
			# force the heater/velocity rescaler options to show...
			self.heatMethod.invoke(self.heatMethod.getvalue())
		elif tag=='production':
			self.prodGroup.grid()
			self.minGroup.grid_remove()
			self.equilGroup.grid_remove()
			self.runGroup.grid_remove()
		else:
			self.runGroup.grid()
			self.minGroup.grid_remove()
			self.equilGroup.grid_remove()
			self.prodGroup.grid_remove()
		self.notebook.setnaturalsize()

	def _groupChange(self, var, widgets):
		state = 'normal' if var.get() else 'disabled'
		from chimera.tkoptions import Option
		for widget in widgets:
			if isinstance(widget, Option):
				if var.get():
					widget.enable()
				else:
					widget.disable()
			else:
				widget.configure(state=state)

	def _equilibrateChange(self, *args):
		self._groupChange(self.heating, self.equilibrateWidgets)

	def _pbcChange(self, *args):
		if self.pbc.get():
			ewaldState = "normal"
		else:
			ewaldState = "disabled"
		self.cutOffMenu.component("menu").entryconfigure("Ewald",
			state=ewaldState)

	def _productionChange(self, *args):
		self._groupChange(self.production, self.productionWidgets)

	def _minimizationChange(self, *args):
		state = 'normal' if self.minimization.get() else 'disabled'
		for entry in self.minimizeEntries:
			entry.component('entry').configure(state=state)
			entry.component('label').configure(state=state)

	def _multi(self):
		if self.multi.get():
			self.nprocsDialog.grid()
		else:
			self.nprocsDialog.grid_remove()

	def _setAtoms(self):
	
		from chimera import runCommand as run
		if self.FixMenu.get()=='selected':
			self.fixAtoms = selection.copyCurrent()
		elif self.FixMenu.get()=='unselected':
			run("sel invert sel")
			self.fixAtoms = selection.copyCurrent()
			run("sel invert sel")
		self.status("%d atoms fixed" % len(self.fixAtoms))

	def changeOptions(self, tag):
		if self.runningOptions.getcurselection()=="Background":
			self.outside=True
			self.runIntFrame.grid_remove()
			self.runBackFrame.grid()
		else:
			self.outside=False
			self.runBackFrame.grid_remove()
			self.runIntFrame.grid()
		

	def _changed(self):
		if self.fixedAtomsVar.get():
			self.FixMenuOptions.config(state = NORMAL)
			self.fixSetButton.config(state = NORMAL)
		else:
			self.FixMenuOptions.config(state=DISABLED)
			self.fixSetButton.config(state = DISABLED)

	def _esMenuChange(self, name):
		if name in ["cutoff", "screened"]:
			self.cutOffDialog.grid()
			if name == "screened":
				self.betaDialog.grid()
			else:
				self.betaDialog.grid_remove()
		else:
			self.cutOffDialog.grid_remove()
			self.betaDialog.grid_remove()

	def _ljMenuChange(self, name):
		if name == "cutoff":
			self.lenDialog.grid()
		else:
			self.lenDialog.grid_remove()

	"""
	def _solvate(self):
		if self.SolvateMenu.get() == 'Amber':
			chimera.dialogs.display(SolvateDialog.name)
	"""

	def assignVar(self):
		heatMD = None
		prodMD = None
		#eqMD = None
		minMD = None

		filename = self.MMTKInputFileOption.get()
		self.molecules = self.molList.getvalue()
		traj = dict()
		if self.heating.get():
			traj["heat"] = self.heatTrajFileOption.get()
		if self.production.get():
			traj["prod"] = self.prodTrajFileOption.get()
		traj["heatRes"] = self.heatResTrajFileOption.get()
		if self.prodRes.get():
			traj["prodRes"] = self.prodResTrajFileOption.get()

		if self.heating.get():
			heatMD = dict()

			if self.heatMethod.getvalue() == "heater":
				heatMD["iTemp"] = float(self.heaterInitialTemp.get())
				heatMD["fTemp"] = float(self.heaterFinalTemp.get())
				heatMD["grad"] = float(self.heaterGradient.get())
				heatMD["first"] = int(self.heaterFirstStep.get())
				heatMD["last"] = getNumOrNone(self.heaterLastStep)
				heatMD["skip"] = int(self.heaterSkip.get())-1
			else:
				heatMD["velTemp"] = float(self.velScalerTemp.get())
				heatMD["velTemp_win"] = float(self.velScalerTempWindow.get())
				heatMD["velFirst"] = int(self.velScalerFirstStep.get())
				heatMD["velLast"] = getNumOrNone(self.velScalerLastStep)
				heatMD["velSkip"] = int(self.velScalerSkip.get())-1
			if self.baro.get():
				heatMD["barFirst"] = int(self.baroResFirstStep.get())
				heatMD["barLast"] = getNumOrNone(self.baroResLastStep)
				heatMD["barSkip"] = int(self.baroResSkip.get())-1
			heatMD["steps"] = int(self.heatSteps.get())
			heatMD["int"] = int(self.heatIntegration.get())

		if self.production.get():
			prodMD = dict()

			prodMD["steps"] = int(self.prodSteps.get())
			prodMD["int"] = int(self.entryProdIntegration.get())

			if self.prodBarostat.get():
				prodMD["bar"] = float(self.prodBarostatValue.get())
				prodMD["barRelax"] = float(self.prodBarostatRelax.get())
			if self.prodThermostat.get():
				prodMD["thermostat"] = float(self.prodThermostatValue.get())
				prodMD["thermostatRelax"] = float(self.prodThermostatRelax.get())

		if self.minimization.get():
			minMD = dict()

			minMD["sdSteps"] = int(self.sdSteps.get())
			minMD["sdStepSize"] = float(self.sdStepSize.get())
			minMD["cgSteps"] = int(self.cgSteps.get())
			minMD["cgStepSize"] = float(self.cgStepSize.get())

		dynVar = dict()
		if self.trans.get():
			dynVar["tfirst"] = int(self.transRemI.getvalue())
			dynVar["tlast"] = getNumOrNone(self.transRemF)
			dynVar["tskip"] = int(self.transRemS.getvalue())-1

		if self.rot.get():
			dynVar["rfirst"] = int(self.rotRemI.getvalue())
			dynVar["rlast"] = getNumOrNone(self.rotRemF)
			dynVar["rskip"] = int(self.rotRemS.getvalue())-1
			
		dynVar["PBC"]=self.pbc.get()
		dynVar["autoPBC"] = self.autoPBC
		if self.pbc.get() and not self.autoPBC:
			dynVar["xPBC"]=float(self.xCoord.get())
			dynVar["yPBC"]=float(self.yCoord.get())
			dynVar["zPBC"]=float(self.zCoord.get())

		#Dynamics Options

		if self.multi.get():
			multi = int(self.nprocsDialog.getvalue())
		else:
			multi=1

		#Dynamics Parameters
		fixed = self.fixedAtomsVar.get()
		if fixed:
			fixedAtoms = ItemizedSelection(
				[a for a in self.fixAtoms.atoms() if a.molecule in self.molecules])
		else:
			fixedAtoms = ItemizedSelection()

		#Dynamics Running Options
		
		filename = self.MMTKInputFileOption.get()
		outside = self.outside
		if self.framesDialog.getvalue() == "":
			self.frame = 1
		else:
			self.frame = int(self.framesDialog.getvalue())

		if self.cutOffMenu.getcurselection() == "default":
			cutOff = None
		else:
			cutOff=dict()
			selMethod = self.cutOffMenu.getcurselection().lower()
			if selMethod in ["cutoff", "screened"]:
				cutOff["cutoff"]=float(self.cutOffDialog.get())/10
				if selMethod == "screened":
					cutOff["beta"]=float(self.betaDialog.get())
			if selMethod != "cutoff":
				cutOff["method"]=self.cutOffMenu.getcurselection().lower()
			
		if self.lenMenu.getcurselection() == "default":
			lenJon=None
		else:
			lenJon=dict()
			if self.lenMenu.getcurselection() == "cutoff":
				lenJon[self.lenMenu.getcurselection()]=float(self.lenDialog.get())/10
			else:
				lenJon["method"] = self.lenMenu.getcurselection()

		return prodMD, heatMD, minMD, dynVar, traj, cutOff, multi, outside, filename, fixedAtoms, lenJon
	
	def Run(self):
		prodMD, heatMD, minMD, dynVar, traj, cutOff, multi, outside, filename, fixedAtoms, lenJon = self.assignVar()

		if not self.molecules:
			raise UserError("No molecules have been selected for the Molecular Dynamics Simulation")

		if dynVar["PBC"] and not dynVar["autoPBC"] and (
		dynVar["xPBC"] <= 0.0 or dynVar["yPBC"] <= 0.0 or dynVar["zPBC"] <= 0.0):
			raise UserError("Bad PBC box size\n"
				"You have PBC turned on without automatic box sizing "
				"and one or more dimensions of the box is less than or equal to zero.  "
				"Please either turn off PBC, fix the box dimensions, or turn on "
				"automatic box sizing.")

		#Running the Dynamic

		from base import Dynamics

		self.md = Dynamics(self.molecules, traj, self.frame,
				dynVar = dynVar, heatMD = heatMD, prodMD = prodMD, minMD = minMD,
				fixed = fixedAtoms, filename = filename, outside = outside, multi = multi,
				live = self.onLive.get(), rot = self.rot.get(), trans = self.trans.get(),
				memorize = self.memoryType.getvalue(), esOptions=cutOff, lenOptions=lenJon)

	def _sessionSaveCB(self,triggerName,myData, sessionFile):
		sesData = dict()

		#Code to save the rest of the session

		sesData["memory"] = self.memoryType.getvalue()

		#Solvation

		sesData["PBCcon"] = self.pbc.get()
		sesData["PBCval"] = [self.xCoord.get(),self.yCoord.get(),self.zCoord.get()]
		sesData["PBCauto"] = self.autoPBC 

		#MD Options

		sesData["Minimize"] = self.minimization.get()
		sesData["sdStep"] = self.sdSteps.get() 
		sesData["sdStepSize"] = self.sdStepSize.get() 
		sesData["cgStep"] = self.cgSteps.get() 
		sesData["cgStepSize"] = self.cgStepSize.get() 

		#Equilibration Options

		sesData["heat"] = self.heating.get()
		sesData["iTemp"] = self.heaterInitialTemp.get()
		sesData["fTemp"] = self.heaterFinalTemp.get()
		sesData["grad"] = self.heaterGradient.get()
		sesData["iStep"] = self.heaterFirstStep.get()
		sesData["fStep"] = getNumOrNone(self.heaterLastStep)
		sesData["skip"] = int(self.heaterSkip.get())-1
		sesData["eqSteps"]=self.heatSteps.get()
		sesData["velScalerTemp"] = self.velScalerTemp.get()
		sesData["velScalerTempWin"] = self.velScalerTempWindow.get()
		sesData["velScalerFirst"] = self.velScalerFirstStep.get()
		sesData["velScalerLast"] = self.velScalerLastStep.get()
		sesData["velScalerSkip"] = int(self.velScalerSkip.get())-1
		sesData["eqInt"]=self.heatIntegration.get()

		#Production Options

		sesData["Production"] = self.production.get()
		sesData["prodSteps"] = self.prodSteps.get()
		sesData["prodInt"]=self.entryProdIntegration.get()
		sesData["prodAndersen"]=self.prodBarostat.get()
		sesData["prodBarRelax"]=self.prodBarostatRelax.get()
		sesData["prodBar"]=self.prodBarostatValue.get()
		sesData["prodNose"]=self.prodThermostat.get()
		sesData["prodThermostat"]=self.prodThermostatValue.get()
		sesData["prodThermostatValue"]=self.prodThermostatRelax.get()
		sesData["prodRes"]=self.prodRes.get()

		#Constraints
		
		if len(self.fixAtoms) != 0:
			sesFixAtoms = list()
			for a in self.fixAtoms.atoms():
				sesFixAtoms.append(a.serialNumber)
			sesData['fixed'] = sesFixAtoms

		#Miscellanea

		sesData["rotRem"] = self.rot.get()
		sesData["iRotRem"] = self.rotRemI.get()
		sesData["fRotRem"] = self.rotRemF.get()
		sesData["rotSkip"] = int(self.rotRemS.get())-1
		sesData["transRem"] = self.trans.get()
		sesData["iTransRem"] = self.transRemI.get()
		sesData["fTransRem"] = self.transRemF.get()
		sesData["transSkip"] = int(self.transRemS.get())-1
		sesData["elecCutOffValue"] = self.cutOffDialog.get()
		sesData["elecBetaValue"] = self.betaDialog.get()
		sesData["elecCutOffOpt"] = self.cutOffMenu.getcurselection()
		sesData["lenVal"] = self.lenDialog.get()
		sesData["levOpt"] = self.lenMenu.getcurselection()
		
		#Running

		#sesData["MMTKinput"] = self.MMTKInputFileOption
		sesData["procsOpt"] = self.multi.get()
		sesData["procs"] = self.nprocsDialog.get()
		sesData["open"] = self.framesDialog.get()
		sesData["live"] = self.onLive.get()

		from SimpleSession.save import pickled
		print >> sessionFile, "data=%s" % pickled(sesData)
		print >> sessionFile, """
try:
	from chimera.dialogs import display
	from md.gui import MolecularDynamicsDialog
	display(MolecularDynamicsDialog.name)._restoreSession(data)
except:
	reportRestoreError("Error restoring Session")
"""

def numberOrNone(val, **kw):
	val = val.strip()
	if val:
		try:
			if int(val) >= 0:
				return Pmw.OK
			else:
				return Pmw.ERROR
		except ValueError:
			return Pmw.ERROR
	return Pmw.OK

def getNumOrNone(opt):
	val_string = opt.getvalue().strip()
	if val_string:
		val = int(val_string)
		# The value is the first step where the action stops
		# happening, so since the label of the field is 'end',
		# add one
		val += 1
		if val == 1:
			val = None
	else:
		val = None
	return val

class StepsTag(Tkinter.Frame):
	def __init__(self, parent,
			text="", variable=None, command=None, steps=5000):
		Tkinter.Frame.__init__(self, parent)
		self.chkbut = Tkinter.Checkbutton(self, text=text, variable=variable,
			command=command)
		self.chkbut.grid(row=0, column=0)
		self.stepsEntry = Pmw.EntryField(self, labelpos='e', label_text="steps",
				validate = {'validator':'numeric',
					'minstrict': True, 'maxstrict': False, 'min':'1'},
				entry_width=7, entry_justify="center", value = steps)
		self.stepsEntry.grid(row=0, column=1)

	def winfo_reqheight(self, *args, **kw):
		return max(self.chkbut.winfo_reqheight(*args, **kw),
			self.stepsEntry.component('entry').winfo_reqheight(*args, **kw),
			self.stepsEntry.component('label').winfo_reqwidth(*args, **kw))

	def winfo_reqwidth(self, *args, **kw):
		return self.chkbut.winfo_reqwidth(*args, **kw) + \
			self.stepsEntry.component('entry').winfo_reqwidth(*args, **kw) + \
			self.stepsEntry.component('label').winfo_reqwidth(*args, **kw)

from chimera import dialogs
dialogs.register(MolecularDynamicsDialog.name, MolecularDynamicsDialog)

