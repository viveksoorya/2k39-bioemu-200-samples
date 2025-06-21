#ifndef Chimera_LensViewer_h
# define Chimera_LensViewer_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "Geom3d.h"
# include "Symbol.h"
# include <set>
# include <vector>
# include "_chimera_config.h"
# include "Viewer.h"
# include "Texture.h"
# include <GfxInfo.h>

extern "C" {
struct Togl;
}

namespace chimera {

class ScreenBox;
class GfxState;
class Lens;
class Selectable;
class Tile;
class Model;
class Light;

typedef std::vector<ScreenBox> ScreenBoxes;

class CHIMERA_IMEX LensViewer: public Viewer
{
	LensViewer(const LensViewer&);			// disable
	LensViewer& operator=(const LensViewer&);	// disable
public:
	LensViewer();
	~LensViewer();

	enum DrawPass {
		OpaqueSurfaces,	// draw opaque surfaces
		Labels,		// draw 3D positioned text labels
		LitLines,	// draw lit lines and points
		UnlitLines,	// draw unlit lines, points, and 2d labels
		Translucent1,	// draw back of translucent surface
		Translucent2,	// draw front of translucent surface, volumes
		Overlay2d,	// draw 2d overlay graphics
		LowRes,		// draw low-resolution version for sideview
		Selection,	// draw selectable geometry
		NumDrawPass
	};

	// selection highlighting methods
	enum Highlight { Outline, Fill };
	Highlight	highlight() const;
	void		setHighlight(Highlight h);
	Color		*highlightColor() const;
	void		setHighlightColor(/*NULL_OK*/ Color *color);

	bool		showSilhouette() const;
	void		setShowSilhouette(bool s);
	Color		*silhouetteColor() const;
	void		setSilhouetteColor(/*NULL_OK*/ Color *color);
	float		silhouetteWidth() const;
	void		setSilhouetteWidth(float w);
	bool		drawingSilhouette() const;
	bool		showShadows() const;
	void		setShowShadows(bool s);
	int		shadowTextureSize() const;
	void		setShadowTextureSize(int s);
	bool		singleLayerTransparency() const;
	void		setSingleLayerTransparency(bool s);
	bool		angleDependentTransparency() const;
	void		setAngleDependentTransparency(bool s);

	// background alternatives
	// solid background color is in Viewer base class
	enum BackgroundMethod { Solid, Gradient, Image };
	BackgroundMethod	backgroundMethod() const;
	void		setBackgroundMethod(BackgroundMethod method);
	void		backgroundGradient(/*OUT*/ Texture **texture1d,
				/*OUT*/ int *width,
				/*OUT*/ double *angle, /*OUT*/ double *offset);
	void		setBackgroundGradient(/*NULL_OK*/ Texture *texture1d,
				int width, double angle, double offset);
	enum Tiling { Stretched, Tiled, Zoomed, Centered };
	void		backgroundImage(/*OUT*/ Texture **texture2d,
				/*OUT*/ double *xscale, /*OUT*/ double *yscale,
				/*OUT*/ Tiling *tiling,
				/*OUT*/ double *angle, /*OUT*/ double *offset);
	void		setBackgroundImage(/*NULL_OK*/ Texture *texture2d,
				double xscale, double yscale, Tiling tiling,
				double angle, double offset);

	// label display
	bool		labelsOnTop() const;
	void		setLabelsOnTop(bool ontop);

	// associated lenses
	// ATTRIBUTE: backgroundLens
	Lens		*backgroundLens() const;
#if 0
	bool		lensBorder() const;
	void		setLensBorder(bool lb);
	Color		*lensBorderColor() const;
	void		setLensBorderColor(/*NULL_OK*/ Color *color);
	float		lensBorderWidth() const;
	void		setLensBorderWidth(float w);
#endif

	// depth-cueing
	bool		depthCue() const;
	void		setDepthCue(bool dc);
	Color		*depthCueColor() const;
	void		setDepthCueColor(/*NULL_OK*/ Color *color);
	void		depthCueRange(/*OUT*/ float *start, /*OUT*/ float *end);
	void		setDepthCueRange(float start, float end);

