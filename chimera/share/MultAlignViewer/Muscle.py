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

from chimera import replyobj, UserError, NonChimeraError
import os
from prefs import prefs, MUSCLE_ITERATIONS, MUSCLE_ITERATION_TIME, \
	MUSCLE_DIAGONALS, MUSCLE_LOG

class MuscleOptions:
	name = "MUSCLE" # identification to user
	reordersSequences = True

	def __init__(self, master, rowCounter):
		self.options = []
		from chimera.tkoptions import IntOption, BooleanOption, FloatOption
		self.numIters = IntOption(master, rowCounter.next(), "Maximum number"
			" of iterations", prefs[MUSCLE_ITERATIONS], None,
			balloon="Controls -maxiters flag;"
			" see http://www.drive5.com/muscle/manual/options.html",
			min=0, max=1000)
		self.options.append(self.numIters)
		self.iterTime = FloatOption(master, rowCounter.next(), "Maximum time"
			" to iterate in hours (0 means no limit)",
			prefs[MUSCLE_ITERATION_TIME], None,
			balloon="Controls -maxhours flag;"
			" see http://www.drive5.com/muscle/manual/options.html", min=0.0)
		self.options.append(self.iterTime)
		self.diagonals = BooleanOption(master, rowCounter.next(), "Find"
			" diagonals (faster execution if sequences are similar)",
			prefs[MUSCLE_DIAGONALS], None, balloon="Controls -diags flag;"
			" see http://www.drive5.com/muscle/manual/options.html")
		self.options.append(self.diagonals)
		"""
		self.log = BooleanOption(master, rowCounter.next(), "Copy MUSCLE log"
			" output to reply log", prefs[MUSCLE_LOG], None)
		self.options.append(self.log)
		"""
		self.citation = MuscleCitation(master)
		self.citation.grid(row=rowCounter.next(), column=0, columnspan=2)

	def get(self, setPrefs=True):
		if setPrefs:
			for opt, pref in zip(self.options, [MUSCLE_ITERATIONS,
					MUSCLE_ITERATION_TIME, MUSCLE_DIAGONALS]):
				prefs[pref] = opt.get()
		optTexts = []
		iters = self.numIters.get()
		optTexts.append("-maxiters %d" % iters)
		iterTime = self.iterTime.get()
		if iterTime > 0.0:
			optTexts.append("-maxhours %.2f" % iterTime)
		if self.diagonals.get():
			optTexts.append("-diags")
		return ("muscle", ("-in", "-out"), " ".join(optTexts))

	def grid(self):
		for opt in self.options:
			opt.manage()
		self.citation.grid()

	def grid_remove(self):
		for opt in self.options:
			opt.forget()
		self.citation.grid_remove()

from RealignBase import ServiceOptions
ServiceOptions.registerService(MuscleOptions)

from CGLtk.Citation import Citation
class MuscleCitation(Citation):
	def __init__(self, parent):
		Citation.__init__(self, parent, u"R. C. Edgar\n"
			"MUSCLE: multiple sequence alignment with high accuracy and high throughput.\n"
			"Nucl. Acids Res. 32 (5), 1792-1797, 2004.",
			prefix= "Publications using MUSCLE results should cite:",
			url='https://www.ncbi.nlm.nih.gov/pubmed/15034147')

