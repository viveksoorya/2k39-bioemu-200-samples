# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# ModellerDialog.py yz@cgl.ucsf.edu 05/2010

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
from chimera.misc import oslModelCmp
import Pmw, Tkinter
from PIL import Image, ImageTk
from MAViewer import ADDDEL_SEQS, SEQ_RENAMED
from prefs import prefs, MODELLER_KEY, MODELLER_USE_WEB, MODELLER_PATH, MODELLER_TEMP_PATH
from chimera.Sequence import percentIdentity
from chimera import UserError
import os
import shutil

class ModellerDialog(ModelessDialog):

	"""Using Modeller to construct homology or comparative structures"""

	buttons = ("OK", "Apply", "Close")
	default = "OK"
	help = "ContributedSoftware/multalignviewer/modeller.html"
	provideStatus = True
	statusPosition = "above"

	def __init__(self, mav, *args, **kw):
		self.mav = mav
		self.title = "Comparative Modeling with Modeller"
		self.closeModelsID = chimera.openModels.addRemoveHandler(
								self._closeModelsCB, None)
		ModelessDialog.__init__(self, *args, **kw)
		self.pathTemp = "@_undefined_@"

	def fillInUI(self, parent):

		from chimera.tkoptions import OutputFileOption, InputFileOption

		#fontTitle1 = "Helvetica bold"
		#fontTitle2 = "Helvetica bold"
		#fontAdvOpt = "Helvetica"

		sf = Pmw.ScrolledFrame(parent,
					usehullsize=1, hull_width=610, hull_height=400,
					horizflex='expand', vertflex='expand')
		sf.grid(row=0, column=0, sticky="nsew")
		sfin = sf.interior()
		parent.columnconfigure(0, weight=1)
		parent.rowconfigure(0, weight=1)

		self.balloon = Pmw.Balloon(sfin)

		from itertools import count
		rowCounter = count()

		# Target Sequence menu
		row = rowCounter.next()

		pkgdir = os.path.dirname(__file__)

		iconImage = ImageTk.PhotoImage(Image.open(os.path.join(pkgdir, "icon_seq.png")))
		seqIcon = Tkinter.Label(sfin, image=iconImage)
		seqIcon.photo = iconImage
		seqIcon.grid(row=row, column=0, padx=5, pady=5,
					sticky="n")
		self.balloon.bind(seqIcon, "Choose the target sequence to be modeled.")

		seqLabel = Tkinter.Label(sfin,
					text="Choose the target (sequence to be modeled): ")
		seqLabel.grid(row=row, column=1, columnspan=3,
					sticky="nw", pady=12)
		balloonText = "Choose the sequence for which model structures will" \
			" be built."
		self.balloon.bind(seqLabel, balloonText)
		from MAViewer import SeqMenu
		self.seqMenu = SeqMenu(sfin, self.mav, command=self._newSeqCB)
		self.seqMenu.grid(row=row, column=4, columnspan=1,
					sticky="new", pady=8)
		self.balloon.bind(self.seqMenu, balloonText)

		# Template(tpl) sequence menu
		row = rowCounter.next()

		iconImage = ImageTk.PhotoImage(Image.open(os.path.join(pkgdir, "icon_tmp.png")))
		tplIcon = Tkinter.Label(sfin, image=iconImage)
		tplIcon.photo = iconImage
		tplIcon.grid(row=row, column=0, padx=5, pady=5,
					rowspan=2, sticky="n")
		self.balloon.bind(tplIcon, "Select at least one template structure.")
		buttonText = "Fetch Structures/Annotations"
		balloonText = "Select at least one template structure.\n" \
			"If no structure is yet associated with the template sequence,\n" \
			"a structure will be loaded if a structure ID can be determined\n" \
			"from the sequence name.  More structural information will be\n" \
			"shown if the %s button is clicked." % buttonText

		tplLabel = Tkinter.Label(sfin,
					text="Choose at least one template: ")
		tplLabel.grid(row=row, column=1, columnspan=3,
					sticky="nw", pady=5)
		self.balloon.bind(tplLabel, balloonText)

		self.checkStruc = Tkinter.Button(sfin, text=buttonText,
					underline=0, command=self._strucInfo)
		self.checkStruc.grid(row=row, column=4,
					sticky="new" , padx=5, pady=1)
		self.balloon.bind(self.checkStruc, balloonText)

		# Template seq-struc table (tplTable)
		from CGLtk.Table import SortableTable
		row = rowCounter.next()

		self.tplTable = SortableTable(sfin)
		self.tplTable.grid(row=row, column=1, padx=5,
					columnspan=4, rowspan=1, sticky="nsew")
		sfin.rowconfigure(row, weight=1)
		self._addColumn("Sequence", "seqID", format="%s ",
						anchor="nw", wrapLength='5c')
		self._addColumn("Structure ID", "fetchID", format="%s ", anchor='n')
		self._addColumn("%ID", "identity", format="%.1f%% ", anchor='n')
		self._addColumn("Title", "title", anchor='nw', wrapLength='10c')
		self._addColumn("Organism", "organism", anchor='n')

		# Choose which modeller to use
		row = rowCounter.next()
		iconImage = ImageTk.PhotoImage(Image.open(os.path.join(pkgdir, "icon_gears.png")))
		runIcon = Tkinter.Label(sfin, image=iconImage)
		runIcon.photo = iconImage
		runIcon.grid(row=row, column=0, padx=5, pady=5,
					rowspan=2, sticky="n")
		self.balloon.bind(runIcon, "Choose whether to run Modeller on local machine"
			" or over the web")

		self.optBalloon = Pmw.Balloon(sfin)
		radiogroups = []
		self.runOnWeb = Tkinter.IntVar(parent)
		self.runOnWeb.set(prefs[MODELLER_USE_WEB])
		self.runOnWeb.trace("w", self._runningLocCB)
		radioframe = Tkinter.Frame(sfin)
		self.runOnWebPanel = Pmw.Group(radioframe,
					tag_pyclass = Tkinter.Radiobutton,
					tag_text = 'Run Modeller via web service',
					#tag_font = fontTitle2,
					tag_value = 1,
					tag_variable = self.runOnWeb)
		self.runOnWebPanel.grid(row=0, column=0, columnspan=3, sticky='ew', padx=5)

		# License Key
		self.licEntry = Pmw.EntryField(self.runOnWebPanel.interior(),
					label_text = "Modeller license key: ",
					labelpos="w",
					entry_show = '*',
					value = prefs[MODELLER_KEY] )
		self.licEntry.grid(column=1, sticky='ew', padx=26)
		radiogroups.append(self.runOnWebPanel)
		self.balloon.bind(self.licEntry,
			"Please provide the Modeller license key, which can be obtained\n"
			"by registering on Modeller's home page")

		from chimera import help
		modellerHomeButton = Tkinter.Button(self.runOnWebPanel.interior(),
			text="Modeller home page", command=lambda disp=help.display:
			disp("http://www.salilab.org/modeller/"))
		modellerHomeButton.grid(row=0, column=2)

		# Run Modeller locally ------------------------------------------------
		self.runOnLocalPanel = Pmw.Group(radioframe,
					tag_pyclass = Tkinter.Radiobutton,
					tag_text = 'Run Modeller locally',
					#tag_font = fontTitle2,
					tag_value = 0,
					tag_variable = self.runOnWeb)
		self.runOnLocalPanel.grid(row = 1, column = 0, columnspan=3, sticky='ew', padx=5)

		# Local modeller path
		rowInd = 0
		balloonText = \
			"If you have Modeller installed on your machine, please specify the\n" \
			"location of the Modeller executable.  If you do not have Modeller\n" \
			"installed, you can download it from the Modeller web site."

		self.modPath = InputFileOption( self.runOnLocalPanel.interior(),
					rowInd,
					'Location of Modeller executable',
					prefs[MODELLER_PATH], None,
					balloon = balloonText)
		rowInd += 1
		
		# temporarily disabled 
		"""
		# Advanced options: Providing the initial model (Optional) 
		balloonText = "Provide your initial model instead of using the \n" \
			"one generated by Modeller's automodel function."
		self.initialModelEntry = InputFileOption(self.runOnLocalPanel.interior(), 
					rowInd,
					"Initial model PDB file (optional)",
					None, None, 
					balloon = balloonText)
		rowInd += 1
		"""

		# Providing customized Modeller scripts (Optional)
		balloonText = "Provide custom Modeller script"
		self.userScriptsEntry = InputFileOption(self.runOnLocalPanel.interior(), 
					rowInd,
					"Modeller script file (optional, overrides dialog)",
					None, None,
					balloon  = balloonText)
		rowInd += 1



		#Get Current Modeller Script
		self.curScriptsView = Tkinter.Button(self.runOnLocalPanel.interior(),
				text="Get Current Modeller Script", 
				command=self._viewScripts)
		self.curScriptsView.grid(row=rowInd, column=0, columnspan=2)
		self.optBalloon.bind(self.curScriptsView,
					"View the current Modeller script, which has \n"
					"incorporated above options.")
		rowInd += 1
		self.runOnLocalPanel.interior().columnconfigure(0, weight=0)
		self.runOnLocalPanel.interior().columnconfigure(1, weight=1)

		radiogroups.append(self.runOnLocalPanel)
		radioframe.grid(row=row, column=1, columnspan=4, sticky="new" )
		Pmw.aligngrouptags(radiogroups)
		radioframe.columnconfigure(0, weight=1)
		radioframe.columnconfigure(1, weight=1)

		self._runningLocCB()

		# Advanced options
		row = rowCounter.next()
		iconImage = ImageTk.PhotoImage(Image.open(os.path.join(pkgdir, "icon_adv.png")))
		advIcon = Tkinter.Label(sfin, image=iconImage)
		advIcon.photo = iconImage
		advIcon.grid(row=row, column=0, padx=5, pady=5,
					#rowspan=2, sticky="n")
					sticky="n")
		self.balloon.bind(advIcon,
			"Advanced Options allow more control over the request sent \n"
			"to Modeller. For a complete descriptions of these options, \n"
			"please visit:  http://salilab.org/modeller/manual/ \n"
			"Click on the Advanced Options button to toggle the option display.")

		self.advPanel = Pmw.Group(sfin,
					tag_pyclass = Tkinter.Button,
					tag_text = "Advanced Options")
		self.advPanel.configure(tag_command = self.advPanel.toggle)
		self.advPanel.grid(row=row, column=1, columnspan=4, sticky="new", padx=5)
		self.advPanel.toggle()
		advin = self.advPanel.interior()

		# Advanced options: initialization
		optRow = 0

		# Advanced options: Number of output models
		self.numModelLabel = Tkinter.Label(advin,
					text = "Number of output models: ")
					#font = fontAdvOpt )
		self.numModelLabel.grid(row=optRow, column=0, sticky="e")
		balloonText = "Number of model structure to generate. \n" \
			"Must be less than 1000.  The default is 5. \n" \
			"Warning: please consider the calculation time!"
		self.optBalloon.bind(self.numModelLabel, balloonText)
		f = Tkinter.Frame(advin)
		f.grid(row=optRow, column=1, sticky='w', padx=5)
		self.previousnumModel = 5  #default value
		self.numModelEntry = Pmw.EntryField(f,
					value = self.previousnumModel,
					validate = {'validator' : 'numeric',
						'min' : '1', 'max' : '1000',
						'minstrict' : 1, 'maxstrict' : 1},
						entry_width = 10)
		self.numModelEntry.grid(row=0, column=0)
		Tkinter.Label(f, text="(max 1000)").grid(row=0, column=1)
		self.optBalloon.bind(self.numModelEntry, balloonText)

		optRow += 1

		# Advanced options: Including non-water HETATM resides
		hetAtomLabel = Tkinter.Label(advin,
					text = "Include non-water HETATM residues from template: ")
					#font = fontAdvOpt )
		hetAtomLabel.grid(row=optRow, column=0, sticky="e")
		balloonText = "If enabled, all non-water HETATM residues in the template \n" \
			"structure(s) will be transferred into the generated models. \n"
		self.optBalloon.bind(hetAtomLabel, balloonText)
		self.hetAtomVar = Tkinter.IntVar(parent)
		self.hetAtomVar.set(0)
		hetAtomCheckButton = Tkinter.Checkbutton(advin,
					variable = self.hetAtomVar )
		hetAtomCheckButton.grid(row=optRow, column=1, sticky="w")
		self.optBalloon.bind(hetAtomCheckButton, balloonText)
		optRow += 1

		# Advanced options: Including water molecules
		waterLabel = Tkinter.Label(advin,
					text = "Include water molecules from template: ")
					#state = "disabled" ) # TODO: remove this line after fixing Water 
					#font = fontAdvOpt )
		waterLabel.grid(row=optRow, column=0, sticky="e")
		balloonText = "If enabled, all water molecules in the template structure(s) \n" \
				"will be included in the generated models." 
			#"Not yet implemented."  TODO: remove this line after fixing water 
		self.optBalloon.bind(waterLabel, balloonText)
		self.waterVar = Tkinter.IntVar(parent)
		self.waterVar.set(0)
		waterCheckButton = Tkinter.Checkbutton(advin,
					#state = "disabled",  # TODO: remove this line after fixing Water 
					variable = self.waterVar )
		waterCheckButton.grid(row=optRow, column=1, sticky="w")
		self.optBalloon.bind(waterCheckButton, balloonText)
		optRow += 1