	// lighting
	// -- do not set directly, use Lighting package interface
	Light		*fillLight() const;
	void		setFillLight(/*NULL_OK*/ Light *l);
	Light		*keyLight() const;
	void		setKeyLight(/*NULL_OK*/ Light *l);
	Light		*backLight() const;
	void		setBackLight(/*NULL_OK*/ Light *l);
	double		ambient() const;
	void		setAmbient(double ambient);

	// opengl shaders
	bool		haveShaderSupport() const;
	enum ShaderType { NO_SHADER, STANDARD_SHADER, UNLIT_SHADER, PICK_SHADER,
			  INSTANCE_SHADER, INSTANCE_PICK_SHADER,
			  TEXTURE_1D_SHADER, TEXTURE_2D_SHADER, TEXTURE_3D_SHADER };
	unsigned int	pushShader(ShaderType t) const;
	unsigned int	popShader() const;
	bool		haveShader() const;

	// debugging
	bool		showBound() const;
	void		setShowBound(bool show);
	bool		showCofR() const;
	void		setShowCofR(bool show);

	// image support
	//	pilImages() is an internal interface -- do not use it!
	//	Use chimera.printer.saveImage() instead.
	PyObject	*pilImages(int width = 0, int height = 0,
				const char *printMode = NULL,
				int supersample = 0,
				bool opacity = false) const;
	// images need to use special rasterPos3 to work when tiling
#ifndef WrapPy
	void		rasterPos3(float x, float y, float z);
#endif
	void		rasterPos3(double x, double y, double z);

	// export support
	void		x3dWrite(const std::string &filename,
					const std::string& title = "",
					const std::string& version = "");
	void		x3dWrite(std::ostream &out, unsigned indent = 0,
					const std::string& title = "",
					const std::string& version = "");

	// gui support -- we assume that all Model's that can be affected
	//	by the gui are accessible through the background lens.
	void		recordPosition(long time, int x, int y, /*NULL_OK*/ const char *cursor);
	Xform		vsphere(long time, int x, int y, bool throttle = false);
	bool		startAutoSpin(long time, int x, int y);
	void		translateXY(int x, int y, bool throttle = false);
	void		translateZ(int x, int y, bool throttle = false);
	void		zoom(int x, int y, bool throttle = false);
	void		dragPick(int x, int y);
	void		pick(int x, int y,
			     /*OUT*/ std::vector<Selectable *> *objs);
	void		pickLabel(int x, int y, /*OUT*/ Selectable **objs);
	bool		enablePickFrameBuffer(bool enable);
	void		moveLabel(int x, int y, bool adjustZ, /*INOUT*/ Point *coord);
	void		delta(/*OUT*/ Real *dx, /*OUT*/ Real *dy, int x, int y, bool throttle = false);
	void		trackingXY(const char *mode, /*OUT*/ int *x, /*OUT*/ int *y);

	// per-model plane gui
	// WEAKREF: showPlaneModel
	bool		showPlaneModel() const;
	void		setShowPlaneModel(/*NULL_OK*/ Model *m, float opacity);

	// togl support
	void		createCB(PyObject *widget);
	void		destroyCB(PyObject *widget);
	void		reshapeCB(PyObject *widget);
	void		displayCB(PyObject *widget);
	void		updateCB(PyObject *widget);

	// for graphics benchmarking:
	//	0 -- use swapbuffers, 1 -- use glFlush, 2 -- use glFinish
	int		benchmarking() const;
	void		setBenchmarking(int i);

