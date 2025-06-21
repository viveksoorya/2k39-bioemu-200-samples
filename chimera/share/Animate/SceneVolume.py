#THIS MODULE IS OBSOLETE! NO MODIFICATION SHOULD BE DONE IN THIS FILE.
#IT IS SOLELY HERE TO SUPPORT SAVED SESSIONS CREATED WHEN THIS MODULE
#WAS ACTIVE. PRESENCE OF THIS MODULE ENABLES OLDER SAVED SESSIONS TO BE
#RESTORED. THEY CAN THEN BE SAVED AGAIN AND WILL BECOME COMPATIBLE WITH THE
#CURRENT VERSION.

# Volume scene saving and restoring.
class SceneVolume(object):

	def __init__(self):
		self.scene_state = None

	# Pickle support
	def __getstate__(self):
		return self.toString()
	def __setstate__(self, unpickledStr):
		self.fromString(unpickledStr)

	def toString(self):
		from SessionUtil import objecttree
		t = objecttree.instance_tree_to_basic_tree(self.scene_state)
		s = repr(t)
		return s

	def fromString(self, s):
		t = eval(s)
		from VolumeViewer import session
		self.scene_state = session.volume_manager_state_from_basic_tree(t)

	def save(self):
		from VolumeViewer import session, volume
		vms = session.Volume_Manager_State()
		vms.state_from_manager(volume.volume_manager,
			include_unsaved_volumes=True)
		self.scene_state = vms

	def restore(self):
		self.scene_state.set_attributes()


#vs = SceneVolume()
#from Accelerators import add_accelerator as add
#add('vc', 'Save volume scene', vs.save_volume_scene)
#add('vr', 'Restore volume scene', vs.restore_volume_scene)
