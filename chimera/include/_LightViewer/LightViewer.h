#ifndef LightViewer_h
# define LightViewer_h

# include <_chimera/_chimera.h>
# include <GfxInfo.h>
# include <vector>

extern "C" {
struct Togl;
}

#ifdef WrapPy
typedef float GLfloat;

namespace chimera {

class Light: public otf::WrapPyObj
{
	// ABSTRACT
};

class LensViewer: public otf::WrapPyObj
{
};

}
#endif

namespace _LightViewer {

class LightViewer: public otf::WrapPyObj
{
public:
			LightViewer(chimera::LensViewer *viewer);
			~LightViewer();
#ifndef WrapPy
	virtual PyObject *
			wpyNew() const;
#endif
	void		createCB(PyObject *widget);
	void		reshapeCB(PyObject *widget);
	void		displayCB(PyObject *widget);
	void		destroyCB(PyObject *widget);
	void		postRedisplay() const;
	enum Mode { All, Single, Shininess };
	Mode		mode() const;
	void		setMode(Mode m);
	chimera::Light	*selected() const;
	void		setSelected(/*NULL_OK*/chimera::Light *light);
	bool		dragStart(int x, int y);
	void		dragMotion(int x, int y);
	void		dragEnd();
	static const GLfloat	keyColor[4];
	static const GLfloat	fillColor[4];
	static const GLfloat	backColor[4];
#ifndef WrapPy
	static const GLfloat	sphereColor[4];
#endif
private:
	void		setupView() const;
	void		addLight(GLenum which,
					const chimera::DirectionalLight *light,
					const GLfloat diffuse[4],
					const GLfloat lightColor[4]) const;
	void		drawLight(const chimera::Light *light) const;
	void		drawReference() const;
	bool		pickLight(int x, int y);

	void		graphicsSize(int *width, int *height) const;
	int		pixelScale() const;
	void		graphicsPosition(int win_x, int win_y, int *gx, int *gy) const;
private:
	Togl			*togl;
	chimera::LensViewer	*viewer;
	Mode			mode_;
	chimera::DirectionalLight
				*selectedLight;
	int			lastX, lastY;
	int			width, height;
	float			vsphereR, vsphereX, vsphereY;
	float			lastR, lastWinR;
};

}

#endif
