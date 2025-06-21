# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import numpy
from numpy import linalg
import math
import operator

import chimera
from CGLutil import vrml

#
# initialize and deinitialize are called before
# and after calls to displayHelices, displayStrands
# and displayTurns.  displayTurns should be called
# last because it uses data populated by the first
# two routines.
#
def initialize():
	global ssMap
	ssMap = {}

def deinitialize():
	global ssMap
	ssMap = {}

#
# Calculate orthonormal basis vectors via principal component analysis
#
def findAxes(resList, atomNames):
	coords = []
	for r in resList:
		for atomName in atomNames:
			a = r.findAtom(atomName)
			if a:
				c = a.coord()
				coords.append((c.x, c.y, c.z))
				break
	if len(coords) < 2:
		raise ValueError("no usable atoms found")
	coordinates = numpy.array(coords)
	if len(coords) >= 3:
		crds = coordinates
	else:
		# Assume there is at least 2 points
		x = (coords[0][0] + coords[1][0]) / 2
		y = (coords[0][1] + coords[1][1]) / 2
		z = (coords[0][2] + coords[1][2]) / 2
		coords.insert(1, (x, y, z))
		crds = numpy.array(coords)
	centroid = coordinates.mean(0)
	ignore, vals, vecs = linalg.svd(crds - centroid)
	axes = vecs.take(vals.argsort()[::-1], 1)

	if numpy.dot(numpy.cross(axes[0], axes[1]), axes[2]) < 0:
		# make right-handed
		axes[0] = -axes[0]
	# make sure that long axes (axes[0]) is pointing
	# from the first residue towards the last
	matrix = numpy.array([	[axes[0][0], axes[1][0], axes[2][0]],
				[axes[0][1], axes[1][1], axes[2][1]],
				[axes[0][2], axes[1][2], axes[2][2]] ])
	s, t, u = parametricVars(matrix, centroid, coordinates[0])
	if s > 0:
		# flip two axes to keep handedness
		axes[0] = -axes[0]
		axes[1] = -axes[1]

	return coordinates, centroid, axes

def _normalize(v):
	length = _length(v)
	for i in range(len(v)):
		v[i] = v[i] / length

def _cross(a, b):
	return numpy.array([
		a[1] * b[2] - a[2] * b[1],
		a[2] * b[0] - a[0] * b[2],
		a[0] * b[1] - a[1] * b[0] ])

def _subtract(a, b):
	return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]

def _length(v):
	return math.sqrt(numpy.dot(v, v))

#
# Chimera is very picky about its matrices
# 
# Routine below normalizes a 3x3 matrix to the acceptable tolerance
# 
def matrixNormalize(m):
	det = determinant(m)
	for i in range(3):
		for j in range(3):
			m[i][j] = m[i][j] / det

def determinant(mat):
	return mat[0][0] * _minor(mat, 1, 2, 1, 2) \
		- mat[0][1] * _minor(mat, 1, 2, 0, 2) \
		+ mat[0][2] * _minor(mat, 1, 2, 0, 1)

def _minor(mat, r0, r1, c0, c1):
	return mat[r0][c0] * mat[r1][c1] - mat[r1][c0] * mat[r0][c1]

#
# Compute the parametric variables from "base" to "c" using orthonormal
# bases of "axes"
#
def parametricVars(matrix, base, c):
	vector = c - base
	return linalg.solve(matrix, vector)

#
# Split a list of residues by finding the pair that has
# the most divergent axes
#
def splitResidues(residues, atomNames):
	for i in range(3, len(residues) - 3):
		front = residues[:i + 1]
		fcrd, fc, fa = findAxes(front, atomNames)
		back = residues[i:]
		bcrd, bc, ba = findAxes(back, atomNames)
		angle = numpy.dot(fa[0], ba[0])
		try:
			if angle < bestAngle:
				best = (front, back)
				bestAngle = angle
		except NameError:
			best = (front, back)
			bestAngle = angle
	try:
		return best
	except NameError:
		return [residues, []]

