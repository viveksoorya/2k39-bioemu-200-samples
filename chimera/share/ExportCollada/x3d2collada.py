from numpy import array, arange, zeros, empty
from numpy import eye as identity, dot, cross, linalg, dstack, concatenate
from math import sin, cos, tan, radians, sqrt, pi, acos, atan
from collada import Collada, scene, source, geometry, material, light, camera

def degrees(angle):
	return angle * 180 / pi

def radians(angle):
	return angle * pi / 180

def rotation(axis, angle, inDegrees=False):
	assert(len(axis) == 3 or axis[0] == 0)
	if inDegrees:
		angle = radians(angle)
	sqlength = dot(axis, axis)
	if sqlength == 0:
		raise ValueError("can't rotate about zero vector")
	length = sqrt(sqlength)
	x = axis[0] / length
	y = axis[1] / length
	z = axis[2] / length
	s = sin(angle)
	c = cos(angle)
	t = 1 - c
	return array([
		[ t * x * x + c, t * x * y - s * z, t * x * z + s * y, 0 ],
		[ t * y * x + s * z, t * y * y + c, t * y * z - s * x, 0 ],
		[ t * z * x - s * y, t * z * y + s * x, t * z * z + c, 0 ],
		[ 0, 0, 0, 1 ]
	])

def translation(vector):
	assert(len(vector) == 3 or vector[0] == 0)
	t = identity(4)
	t[0:3, 3] = vector[0:3]
	return t

def scale(vector):
	assert(len(vector) == 3)
	s = identity(4)
	s[0][0] = vector[0]
	s[1][1] = vector[1]
	s[2][2] = vector[2]
	return s

NamespaceAbbreviations = {
	"{http://www.cgl.ucsf.edu/chimera/}": "Chimera",
	#"{http://www.web3d.org/specifications/x3d-3.0.xsd}": "",
	#"{http://www.web3d.org/specifications/x3d-3.1.xsd}": "",
	#"{http://www.web3d.org/specifications/x3d-3.2.xsd}": "",
}

def canonicalTag(tag):
	# convert namespace at beginning of tag to our canonical version
	if not tag.startswith('{'):
		return tag
	for ns, abbr in NamespaceAbbreviations.items():
		if tag.startswith(ns):
			return '%s%s' % (abbr, tag[len(ns):])
	return tag

class Shape:
	def __init__(self):
		self.type = "unknown"
		self.appearanceDef = None
		self.material = None
		self.lineProperties = None
		self.coords = None
		self.normals = None
		self.colors = None
		self.colorsRGBA = None
		self.indices = None

class Material:
	def __init__(self):
		self.ambientIntensity = 0.2
		self.diffuseColor = [0.8, 0.8, 0.8]
		self.emissiveColor = [0, 0, 0]
		self.shininess = 0.2
		self.specularColor = [0, 0, 0]
		self.transparency = 0

