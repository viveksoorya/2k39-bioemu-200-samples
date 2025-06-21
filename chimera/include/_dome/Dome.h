#ifndef Chimera_Dome_h
# define Chimera_Dome_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <_chimera/_chimera_config.h>
# include <_chimera/Camera.h>
# include <_chimera/CameraMode.h>
# include "_dome_config.h"
# include <GfxInfo.h>

namespace dome {

#ifndef WrapPy

using chimera::Camera;
using chimera::CameraMode;
using chimera::CameraView;
using chimera::Viewer;

class _DOME_IMEX Dome: public CameraMode {
	CameraView	mono;
	mutable CameraView	current;
	mutable int	currentView;
	void		allocateFBO(const Viewer *viewer) const;
	void		reset(bool all) const;
	virtual bool	setup(const Viewer *viewer, int view) const;
	virtual void	printViews(/*OUT*/ std::vector<ViewLen> *views) const;
	virtual void	*initialize(const Viewer *viewer);
	virtual void	finalize(const Viewer *viewer, /*NULL_OK*/ void *closure);
	virtual bool	supportsPicking() const { return false; }
	int		numFaces() const;
	void		parallaxView() const;
	void		freeDisk() const;

	const bool	truncated;
	float		tilt, parallaxDegrees, tanParallax;
	mutable GLsizei	fbo_side;
	mutable GLuint	fbo, color_rb, depth_stencil_rb, stencil_rb;
	mutable GLuint	disk;
	mutable PyObject *cubeFace[6];
	mutable bool	printing;
	mutable bool	printedFace[6];
public:
			Dome(const char *name, bool truncated = false);
			~Dome();
	int		numViews() const;
	const CameraView *
			view(int view) const;
	void		computeViews(const Camera &camera);
	float		tiltAngle() const;
	void		setTiltAngle(float angle);
	float		parallaxAngle() const;	// For stereo camera view.
	void		setParallaxAngle(float angle);
};

#endif

_DOME_IMEX void addDomeCameraModes();
_DOME_IMEX float domeTiltAngle();
_DOME_IMEX void setDomeTiltAngle(float angle);
_DOME_IMEX float domeParallaxAngle();
_DOME_IMEX void setDomeParallaxAngle(float angle);

} // namespace dome

#endif