	// environment map support
	bool		envMap() const;
	void		setEnvMap(bool onoff);
	// ATTRIBUTE: envMapImage
	void		setEnvMapImages(PyObject *px, PyObject *nx,
					PyObject *py, PyObject *ny,
					PyObject *pz, PyObject *nz);

# ifndef WrapPy
	virtual void	draw() const;
	virtual void	postRedisplay() const;
	virtual void	invalidateSelectionCache() const;
	virtual void	invalidateCache() const;
	virtual void	invalidateCache(Model *m) const;
	virtual void	addModel(Model *m);
	virtual void	removeModel(Model *m);
	virtual void	windowSize(/*OUT*/ int *width, /*OUT*/ int *height) const;
	virtual void	setWindowSize(int width, int height);
	virtual void	windowOrigin(/*OUT*/ int *x, /*OUT*/ int *y) const;
	virtual int	pixelScale() const;
	virtual bool	hasGraphicsContext() const;
	virtual void	makeGraphicsContextCurrent() const;
	virtual void	setCursor(/*NULL_OK*/ const char *cursor);
	virtual void	notify(const NotifierReason &reason) const;

	void		drawBackground(const Array<int, 4> &vBox) const;
	Tile		*tile() const;

	virtual void	wpyAssociate(PyObject* o) const;
	virtual PyObject* wpyNew() const;

	void		pushFBO(GLuint fbo, int width, int height) const;
	void		popFBO() const;
	int		FBOcount() const;
# endif
	// use z-buffer support
	bool		saveZbuffer() const;
	void		setSaveZbuffer(bool s);
	void		parallax(/*OUT*/ float *negative, /*OUT*/ float *positive);
private:
	friend class GuardFBO;
	mutable Togl	*togl;
	GfxState	*state_;
	class GuardFBO	*pickFBO;

	Lens		*backgroundLens_;
	Highlight	highlight_;
	Color		*highlightColor_;
	bool		showSilhouette_;
	Color		*silhouetteColor_;
	float		silhouetteWidth_;
	mutable bool	drawingSilhouette_;
	bool		showShadows_;
	int		shadowTextureSize_;
	bool		singleLayerTransparency_;
	bool		angleDependentTransparency_;
#if 0
	bool		border;
	Color		*borderColor_;
	float		borderWidth_;
#endif

	bool		depthCue_;
	Color		*fog;
	float		startDepth_;
	float		endDepth_;
	static void	drawFog(const Array<double, 4> &rgba);

	void		enableDepthCueing() const;
	void		enableLights() const;

	void		pickObjects(int x, int y, bool labelsOnly,
				    std::vector<Selectable *> *objs);
	virtual void	setBackground(/*NULL_OK*/ Color *c);

	virtual void	updateCamera(const NotifierReason &);

	void		updateLens(Lens *lens, const NotifierReason &);
	class CHIMERA_IMEX LensNotifier: public Notifier {
	public:
		void update(const void *tag, void *lens,
					const NotifierReason &reason) const {
			LensViewer *lv = static_cast<LensViewer *>
						(const_cast<void *>(tag));
			Lens *l = static_cast<Lens *>(lens);
			lv->updateLens(l, reason);
		}
	};
	friend class LensNotifier;
	LensNotifier	lensNotifier;

	// opengl shader
	class Shader;
	struct ShaderCompare {
		bool operator()(const Shader *a, const Shader *b) const;
	};
	mutable std::set<Shader *, ShaderCompare> shaders;
	mutable std::vector<Shader *> shaderProgramStack;
	unsigned int	createShader(const char *vshader,
				     const char *fshader) const;
	void		deleteShader(unsigned int prog) const;
	Shader		*currentShader() const;
	void		activateShader() const;
	void		updateShader() const;
	Shader 		*shaderProgram(ShaderType t) const;

	// gui temporaries
	Real		vsphereCenter[2];
	Real		vsphereRadius;	// TODO: [2] for cheap stereo
	ScreenBoxes	*selectedLenses;
	enum Anchor { N, NE, E, SE, S, SW, W, NW, Center };
	Anchor		lensAnchor;
	Vector		spinAxis;
	Real		spinAngle;
	long		lastTime;
	int		lastX, lastY;
	bool		pickAreaVisible;
	int		pickX, pickY;
	void		drawPickArea() const;