class Processor:
	"""convert chimera X3D output to target output format"""
	# Processor should be independent of the output format.
	# All output go through the 'write_data' method to be
	# supplied by subclass.

	def __init__(self):
		# viewport default
		self.width = 500
		self.height = 500
		# background default
		self.bgcolor = (0, 0, 0)
		# projection defaults
		self.cofr = [0, 0, 0]
		self.fov = pi / 4
		self.camera_type = "persp"
		self.orientation = [0, 0, 1, 0]
		self.position = [0, 0, 10]
		self.hither = 0.1
		self.yon = 10000
		# triangle cache
		self.tcache = {}

		self.defines = {}
		# xforms is list of 2-tuples where the first element
		# is the current transformation, and the second element
		# is the matrix that modified the previous current
		# transform, so we can easily incorporate the last
		# transform for instancing
		self.xforms = [(identity(4), identity(4))]

	def close(self):
		self.flushTriangleCache()
		self.write_data(['vp', self.width, self.height, self.hither, self.yon])

	# tag visiting

	def start(self, tag, attrib):
		# call startTAG function if it exists
		tag = canonicalTag(tag)
		func = getattr(self, "start%s" % tag, None)
		if func is not None:
			try:
				func(attrib)
			except:
				import traceback
				traceback.print_exc()

	def end(self, tag):
		# call endTAG function if it exists
		tag = canonicalTag(tag)
		func = getattr(self, "end%s" % tag, None)
		if func is not None:
			try:
				func()
			except:
				import traceback
				traceback.print_exc()

	def data(self, data):
		# X3D doesn't have any data in a node
		pass

	# tag specific code goes here

	def startChimeraWindowSize(self, attrib):
		self.width = int(attrib['width'])
		self.height = int(attrib['height'])

	def startOrthoViewpoint(self, attrib):
		# only support one viewpoint for now
		try:
			cofr = attrib['centerOfRotation']
			self.cofr = [float(x) for x in cofr.split()]
		except KeyError:
			self.cofr = [0, 0, 0]
		try:
			fov = attrib['fieldOfView']
			self.fov = [float(x) for x in fov.split()]
		except KeyError:
			self.fov = [-1, -1, 1, 1]
		try:
			orientation = attrib['orientation']
			self.orientation = [float(x) for x in orientation.split()]
		except KeyError:
			self.orientation = [0, 0, 1, 0]
		try:
			position = attrib['position']
			self.position = [float(x) for x in position.split()]
		except KeyError:
			self.position = [0, 0, 10]
		self.camera_type = "ortho"
		self.write_data(['cofr'] + list(self.cofr))
		self.write_data(['eyepos'] + list(self.position))
		self.write_data(['up'] + [0, 1, 0]) # TODO: use self.orientation
		self.write_data(['ortho'] + self.fov)

	def startViewpoint(self, attrib):
		# only support one viewpoint for now
		try:
			cofr = attrib['centerOfRotation']
			self.cofr = [float(x) for x in cofr.split()]
		except KeyError:
			self.cofr = [0, 0, 0]
		try:
			self.fov = float(attrib['fieldOfView'])
		except KeyError:
			self.fov = pi / 4
		try:
			orientation = attrib['orientation']
			self.orientation = [float(x) for x in orientation.split()]
		except KeyError:
			self.orientation = [0, 0, 1, 0]
		try:
			position = attrib['position']
			self.position = [float(x) for x in position.split()]
		except KeyError:
			self.position = [0, 0, 10]
		self.camera_type = "persp"
		self.write_data(['cofr'] + list(self.cofr))
		self.write_data(['eyepos'] + list(self.position))
		self.write_data(['up'] + [0, 1, 0]) # TODO: use self.orientation
		if self.width < self.height:
			# convert horizontal fov to vertical
			self.fov = 2 * atan(tan(self.fov / 2) * self.height / self.width)
		self.write_data(['persp', degrees(self.fov)])

	def startBackground(self, attrib):
		try:
			color = attrib['skyColor']
		except KeyError:
			return
		self.bgcolor = [float(x) for x in color.split()]
		self.write_data(['bg'] + list(self.bgcolor))

	def startClipPlane(self, attrib):
		try:
			plane = [float(x) for x in attrib['plane'].split()]
		except KeyError:
			return
		if len(self.xforms) == 1 and self.orientation[3] == 0:
			# hack to find hither and yon planes
			if plane[0:3] == [0, 0, -1]:
				# hither plane
				zNear = plane[3]
				self.hither = self.position[2] - zNear
			elif plane[0:3] == [0, 0, 1]:
				# yon plane
				zFar = -plane[3]
				self.yon = self.position[2] - zFar

	def startTransform(self, attrib):
		if attrib is None:
			self.xforms.append((self.xforms[-1][0], identity(4)))
			return
		try:
			xyza = [float(x) for x in attrib['rotation'].split()]
			r = rotation(xyza[0:3], xyza[3])
		except KeyError:
			r = None
		try:
			xyz = [float(x) for x in attrib['translation'].split()]
			t = translation(xyz)
		except KeyError:
			t = None
		try:
			xyz = [float(x) for x in attrib['center'].split()]
			c = translation(xyz)
			invc = translation([-f for f in xyz])
		except KeyError:
			c = None
		try:
			xyz = [float(x) for x in attrib['scale'].split()]
			s = scale(xyz)
		except KeyError:
			s = None
		try:
			xyza = [float(x) for x in
					attrib['scaleOrientation'].split()]
			sr = rotation(xyza[0:3], xyza[3])
			invsr = rotation(xyza[0:3], -xyza[3])
		except KeyError:
			sr = None
			invsr = None
		# From X3D Transform spec:
		#    mat = t * c * r * sr * s * -sr * -c
		if s is None:
			mat = identity(4)
		elif sr is not None:
			mat = dot(sr, dot(s, invsr))
		else:
			mat = s
		if r is not None:
			mat = dot(r, mat)
			if c is not None:
				mat = dot(c, dot(mat, invc))
		if t is not None:
			mat = dot(t, mat)

		top = self.xforms[-1][0]
		newtop = dot(top, mat)
		self.xforms.append((newtop, mat))

	def endTransform(self):
		self.xforms.pop()

	def startShape(self, attrib):
		shape = self.shape = Shape()
		shape.type = "unknown"
		shape.coords = None
		shape.normals = None
		shape.colorsRGBA = None
		shape.indices = None

	def endShape(self):
		shape = self.shape
		if shape.type == "unknown":
			return
		if shape.type in ("sphere", "cylinder"):
			mat = self.shape.material
			r, g, b = mat.diffuseColor
			a = 1 - mat.transparency
			self.write_data(self.shape.data + [[r, g, b, a]])
			return
		if shape.type == "point set":
			self.write_data(['p', shape.coords, shape.colorsRGBA])
			return
		if shape.type == "line set":
			# process line strips into pairs of points
			i = 0
			for c in shape.vertexCounts:
				if c < 2:
					return	# malformed
				if c == 2:
					i += c
					continue
				c -= 2
				i += 2
				while c > 2:
					shape.coords[i:i] = [shape.coords[i - 3:i]]
					shape.colorsRGBA[i:i] = [shape.colorsRGBA[i - 4:i]]
					c -= 1
					i += 2
			self.write_data(['l', shape.coords, shape.colorsRGBA,
							shape.lineProperties])
			return
		if shape.type == "indexed line set":
			# TODO: color indices
			# process line strips into pairs of points
			indices = []
			curLineLen = 0
			for i in shape.indices:
				if i == -1:
					curLineLen = 0
					continue
				if curLineLen < 2:
					indices.append(i)
				else:
					indices.extend([indices[-1], i])
				curLineLen += 1
			if not indices:
				indices = None
			self.write_data(['il', shape.coords, shape.colorsRGBA,
							shape.lineProperties, indices])
			return

		if shape.type == "triangles":
			data = ['t']
		elif shape.type == "triangle strip":
			data = ['ts']
		else:
			return

		if shape.coords is None:
			return
		data += [shape.coords]

		if shape.normals is not None:
			data += [shape.normals]
		else:
			if shape.type == "triangles":
				stride = 3
				limit = 0
			else:
				stride = 1
				limit = 2
			normals = []
			for i in range(0, len(shape.coords) - limit * 3, stride * 3):
				p0 = array(shape.coords[i:i + 3])
				p1 = array(shape.coords[i + 3:i + 6])
				p2 = array(shape.coords[i + 6:i + 9])
				n = cross(p1 - p0, p2 - p0)
				sqlength = dot(n, n)
				n /= sqrt(sqlength)
				normals += list(n) * stride
			normals += list(n) * limit
			data += [normals]

		if shape.colorsRGBA is not None:
			data += [shape.colorsRGBA]
		elif shape.material:
			mat = shape.material
			data += [[mat.diffuseColor[0], mat.diffuseColor[1],
				mat.diffuseColor[2], 1 - mat.transparency]]
		else:
			data += [None]

		data += [shape.indices]
		self.addTriangleCache(data)
		self.shape = None

	def startAppearance(self, attrib):
		if attrib is None:
			return
		if 'DEF' in attrib:
			self.shape.appearanceDef = attrib['DEF']
		elif 'USE' in attrib:
			(self.shape.material,
				self.shape.lineProperties) = self.defines[attrib['USE']]

	def endAppearance(self):
		if self.shape.appearanceDef:
			self.defines[self.shape.appearanceDef] = (self.shape.material,
								self.shape.lineProperties)

	def startMaterial(self, attrib):
		mat = self.shape.material = Material()
		try:
			mat.ambientIntensity = float(attrib['ambientIntensity'])
		except KeyError:
			pass
		try:
			mat.diffuseColor = [float(x) for x in attrib['diffuseColor'].split()]
		except KeyError:
			pass
		try:
			mat.emissiveColor = [float(x) for x in attrib['emissiveColor'].split()]
		except KeyError:
			pass
		try:
			mat.shininess = float(attrib['shininess'])
		except KeyError:
			pass
		try:
			mat.specularColor = [float(x) for x in attrib['specularColor'].split()]
		except KeyError:
			pass
		try:
			mat.transparency = float(attrib['transparency'])
		except KeyError:
			pass

	def startLineProperties(self, attrib):
		lp = self.shape.lineProperties = dict()
		try:
			lp['linewidth'] = float(attrib['linewidthScaleFactor'])
		except KeyError:
			pass
		try:
			lp['linetype'] = attrib['linetype']
		except KeyError:
			pass

	def startCoordinate(self, attrib):
		points = [float(x) for x in attrib['point'].replace(',', ' ').split()]
		assert(len(points) % 3 == 0)
		top = self.xforms[-1][0]
		for i in range(0, len(points), 3):
			pt = dot(top, points[i:i + 3] + [1])
			points[i:i + 3] = pt.tolist()[0:3]
		self.shape.coords = points

	def startNormal(self, attrib):
		normals = [float(x) for x in attrib['vector'].replace(',', ' ').split()]
		assert(len(normals) % 3 == 0)
		rot = self.xforms[-1][0][0:3, 0:3]
		if linalg.det(rot) == 1:
			renormalize = False
		else:
			rot = linalg.inv(rot).transpose()
			renormalize = True
		for i in range(0, len(normals), 3):
			n = dot(rot, normals[i:i + 3])
			if renormalize:
				n /= sqrt(dot(n, n))
			normals[i:i + 3] = n.tolist()
		self.shape.normals = normals

	def startColor(self, attrib):
		colors = [float(x) for x in attrib['color'].replace(',', ' ').split()]
		assert(len(colors) % 3 == 0)
		rgba = zip(colors[::3], colors[1::3], colors[2::3], [1] * (len(colors) / 3))
		import itertools as it
		self.shape.colorsRGBA = list(it.chain.from_iterable(rgba))

	def startColorRGBA(self, attrib):
		colors = [float(x) for x in attrib['color'].replace(',', ' ').split()]
		assert(len(colors) % 4 == 0)
		self.shape.colorsRGBA = colors

	def startTriangleSet(self, attrib):
		self.shape.type = "triangles"

	def startTriangleStripSet(self, attrib):
		self.shape.type = "triangle strip"

	def startIndexedTriangleSet(self, attrib):
		self.shape.type = "triangles"
		indices = [int(x) for x in attrib['index'].replace(',', ' ').split()]
		assert(len(indices) % 3 == 0)
		self.shape.indices = indices

	def startIndexedTriangleStripSet(self, attrib):
		self.shape.type = "triangle strip"
		indices = [int(x) for x in attrib['index'].replace(',', ' ').split()]
		while indices[-1] == -1:
			del indices[-1]
		# replace strip terminations with degenerate triangles
		# so they can stay as one strip
		i = 0
		while 1:
			try:
				i = indices.index(-1, i)
			except ValueError:
				break
			indices[i:i + 1] = indices[i - 1:i + 2: 2]
		self.shape.indices = indices

	def startIndexedLineSet(self, attrib):
		self.shape.type = "indexed line set"
		self.shape.indices = [int(x) for x in attrib['coordIndex'].replace(',', ' ').split()]
		# TODO: colorIndex

	def startLineSet(self, attrib):
		self.shape.type = "line set"
		self.shape.vertexCounts = [int(x) for x in attrib['vertexCount'].replace(',', ' ').split()]

	def startPointSet(self, attrib):
		self.shape.type = "point set"

	def startCylinder(self, attrib):
		self.shape.type = "cylinder"
		# TODO: check bottom and top cap attributes
		# and if true, emit corresponding Disk2D
		try:
			radius = float(attrib['radius'])
		except KeyError:
			radius = 1.0
		try:
			height = float(attrib['height'])
		except KeyError:
			height = 2.0
		top = self.xforms[-1][0]
		p0 = dot(top, array([0, -height / 2, 0, 1]))
		p1 = dot(top, array([0, height / 2, 0, 1]))
		xf = translation(array([(p0[0] + p1[0]) / 2,
				(p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2]));
		delta = array([p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]])
		cylAxis = array([0, 1, 0])
		axis = cross(cylAxis, delta)
		if dot(axis, axis) == 0:
			axis = [1, 0, 0]
			angle = pi
		else:
			cosine = dot(cylAxis, delta) / height
			angle = acos(cosine)
		r = rotation(axis, angle)
		xf = dot(xf, r)
		self.shape.data = ['c', radius, height,
			[[xf[0][0], xf[0][1], xf[0][2], xf[0][3]],
			 [xf[1][0], xf[1][1], xf[1][2], xf[1][3]],
			 [xf[2][0], xf[2][1], xf[2][2], xf[2][3]]
			]]

	def startSphere(self, attrib):
		self.shape.type = "sphere"
		try:
			radius = float(attrib['radius'])
		except KeyError:
			radius = 1
		self.shape.data = ['s', radius, self.xforms[-1][0]]
		#top = self.xforms[-1][0]
		#x, y, z, w = dot(top, [0, 0, 0, 1])
		#self.shape.data = ['s', radius, [x, y, z]]

	def startBox(self, attrib):
		# TODO: output a box primitive
		# don't have flat shading so use separate triangles
		self.shape.type = "triangles"
		x, y, z = [0.5 * float(s) for s in attrib['size'].split()]
		box = [[-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z],
			[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z]]
		top = self.xforms[-1][0]
		for i in range(len(box)):
			x, y, z = box[i]
			x, y, z, w = dot(top, [x, y, z, 1])
			box[i] = [x, y, z]
		indices = [0, 1, 2, 0, 2, 3,
				1, 5, 6, 1, 6, 2,
				5, 4, 7, 5, 7, 6,
				4, 0, 3, 4, 3, 7,
				4, 5, 1, 4, 1, 0,
				3, 2, 6, 2, 6, 7]
		coords = []
		for i in indices:
			coords.extend(box[i])
		self.shape.coords = coords


	def startCone(self, attrib):
		pass

	def startDisk2D(self, attrib):
		pass

	def startCircle2D(self, attrib):
		pass

	def startDirectionalLight(self, attrib):
		try:
			ambient = float(attrib['ambientIntensity'])
		except KeyError:
			ambient = 0
		try:
			color = attrib['color']
			rgb = [float(x) for x in color.split()]
		except KeyError:
			rgb = [1, 1, 1]
		try:
			d = attrib['direction']
			direction = [float(x) for x in d.split()]
		except KeyError:
			direction = [0, 0, -1]
		try:
			global_ = attrib['global'].lower() == 'true'
		except KeyError:
			global_ = True
		try:
			intensity = float(attrib['intensity'])
		except KeyError:
			intensity = 0
		try:
			on = attrib['on'].lower() == 'true'
		except KeyError:
			on = True

		if not on:
			return

		if ambient != 0:
			# ambient light
			self.write_data(['la', ambient * rgb[0], ambient * rgb[1],
							ambient * rgb[2]])
		if intensity != 0:
			# directional
			self.write_data(['ld', intensity * rgb[0],
					intensity * rgb[1], intensity * rgb[2]]
				+ direction)

	def flushTriangleCache(self):
		for data in self.tcache.values():
			self.write_data(data)

	def addTriangleCache(self, data):
		t, coords, normals, colors, indices = data
		if t not in self.tcache:
			if len(colors) == 4:
				colors.extend(colors * (len(coords) / 3 - 1))
			self.tcache[t] = data
			return
		tct, tccoords, tcnormals, tccolors, tcindices = self.tcache[t]
		if ((indices is None and tcindices is not None)
		or (indices is not None and tcindices is None)
		or (t == 't' and len(coords) + len(tccoords) > 16384)
		or (t == 'ts' and len(coords) + len(tccoords) > 16382)):
			self.write_data(self.tcache[t])
			self.tcache[t] = data
			return
		if len(tccolors) == 4:
			tccolors.extend(tccolors * (len(tccoords) / 3 - 1))
		if len(colors) == 4:
			colors.extend(colors * (len(coords) / 3 - 1))
		addDegenerate = t == 'ts'
		if indices is None and addDegenerate:
			tccoords.extend(tccoords[-3:] + coords[:3])
			tcnormals.extend(tcnormals[-3:] + normals[:3])
			if len(tccolors) > 4:
				tccolors.extend(tccolors[-4:] + colors[:4])
		elif indices is not None:
			offset = len(tccoords) / 3
			if addDegenerate:
				tcindices.extend([tcindices[-1], indices[0] + offset])
			tcindices.extend([i + offset for i in indices])
		tccoords.extend(coords)
		tcnormals.extend(normals)
		tccolors.extend(colors)


