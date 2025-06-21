from chimera.extension import EMO, manager

# -----------------------------------------------------------------------------
#
class Transform_Coordinates_EMO(EMO):

	def name(self):
		return 'Transform Coordinates'
	def description(self):
		return 'Apply a rotation and translation to model coordinate axes'
	def categories(self):
		return ['Movement']
	def icon(self):
		return None
	def activate(self):
		self.module('gui').show_transform_coordinates_dialog()
		return None

# -----------------------------------------------------------------------------
#
manager.registerExtension(Transform_Coordinates_EMO(__file__))