	void		updateLOD(const NotifierReason &r);
	class CHIMERA_IMEX LODNotifier: public Notifier {
	public:
		void update(const void *tag, void *,
					const NotifierReason &reason) const {
			LensViewer *lv = static_cast<LensViewer *>
						(const_cast<void *>(tag));
			lv->updateLOD(reason);
		}
	};
	friend class LODNotifier;
	LODNotifier	lodNotifier;

	Model		*planeModel;
	float		planeModelOpacity;
	void		updatePlaneModel(const NotifierReason &r);
	class CHIMERA_IMEX PlaneModelNofifier: public Notifier {
	public:
		void update(const void *tag, void *,
					const NotifierReason &reason) const {
			LensViewer *lv = static_cast<LensViewer *>
						(const_cast<void *>(tag));
			lv->updatePlaneModel(reason);
		}
	};
	friend class PlaneModelNofifier;
	PlaneModelNofifier
			planeModelNotifier;

	bool		showBound_;
	bool		showCofR_;
	void		drawScreenBoxes(const Array<int, 4> &vBox,
				ScreenBoxes::iterator first,
				ScreenBoxes::iterator last) const;
	void		drawSilhouette(const Array<int, 4> &vBox,
				DrawPass dp,
				ScreenBoxes::iterator first,
				ScreenBoxes::iterator last) const;
	mutable Tile	*tile_;
	mutable	bool	skipLODNotification;
	class CHIMERA_IMEX WrapLODCall {
		const LensViewer *lv;
	public:
		WrapLODCall(const LensViewer *viewer): lv(viewer) {
			lv->skipLODNotification = true;
		}
		~WrapLODCall() {
			lv->skipLODNotification = false;
		}
	};
	friend class GuardLODNotification;


	Light		*fill;
	Light		*key;
	Light		*back;
	double		ambient_;
	void		updateLight(Light *light, const NotifierReason &);
	class CHIMERA_IMEX LightNofifier: public Notifier {
	public:
		void update(const void *tag, void *light,
					const NotifierReason &reason) const {
			LensViewer *lv = static_cast<LensViewer *>
						(const_cast<void *>(tag));
			Light *l = static_cast<Light *>(light);
			lv->updateLight(l, reason);
		}
	};
	friend class LightNofifier;
	LightNofifier	lightNotifier;

	int		benchmarking_;

	// The following are for the OSMesa windowing system, but are always
	// included so instances of this class are the same size regardless of
	// windowing system.
	int		myWidth;
	int		myHeight;
	unsigned char	*framebuffer;
	mutable bool	updatePending;

	struct FBOInfo {
		GLuint fbo;
		int width, height;
		FBOInfo(GLuint f, int w, int h): fbo(f), width(w), height(h) {}
	};
	mutable std::vector<FBOInfo> fboStack;

	// use z-buffer support
	bool		saveZbuffer_;
	float		*zbuffer;

	// environment map support
	bool		envMap_;
	GLuint		envMapImages;

	// shadow support
	mutable GLuint	shadowMap;		// texture id
	mutable GLuint	shadowMapFBO;		// framebuffer object
	mutable GLsizei	shadowMapSide;		// square shadow maps (for now)
	mutable GLint prevDrawBuffer;

	void		drawShadowsWithoutShader(const Array<int, 4> &vBox,
						 ScreenBoxes &bbls) const;
	void		computeShadowMap() const;
	void		bindShadowTexture() const;
	void		unbindShadowTexture() const;
	void		setShadowTextureMatrix() const;
	void		debugRenderShadowMap(const Array<int, 4> &vBox) const;
	void		setupLightView(/*OUT*/ Array<int, 4> *vp,
				/*OUT*/ Array<double, 16> *proj,
				/*OUT*/ Array<double, 16> *modelview) const;
	void		computeLightFrustum(const Xform &lightFrame,
				/*OUT*/ Array<double, 16> *proj) const;
	void		finishLightView(bool failure = false) const;

	// supersampled image saving
	mutable GLuint	tileFBO;		// tile framebuffer object

