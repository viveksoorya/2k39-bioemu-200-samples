# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: ChimeraExtension.py 41226 2016-08-16 21:10:20Z pett $

import chimera.extension

class BuildStructureEMO(chimera.extension.EMO):
	def name(self):
		return 'Build Structure'
	def description(self):
		return "build/modify structures"
	def categories(self):
		return ['Structure Editing']
	def activate(self):
		from chimera import dialogs
		gui = self.module('gui')
		dlg = dialogs.display(gui.BuildStructureDialog.name)
		dlg.setCategory(gui.ADD_ATOMS)
		return None
	def openSmiles(self, smiles):
		if not smiles:
			from Midas import MidasError
			raise MidasError("Empty SMILES string, or space after 'smiles:' prefix")
		Smiles = self.module('Smiles')
		try:
			sm = Smiles.smiles2mol(smiles)
		except Smiles.SmilesTranslationError, v:
			from chimera import UserError
			raise UserError(unicode(v))
		return [sm]
	def openPubChem(self, pcID, ignore_cache=False):
		PubChem = self.module('PubChem')
		try:
			pc = PubChem.pubChem2mol(pcID, ignore_cache=ignore_cache)
		except PubChem.InvalidPub3dID, v:
			from chimera import UserError
			raise UserError(unicode(v))
		return [pc]

emo = BuildStructureEMO(__file__)
chimera.extension.manager.registerExtension(emo)

chimera.fileInfo.register("SMILES", emo.openSmiles, None,
		["smiles", "SMILES"], category=chimera.FileInfo.STRUCTURE)
chimera.fileInfo.register("PubChem", emo.openPubChem, None,
		["pubchem", "PubChem"], category=chimera.FileInfo.STRUCTURE)
from chimera import fetch, openModels
fetch.registerIdType("PubChem",				# name of database
			6,				# identifier length
			"12123", 			# example
			"PubChem",			# file type
			"https://pubchem.ncbi.nlm.nih.gov",	# homepage
			"https://www.ncbi.nlm.nih.gov/sites/entrez?db=pccompound&term=%s")				# info url

def cmdInvert(cmdName, args):
	from BuildStructure import cmdInvertShim
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(cmdInvertShim, args, specInfo=[("atomSpec", "atoms", "atoms")])
from Midas.midas_text import addCommand
addCommand("invert", cmdInvert, help=True)

class AdjustTorsionsEMO(chimera.extension.EMO):
	def name(self):
		return 'Adjust Torsions'
	def description(self):
		return "interactively adjust torsion angles"
	def categories(self):
		return ['Structure Editing']
	def activate(self):
		from chimera import dialogs
		gui = self.module('gui')
		dlg = dialogs.display(gui.BuildStructureDialog.name)
		dlg.setCategory(gui.BOND_ROTS)
		return None

atEMO = AdjustTorsionsEMO(__file__)
chimera.extension.manager.registerExtension(atEMO)