class ColladaProcessor(Processor):
	"""convert x3d format file into Collada format file"""
	def __init__(self, name="_initial_view_"):
		self.identity = array(((1, 0, 0, 0),
						(0, 1, 0, 0),
						(0, 0, 1, 0),
						(0, 0, 0, 1)))
		self.mesh = Collada()
		self._id_cache = dict()
		self._material_cache = dict()
		self._sphere_cache = dict()
		self._cylinder_cache = dict()
		self.material_node = self._get_material_node("default_material",
								(1, 1, 1, 1))
		self.reset(name)

	def next_id(self, key):
		n = self._id_cache.get(key, 0)
		self._id_cache[key] = n + 1
		return "%s_%s" % (key, n)

	def reset(self, name=None):
		if name:
			self.scene_name = name
		Processor.__init__(self)
		self.lights = list()
		self.nodes = list()

	def write_data(self, value):
		f = getattr(self, "_write_%s" % value[0], None)
		if f is None:
			import sys
			print >> sys.stderr, "unsupported value type: %s" % value[0]
		else:
			f(*value[1:])

	def _write_bg(self, r, g, b):
		# Background
		# Currently unused
		pass

	def _write_cofr(self, x, y, z):
		# Center of rotation
		# Currently unused
		pass

	def _write_eyepos(self, x, y, z):
		# Eye position
		# Handled as part of camera later
		pass

	def _write_up(self, x, y, z):
		# Camera up vector
		# Handled as part of camera later
		pass

	def _write_persp(self, fov):
		# Perspective camera
		# Handled as part of camera later
		pass

	def _write_ortho(self, llx, lly, urx, ury):
		# Orthographic camera
		# Handled as part of camera later
		pass

	def _write_t(self, coords, normals, colors, indices):
		# Triangles
		# "colors" should be a list whose length is a
		# multiple of 4 (RGBA).  We only need to worry
		# splitting up into multiple triangle lists if
		# there is more than one color.
		vertex_name = self.next_id("vertex")
		vertex_src = source.FloatSource(vertex_name,
						array(coords),
						('X', 'Y', 'Z'))
		normal_name = self.next_id("normal")
		normal_src = source.FloatSource(normal_name,
						array(normals),
						('X', 'Y', 'Z'))
		sources = [ vertex_src, normal_src ]
		if colors[0] is None or len(colors) == 4:
			# Zero or one (RGBA) color
			color_name = None
		else:
			color_name = self.next_id("rgba")
			color_src = source.FloatSource(color_name,
						array(colors),
						('R', 'G', 'B', 'A'))
			sources.append(color_src)
		g = geometry.Geometry(self.mesh, self.next_id("geometry"),
					self.next_id("triangles"), sources)
		self.mesh.geometries.append(g)
		input_list = source.InputList()
		input_list.addInput(0, "VERTEX", '#' + vertex_name)
		input_list.addInput(1, "NORMAL", '#' + normal_name)
		if color_name:
			input_list.addInput(2, "COLOR", '#' + color_name)
		else:
			if len(colors) == 4:
				mat_name = self.next_id("matsym")
				mat_node = self._get_material_node(mat_name, colors)
			else:
				mat_name = "default_material"
				mat_node = self.material_node

		# Alpha is handled quite differently than RGB by Preview
		# on the Mac, so we split the triangle list by alpha
		geom_nodes = list()
		if not color_name:
			ind = dstack((indices, indices))
			tset = g.createTriangleSet(ind, input_list, mat_name)
			g.primitives.append(tset)
			self.mesh.geometries.append(g)
			geom_nodes.append(scene.GeometryNode(g, [mat_node]))
		else:
			if indices is None:
				# coordinates and colors used as sets of threes
				indices = range(int(len(coords) / 3))
			by_alpha = dict()
			for i in range(0, len(indices), 3):
				a = colors[indices[i] * 4 + 3]
				try:
					tl = by_alpha[a]
				except KeyError:
					tl = list()
					by_alpha[a] = tl
				tl.append(indices[i])
				tl.append(indices[i + 1])
				tl.append(indices[i + 2])
			for a, tl in by_alpha.iteritems():
				ind = dstack((tl, tl, tl))
				mat_name = self.next_id("matsym")
				mat_node = self._get_material_node(mat_name,
									(1, 1, 1, 1),
									transparency=a)
				tset = g.createTriangleSet(ind, input_list, mat_name)
				g.primitives.append(tset)
				geom_nodes.append(scene.GeometryNode(g, [mat_node]))

		self.nodes.append(scene.Node(id=self.next_id("subnode"),
						children=geom_nodes, transforms=[]))

	def _write_ts(self, coords, normals, colors, indices):
		# Triangle strip
		# We convert to triangles and use code above
		new_indices = list()
		flip = True
		for i in range(len(indices) - 2):
			i0, i1, i2 = indices[i:i+3]
			flip = not flip
			if i0 == i1 or i0 == i2 or i1 == i2:
				continue
			if flip:
				new_indices.append(i1)
				new_indices.append(i0)
				new_indices.append(i2)
			else:
				new_indices.append(i0)
				new_indices.append(i1)
				new_indices.append(i2)
		self._write_t(coords, normals, colors, new_indices)

	def _write_s(self, radius, matrix, color):
		n = max(int(radius * radius * 40), 100)
		g = self._get_sphere(n, color)
		mat = self._get_material(color)
		material_node = scene.MaterialNode(self.PRIMITIVE_COLOR, mat, inputs=[])
		geom_node = scene.GeometryNode(g, [material_node])
		sx = radius
		sy = radius
		sz = radius
		xform = [ matrix[0][0] * sx, matrix[0][1] * sx, matrix[0][2] * sx, matrix[0][3],
			matrix[1][0] * sy, matrix[1][1] * sy, matrix[1][2] * sy, matrix[1][3],
			matrix[2][0] * sz, matrix[2][1] * sz, matrix[2][2] * sz, matrix[2][3],
			0, 0, 0, 1 ]
		matrix_node = scene.MatrixTransform(array(xform))
		self.nodes.append(scene.Node(id=self.next_id("subnode"),
						children=[geom_node],
						transforms=[ matrix_node ]))

	def _write_c(self, radius, height, matrix, color):
		n = max(int(radius * 36), 36)
		g = self._get_cylinder(n, color)
		mat = self._get_material(color)
		material_node = scene.MaterialNode(self.PRIMITIVE_COLOR, mat, inputs=[])
		geom_node = scene.GeometryNode(g, [material_node])
		sx = radius
		sy = height / 2
		sz = radius
		xform = [ matrix[0][0] * sx, matrix[0][1] * sy, matrix[0][2] * sz, matrix[0][3],
			matrix[1][0] * sx, matrix[1][1] * sy, matrix[1][2] * sz, matrix[1][3],
			matrix[2][0] * sx, matrix[2][1] * sy, matrix[2][2] * sz, matrix[2][3],
			0, 0, 0, 1 ]
		matrix_node = scene.MatrixTransform(array(xform))
		self.nodes.append(scene.Node(id=self.next_id("subnode"),
						children=[geom_node],
						transforms=[ matrix_node ]))

