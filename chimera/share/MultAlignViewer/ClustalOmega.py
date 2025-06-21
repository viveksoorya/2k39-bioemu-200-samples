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
from prefs import prefs, CLUSTALO_ITERATIONS, CLUSTALO_FULL_INITIAL, \
	CLUSTALO_FULL_ITERATION

class ClustalOmegaOptions:
	name = "Clustal Omega" # identification to user

	def __init__(self, master, rowCounter):
		self.options = []
		from chimera.tkoptions import IntOption, BooleanOption
		self.numIters = IntOption(master, rowCounter.next(), "Number of"
			" guide-tree/HMM iterations", prefs[CLUSTALO_ITERATIONS], None,
			balloon="Controls --iterations flag; see www.clustal.org/omega/"
			"README", min=0, max=1000)
		self.options.append(self.numIters)
		self.fullInitial = BooleanOption(master, rowCounter.next(), "Use"
			" full distance matrix during initial alignment",
			prefs[CLUSTALO_FULL_INITIAL], None,
			balloon="Controls --full flag; see www.clustal.org/omega/README")
		self.options.append(self.fullInitial)
		self.fullIteration = BooleanOption(master, rowCounter.next(), "Use"
			" full distance matrix during alignment iteration",
			prefs[CLUSTALO_FULL_ITERATION], None, balloon=
			"Controls --full-iter flag; see www.clustal.org/omega/README")
		self.options.append(self.fullIteration)
		self.citation = ClustalOmegaCitation(master)
		self.citation.grid(row=rowCounter.next(), column=0, columnspan=2)

	def get(self, setPrefs=True):
		if setPrefs:
			for opt, pref in zip(self.options, [CLUSTALO_ITERATIONS,
					CLUSTALO_FULL_INITIAL, CLUSTALO_FULL_ITERATION]):
				prefs[pref] = opt.get()
		optTexts = []
		iters = self.numIters.get()
		if iters:
			optTexts.append("--iterations %d" % iters)
		if self.fullInitial.get():
			optTexts.append("--full")
		if self.fullIteration.get():
			optTexts.append("--full-iter")
		return ("clustal_omega", ("-i", "-o"), " ".join(optTexts))

	def grid(self):
		for opt in self.options:
			opt.manage()
		self.citation.grid()

	def grid_remove(self):
		for opt in self.options:
			opt.forget()
		self.citation.grid_remove()

from RealignBase import ServiceOptions
ServiceOptions.registerService(ClustalOmegaOptions)

from CGLtk.Citation import Citation
class ClustalOmegaCitation(Citation):
	def __init__(self, parent):
		Citation.__init__(self, parent, u"F. Sievers, A. Wilm, D. Dineen, T. J. Gibson, K. Karplus, W. Li, R. Lopez, H. McWilliam,\n\tM. Remmert, J. S\N{LATIN SMALL LETTER O WITH DIAERESIS}ding, J. D. Thompson, and D. G Higgins. \n"
			"Fast, scalable generation of high-quality protein multiple sequence alignments using Clustal Omega.\n"
			"Mol. Syst. Biol. 7:539, 2011.",
			prefix= "Publications using Clustal Omega results should cite:",
			url='https://www.ncbi.nlm.nih.gov/pubmed/21988835')

