from VolumeViewer import selectregion

Identity = (
	( 1.0, 0.0, 0.0, 0.0 ),
	( 0.0, 1.0, 0.0, 0.0 ),
	( 0.0, 0.0, 1.0, 0.0 ) )

class SearchVolume(selectregion.Select_Volume_Subregion):

	def __init__(self, model, cb, title):
		self.model = model
		selectregion.Select_Volume_Subregion.__init__(self, cb,
								box_name=title)

	def volume(self):
		return self.model

	def box_transform_and_xform(self, model):
		xform = model.openState.xform
		if xform is None:
			return None, None, None
		valid, bbox = model.openState.bbox()
		if not valid:
			return None, None, None
		llf = bbox.llf
		urb = bbox.urb
		box = [ [ bbox.llf[0], bbox.llf[1], bbox.llf[2] ],
			[ bbox.urb[0], bbox.urb[1], bbox.urb[2] ] ]
		# Always use identity matrix
		return box, Identity, xform

	#
	# These methods are our own (do not override base class methods)
	#
	def bounds(self):
		"Return center and size of box in local coordinate system"
		# We don't need to do the fancy box transformations
		# because our transformation is always the identity
		origin = self.box_model.box[0]
		corner = self.box_model.box[1]
		size = [ corner[i] - origin[i] for i in range(3) ]
		center = [ origin[i] + size[i] / 2 for i in range(3) ]
		return center, size

	def hasBounds(self):
		return self.box_model.box is not None

	def setBounds(self, center, size):
		"Set center and size of box in local coordinate system"
		try:
			half_size = [ size[i] / 2 for i in range(3) ]
			box = [ [ center[i] - half_size[i] for i in range(3) ],
				[ center[i] + half_size[i] for i in range(3) ] ]
		except TypeError:
			# center and size can sometimes be None if user
			# is entering numbers in entry fields rather than
			# dragging box faces
			pass
		else:
			self.box_model.reshape_box(box, Identity)

	def restore_box(self, m):
		self.box_model.corner_atoms = m.atoms
		valid, bbox = m.openState.bbox()
		if not valid:
			self.box_model.box = None
			self.box_model.box_transform = None
		else:
			llf = bbox.llf
			urb = bbox.urb
			self.box_model.box = [
				[ bbox.llf[0], bbox.llf[1], bbox.llf[2] ],
				[ bbox.urb[0], bbox.urb[1], bbox.urb[2] ] ]
			self.box_model.box_transform = Identity
		import chimera
		chimera.addModelClosedCallback(m, self.box_model.model_closed_cb)