#
# Find helices and sheets in model
#
def _sameSSE(r, prev):
	if prev is None:
		return False
	if r.isHelix and prev.isHelix:
		# Both are helices
		if r.ssId != prev.ssId:
			return False
		return True
	if r.isSheet and prev.isSheet:
		# Both are strands
		if r.ssId != prev.ssId:
			return False
		return True
	if ((not r.isSheet and not r.isHelix) and
			(not prev.isSheet and not prev.isHelix)):
		# Both are turns
		return True
	return False

def _connected(r, prev):
	if prev is None:
		return False
	return chimera.bondsBetween(r, prev)

def findHelices(mol):
	helices = []
	helix = []
	prev = None
	for r in mol.residues:
		if not _sameSSE(r, prev) or not _connected(r, prev):
			# start of a new SSE
			if helix:
				helices.append(helix)
				helix = []
		if r.isHelix:
			helix.append(r)
		prev = r
	if helix:
		helices.append(helix)
	return helices

def findStrands(mol):
	strands = []
	strand = []
	prev = None
	for r in mol.residues:
		if not _sameSSE(r, prev) or not _connected(r, prev):
			# start of a new SSE
			if strand:
				strands.append(strand)
				strand = []
		if r.isSheet:
			strand.append(r)
		prev = r
	if strand:
		strands.append(strand)
	return strands

def findTurns(mol):
	# We actually include the previous and next residues
	# around the turn because we want the secondary structures
	# to connect when displayed
	turns = []
	turn = []
	prev = None
	for r in mol.residues:
		connected = _connected(r, prev)
		if not connected or not _sameSSE(r, prev):
			# Start of new SSE
			if turn:
				# Last SSE was a turn
				# Terminate it.
				# We need not start a new turn or
				# they would be the same SSE.
				if connected:
					# Add this residue if connected
					turn.append(r)
				if len(turn) > 1:
					turns.append(turn)
				turn = []
			elif not r.isSheet and not r.isHelix:
				# Last SSE was not a turn.
				# This SSE is a turn.
				# Insert previous residue if connected.
				if connected:
					turn.append(prev)
				turn.append(r)
			else:
				# Last SSE was not a turn.
				# This SSE is not a turn.
				# If these SSEs are connected, create
				# an empty turn so a connector gets created.
				if connected:
					turns.append([prev, r])
		else:
			# Extend turn if necessary
			if not r.isSheet and not r.isHelix:
				turn.append(r)
		prev = r
	if len(turn) > 1:
		turns.append(turn)
	return turns

