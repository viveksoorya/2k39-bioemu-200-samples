# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import Tkinter
import Pmw

import chimera
from chimera import tkoptions
from chimera.baseDialog import ModelessDialog
import base
from chimera import replyobj

class SurfnetOptions:

	def setupOptions(self, f, row=0):
		class ReprOption(tkoptions.EnumOption):
			values = ('Mesh', 'Surface')
		self.reprType = ReprOption(f, row, 'Representation',
						ReprOption.values[0], None)

		class DensityOption(tkoptions.EnumOption):
			values = ('Gaussian', 'Quadratic')
		self.density = DensityOption(f, row + 1, 'Density',
						DensityOption.values[0], None)

		self.gridInterval = tkoptions.FloatOption(f, row + 2,
						'Grid Interval', 1.0, None)
		self.cutoff = tkoptions.FloatOption(f, row + 3,
						'Distance Cutoff', 10.0, None)
		self.color = tkoptions.ColorOption(f, row + 4,
						'Color', None, None)

class InterfaceSurfnetCB(ModelessDialog, SurfnetOptions):

	title = 'Surfnet'
	help = 'ContributedSoftware/surfnet/surfnet.html'

	def fillInUI(self, parent):
		self.as1 = tkoptions.StringOption(parent, 0, 'Atom Set 1',
							'', None)
		self.as2 = tkoptions.StringOption(parent, 1, 'Atom Set 2',
							'', None)
		self.setupOptions(parent, row=2)

	def Apply(self):
		as1 = self.as1.get()
		if as1 == '':
			replyobj.error('Atom set 1 selection is empty')
			return
		as2 = self.as2.get()
		if as2 == '':
			as2 = as1
		error = base.interface_surfnet(as1, as2,
					useMesh=self.reprType.get() == 'Mesh',
					cutoff=self.cutoff.get(),
					density=self.density.get(),
					interval=self.gridInterval.get(),
					color=self.color.get())
		if error:
			replyobj.error(error)