	// background support
	BackgroundMethod	backgroundMethod_;
	Texture		*bg_gradient_texture;
	int		bg_gradient_width;
	double		bg_gradient_angle, bg_gradient_offset;
	Texture		*bg_image_texture;
	Tiling		bg_image_tiling;
	double		bg_image_xscale, bg_image_yscale, bg_image_angle, bg_image_offset;
	void		updateTexture(Texture *t, const NotifierReason &);
	class CHIMERA_IMEX TextureNofifier: public Notifier {
	public:
		void update(const void *tag, void *texture,
					const NotifierReason &reason) const {
			LensViewer *lv = static_cast<LensViewer *>
						(const_cast<void *>(tag));
			Texture *l = static_cast<Texture *>(texture);
			lv->updateTexture(l, reason);
		}
	};
	friend class TextureNofifier;
	TextureNofifier	textureNotifier;
	bool		darkBackground() const;

	// label display
	bool labelsOnTop_;
};

# ifndef WrapPy

inline Lens *
LensViewer::backgroundLens() const
{
	return backgroundLens_;
}

#if 0
inline bool
LensViewer::lensBorder() const
{
	return border;
}

inline Color *
LensViewer::lensBorderColor() const
{
	return borderColor_;
}

inline float
LensViewer::lensBorderWidth() const
{
	return borderWidth_;
}
#endif

inline LensViewer::Highlight
LensViewer::highlight() const
{
	return highlight_;
}

inline Color *
LensViewer::highlightColor() const
{
	return highlightColor_;
}

inline bool
LensViewer::showSilhouette() const
{
	return showSilhouette_;
}

inline Color *
LensViewer::silhouetteColor() const
{
	return silhouetteColor_;
}

inline float
LensViewer::silhouetteWidth() const
{
	return silhouetteWidth_;
}

inline bool
LensViewer::drawingSilhouette() const
{
	return drawingSilhouette_;
}

inline bool
LensViewer::showShadows() const
{
	return showShadows_;
}

inline bool
LensViewer::singleLayerTransparency() const
{
	return singleLayerTransparency_;
}

inline bool
LensViewer::showBound() const
{
	return showBound_;
}

inline bool
LensViewer::showCofR() const
{
	return showCofR_;
}

inline Tile *
LensViewer::tile() const
{
	return tile_;
}

inline bool
LensViewer::depthCue() const
{
	return depthCue_;
}

inline Color *
LensViewer::depthCueColor() const
{
	return fog;
}

inline Light *
LensViewer::fillLight() const
{
	return fill;
}

inline Light *
LensViewer::keyLight() const
{
	return key;
}

inline Light *
LensViewer::backLight() const
{
	return back;
}

inline double
LensViewer::ambient() const
{
	return ambient_;
}

inline int
LensViewer::benchmarking() const
{
	return benchmarking_;
}

inline bool
LensViewer::saveZbuffer() const
{
	return saveZbuffer_;
}

inline bool
LensViewer::envMap() const
{
	return envMap_;
}

inline LensViewer::BackgroundMethod
LensViewer::backgroundMethod() const
{
	return backgroundMethod_;
}

inline void
LensViewer::backgroundGradient(/*OUT*/ Texture **texture1d,
	/*OUT*/ int *width, /*OUT*/ double *angle, /*OUT*/ double *offset)
{
	*texture1d = bg_gradient_texture;
	*width = bg_gradient_width;
	*angle = bg_gradient_angle;
	*offset = bg_gradient_offset;
}

inline void
LensViewer::backgroundImage(/*OUT*/ Texture **texture2d,
	/*OUT*/ double *xscale, /*OUT*/ double *yscale, /*OUT*/ Tiling *tiling,
	/*OUT*/ double *angle, /*OUT*/ double *offset)
{
	*texture2d = bg_image_texture;
	*xscale = bg_image_xscale;
	*yscale = bg_image_yscale;
	*tiling = bg_image_tiling;
	*angle = bg_image_angle;
	*offset = bg_image_offset;
}

inline int
LensViewer::FBOcount() const
{
	return fboStack.size();
}

# endif /* WrapPy */

} // namespace chimera

#endif