#
# Create a VRML node representing a helix
#
def showHelix(helix, color, fixedRadius, radius, split, splitRatio,
		showArrow, edgeColor, ptsPerCircle):
	if len(helix) < 2:
		if helix:
			print "Skipping one-residue helix", helix[0]
		return []

	# Find cylinder axes, length and radius
	try:
		coords, centroid, axes = findAxes(helix, ['CA'])
	except ValueError:
		return []
	matrix = numpy.array([	[axes[0][0], axes[1][0], axes[2][0]],
				[axes[0][1], axes[1][1], axes[2][1]],
				[axes[0][2], axes[1][2], axes[2][2]] ])
	for c in coords:
		s, t, u = parametricVars(matrix, centroid, c)
		d = math.sqrt(t * t + u * u)
		try:
			minS = min(s, minS)
			maxS = max(s, maxS)
			minD = min(d, minD)
			maxD = max(d, maxD)
			sumD = sumD + d
		except NameError:
			minS = maxS = s
			minD = maxD = d
			sumD = d
	if split and maxD / minD > splitRatio:
		front, back = splitResidues(helix, ['CA'])
		if back:	# successful split
			return showHelix(front, color, fixedRadius, radius,
						split, splitRatio,
						showArrow, edgeColor,
						ptsPerCircle) \
				+ showHelix(back, color, fixedRadius, radius,
						split, splitRatio,
						showArrow, edgeColor,
						ptsPerCircle)
	if not fixedRadius:
		radius = max(sumD / len(coords), 0.25)
	axisLength = maxS + -minS
	halfLength = axisLength / 2
	center = (maxS + minS) / 2 * axes[0] + centroid
	s, t, u = parametricVars(matrix, center, coords[0])
	if maxS - s < s - minS:
		ssMap[helix[0]] = ( center + halfLength * axes[0],
					axes[0], axes[1], axes[2] )
		ssMap[helix[-1]] = ( center - halfLength * axes[0],
					-axes[0], axes[1], axes[2] )
	else:
		ssMap[helix[0]] = ( center - halfLength * axes[0],
					-axes[0], axes[1], axes[2] )
		ssMap[helix[-1]] = ( center + halfLength * axes[0],
					axes[0], axes[1], axes[2] )

	mat = [		# Note that the Y axis is mapped onto major axis
		[ -axes[1][0],	-axes[0][0],	axes[2][0]	],
		[ -axes[1][1],	-axes[0][1],	axes[2][1]	],
		[ -axes[1][2],	-axes[0][2],	axes[2][2]	]
	]
	matrixNormalize(mat)
	xf = chimera.Xform.xform(mat[0][0], mat[0][1], mat[0][2], 0,
				mat[1][0], mat[1][1], mat[1][2], 0,
				mat[2][0], mat[2][1], mat[2][2], 0)
	rotAxis, angle = xf.getRotation()
	angle = math.radians(angle)

	transform = vrml.Transform()
	trans = vrml.Transform(translation=(center[0], center[1], center[2]))
	transform.addChild(trans)
	rot = vrml.Transform(rotation=(rotAxis.x, rotAxis.y, rotAxis.z, angle))
	trans.addChild(rot)
	rgba = color.rgba()
	rgb = rgba[:3]
	alpha = rgba[3]
	floatPtsPerCircle = float(ptsPerCircle)
	if not showArrow:
		cylinder = vrml.Cylinder(radius=radius, height=axisLength,
					color=rgb, ambientIntensity=1)
		if alpha < 1.0:
			cylinder.transparency = 1.0 - alpha
		if edgeColor:
			topY = axisLength / 2
			bottomY = -topY
			top = list()
			bottom = list()
			for i in range(ptsPerCircle):
				radian = math.pi * 2 * (i / floatPtsPerCircle)
				x = radius * math.sin(radian)
				z = radius * math.cos(radian)
				top.append((x, topY, z))
				bottom.append((x, bottomY, z))
			top.append(top[0])
			bottom.append(bottom[0])
			rgb = edgeColor.rgba()[:3]
			lines = vrml.Lines(colorPerVertex=True)
			lines.addLine(top, rgb)
			lines.addLine(bottom, rgb)
			rot.addChild(lines)
		rot.addChild(cylinder)
	else:
		arrowLength = axisLength / 5
		arrowRadius = radius * 1.5
		cylinderLength = axisLength - arrowLength

		cylinderShift = -arrowLength / 2
		shift = vrml.Transform(translation=(0, cylinderShift, 0))
		rot.addChild(shift)
		cylinder = vrml.Cylinder(radius=radius,
						height=cylinderLength,
						color=rgb,
						ambientIntensity=1)
		if alpha < 1.0:
			cylinder.transparency = 1.0 - alpha
		shift.addChild(cylinder)

		arrowShift = axisLength / 2 - arrowLength / 2
		shift = vrml.Transform(translation=(0, arrowShift, 0))
		cone = vrml.Cone(bottomRadius=arrowRadius,
						height=arrowLength,
						color=rgb,
						ambientIntensity=1)
		if alpha < 1.0:
			cone.transparency = 1.0 - alpha
		shift.addChild(cone)
		if edgeColor:
			topY = axisLength / 2 - arrowLength
			bottomY = -axisLength / 2
			top = list()
			bottom = list()
			arrow = list()
			for i in range(ptsPerCircle):
				radian = math.pi * 2 * (i / floatPtsPerCircle)
				s = math.sin(radian)
				c = math.cos(radian)
				x = radius * s
				z = radius * c
				top.append((x, topY, z))
				bottom.append((x, bottomY, z))
				arrow.append((arrowRadius * s, topY,
							arrowRadius * c))
			top.append(top[0])
			bottom.append(bottom[0])
			arrow.append(arrow[0])
			rgb = edgeColor.rgba()[:3]
			lines = vrml.Lines(colorPerVertex=True)
			lines.addLine(top, rgb)
			lines.addLine(bottom, rgb)
			lines.addLine(arrow, rgb)
			rot.addChild(lines)
		rot.addChild(shift)
	return [ transform ]

