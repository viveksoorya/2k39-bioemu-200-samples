# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension

class ModBaseEMO(chimera.extension.EMO):
	def name(self):
		return "ModBase"
	def description(self):
		return "Fetch ModBase database entry"
	def categories(self):
		return ["Structure Analysis"]
	def open(self, path, ignore_cache=False):
		# Comment out if cannot open new file type
		return self.module("gui").processModBaseID(path, ignore_cache=ignore_cache)

emo = ModBaseEMO(__file__)

from chimera import fileInfo, FileInfo
fileInfo.register("ModBase",				# name of file type
			emo.open,			# function to call
			None,				# extensions
			['modbase', 'ModBase'],		# prefixes
			category=FileInfo.STRUCTURE)	# category
from chimera import fetch, openModels
fetch.registerIdType("ModBase",				# name of database
			8,				# identifier length
			"P04848", 			# example
			"ModBase",			# file type
			"modbase.compbio.ucsf.edu",	# homepage
			"http://modbase.compbio.ucsf.edu/modbase-cgi/model_search.cgi?databaseID=%s")					# info url
