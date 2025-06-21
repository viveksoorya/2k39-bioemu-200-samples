#ifndef Chimera_CameraView_h
# define Chimera_CameraView_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

namespace chimera {

// Don't need export CameraView because it has no methods
struct CameraView {
	double	eye[3];			// Eye position
	double	lookat[3];		// Lookat coordinate
	double	up[3];
	double	l, r, b, t, h, y, f;	// ortho/frustrum bounds
		// left, right, bottom, top, hither, yon, focal
		// l, r, b, t are at near clip plane.
		// hither, yon, focal are distance from eye.
		// Units are from model coordinates.

	int	llx, lly, urx, ury;	// Viewport bounds in pixels.
};

} // namespace chimera

# endif /* WrapPy */

#endif