def displayHelices(mol, color, fixedRadius, radius, split, splitRatio,
			showArrow, edgeColor, ptsPerCircle=50):
	nodes = []
	for helix in findHelices(mol):
		c = color or helix[0].ribbonColor or helix[0].molecule.color
		helices = showHelix(helix, c, fixedRadius, radius,
					split, splitRatio,
					showArrow, edgeColor, ptsPerCircle)
		nodes = nodes + helices
	return nodes
#
# Create a VRML node representing a sheet
#
def showStrand(strand, color, fixedWidth, width, fixedThickness, thickness,
		split, splitRatio, showArrow, edgeColor):
	if len(strand) < 2:
		if strand:
			print "Skipping one-residue strand", strand[0]
		return []
	# Find box axes, length, width and thickness
	try:
		coords, centroid, axes = findAxes(strand, ['O', 'CA'])
	except ValueError:
		return []
	matrix = numpy.array([	[axes[0][0], axes[1][0], axes[2][0]],
				[axes[0][1], axes[1][1], axes[2][1]],
				[axes[0][2], axes[1][2], axes[2][2]] ])
	for i, c in enumerate(coords):
		s, t, u = parametricVars(matrix, centroid, c)
		t = math.fabs(t)
		u = math.fabs(u)
		try:
			minS = min(s, minS)
			maxS = max(s, maxS)
			sumT = sumT + t
			minU = min(u, minU)
			maxU = max(u, maxU)
			sumU = sumU + u
		except NameError:
			minS = maxS = s
			sumT = t
			minU = maxU = u
			sumU = u
	if split and maxU / minU > splitRatio:
		front, back = splitResidues(strand, ['O'])
		if back:	# successful split
			return showStrand(front, color, fixedWidth, width,
						fixedThickness, thickness,
						split, splitRatio,
						showArrow, edgeColor) \
				+ showStrand(back, color, fixedWidth, width,
						fixedThickness, thickness,
						split, splitRatio,
						showArrow, edgeColor)
	length = maxS + -minS
	center = (maxS + minS) / 2 * axes[0] + centroid
	if not fixedWidth:
		width = max(sumT / len(coords) * 2, 0.5)
	if not fixedThickness:
		thickness = max(sumU / len(coords) * 2, 0.25)
	hl = length / 2
	s, t, u = parametricVars(matrix, center, coords[0])
	if maxS - s > s - minS:
		ssMap[strand[0]] = ( center - hl * axes[0],
					-axes[0], axes[1], axes[2] )
		ssMap[strand[-1]] = ( center + hl * axes[0],
					axes[0], axes[1], axes[2] )
	else:
		ssMap[strand[0]] = ( center + hl * axes[0],
					axes[0], axes[1], axes[2] )
		ssMap[strand[-1]] = ( center - hl * axes[0],
					-axes[0], axes[1], axes[2] )

	mat = [		# Note that the X axis is mapped onto length axis
			# ... and Y is mapped onto width axis 
		[ axes[0][0],	axes[1][0],	axes[2][0]	],
		[ axes[0][1],	axes[1][1],	axes[2][1]	],
		[ axes[0][2],	axes[1][2],	axes[2][2]	]
	]
	matrixNormalize(mat)
	xf = chimera.Xform.xform(mat[0][0], mat[0][1], mat[0][2], 0,
				mat[1][0], mat[1][1], mat[1][2], 0,
				mat[2][0], mat[2][1], mat[2][2], 0)
	rotAxis, angle = xf.getRotation()
	angle = angle / 180.0 * math.pi

	transform = vrml.Transform()
	trans = vrml.Transform(
			translation=(center[0], center[1], center[2]))
	transform.addChild(trans)
	rot = vrml.Transform(
			rotation=(rotAxis.x, rotAxis.y, rotAxis.z, angle))
	trans.addChild(rot)
	rgba = color.rgba()
	rgb = rgba[:3]
	alpha = rgba[3]
	if not showArrow:
		box = vrml.Box(size=(length, width, thickness),
					color=rgb, ambientIntensity=1)
		if alpha < 1.0:
			box.transparency = 1.0 - alpha
		if edgeColor:
			top = length / 2
			bottom = -length / 2
			left = -width / 2
			right = width / 2
			near = -thickness / 2
			far = thickness / 2
			tln = (top, left, near)
			trn = (top, right, near)
			bln = (bottom, left, near)
			brn = (bottom, right, near)
			tlf = (top, left, far)
			trf = (top, right, far)
			blf = (bottom, left, far)
			brf = (bottom, right, far)
			rgb = edgeColor.rgba()[:3]
			lines = vrml.Lines(colorPerVertex=True)
			lines.addLine([ tln, trn, brn, bln, tln ], rgb)
			lines.addLine([ tlf, trf, brf, blf, tlf ], rgb)
			lines.addLine([ tln, tlf ], rgb)
			lines.addLine([ trn, trf ], rgb)
			lines.addLine([ bln, blf ], rgb)
			lines.addLine([ brn, brf ], rgb)
			rot.addChild(lines)
		rot.addChild(box)
	else:
		arrowLength = length / 5
		boxLength = length - arrowLength

		boxShift = -arrowLength / 2
		shift = vrml.Transform(translation=(boxShift, 0, 0))
		box = vrml.Box(size=(boxLength, width, thickness),
					color=rgb, ambientIntensity=1)
		if alpha < 1.0:
			box.transparency = 1.0 - alpha
		shift.addChild(box)

		arrowTop = length / 2
		arrowBottom = arrowTop - arrowLength
		arrowLeft = -width / 2 * 1.5
		arrowRight = -arrowLeft
		near = -thickness / 2
		far = -near
		atn = (arrowTop, 0, near)
		aln = (arrowBottom, arrowLeft, near)
		arn = (arrowBottom, arrowRight, near)
		atf = (arrowTop, 0, far)
		alf = (arrowBottom, arrowLeft, far)
		arf = (arrowBottom, arrowRight, far)
		faces = vrml.Faces(solid=True)
		faces.addFace([ atn, aln, arn ], rgb)
		faces.addFace([ atf, arf, alf ], rgb)
		faces.addFace([ atn, arn, arf, atf ], rgb)
		faces.addFace([ atf, alf, aln, atn ], rgb)
		faces.addFace([ arn, aln, alf, arf ], rgb)
		if alpha < 1.0:
			faces.transparency = 1.0 - alpha
		rot.addChild(faces)
		if edgeColor:
			bottom = -length / 2
			left = -width / 2
			right = width / 2
			tln = (arrowBottom, left, near)
			trn = (arrowBottom, right, near)
			bln = (bottom, left, near)
			brn = (bottom, right, near)
			tlf = (arrowBottom, left, far)
			trf = (arrowBottom, right, far)
			blf = (bottom, left, far)
			brf = (bottom, right, far)
			rgb = edgeColor.rgba()[:3]
			lines = vrml.Lines(colorPerVertex=True)
			lines.addLine([ atn, aln, tln, bln,
					brn, trn, arn, atn], rgb)
			lines.addLine([ atf, alf, tlf, blf,
					brf, trf, arf, atf], rgb)
			lines.addLine([ atf, atn ], rgb)
			lines.addLine([ alf, aln ], rgb)
			lines.addLine([ arf, arn ], rgb)
			lines.addLine([ tlf, tln ], rgb)
			lines.addLine([ trf, trn ], rgb)
			lines.addLine([ blf, bln ], rgb)
			lines.addLine([ brf, brn ], rgb)
			rot.addChild(lines)
		rot.addChild(shift)
	return [ transform ]