#	# This code generates a lineset, but that does not seem to show in
#	# Preview on Mac
#	def _write_l(self, coords, rgba, lineProperties):
#		r = arange(len(coords) / 3, dtype=int)
#		ind = dstack((r, r))
#		vertices = array(coords)
#		colors = array(rgba)
#
#		vertex_name = self.next_id("vertex")
#		vertex_src = source.FloatSource(vertex_name, vertices, ('X', 'Y', 'Z'))
#		color_name = self.next_id("hack_color")
#		color_src = source.FloatSource(color_name, colors, ('R', 'G', 'B', 'A'))
#		sources = [ vertex_src, color_src ]
#
#		lid = self.next_id("line")
#		g = geometry.Geometry(self.mesh, lid, lid, sources)
#		self.mesh.geometries.append(g)
#
#		input_list = source.InputList()
#		input_list.addInput(0, "VERTEX", '#' + vertex_name)
#		input_list.addInput(1, "COLOR", '#' + color_name)
#		g.createLineSet(ind, input_list, self.PRIMITIVE_COLOR)
#
#		geom_node = scene.GeometryNode(g, [self.material_node])
#		self.nodes.append(scene.Node(id=self.next_id("subnode"),
#						children=[geom_node]))

	def _write_l(self, coords, rgba, lineProperties):
		for i in range(0, len(coords) // 3, 2):
			self._write_l_segment(coords, rgba, lineProperties, i, i + 1)

	def _write_l_segment(self, coords, rgba, lineProperties, i, j):
		Epsilon = 1e-5
		radius = 0.1 * lineProperties.get('linewidth', 1.0)
		y_axis = [0, 1, 0]
		n = i * 4		# RGBA = 4 per value
		color = rgba[n:n+4]
		i0 = i * 3		# XYZ = 3 per value
		i1 = j * 3
		dx = coords[i0 + 0] - coords[i1 + 0]
		dy = coords[i0 + 1] - coords[i1 + 1]
		dz = coords[i0 + 2] - coords[i1 + 2]
		height = sqrt(dx * dx + dy * dy + dz * dz)
		if height < Epsilon:
			# Too short, just ignore
			return
		v = [ dx / height, dy / height, dz / height ]
		cos_theta = dot(y_axis, v)
		if cos_theta > (1 - Epsilon):
			matrix = [
				[ 1, 0, 0, 0 ],
				[ 0, 1, 0, 0 ],
				[ 0, 0, 1, 0 ],
			]
		else:
			theta = acos(cos_theta)
			axis = cross(y_axis, v)
			matrix = rotation(axis, theta)
		MaxSegLength = 1.0
		GapSegRatio = 1.5		# ((gap + seg) / seg) ratio
		SegPlusGap = MaxSegLength * GapSegRatio
		solid = lineProperties.get('linetype') == '1'
		if solid:
			nSeg = 1
		else:
			nSeg = max(2, int((height - MaxSegLength) / SegPlusGap))
		segLength = height / (1 + (nSeg - 1) * GapSegRatio)
		segGapLength = segLength * GapSegRatio
		radius = min(radius, segLength / 10.0)
		dv = list()
		sv = list()
		sgv = list()
		for j in range(3):
			d = segLength * v[j]
			dv.append(d)
			sv.append(coords[i1 + j] + d / 2)
			sgv.append(d * GapSegRatio)
		for i in range(nSeg):
			for j in range(3):
				matrix[j][3] = sv[j] + i * sgv[j]
			self._write_c(radius, segLength, matrix, color)

	def _write_il(self, coords, rgba, lineProperties, indices):
		prev_index = -1
		for i in indices:
			if i != -1 and prev_index != -1:
				self._write_l_segment(coords, rgba, lineProperties,
									prev_index, i)
			prev_index = i

	def _write_p(self, coords, rgba):
		matrix = [
			[ 1, 0, 0, 0 ],
			[ 0, 1, 0, 0 ],
			[ 0, 0, 1, 0 ],
		]
		for i in range(len(coords) // 3):
			n = i * 4		# RGBA = 4 per value
			color = rgba[n:n+4]
			i0 = i * 3		# XYZ = 3 per value
			matrix[0][3] = coords[i0 + 0]
			matrix[1][3] = coords[i0 + 1]
			matrix[2][3] = coords[i0 + 2]
			self._write_s(0.1, matrix, color)

	def _write_la(self, r, g, b):
		# Ambient light
		l = light.AmbientLight(self.next_id("light"), (r, g, b))
		self.mesh.lights.append(l)
		self.lights.append(scene.Node(id=self.next_id("light_node"),
						children=[ scene.LightNode(l) ]))

	def _write_ld(self, r, g, b, x, y, z):
		# Directional light
		ratio = 1.0
		l = light.DirectionalLight(self.next_id("light"),
						(r * ratio, g * ratio, b * ratio))
		self.mesh.lights.append(l)
		if x == 0 and z == 0:
			up = array((1, 0, 0))
		else:
			up = array((0, 1, 0))
		lookat = scene.LookAtTransform(array((0, 0, 0)),
						array((x, y, z)), up)
		self.lights.append(scene.Node(id=self.next_id("light_node"),
						children=[ scene.LightNode(l) ],
						transforms=[ lookat ]))
		return
		#
		# Add a second light in the opposite direction so that the
		# back side is (less brightly) lit.  Lighting will be slightly
		# different since there are more light sources, and perhaps
		# less efficient.
		#
		ratio = 0.3
		l = light.DirectionalLight(self.next_id("light"),
						(r * ratio, g * ratio, b * ratio))
		self.mesh.lights.append(l)
		lookat = scene.LookAtTransform(array((0, 0, 0)),
						array((-x, -y, -z)), up)
		self.lights.append(scene.Node(id=self.next_id("light_node"),
						children=[ scene.LightNode(l) ],
						transforms=[ lookat ]))

	def _write_vp(self, width, height, hither, yon):
		# Viewport
		# Currently unused
		pass

	def close(self):
		Processor.close(self)
		if self.camera_type == "ortho":
			mag = (self.fov[2] - self.fov[0]) / 2
			cam = camera.OrthographicCamera(self.next_id("camera"),
							self.hither,
							self.yon,
							xmag=mag,
							ymag=mag)
		else:
			if self.width < self.height:
				param = { 'yfov': degrees(self.fov) }
			else:
				param = { 'xfov': degrees(self.fov) }
			cam = camera.PerspectiveCamera(self.next_id("camera"),
							self.hither, self.yon, **param)
		self.mesh.cameras.append(cam)
		cam_node = scene.CameraNode(cam)
		lookat = scene.LookAtTransform(array(self.position),
						array(self.cofr),
						array((0, 1, 0)))
		nodes = [
			scene.Node(id=self.next_id("node"), children=[cam_node],
						transforms=[lookat]),
			scene.Node(id=self.next_id("node"), children=self.nodes)
		]

		# Make sure there is at least one directional light source
		# so that viewer will not add a default one
		for l in self.mesh.lights:
			if isinstance(l, light.DirectionalLight):
				break
		else:
			self._write_ld(0, 0, 0, 0, 0, 1)

		sc = scene.Scene(self.scene_name, self.lights + nodes)
		if self.mesh.scene is None:
			self.mesh.scene = sc
		self.mesh.scenes.append(sc)
		self.reset()

	def write_file(self, f):
		self.mesh.write(f)

	#
	# Methods for maintaining color, sphere and cylinder caches
	#
	def _get_material(self, color, transparency=1.0):
		key = tuple(color) + (transparency,)
		try:
			return self._material_cache[key]
		except KeyError:
			pass
		c = tuple(color)
		effect = material.Effect(self.next_id("effect"), [], "blinn",
						ambient=c,
						diffuse=c,
						transparent=c,
						specular=(1.0, 1.0, 1.0),
						transparency=transparency)
		mat_name = self.next_id("material")
		mat = material.Material(mat_name, mat_name, effect)
		self.mesh.effects.append(effect)
		self.mesh.materials.append(mat)
		self._material_cache[key] = mat
		return mat

	def _get_material_node(self, symbol, color, transparency=1.0):
		mat = self._get_material(color, transparency)
		return scene.MaterialNode(symbol, mat, inputs=[])

	PRIMITIVE_COLOR = "primitive_color"
	def _get_sphere(self, n, color):
		key = (n, tuple(color))
		try:
			return self._sphere_cache[key]
		except KeyError:
			pass
		# Compute the points and indices
		import spiral
		pts, phis = spiral.points(n)
		indices = spiral.triangles(n, phis)

		# Create the geometry object
		vertices = array(pts)
		vertex_name = self.next_id("vertex")
		vertex_src = source.FloatSource(vertex_name, vertices, ('X', 'Y', 'Z'))
		normal_name = self.next_id("normal")
		normal_src = source.FloatSource(normal_name, vertices, ('X', 'Y', 'Z'))

		# Due to the way transparency (does not) work in Preview,
		# we have to create a color array for the RGB and depend
		# on the caller to set up the transparency
		#sources = [ vertex_src, normal_src ]
		color_name = self.next_id("hack_color")
		color_src = source.FloatSource(color_name, array(color),
							('R', 'G', 'B', 'A'))
		sources = [ vertex_src, normal_src, color_src ]

		g = geometry.Geometry(self.mesh, self.next_id("geometry"),
							"sphere-%d" % n, sources)
		self.mesh.geometries.append(g)
		input_list = source.InputList()
		input_list.addInput(0, "VERTEX", '#' + vertex_name)
		input_list.addInput(1, "NORMAL", '#' + normal_name)

		# Due to the way transparency (does not) work in Preview,
		# we have to create a color array for the RGB and depend
		# on the caller to set up the transparency
		#ind = dstack((indices, indices))
		input_list.addInput(2, "COLOR", '#' + color_name)
		index_zero = zeros((len(indices), 3), dtype=int)
		ind = dstack((indices, indices, index_zero))

		tset = g.createTriangleSet(ind, input_list, self.PRIMITIVE_COLOR)
		g.primitives.append(tset)

		self._sphere_cache[key] = g
		return g

	def _get_cylinder(self, n, color):
		key = (n, tuple(color))
		try:
			return self._cylinder_cache[key]
		except KeyError:
			pass
		# Compute the points and indices
		pts, normals, indices = make_cylinder(n)

		# Create the geometry object.  Note that this is similar
		# to the sphere code above but has extra sections to create
		# then end caps.
		vertex_name = self.next_id("vertex")
		vertex_src = source.FloatSource(vertex_name, array(pts),
							('X', 'Y', 'Z'))
		normal_name = self.next_id("normal")
		normal_src = source.FloatSource(normal_name, array(normals),
							('X', 'Y', 'Z'))

		# Due to the way transparency (does not) work in Preview,
		# we have to create a color array for the RGB and depend
		# on the caller to set up the transparency
		#sources = [ vertex_src, normal_src ]
		color_name = self.next_id("hack_color")
		color_src = source.FloatSource(color_name, array(color),
							('R', 'G', 'B', 'A'))
		sources = [ vertex_src, normal_src, color_src ]

		g = geometry.Geometry(self.mesh, self.next_id("geometry"),
							"cylinder-%d" % n, sources)
		self.mesh.geometries.append(g)
		input_list = source.InputList()
		input_list.addInput(0, "VERTEX", '#' + vertex_name)
		input_list.addInput(1, "NORMAL", '#' + normal_name)

		# Due to the way transparency (does not) work in Preview,
		# we have to create a color array for the RGB and depend
		# on the caller to set up the transparency
		#ind = dstack((indices, indices))
		input_list.addInput(2, "COLOR", '#' + color_name)
		index_zero = zeros((len(indices), 3), dtype=int)
		ind = dstack((indices, indices, index_zero))

		tset = g.createTriangleSet(ind, input_list, self.PRIMITIVE_COLOR)
		g.primitives.append(tset)

		# Now we construct the end caps
		cap_indices = arange(0, n, dtype=int)
		shape = (len(cap_indices),)
		normal_indices = empty(shape, dtype=int)
		normal_indices.fill(2 * n)
		index_zero = zeros(shape, dtype=int)
		ind = dstack((cap_indices, normal_indices, index_zero))
		counts = [ n ]
		pset = g.createPolylist(ind, counts, input_list, self.PRIMITIVE_COLOR)
		g.primitives.append(pset)

		cap_indices = arange(n * 2 - 1, n - 1, -1, dtype=int)
		normal_indices.fill(2 * n + 1)
		ind = dstack((cap_indices, normal_indices, index_zero))
		pset = g.createPolylist(ind, counts, input_list, self.PRIMITIVE_COLOR)
		g.primitives.append(pset)
		return g

def make_cylinder(n):
	import numpy
	angles = numpy.linspace(0, pi * 2, n, False)
	cosines = numpy.cos(angles)
	sines = numpy.sin(angles)
	all_zeros = numpy.zeros((n,), dtype=float)
	all_ones = numpy.ones((n,), dtype=float)
	minus_ones = -all_ones
	top = numpy.dstack((cosines, minus_ones, sines))
	bottom = numpy.dstack((cosines, all_ones, sines))
	pts = numpy.concatenate((top, bottom), axis=1)
	half_normals = numpy.dstack((cosines, all_zeros, sines))
	# We append the cap normals at the end for use by caller
	caps = numpy.array([[ [0,-1,0], [0,1,0] ]], dtype=float)
	normals = numpy.concatenate((half_normals, half_normals, caps), axis=1)

	indices = list()
	def add(v0, v1, v2):
		indices.append((v0, v2, v1))
	for i in range(n - 1):
		add(i, i + n + 1, i + n)
		add(i, i + 1, i + n + 1)
	add(n - 1, n, n - 1 + n)
	add(n - 1, 0, n)
	# We only return the indices for the cylinder sides.
	# Caller has to construct the indices for the caps.
	return pts, normals, indices

def main():
	import getopt, sys
	try:
		opts, args = getopt.getopt(sys.argv[1:], "")
	except getopt.error:
		print >> sys.stderr, "usage: %s x3d-file(s)"
		raise SystemExit, 2
	for opt, val in opts:
		pass
	import xml.etree.cElementTree as ET
	for filename in args:
		input = open(filename, 'rU')
		p = ColladaProcessor("_initial_view_")
		ET.parse(input, parser=ET.XMLParser(target=p))
		p.write_file("collada.dae")

if __name__ == '__main__':
	main()
