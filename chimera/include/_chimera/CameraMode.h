#ifndef Chimera_CameraMode_h
# define Chimera_CameraMode_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include "_chimera_config.h"
# include "CameraView.h"
# include <memory>
# include <vector>

# ifndef WrapPy

# ifdef _WIN32
#  undef near
#  undef far
# endif

namespace chimera {

class Camera;
class Viewer;

class CHIMERA_IMEX CameraMode
{
	friend class Camera;
	friend class Tile;
	const char	*name_;
	mutable bool	didScissor;
protected:
	// Returns true if there is geometry to draw.
	virtual bool	setup(const Viewer *viewer, int view) const;
	CameraMode(const char *n): name_(n), didScissor(false) {}
public:
	virtual ~CameraMode() {}
	// Return name of camera mode.
	const char	*name() const { return name_; }
	// Called when starting to use camera mode.
	virtual void	*initialize(const Viewer *viewer);
	// Called when done with camera mode.
	virtual void	finalize(const Viewer *viewer, /*NULL_OK*/ void *closure);
	// Return number of OpenGL passes needed.
	virtual int	numViews() const = 0;
	// Get OpenGL (glOrtho/glFustrum, gluLookat, glViewport) parameters.
	virtual const CameraView *
			view(int view) const = 0;
	// Compute OpenGL parameters.
	virtual void	computeViews(const Camera &camera) = 0;
	// Returns true if there is geometry to draw.
	virtual bool	setupView(const Viewer *viewer, int view, bool ortho) const;
	// Return if background should be cleared (assumed true for view 0)
	virtual bool	needBackgroundClear(int view) const;
	// Return if camera mode is for printing only
	virtual bool	printOnly() const;
	typedef std::pair<int, int> ViewLen;
	// Return pairs of (view, number of views) for multiple images.
	// Usually post-combined for stereo pairs.
	virtual void	printViews(/*OUT*/ std::vector<ViewLen> *views) const;
	// Return if camera mode is a stereo mode
	virtual bool	stereoView() const;
	virtual bool	supportsPicking() const { return true; }
};

} // namespace chimera

# endif /* WrapPy */

#endif