def displayStrands(mol, color, fixedWidth, width, fixedThickness, thickness,
			split, splitRatio, showArrow, edgeColor):
	nodes = []
	for strand in findStrands(mol):
		c = color or strand[0].ribbonColor or strand[0].molecule.color
		nodes = nodes + showStrand(strand, c,
						fixedWidth, width,
						fixedThickness, thickness,
						split, splitRatio,
						showArrow, edgeColor)
	return nodes
#
# Create a VRML node representing a turn
#
def showTurn(turn, color, width, thickness, ptsPerSpline, edgeColor):
	from chimera import Xform, Point, Vector
	# Find coordinates associated with residues
	rList = list()
	ptMap = dict()
	for r in turn:
		for atomName in [ 'CA', 'P' ]:
			a = r.findAtom(atomName)
			if a:
				rList.append(r)
				ptMap[r] = a.coord()
				break
	if len(rList) < 2:
		return []
	# Create control points for our spline
	# First and last residue may be other secondary structure
	# elements that we need to connect with
	cpList = list()
	try:
		# Another SSE
		c, d, n, b = ssMap[rList[0]]
	except KeyError:
		# Not another SSE, must be at start of chain
		pt = ptMap[rList[0]]
		cpList.append(pt)
		cpList.append(pt)
	else:
		pt = chimera.Point(*c)
		dv = chimera.Vector(*d)
		cpList.append(pt - dv)
		cpList.append(pt)
		cpList.append(pt + dv)
	for r in rList[1:-1]:
		cpList.append(ptMap[r])
	try:
		# Another SSE
		c, d, n, b = ssMap[rList[-1]]
	except KeyError:
		# Not another SSE, must be at end of chain
		pt = ptMap[rList[-1]]
		cpList.append(pt)
		cpList.append(pt)
	else:
		pt = chimera.Point(*c)
		dv = chimera.Vector(*d)
		cpList.append(pt + dv)
		cpList.append(pt)
		cpList.append(pt - dv)
	# This will be the center of our extrusion
	coords = makeFromSpline(cpList, ptsPerSpline)

	rgba = color.rgba()
	if 1:
		# Extruded cross section
		xsection = [ [0.0, thickness], [width, 0.0],
				 [0.0, -thickness], [-width, 0.0] ]
		return extrude(coords, xsection, rgba[:3], rgba[3], edgeColor)
		#lines = vrml.Lines(colorPerVertex=True)
		#lines.addLine(cpList, (1, 1, 1))
		#return [ ext, lines ]
	else:
		# Lines
		lines = vrml.Lines(colorPerVertex=True)
		lines.addLine(coords, rgba[:3])
		#lines.addLine(cpList, (1, 1, 1))
		return [ lines ]

