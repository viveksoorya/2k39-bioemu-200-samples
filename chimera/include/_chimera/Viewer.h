#ifndef Chimera_Viewer_h
# define Chimera_Viewer_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "Array.h"
# include "Symbol.h"
# include "Geom3d.h"
# include "_chimera_config.h"
# include "Notifier.h"
# include "TrackChanges.h"

namespace chimera {

class Camera;
class Color;
class OpenModels;
class Model;

class CHIMERA_IMEX Viewer: public NotifierList, public otf::WrapPyObj
{
	// ABSTRACT
	Viewer(const Viewer&);			// disable
	Viewer& operator=(const Viewer&);	// disable
public:
	virtual void	windowSize(/*OUT*/ int *width, /*OUT*/ int *height) const = 0;
	virtual void	setWindowSize(int width, int height) = 0;
	// ATTRIBUTE: windowOrigin
	virtual void	windowOrigin(/*OUT*/ int *x, /*OUT*/ int *y) const = 0;
	// ATTRIBUTE: pixelScale
	virtual int	pixelScale() const { return 1; }
	void		graphicsPosition(int event_x, int event_y,
					 /*OUT*/ int *gx, /*OUT*/ int *gy) const;

# ifndef WrapPy
	virtual void	draw() const = 0;
	virtual void	makeGraphicsContextCurrent() const = 0;
# endif
	virtual void	postRedisplay() const = 0;
	virtual bool	hasGraphicsContext() const = 0;
	virtual void	setCursor(/*NULL_OK*/ const char *cursor) = 0;

	Color		*background() const;
	virtual void	setBackground(/*NULL_OK*/ Color *color);
	// ATTRIBUTE: selectionSet
	PyObject	*selectionSet() const;
	virtual void	invalidateSelectionCache() const;
	virtual void	invalidateCache() const;
	virtual void	invalidateCache(Model *m) const;
	virtual void	addModel(Model *m);
	virtual void	removeModel(Model *m);
	Camera		*camera() const;
	void		setCamera(Camera *camera);
# ifndef WrapPy
	Xform		cameraViewXform() const;	// For current view being drawn.
	void		setCameraViewXform(const Xform &) const;
#endif
	double		viewSize() const;
	void		setViewSize(double size);
	double		scaleFactor() const;
	void		setScaleFactor(double sf);
	// Set viewSize and scaleFactor together to avoid exceptions due
	// to changes that are extremely different from current values.
	void		setViewSizeAndScaleFactor(double size, double sf);

	// opengl shaders
	virtual bool	haveShaderSupport() const { return false; }
	virtual bool	haveShader() const { return false; }

	// near/far clip planes enabled
	bool		clipping() const;
	void		setClipping(bool c);
	void		adjustClipPlanes() const;

	void		checkInitialView();
	bool		didInitialView() const { return didInitialView_; }
	void		setDidInitialView(bool d) { didInitialView_ = d; }
	void		resetView();
	void		viewAll(bool resetCofrMethod = true);
	void		touch();

	virtual void	destroy();

# ifndef WrapPy
	virtual PyObject* wpyNew() const;

	struct CHIMERA_IMEX Reason: public NotifierReason {
		Reason(const char *r): NotifierReason(r) {}
	};
	// notification reasons
	static Reason	ATTR_CHANGE;
	static Reason	CLIPPING_CHANGE;
	static Reason	TOUCH;
	static Reason	NEW_SELECTION;

# endif

protected:
	Viewer();
	virtual ~Viewer();
	static TrackChanges::Changes *const
			changes;
	void		defaultCamera() const;
	mutable Camera	*cam;
	mutable Xform	cameraViewXform_;
	double		viewSize_;
	double		scaleFactor_;
	Color		*bg;
	PyObject	*selectionSet_;
	bool		clipping_;
	mutable bool	didInitialView_;

	virtual void	updateCamera(const NotifierReason &);
	class CHIMERA_IMEX CameraNotifier: public Notifier {
	public:
		void update(const void *tag, void *,
					const NotifierReason &reason) const;
	};
	friend class CameraNotifier;
	CameraNotifier	cameraNotifier;

	void		updateOpenModels(OpenModels *, const NotifierReason &);
	class CHIMERA_IMEX OpenModelsNotifier: public Notifier {
		void update(const void *tag, void *openModels,
					const NotifierReason &reason) const;
	};
	friend class OpenModelsNotifier;
	OpenModelsNotifier
			openModelsNotifier;
};

# ifndef WrapPy

template <class C> inline bool
selected(PyObject *attrs, C *inst)
{
	if (attrs == NULL)
		return false;
	PyObject *obj = inst->wpyGetObject(otf::PWC_DONT_CREATE);
	if (obj == NULL)
		return false;
	//bool inSelection = PyDict_GetItem(attrs, obj) != NULL;
	int result = PySequence_Contains(attrs, obj);
	bool inSelection = result == 1;
	if (result == -1)
		PyErr_Clear();
	Py_DECREF(obj);
	return inSelection;
}

inline PyObject *
Viewer::selectionSet() const
{
	if (selectionSet_ == NULL)
		Py_RETURN_NONE;
	Py_INCREF(selectionSet_);
	return selectionSet_;
}

inline double
Viewer::viewSize() const
{
	return viewSize_;
}

inline double
Viewer::scaleFactor() const
{
	return scaleFactor_;
}

inline Color *
Viewer::background() const
{
	return bg;
}

# endif /* WrapPy */

} // namespace chimera

#endif
