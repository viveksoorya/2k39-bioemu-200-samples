import chimera.extension

class ModelLoopsEMO(chimera.extension.EMO):
	def name(self):
		return 'Model/Refine Loops'
	def description(self):
		return 'use MODELLER to model structure'
	def categories(self):
		return ['Structure Editing']
	def icon(self):
		return None
	def activate(self):
		self.module('gui').modelLoops()
		return None

chimera.extension.manager.registerExtension(ModelLoopsEMO(__file__))

