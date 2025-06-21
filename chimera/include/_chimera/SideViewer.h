#ifndef Chimera_SideViewer_h
# define Chimera_SideViewer_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "_chimera_config.h"
# include "Viewer.h"
# include <GfxInfo.h>

extern "C" {
struct Togl;
}

namespace chimera {

class GfxState;
class LensViewer;

class CHIMERA_IMEX SideViewer: public Viewer
{
	SideViewer(const SideViewer&);			// disable
	SideViewer& operator=(const SideViewer&);	// disable
public:
	SideViewer(LensViewer *followViewer);
	bool	lowRes() const;
	void	setLowRes(bool lr);
	bool	advancedUI() const;
	void	setAdvancedUI(bool adv);
#ifndef WrapPy
	virtual PyObject* wpyNew() const;

	virtual void	draw() const;
	virtual void	postRedisplay() const;
	virtual void	windowSize(int *width, int *height) const;
	virtual void	setWindowSize(int width, int height);
	virtual void	windowOrigin(int *x, int *y) const;
	virtual int	pixelScale() const;
	virtual bool	hasGraphicsContext() const;
	virtual void	makeGraphicsContextCurrent() const;
	virtual void	setCursor(const char *);
	void		updateViewer(LensViewer *, const NotifierReason &);
# endif

	// ATTRIBUTE: follow
	LensViewer	*follow() const;

	// gui control
	enum MousePos { OnNothing, OnEye, OnHither, OnYon, OnFocal,
       				OnLowFOV, OnHighFOV	};
	MousePos	over(int x, int y);
	void		moveEye(int x, int y, bool throttle = false);
	void		moveEyeDist(int x, int y, bool throttle = false);
	void		moveHither(int x, int y, bool throttle = false);
	void		moveYon(int x, int y, bool throttle = false);
	void		moveFocal(int x, int y, bool throttle = false);
	void		moveHighFOV(int x, int y, bool throttle = false);
	void		moveLowFOV(int x, int y, bool throttle = false);
	void		section(int x, int y, bool throttle = false);
	void		thickness(int x, int y, bool throttle = false);

	void		createCB(PyObject *widget);
	void		destroyCB(PyObject *widget);
	void		reshapeCB(PyObject *widget);
	void		displayCB(PyObject *widget);
private:
	LensViewer	*follow_;
	Togl		*togl;
	GfxState	*state_;
	bool		guiActive;		// true if doing gui
	mutable bool	needUpdate;

	class ViewerNotifier: public Notifier {
	public:
		void update(const void *tag, void *viewer,
					const NotifierReason &reason) const {
			SideViewer *sv = static_cast<SideViewer *>
						(const_cast<void *>(tag));
			LensViewer *lv = static_cast<LensViewer *>(viewer);
			sv->updateViewer(lv, reason);
		}
	};
	ViewerNotifier	viewerNotifier;

	static const int MouseDelta = 4;
	mutable float	halfwidth;
	struct ViewInfo {
		GLdouble	eyeX, eyeY;
		GLdouble	hyYmin, hyYmax;		// Hither/Yon Y min/max
	};
	mutable GLdouble	eyeX, eyeY;		// average of ViewInfo
	mutable int		eyeHalfWidth, eyeHalfHeight;
	mutable GLdouble	hitherX, yonX;
	mutable GLdouble	focalX;
	typedef std::vector<ViewInfo> ViewInfos;
	mutable ViewInfos	viewInfo;
	int		lastX, lastY;
	bool		lowRes_;
	bool		advancedUI_;
};

# ifndef WrapPy

inline bool
SideViewer::lowRes() const
{
	return lowRes_;
}

inline bool
SideViewer::advancedUI() const
{
	return advancedUI_;
}

inline bool
SideViewer::hasGraphicsContext() const
{
	return togl != NULL;
}

inline LensViewer *
SideViewer::follow() const
{
	return follow_;
}

# endif /* WrapPy */

} // namespace chimera

#endif