def makeFromSpline(cpList, ptsPerSpline):
	from chimera import Vector, GeometryVector, Spline
	#cList = [ cpList[0] ] + cpList + [ cpList[-1] ]
	cList = cpList
	coords = list()
	floatPtsPerSpline = float(ptsPerSpline)
	for i in range(len(cList) - 3):
		v0 = Vector(*cList[i])
		v1 = Vector(*cList[i+1])
		v2 = Vector(*cList[i+2])
		v3 = Vector(*cList[i+3])
		gv = GeometryVector(v0, v1, v2, v3)
		s = Spline(Spline.BSpline, gv)
		for n in range(ptsPerSpline):
			f = n / floatPtsPerSpline
			coords.append(s.coordinate(f))
	coords.append(s.coordinate(1.0))
	return coords

def extrude(coords, xsection, color, alpha, edgeColor):
	#
	# First we compute the cross sections at each coord,
	# then we convert the coordinates into (rectangular) faces.
	#

	from chimera import Vector, Xform
	# Vertices will be a list of lists
	# Each element of xsList is a cross section corresponding to a coord
	# Each cross section is a list of vertices corresponding to xs
	xsList = list()
	m = Xform.zAlign(coords[0], coords[1])
	m.invert()
	xs = [ m.apply(Vector(c[0], c[1], 0)) for c in xsection ]
	xsList.append([ (coords[0] + v) for v in xs ])
	pDir = coords[1] - coords[0]
	pDir.normalize()
	for i in range(1, len(coords)):
		ci = coords[i]
		nDir = ci - coords[i - 1]
		nDir.normalize()
		axis = chimera.cross(pDir, nDir)
		length = axis.length
		if length > 1e-5:
			# Non-zero.  If zero, no rotation is needed.
			angle = math.degrees(math.asin(length))
			axis.normalize()
			m = Xform.rotation(axis, angle)
			xs = [ m.apply(v) for v in xs ]
		xsList.append([ (v + ci) for v in xs ])
		pDir = nDir

	faces = vrml.Faces(solid=True)
	for i in range(len(coords) - 1):
		xsi = xsList[i]
		i1 = i + 1
		xsi1 = xsList[i + 1]
		for j in range(len(xs)):
			j1 = (j + 1) % len(xs)
			faces.addFace([ xsi[j], xsi1[j],
					xsi1[j1], xsi[j1] ], color)
	faces.addFace(xsList[0], color)
	faces.addFace(xsList[-1][::-1], color)
	if alpha < 1.0:
		faces.transparency = 1.0 - alpha
	vrmlNodes = list()
	if edgeColor:
		rgb = edgeColor.rgba()[:3]
		lines = vrml.Lines(colorPerVertex=True)
		lines.addLine(xsList[0], rgb)
		lines.addLine(xsList[-1], rgb)
		for j in range(len(xs)):
			lines.addLine([ xsi[j] for xsi in xsList ], rgb)
		vrmlNodes.append(lines)
	vrmlNodes.append(faces)
	return vrmlNodes

