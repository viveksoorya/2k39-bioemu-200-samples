#	Copyright 2004-2008 by the Regents of the University of California.
#	All rights reserved.  This software provided pursuant to a
#	license agreement containing restrictions on its disclosure,
#	duplication and use.  This notice must be embedded in or
#	attached to all copies, including partial copies, of the
#	software or any revisions or derivations thereof.
#
#	$Id: spiral.cpp 37382 2012-09-07 00:51:34Z goddard $

#
#   The spiral sphere points algorithm is from:
#
#	E. B. Saff and A. B. J. Kuijlaars, "Distributing Many Points on a
#	Sphere," The Mathematical Intelligencer, Vol. 19 (1997) No. 1, pp.
#	5-11.  It's on the web at
#	<http://www.math.vanderbilt.edu/~esaff/distmany.pdf>.
#
#   Algorithm from the paper:
#
#	"One cuts the global with N horizontal planes spaced 2 / (N - 1)
#	units apart, forming N circles of latitude on the sphere [the first
#	and last of these are degenerate circles (points) consisting of the
#	south and north poles].  Each latitude contains precisely one spiral
#	point.  To obtain the kth spiral point, one proceeds upward from the
#	(k - 1)st point (theta sub k - 1, phi sub k - 1) along a great
#	circle (meridian) to the next latitude and travels counterclockwise
#	along it for a fixed distance (independent of k) to arrive at the
#	kth point (theta sub k, phi sub k)."
#
#    Translation to Python by Conrad Huang, UCSF, conrad@cgl.ucsf.edu, 2013.
#
#    The triangle tesselation algorithm was written by Greg Couch, UCSF
#    Computer Graphics Lab, gregc@cgl.ucsf.edu, January 2004.
#
#    The source code was inspired by Joesph O'Rourke and Min Xu's code
#    for the textbook: "Computational Geometry in C", 1997.  Within that
#    code is an implementation of the recurrence relation given in Saff
#    and Kuijlaars.
#
#    Knud Thomsen modification is from:
#    http://groups.google.com/group/sci.math/browse_thread/thread/983105fb1ced42c/e803d9e3e9ba3d23#e803d9e3e9ba3d23
#
#    Anton Sherwood golden ration modification is available from:
#    http://www.bendwavy.org/pack/pack.htm
#    http://www.cgafaq.info/wiki/Evenly_Distributed_Points_On_Sphere
#

MIN_VERTICES = 8
MAX_VERTICES = 65536
MAX_TRIANGLES = 2 * MAX_VERTICES - 4
MAX_VERTEX_SPREAD = 447

from math import pi, sqrt, acos, sin, cos
two_pi = 2 * pi

def points(n):
	if n >= MAX_VERTICES:
		n = MAX_VERTICES - 1
	pts = n * [ None ]
	phis = n * [ None ]

	pts[0] = (0, 0, -1)
	phis[0] = 0

	step_factor = 3.6 / sqrt(n)
	scale_factor = 2.0 / (n - 1)

	prev_phi = 0
	for k in range(1, n - 1):
		cos_theta = -1 + k * scale_factor
		if cos_theta < -1:
			cos_theta = -1
		elif cos_theta > 1:
			cos_theta = 1
		#theta = acos(cos_theta)
		#sin_theta = sin(theta)
		sin_theta = sqrt(1 - cos_theta * cos_theta)
		phi = prev_phi + step_factor / sin_theta
		if phi > two_pi:
			phi -= two_pi
		prev_phi = phi

		pts[k] = (cos(phi) * sin_theta, sin(phi) * sin_theta, cos_theta)
		phis[k] = phi

	pts[n - 1] = (0, 0, 1)
	phis[n - 1] = 0

	return pts, phis

def angle_in_interval(query, start, stop):
	"return true if query angle is in (start, stop) angle interval"
	d0 = query - start
	if d0 < 0:
		d0 += two_pi
	d1 = stop - query
	if d1 < 0:
		d1 += two_pi
	return d0 <= pi and d1 <= pi

def angle_sdist(start, stop):
	"return signed angular distance counterclockwise from start to stop"
	d = stop - start
	if d < -pi:
		d += two_pi
	return d

def triangles(n, phis):
	num_triangles = 2 * n - 4
	tris = num_triangles * [ None ]
	if n < MIN_VERTICES:
		raise ValueError("too few vertices to triangulate")
	if n > MAX_VERTICES:
		raise ValueError("too many vertices to triangulate")

	def add(n, v0, v1, v2):
		tris[n] = (v0, v1, v2)
		#tris[n] = (v0, v2, v1)

	# south pole cap -- triangle fan
	t = 0
	prev_phi = phis[1]
	for k in range(2, n - 2):
		add(t, 0, k, k - 1)
		t += 1
		if angle_in_interval(prev_phi, phis[k], phis[k + 1] + pi / k):
			add(t, 0, 1, k)
			t += 1
			break
	# k is the last spiral point used

	# north pole cap -- triangle fan
	# Place these triangles at end of list, so triangles
	# are ordered from south to north pole
	t2 = num_triangles - 1
	j = n - 2
	prev_phi = phis[j]
	for j in range(j - 1, 1, -1):
		add(t2, j, j + 1, n - 1)
		t2 -= 1
		if angle_in_interval(prev_phi, phis[j - 1] - pi / (n - j), phis[j]):
			add(t2, j, n - 1, n - 2)
			t2 -= 1
			break
	# j - 1 is the end of unused spiral points

	# triangle strip around the middle
	# i and k are nearby longitudinally, and start out as
	# the unconnected longitudinal edge from the south pole cap,
	# and are updated to the next unconnected edge
	i = 1
	add(t, k, i, k + 1)
	k += 1
	t += 1
	while i < j and k < (n - 2):
		dist_kk = angle_sdist(phis[k], phis[k + 1])
		dist_ki = angle_sdist(phis[k], phis[i + 1])
		dist_ik = angle_sdist(phis[i], phis[k + 1])
		if dist_kk >= dist_ki:
			if dist_ik < dist_ki:
				add(t, i, i + 1, k)
				i += 1
				t += 1
				add(t, i, k + 1, k)
				k += 1
				t += 1
			else:
				add(t, i, i + 1, k)
				i += 1
				t += 1
		else:
			if dist_ki < dist_ik:
				add(t, i, i + 1, k)
				i += 1
				t += 1
				add(t, i, k + 1, k)
				k += 1
				t += 1
			else:
				add(t, i, k + 1, k)
				k += 1
				t += 1
	while i != j or k != (n - 2):
		k = n - 2
		add(t, i, i + 1, k)
		i += 1
		t += 1
	if t != t2 + 1:
		raise RuntimeError("point count mismatch")
	return tris
