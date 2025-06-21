# Copyright (c) 2009 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: version.py.in 42529 2024-07-16 00:13:35Z gregc $

def compare(r0, r1):
	# compare two release number lists, e.g., [1, 3, 2600]
	if len(r0) < len(r1):
		diff = len(r1) - len(r0)
		r0 = r0[:-1] + diff * [0] + r0[-1:]
	elif len(r1) < len(r0):
		diff = len(r0) - len(r1)
		r1 = r1[:-1] + diff * [0] + r1[-1:]
	return cmp(r0, r1)

def newer(r0, r1):
	return compare(r0, r1) > 0

def sameVersion(r0, r1):
	# check two release number lists, but ignore build numbers
	if len(r0) < len(r1):
		diff = len(r1) - len(r0) - 1
		r0 = r0[:-1] + diff * [0]
		r1 = r1[:-1]
	elif len(r1) < len(r0):
		diff = len(r0) - len(r1) - 1
		r1 = r1[:-1] + diff * [0]
		r0 = r0[:-1]
	else:
		r0 = r0[:-1]
		r1 = r1[:-1]
	return r0 == r1

def expandVersion(ver):
	ver = ver.replace('_b', '.')
	return [int(i) for i in ver.split('.')]

def buildVersion(nums):
	return '%s (build %s)' % ('.'.join(str(i) for i in nums[:-1]), nums[-1])

def releaseVersion():
	# version for use in distribution file names and shortcuts
	# there should be no spaces in the return value
	build_type, _, release, _, _, date, _ = version.split(None, 6)
	if build_type == "production":
		return release
	if build_type == "candidate":
		return "%src" % release
	if build_type == "snapshot":
		return "%ss" % release
	return date

release = "1.19_b42556"		# change major.minor[.bugfix] part by hand
releaseNum = expandVersion(release)
version = "production version %s (build %s) 2025-03-06 07:54:28 UTC" \
						% tuple(release.rsplit('_b'))

if __name__ == "__main__":
	print "version:", version
	print "build version:", buildVersion(releaseNum)
