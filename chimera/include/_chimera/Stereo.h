#ifndef Chimera_Stereo_h
# define Chimera_Stereo_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

# include "Camera.h"
# include "CameraMode.h"

namespace chimera {

class CHIMERA_IMEX Stereo: public CameraMode
{
protected:
	CameraView	left;
	CameraView	right;
	friend class StereoLeftEye;
	friend class StereoRightEye;
	friend class Lenticular;
	virtual bool	setup(const Viewer *viewer, int view) const;
	bool		switch_eyes;
public:
	Stereo(const char *n, bool reverse = false):
				CameraMode(n), switch_eyes(reverse) {}
	virtual void	*initialize(const Viewer *viewer);
	virtual void	finalize(const Viewer *viewer, void *closure);
	virtual int	numViews() const;
	virtual const CameraView *
			view(int view) const;
	virtual void	computeViews(const Camera &camera);
	virtual bool	stereoView() const { return true; }
};

class CHIMERA_IMEX StereoLeftEye: public CameraMode
{
public:
	StereoLeftEye(const char *n): CameraMode(n) {}
	virtual int	numViews() const;
	virtual const CameraView *
			view(int view) const;
	virtual void	computeViews(const Camera &camera);
	virtual bool	stereoView() const { return true; }
};

class CHIMERA_IMEX StereoRightEye: public CameraMode
{
public:
	StereoRightEye(const char *n): CameraMode(n) {}
	virtual int	numViews() const;
	virtual const CameraView *
			view(int view) const;
	virtual void	computeViews(const Camera &camera);
	virtual bool	stereoView() const { return true; }
};

class CHIMERA_IMEX StereoCrossEye: public CameraMode
{
	CameraView	left;
	CameraView	right;
public:
	StereoCrossEye(const char *n): CameraMode(n) {}
	virtual int	numViews() const;
	virtual const CameraView *
			view(int view) const;
	virtual void	computeViews(const Camera &camera);
	virtual bool	stereoView() const { return true; }
	virtual void	printViews(/*OUT*/ std::vector<ViewLen> *views) const;
};

class CHIMERA_IMEX StereoWallEye: public CameraMode
{
	CameraView	left;
	CameraView	right;
public:
	StereoWallEye(const char *n): CameraMode(n) {}
	virtual int	numViews() const;
	virtual const CameraView *
			view(int view) const;
	virtual void	computeViews(const Camera &camera);
	virtual bool	stereoView() const { return true; }
	virtual void	printViews(/*OUT*/ std::vector<ViewLen> *views) const;
};

class CHIMERA_IMEX StereoDTISideBySide: public CameraMode
{
	CameraView	left;
	CameraView	right;
public:
	StereoDTISideBySide(const char *n): CameraMode(n) {}
	virtual int	numViews() const;
	virtual const CameraView *
			view(int view) const;
	virtual void	computeViews(const Camera &camera);
	virtual bool	stereoView() const { return true; }
	virtual void	printViews(/*OUT*/ std::vector<ViewLen> *views) const;
};

class CHIMERA_IMEX StereoRowInterleaved: public Stereo
{
#ifdef CHIMERA_USE_STENCIL_BITMAP
	// abysmally slow on NVidia graphics cards and older ATI graphics cards
	mutable void	*mask;
#else
	mutable unsigned mask;
#endif
	mutable int	width, height;
	mutable unsigned int bit;
	virtual bool	setup(const Viewer *viewer, int view) const;
public:
	StereoRowInterleaved(const char *n, bool reverse = false);
	virtual ~StereoRowInterleaved();
	virtual void	*initialize(const Viewer *viewer);
	virtual void	finalize(const Viewer *viewer, void *closure);
	virtual bool	needBackgroundClear(int view) const;
	virtual void	printViews(/*OUT*/ std::vector<ViewLen> *views) const;
};

class CHIMERA_IMEX StereoAnaglyph: public Stereo
{
	virtual bool	setup(const Viewer *viewer, int view) const;
public:
	StereoAnaglyph(const char *n): Stereo(n) {}
	virtual void	*initialize(const Viewer *viewer);
	virtual void	finalize(const Viewer *viewer, void *closure);
	virtual void	printViews(/*OUT*/ std::vector<ViewLen> *views) const;
};

class CHIMERA_IMEX StereoTrioscopic: public StereoAnaglyph
{
	virtual bool	setup(const Viewer *viewer, int view) const;
public:
	StereoTrioscopic(const char *n): StereoAnaglyph(n) {}
};

class CHIMERA_IMEX Lenticular: public CameraMode
{
	int		num_images;
	typedef std::vector<CameraView> CamViews;
	CamViews	inbetween;
public:
	Lenticular(const char *n);
	virtual int	numViews() const;
	virtual const CameraView *
			view(int view) const;
	virtual void	computeViews(const Camera &camera);
	virtual bool	printOnly() const;
	virtual bool	stereoView() const { return true; }
	void		setNumImages(int ni);
};

class CHIMERA_IMEX StereoPair: public Stereo
{
	// same as Stereo, but draw both eyes into same buffer --
	// so for printing only
	virtual bool	setup(const Viewer *viewer, int view) const;
public:
	StereoPair(const char *n): Stereo(n) {}
	virtual void	*initialize(const Viewer *viewer);
	virtual void	finalize(const Viewer *viewer, void *closure);
	virtual bool	printOnly() const;
};

CHIMERA_IMEX extern Stereo stereo;
CHIMERA_IMEX extern Stereo reverse_stereo;
CHIMERA_IMEX extern StereoLeftEye stereoLeftEye;
CHIMERA_IMEX extern StereoRightEye stereoRightEye;
CHIMERA_IMEX extern StereoCrossEye stereoCrossEye;
CHIMERA_IMEX extern StereoWallEye stereoWallEye;
CHIMERA_IMEX extern StereoDTISideBySide stereoDTISideBySide;
CHIMERA_IMEX extern StereoRowInterleaved stereoRowInterleavedOdd;
CHIMERA_IMEX extern StereoRowInterleaved stereoRowInterleavedEven;
CHIMERA_IMEX extern StereoAnaglyph stereoAnaglyph;
CHIMERA_IMEX extern StereoTrioscopic stereoTrioscopic;
CHIMERA_IMEX extern Lenticular lenticular;
CHIMERA_IMEX extern StereoPair stereoPair;
CHIMERA_IMEX extern StereoPair wallEyeStereoPair;

} // namespace chimera

# endif /* WrapPy */

#endif
