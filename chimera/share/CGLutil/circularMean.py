# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $


def circularMean(angles, returnQuality=False):
	"""return the circular mean of the given angles, in degrees

	   If 'returnQuality' is True, also return a measure of how
	   good the circular mean is, in the range zero (bad) to one (good).
	"""

	from math import radians, sin, cos, atan2, sqrt, degrees
	radAngles = [radians(a) for a in angles]
	cosMean = sum([cos(ra) for ra in radAngles]) / len(radAngles)
	sinMean = sum([sin(ra) for ra in radAngles]) / len(radAngles)
	mean = degrees(atan2(sinMean, cosMean))
	if returnQuality:
		return mean, sqrt(cosMean * cosMean + sinMean * sinMean)
	return mean
