# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera
from chimera.baseDialog import ModelessDialog

class mmmdDialog(ModelessDialog):
	name = "Minimize Structure"
	help = "ContributedSoftware/minimize/minimize.html"
	buttons = ("Minimize", "Close")
	keepShown = "Minimize"

	def fillInUI(self, parent):
		import Tkinter
		from chimera.widgets import MoleculeScrolledListBox
		self.molList = MoleculeScrolledListBox(parent,
						listbox_selectmode="extended")
		self.molList.grid(row=0, column=0, sticky="nsew")
		parent.rowconfigure(0, weight=1)
		parent.columnconfigure(0, weight=1)
		self.minimizeOptions = MinimizeOptions(parent)
		self.minimizeOptions.grid(row=1, column=0)
		import Pmw
		self.memoryType = Pmw.RadioSelect(parent, orient="vertical",
								buttontype='radiobutton', pady=0)
		self.memoryType.add("set", text="Memorize options chosen in"
			" subsequent dialogs", anchor="w", justify="left")
		self.memoryType.add("use", text="Use previously memorized options,"
			" if any", anchor="w", justify="left")
		self.memoryType.add("none", text="Neither memorize nor use memorized"
			" options", anchor="w", justify="left")
		self.memoryType.grid(row=2, column=0)
		from DockPrep.prefs import prefs, MEMORIZED_SETTINGS
		if "Minimize" in prefs[MEMORIZED_SETTINGS]:
			self.memoryType.setvalue("use")
		else:
			self.memoryType.setvalue("set")

	def Apply(self):
		molecules = self.molList.getvalue()
		if not molecules:
			from chimera import UserError
			raise UserError("Please select a molecule to minimize")
		import base
		base.Minimizer(molecules, memorize=self.memoryType.getvalue(),
						callback=self.run)

	def run(self, minimizer):
		self.minimizeOptions.setOptions(minimizer)
		minimizer.run()

	def Dynamics(self):
		raise chimera.LimitationError("MD is unimplemented")


from chimera.tkoptions import EnumOption
import base
class FreezeOption(EnumOption):
	values = (base.FreezeNone, base.FreezeSelected, base.FreezeUnselected)

import Tkinter
class MinimizeOptions(Tkinter.Frame):

	def __init__(self, parent):
		from chimera.tkoptions import IntOption, FloatOption
		Tkinter.Frame.__init__(self, parent)
		self.sdSteps = IntOption(self, 0, "Steepest descent steps",
						100, None)
		self.sdStepsize = FloatOption(self, 1, u"Steepest descent step size (\N{ANGSTROM SIGN})",
						0.02, None,
						min=0.0001, max=1.0)
		self.cgSteps = IntOption(self, 2, "Conjugate gradient steps",
						10, None)
		self.cgStepsize = FloatOption(self, 3, u"Conjugate gradient step size (\N{ANGSTROM SIGN})",
						0.02, None,
						min=0.0001, max=1.0)
		self.interval = IntOption(self, 4, "Update interval", 10, None)
		self.freeze = FreezeOption(self, 5, "Fixed atoms",
						base.FreezeNone, None)

	def setOptions(self, minimizer):
		minimizer.nsteps = self.sdSteps.get()
		minimizer.stepsize = self.sdStepsize.get()
		minimizer.cgsteps = self.cgSteps.get()
		minimizer.cgstepsize = self.cgStepsize.get()
		minimizer.interval = self.interval.get()
		minimizer.fixedAtoms = base.frozenAtoms(self.freeze.get(),
							minimizer.molecules)

from chimera import dialogs
dialogs.register(mmmdDialog.name, mmmdDialog)
