# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

from chimera.extension import EMO, manager

class LightingEMO(EMO):
	def name(self):
		return "Lighting"
	def description(self):
		return "Manipulate lighting parameters"
	def categories(self):
		return ['Viewing Controls']
	def icon(self):
		return self.path('lighting.png')
	def activate(self):
		self.module('controller').display()
		return None

import chimera
if not chimera.nogui:
	from controller import LightingController
	ext = manager.findExtensionPackage(LightingController.Name)
	if ext is None:
		manager.registerExtension(LightingEMO(__file__))
		import controller
		c = controller.singleton()
		from chimera import viewing
		viewing.addCategory(LightingController.Name, 0,
					c.create, c.update, c.map, c.unmap,
					c.save, c.restore, c.reset, None)

import Lighting
chimera.registerPostGraphicsFunc(Lighting._postGraphicsFunc)

# Register lighting command.
def lighting(cmdname, args):
	from Lighting.cmd import lighting
	lighting(cmdname, args)
from Midas.midas_text import addCommand
addCommand('lighting', lighting, help=True)
