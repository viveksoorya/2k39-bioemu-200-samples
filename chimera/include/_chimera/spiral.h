#ifndef Chimera_spiral_h
# define Chimera_spiral_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

//	Copyright 2004 by the Regents of the University of California.
//	All rights reserved.  This software provided pursuant to a
//	license agreement containing restrictions on its disclosure,
//	duplication and use.  This notice must be embedded in or
//	attached to all copies, including partial copies, of the
//	software or any revisions or derivations thereof.
//
//	$Id: spiral.h 37383 2012-09-07 00:51:36Z goddard $

# ifndef WrapPy

# include "_chimera_config.h"
# include <GfxInfo.h>

namespace chimera {

namespace spiral {

const unsigned int MIN_VERTICES	= 8;
const unsigned int MAX_VERTICES	= 65536;    // because index is unsigned short
const unsigned int MAX_TRIANGLES = (2 * MAX_VERTICES - 4);
const unsigned int MAX_VERTEX_SPREAD = 447;	// in a triangle along equator

typedef GLushort Index;

struct tri_info {
	Index v0, v1, v2;
};

struct pt_info {
	double x, y, z;
};

CHIMERA_IMEX extern void points(unsigned int N, pt_info *pts,
				double *phis, double *thetas);
CHIMERA_IMEX extern tri_info *triangles(unsigned int N, pt_info *pts,
					double *phis);
}

}

#endif /* ifndef WrapPy */

#endif
