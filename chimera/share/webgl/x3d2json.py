import sys
from numpy import array, eye as identity, dot, cross, linalg
from math import sin, cos, tan, degrees, radians, sqrt, pi, acos, atan
import json

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

class JSON:
	"""output JSON version of chimera X3D output"""
	# Format:
	#
	# sphere:	's', radius, [x, y, z], [r, g, b, a]
	# cylinder:	'c', radius, height, mat4x3, [r, g, b, a]

	def __init__(self, output=sys.stdout):
		self.output = output
		# viewport default
		self.width = 500
		self.height = 500
		# background default
		self.bgcolor = (0, 0, 0)
		# projection defaults
		self.cofr = [0, 0, 0]
		self.fov = pi / 4
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
		print >> self.output, '['
		json.encoder.FLOAT_REPR = lambda x: repr(round(x, 3))
		self.encoder = json.JSONEncoder(ensure_ascii=False,
				separators=(',', ':'))

	def close(self):
		self.flushTriangleCache()
		self.writeline(['vp', self.width, self.height, self.hither, self.yon], last=True)
		print >> self.output, ']'
		json.encoder.FLOAT_REPR = repr

	def writeline(self, value, last=False):
		chunks = self.encoder.iterencode(value)
		for c in chunks:
			self.output.write(c)
		self.output.write('\n' if last else ',\n')
	
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
		self.writeline(['cofr'] + list(self.cofr))
		self.writeline(['eyepos'] + list(self.position))
		self.writeline(['up'] + [0, 1, 0]) # TODO: use self.orientation
		self.writeline(['ortho'] + self.fov)

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
		self.writeline(['cofr'] + list(self.cofr))
		self.writeline(['eyepos'] + list(self.position))
		self.writeline(['up'] + [0, 1, 0]) # TODO: use self.orientation
		if self.width < self.height:
			# convert horizontal fov to vertical
			self.fov = 2 * atan(tan(self.fov / 2) * self.height / self.width)
		self.writeline(['persp', degrees(self.fov)])

	def startBackground(self, attrib):
		try:
			color = attrib['skyColor']
		except KeyError:
			return
		self.bgcolor = [float(x) for x in color.split()]
		self.writeline(['bg'] + list(self.bgcolor))

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
			self.writeline(self.shape.data + [[r, g, b, a]])
			return
		if shape.type == "point set":
			self.writeline(['p', shape.coords, shape.colorsRGBA])
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
					shape.coords[i:i] = [shape.coords[i - 1]]
					shape.colorsRGBA[i:i] = [shape.colorsRGBA[i - 1]]
					c -= 1
					i += 2
			self.writeline(['l', shape.coords, shape.colorsRGBA])
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
			self.writeline(['il', shape.coords, shape.colorsRGBA, indices])
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
			self.shape.material = self.defines[attrib['USE']]

	def endAppearance(self):
		if self.shape.appearanceDef:
			self.defines[self.shape.appearanceDef] = self.shape.material

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
		# Replace strip terminations with degenerate triangles
		# so they can stay as one strip.  Always start new strip
		# on even index so culling handedness is maintained.
		i = 0
		while 1:
			try:
				i = indices.index(-1, i)
			except ValueError:
				break
			if i % 2 == 0:
				indices[i:i + 1] = indices[i - 1:i + 2: 2]
			else:
				indices[i:i + 1] = [indices[i - 1],
						indices[i - 1], indices[i + 1]]
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
		cosine = dot(cylAxis, delta) / height
		# use axis and cosine tests to avoid floating point errors
		if dot(axis, axis) > 0:
			angle = acos(cosine)
		else:
			axis = [1, 0, 0]
			if cosine < 0:
				angle = pi
			else:
				angle = 0
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
		top = self.xforms[-1][0]
		x, y, z, w = dot(top, [0, 0, 0, 1])
		self.shape.data = ['s', radius, [x, y, z]]

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
			self.writeline(['la', ambient * rgb[0], ambient * rgb[1],
							ambient * rgb[2]])
		if intensity != 0:
			# directional
			self.writeline(['ld', intensity * rgb[0],
					intensity * rgb[1], intensity * rgb[2]]
				+ direction)

	def flushTriangleCache(self):
		for data in self.tcache.values():
			self.writeline(data)

	def addTriangleCache(self, data):
		t, coords, normals, colors, indices = data
		if t not in self.tcache:
			if colors and len(colors) == 4:
				colors.extend(colors * (len(coords) / 3 - 1))
			self.tcache[t] = data
			return
		tct, tccoords, tcnormals, tccolors, tcindices = self.tcache[t]
		if ((indices is None and tcindices is not None)
		or (indices is not None and tcindices is None)
		or (t == 't' and len(coords) + len(tccoords) > 16384)
		or (t == 'ts' and len(coords) + len(tccoords) > 16382)):
			self.writeline(self.tcache[t])
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


def main():
	import getopt
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
		json = JSON(sys.stdout)
		ET.parse(input, parser=ET.XMLParser(target=json))

if __name__ == '__main__':
	main()
