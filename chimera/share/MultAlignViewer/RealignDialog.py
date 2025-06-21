# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: AddSeqDialog.py 27358 2009-04-21 00:32:47Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj, UserError
from prefs import prefs

class RealignDialog(ModelessDialog):
	"""Realign sequences"""

	buttons = ("OK", "Apply", "Close")
	default = "OK"
	title = "Realign Sequences"
	help = "ContributedSoftware/multalignviewer/realign.html"
	
	def __init__(self, mav, *args, **kw):
		self.mav = mav
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		import Pmw, Tkinter
		from itertools import count
		row = count()

		from RealignBase import DestinationOptions, ServiceOptions
		serviceNames = ServiceOptions.names()
		if len(serviceNames) == 1:
			serviceText = serviceNames[0]
		else:
			serviceText = " or ".join([", ".join(serviceNames[:-1]),
				serviceNames[-1]])
		from CGLtk import WrappingLabel, Font
		title = WrappingLabel.WrappingLabel(parent, text="Realign sequences"
			" using %s web service" % serviceText)
		Font.shrinkFont(title, 1.25)
		title.grid(row=row.next(), column=0, columnspan=2, sticky="ew")

		self.destinationOptions = DestinationOptions(parent, row)

		self.serviceOptions = ServiceOptions(parent, row)

	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		serviceName, inOutFlags, options, reordersSequences = self.serviceOptions.get()
		self.mav.computeRealignment(serviceName, inOutFlags, options,
			destination=self.destinationOptions.get(), reordersSequences=reordersSequences)