def displayTurns(mol, color, width, thickness, ptsPerSpline, edgeColor):
	nodes = []
	for turn in findTurns(mol):
		if color is not None:
			c = color
		else:
			# The first residue may be from the previous SSE, so
			# we look for the first residue that is a turn
			for r in turn:
				if not r.isHelix and not r.isSheet:
					tr = r
					break
			else:
				tr = turn[0]
			c = tr.ribbonColor or tr.molecule.color
		nodes = nodes + showTurn(turn, c, width, thickness,
						ptsPerSpline, edgeColor)
	return nodes

def makePandP(mol, helixColor=None, helixEdgeColor=None, helixArrow=True,
		helixFixedRadius=True, helixRadius=1.25,
		helixSplit=False, helixSplitRatio=2.5,
		strandColor=None, strandEdgeColor=None, strandArrow=True,
		strandFixedWidth=True, strandWidth=2.5,
		strandFixedThickness=True, strandThickness=1.0,
		strandSplit=False, strandSplitRatio=2.5,
		displayCoils=True, coilColor=None, coilEdgeColor=None,
		coilResolution=10, coilWidth=0.25, coilThickness=0.25):
	initialize()
	wrl = vrml.Transform()
	helices = displayHelices(mol, helixColor,
					helixFixedRadius,
					helixRadius,
					helixSplit,
					helixSplitRatio,
					helixArrow,
					helixEdgeColor)
	for node in helices:
		wrl.addChild(node)
	strands = displayStrands(mol, strandColor,
					strandFixedWidth,
					strandWidth,
					strandFixedThickness,
					strandThickness,
					strandSplit,
					strandSplitRatio,
					strandArrow,
					strandEdgeColor)
	for node in strands:
		wrl.addChild(node)
	if displayCoils:
		coils = displayTurns(mol, coilColor,
					coilWidth,
					coilThickness,
					coilResolution,
					coilEdgeColor)
		for node in coils:
			wrl.addChild(node)
	deinitialize()
	if not helices and not strands and not coils:
		replyobj.error('No helices, sheets, nor coils found')
		return None
	mList = chimera.openModels.open(vrml.vrml(wrl),
			type='VRML', sameAs=mol,
			identifyAs='%s - Pipes and Planks' % mol.name)
	return mList[0]
