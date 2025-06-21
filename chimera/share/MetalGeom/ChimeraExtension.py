import chimera.extension

class MetalGeomEMO(chimera.extension.EMO):
	def name(self):
		return 'Metal Geometry'
	def description(self):
		return 'measure metal coordination geometry'
	def categories(self):
		return ['Structure Analysis']
	def icon(self):
		#return self.path('icon.png')
		return None
	def activate(self):
		from chimera.dialogs import display
		display(self.module('gui').MetalsDialog.name)
		return None

chimera.extension.manager.registerExtension(MetalGeomEMO(__file__))