#		# Ben recommends against including hydrogens from template
#		# Advanced options: Including hydrogen atoms
#		hydrogenLabel = Tkinter.Label(advin,
#					text = "Include hydrogen atoms from template: ",
#					#font = fontAdvOpt )
#		hydrogenLabel.grid(row=optRow, column=0, sticky="e")
#		self.hydrogenVar = Tkinter.IntVar(parent)
#		self.hydrogenVar.set(0)
#		hydrogenCheckButton = Tkinter.Checkbutton(advin,
#					variable = self.hydrogenVar )
#		hydrogenCheckButton.grid(row=optRow, column=1, sticky='w')
#		self.optBalloon.bind(hydrogenCheckButton,
#					"Enable this option, the hydrogen atoms will be read \n"
#					"from the template PDB files.  When you build all-atom \n"
#					"models, you need to enable this option. " )
#		optRow += 1

		# Advanced options: Building an all hydrogen model
		self.allHydrogenLabel = Tkinter.Label(advin,
					text = "Build models with hydrogens: ")
					#font = fontAdvOpt )
		self.allHydrogenLabel.grid(row=optRow, column=0, sticky="e")
		balloonText = "If enabled, the generated models will include hydrogen atoms. \n" \
			"Otherwise, only heavy atom coordinates will be built. \n" \
			"Increases computation time by approximately a factor of 4."
		self.optBalloon.bind(self.allHydrogenLabel, balloonText)
		self.allHydrogenVar = Tkinter.IntVar(parent)
		self.allHydrogenVar.set(0)
		f = Tkinter.Frame(advin)
		f.grid(row=optRow, column=1, sticky="w")
		self.allHydrogenCheckButton = Tkinter.Checkbutton(f,
					variable = self.allHydrogenVar )
		self.allHydrogenCheckButton.grid(row=0, column=0)
		self.optBalloon.bind(self.allHydrogenCheckButton, balloonText)
		Tkinter.Label(f, text="(warning: slow)").grid(row=0, column=1)
		optRow += 1

		# Advanced options: Getting a very fast and approximate model
		self.veryFastLabel = Tkinter.Label(advin,
					text = "Use fast/approximate mode: ")
					#font = fontAdvOpt )
		self.veryFastLabel.grid(row=optRow, column=0, sticky="e")
		balloonText = "If enabled, use a fast approximate method to generate a single model. \n"\
			"Typically used to get a rough idea what the model will look like or \n" \
			"to check that the alignment is reasonable."
		self.optBalloon.bind(self.veryFastLabel, balloonText)
		self.veryFastVar = Tkinter.IntVar(parent)
		self.veryFastVar.set(0)
		f = Tkinter.Frame(advin)
		f.grid(row=optRow, column=1, sticky='w')
		self.veryFastCheckButton = Tkinter.Checkbutton(f,
					variable = self.veryFastVar,
					command = self._resetNumModelto1)
		self.veryFastCheckButton.grid(row=0, column=0)
		Tkinter.Label(f, text="(produces only one model)").grid(row=0, column=1)
		self.optBalloon.bind(self.veryFastCheckButton, balloonText)
		optRow += 1

		# Advanced options: Thorough optimization (important for MDA)
		self.optimLabel = Tkinter.Label(advin,
					text = "Use thorough optimization: ")
					#font = fontAdvOpt )
		self.optimLabel.grid(row=optRow, column=0, sticky="e")
		balloonText = "If enabled, Modeller will perform a more thorough optimization step. \n"\
			"Recommended to be used in conjunction with MultiDomainAssembler (MDA) \n" \
			"for modeling large multidomain chains."
		self.optBalloon.bind(self.optimLabel, balloonText)
		self.optimVar = Tkinter.IntVar(parent)
		self.optimVar.set(0)
		f = Tkinter.Frame(advin)
		f.grid(row=optRow, column=1, sticky='w')
		self.optimCheckButton = Tkinter.Checkbutton(f,
					variable = self.optimVar,
                                        command = self._optimChangedCB)
		self.optimCheckButton.grid(row=0, column=0)
		Tkinter.Label(f, text="(recommended with MDA)").grid(row=0, column=1)
		self.optBalloon.bind(self.optimCheckButton, balloonText)
		optRow += 1

		# Advanced options: Providing the temp path (Optional) 
		balloonText = "Specify a folder for temporary files.  If not specified, \n"\
						"a location will be generated automatically."
		self.pathTempOpt = OutputFileOption(advin, optRow,
					"Temporary folder location (optional)", 
					prefs[MODELLER_TEMP_PATH], None, # name, default, callback 
					balloon = balloonText, dirsOnly=True)
		optRow += 1

		advin.columnconfigure(0, weight=0)
		advin.columnconfigure(1, weight=1)

		# Advanced options: Providing the distance restraints file (Optional) 
		balloonText = "Specify an input file containing distance restraints."
		self.pathDistRestrFile = InputFileOption(advin, optRow,
					"Distance restraints file (optional)", 
					None, None, 
					balloon = balloonText)
		optRow += 1

		advin.columnconfigure(0, weight=0)
		advin.columnconfigure(1, weight=1)



