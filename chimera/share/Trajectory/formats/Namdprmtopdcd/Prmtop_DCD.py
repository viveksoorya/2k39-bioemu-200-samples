# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: DCD.py 31055 2010-07-23 19:29:18Z pett $

# much of this code is based on sample code provided by Walter Scott

import os

from Trajectory.formats.Amber.Amber import Prmtop_base, Prmtop
from Trajectory.DCD.DCD import DCD_BASE, DCD

class Prmtop_DCD(Prmtop_base, DCD_BASE):
	def __init__(self, prmtopPath, dcdPath, startFrame, endFrame):
		self.prmtop = Prmtop(prmtopPath)
		self.dcd = DCD(dcdPath)
		numDcdAtoms = self.dcd.dcd.trajs[0].numatoms
		if numDcdAtoms != self.GetDict('numatoms'):
			raise ValueError("Prmtop has different number of atoms (%d)"
				" than DCD (%d)!" % (self.GetDict('numatoms'), numDcdAtoms))
		self.startFrame = startFrame
		self.endFrame = endFrame

		self.name = os.path.basename(dcdPath)