#		# Advance options: view and save current Modeller Scripts
#		curScriptsLabel = Tkinter.Label(advin,
#					text = "Current Modeller Scripts: ",
#					#font = fontAdvOpt )
#		curScriptsLabel.grid(row=optRow, column=0, sticky="e")
#		self.curScriptsView = Tkinter.Button(advin,
#					text = "View Scripts", command = self._viewScripts)
#		self.curScriptsView.grid(row=optRow, column=1, sticky="we")
#		self.optBalloon.bind(self.curScriptsView,
#					"View the current Modeller scripts, which has \n"
#					"incorporated above options.")
#		curScriptsSave = Tkinter.Button(advin,
#					text = "Save Scripts", command = self._saveScripts)
#		curScriptsSave.grid(row=optRow, column=2, sticky="we")
#		self.optBalloon.bind(curScriptsSave,
#					"Save the current Modeller scripts, which has \n"
#					"incorporated above options.")


		# Citation
		row = rowCounter.next()
		iconImage = ImageTk.PhotoImage(Image.open(os.path.join(pkgdir, "icon_sal.png")))
		citIcon = Tkinter.Label(sfin, image=iconImage)
		citIcon.photo = iconImage
		citIcon.grid(row=row, column=0, padx=5, pady=5)
		from ModellerBase import ModellerCitation
		ModellerCitation(sfin).grid(row=row, column=1, columnspan=4, sticky="w", padx=5)

		# Initialization and refreshment 
		self.refresh(initial=1)
		self.modellerHandlerIDs = {}
		for trigName in [ADDDEL_SEQS, SEQ_RENAMED]:
			self.modellerHandlerIDs[trigName] = self.mav.triggers.addHandler(
				trigName, self.refresh, None)

		sfin.columnconfigure(0, weight=0)
		sfin.columnconfigure(1, weight=2, minsize=300)
		sfin.columnconfigure(4, weight=1, minsize=150)
		return


	def _runningLocCB(self, *args):
		"""
		Change the Modeller running location call back function to disable some UI
		"""
		if self.runOnWeb.get():
			self.runOnWebPanel.expand()
			self.runOnLocalPanel.collapse()
			#self.licEntry.component('entry').config(state="normal")
			#self.licEntry.component('label').config(state="normal")
			#self.curScriptsView.config(state="disabled")
		else:
			self.runOnWebPanel.collapse()
			self.runOnLocalPanel.expand()
			#self.licEntry.component('entry').config(state="disabled")
			#self.licEntry.component('label').config(state="disabled")
			#self.curScriptsView.config(state="normal")
		return

	def destroy(self):
		for trigName, handlerID in self.modellerHandlerIDs.items():
			self.mav.triggers.deleteHandler(trigName, handlerID)
		self.mav = None
		chimera.openModels.deleteRemoveHandler(self.closeModelsID)
		ModelessDialog.destroy(self)
		return


	def refresh(self, trig1=None, trig2=None, trig3=None, initial=0):
		self.seqNames = []
		for seq in self.mav.seqs:
			self.seqNames.append(seq.name)
		if initial:
			#self.seqMenu.setitems(self.seqNames)
			#self._newSeqCB(self.seqNames[0])
			self._newSeqCB(self.seqMenu.getvalue())
			self.tplTable.launch(selectMode="extended")
			# row number of the Table 
			self.tplTable.tixTable.hlist.configure(height=5)
		else:
			#tgtsel = self.seqMenu.getvalue()
			#if tgtsel in self.seqNames:
			#	selItem = tgtsel
			#else:
			#	selItem = self.seqNames[0]
			#self.seqMenu.setitems(self.seqNames, index=selItem)
			#self._newSeqCB(selItem)
			pass
		return

	def _closeModelsCB(self, trigName, myData, closedModels):
		for cseq in self.candidateSeqs:
			cseq.removeStruc(closedModels)
		"""
		for deadModel in closedModels:
			for cseq in self.candidateSeqs:
				if deadModel in cseq.matchModels:
					cseq.matchModels.remove(deadModel)
		"""
		self.tplTable.refresh()
		return

	def _newSeqCB(self, target):
		self.candidateSeqs = []
		for seq in self.mav.seqs:
			if seq != target:
				print "seq (len %d):" % len(seq), seq.name
				print "target (len %d):" % len(target), target.name
				self.candidateSeqs.append( TemplateSeq(self.mav, seq, target) )
		self.tplTable.setData(self.candidateSeqs)
		self.tplTable.refresh()
		return

	def _resetNumModelto1(self):
		"""
		callback function of veryFastCheckButton. If checking fast mode, reset the numModelEntry
		to 1.
		"""
		if int(self.numModelEntry.getvalue()) != 1 :
			self.previousnumModel = int(self.numModelEntry.getvalue())
		if self.veryFastVar.get():
			self.numModelEntry.setvalue(1)
			self.numModelLabel.config(state='disabled')
			self.numModelEntry.component('entry').config(state="disabled")
			self.allHydrogenLabel.config(state='disabled')
			self.allHydrogenVar.set(0)
			self.allHydrogenCheckButton.config(state='disabled')
			self.optimLabel.config(state='disabled')
			self.optimVar.set(0)
			self.optimCheckButton.config(state='disabled')
		else:
			self.numModelLabel.config(state='normal')
			self.numModelEntry.component('entry').config(state="normal")
			self.numModelEntry.setvalue(self.previousnumModel)
			self.allHydrogenLabel.config(state='normal')
			self.allHydrogenCheckButton.config(state='normal')
			self.optimLabel.config(state='normal')
			self.optimCheckButton.config(state='normal')
		return

	def _optimChangedCB(self):
		"""
		callback function of optimCheckButton. Disables fast mode.
		"""
		if self.optimVar.get():
			self.veryFastLabel.config(state='disabled')
			self.veryFastVar.set(0)
			self.veryFastCheckButton.config(state='disabled')
		else:
			self.veryFastLabel.config(state='normal')
			self.veryFastCheckButton.config(state='normal')

	def _strucInfo(self):
		# load and check the structures based on the candidateSeqs. 
		for templateSeq in self.candidateSeqs:
			replyobj.info("candidate: %s\n" % templateSeq.seqID)
			templateSeq.loadStruc(annotate=True)
			replyobj.info("done with candidate: %s\n" % templateSeq.seqID)
		self.tplTable.setData(self.candidateSeqs)
		for col in self.tplTable.columns:
			self.tplTable.columnUpdate(col, entryPadY=5)

	def _addColumn(self, title, attrFetch, **kw):
		if title in [c.title for c in self.tplTable.columns]:
			return
		c = self.tplTable.addColumn(title, attrFetch, **kw)
		self.tplTable.columnUpdate(c)

	def _viewScripts(self):
		# Prepare the Modeller scripts, based on the setting input from the UI.
		from ModellerBase import writeModellerScripts
		pathModellerScripts, pathModellerConfig, tmpDir = writeModellerScripts(
			self.licEntry.getvalue().strip(), self.numModelEntry.getvalue(),
			self.hetAtomVar.get(), self.waterVar.get(), self.allHydrogenVar.get(),
			self.veryFastVar.get(), None, self.userScriptsEntry.get().strip(),
			self.pathTempOpt.get().strip(), self.optimVar.get(), self.pathDistRestrFile.get().strip())
		from Idle import flist
		flist.open_shell().io.open(editFile=pathModellerScripts)

	def Apply(self):
		self.status("")
		templateModels = []
		for tplSeq in self.tplTable.selected():
			if len(tplSeq.matchModels) == 0:
				tplSeq.loadStruc(annotate=True)
			for mol in tplSeq.matchModels:
				if not mol.__destroyed__ :
					templateModels.append(mol)
		self.tplTable.refresh()
		if len(templateModels) == 0:
			if not self.tplTable.selected():
				self.status('Please select at least one template structure!', color='red')
			else:
				self.status('Could not determine structure to load for selected template.',
						color='red')
			self.enter()
			return

		if self.runOnWeb.get():
			kw = { 'licenseKey': self.licEntry.getvalue() }
		else:
			kw = { 'executableLocation': self.modPath.get().strip(),
				'customScript': self.userScriptsEntry.get().strip() }
		from ModellerBase import model, verifyModelKw
		verified, statusMsg = verifyModelKw(kw)
		if not verified:
			self.status(statusMsg, color="red")
			self.enter()
			return
		model(self.mav, self.seqMenu.getvalue(), templateModels, self.numModelEntry.getvalue(),
			self.hetAtomVar.get(), self.waterVar.get(), self.allHydrogenVar.get(),
			veryFast=self.veryFastVar.get(), tempPath=self.pathTempOpt.get().strip(), thoroughOptim=self.optimVar.get(), distRestrPath=self.pathDistRestrFile.get().strip(), **kw)

class TemplateSeq():

	"""class to handle the data to the template seq table """

	def __init__(self, mav, seq, tgtSeq):
		self.mav = mav
		self.seq = seq
		self.tgtSeq = tgtSeq
		self.seqID = self.seq.name
		self.pdbID = None
		self.fetchID = None
		self.identity = percentIdentity( self.seq, self.tgtSeq )
		self.resolution = None
		self.matchModels = []
		self.title = self.organism = None

	def loadStruc(self, annotate=False): # load the structures
		from SeqAnnotations import name2pdbID
		if hasattr(self.seq, 'matchMaps') and self.seq.matchMaps:
			self.matchModels = self.seq.matchMaps.keys()
			self.pdbID, self.fetchID, fetchType = name2pdbID(self.matchModels[0].name)
			if not fetchType:
				self.mav.modellerHomologyDialog.status("Could not deduce1 PDB ID from"
					" model name (%s)" % self.matchModels[0].name, color="blue")
		else:
			self.pdbID, self.fetchID, fetchType = name2pdbID(self.seqID)
			if not fetchType:
				self.mav.modellerHomologyDialog.status("Could not deduce PDB ID from"
					" sequence name (%s)" % self.seqID, color="blue")
				return []
			prevAutoAssociate = self.mav.autoAssociate
			self.mav.autoAssociate = False
			try:
				self.matchModels = chimera.openModels.open(self.fetchID,
							type=fetchType)
			except:
				replyobj.reportException("Problem opening %s" % self.fetchID)
			finally:
				self.mav.autoAssociate = prevAutoAssociate
			if self.matchModels:
				self.mav.associate(self.matchModels, seq=self.seq, force=True)
			else:
				self.mav.modellerHomologyDialog.status("No models for PDB code %s"
							% self.pdbID)
				self.pdbID, self.fetchID, fetchType = None, None, None

		if annotate and fetchType:
			self.annotate()
		return self.matchModels

	def removeStruc(self, closedModels):
		for mol in closedModels:
			if mol in self.matchModels:
				self.matchModels.remove(mol)
		if len(self.matchModels) == 0:
			self.pdbID = None
			self.resolution = None
			self.title = None
			self.organism = None
			self.fetchID = None
		return


	def annotate(self): # fetch annotations
		modelSeqs = self.matchModels[0].sequences()
		if not modelSeqs:
			return
		mseq = modelSeqs[0]
		pdbID, chainID = self.pdbID, mseq.chainID
		if not chainID or chainID == ' ':
			chainID = 'A'
		status = self.mav.modellerHomologyDialog.status
		status("Fetching annotation for %s, chain %s" % (pdbID, chainID))
		from SeqAnnotations import parseUniprotAlignment, UniprotMappingError
		try:
			chainInfo, alignInfo = parseUniprotAlignment(pdbID, chainID, noAlignmentOkay=True)
		except UniprotMappingError, v:
			status(str(v)+'\n', color="red", log=True)
			return
		self.title = chainInfo['title']
		self.organism = chainInfo['organism']
