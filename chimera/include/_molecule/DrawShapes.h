# ifndef molecule_DrawShapes_h
# define molecule_DrawShapes_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

#include <_chimera/Color.h>		// use Color
#include <_chimera/Geom3d.h>		// use Point
#include <_chimera/LensViewer.h>	// use LensViewer
#include <_chimera/Selectable.h>	// use Selectable
#include <_chimera/X3DScene.h>		// use X3DScene

namespace molecule {

class Extrusion;
class ObjectsVBO;
class ShapeObject;

class Shapes {
public:
	Shapes();
	virtual ~Shapes();

	void drawOpaque(const chimera::LensViewer *v);
	void drawTransparent(const chimera::LensViewer *v);
	void drawUnlitLines(const chimera::LensViewer *v);
	void drawPick(const chimera::LensViewer *v);
	void drawSelection(const chimera::LensViewer *v);
	void setSelection(PyObject *selDict);
	void setMaterial(const chimera::ColorGroup *m);

	void addSphere(const chimera::Point &center, float radius,
		       const chimera::Color *color,
		       const chimera::Selectable *sel);
	void addCylinder(const chimera::Point &p1, const chimera::Point &p2,
			 float radius, bool cap1, bool cap2,
			 const chimera::Color *color,
			 const chimera::Selectable *sel);
	void addDisc(const chimera::Point &center, float radius,
		     const chimera::Vector &normal, bool fill,
		     const chimera::Color *color,
		     const chimera::Selectable *sel);
	void addTriangles(float *vertices, int nv,
			  float *normals, float *colors,
			  unsigned int *triangles, int nt,
			  const chimera::Selectable *sel);
	void addExtrusion(Extrusion *e, // Ownership passes to Shapes object
			  const chimera::Color *color,
			  const chimera::Selectable *sel);
	void addLine(const chimera::Point &p1, const chimera::Point &p2,
		     const chimera::Color *color,
		     const chimera::Selectable *sel);
	void setLineWidth(float width);
	void setLineStipple(int pattern, int factor);
	void addSpring(const chimera::Point &p1, const chimera::Point &p2,
		       float radius, const chimera::Color *color,
		       const chimera::Selectable *sel);
	void addPoint(const chimera::Point &p, const chimera::Color *color,
		      const chimera::Selectable *sel);
	void setPointSize(float size);

	size_t elementCount() const;
	void levelOfDetailChanged();
	void clear();
	void x3dNeeds(chimera::X3DScene *scene) const;
	void x3dWrite(std::ostream &out, unsigned indent,
		      chimera::X3DScene *scene) const;

private:
	std::vector<ShapeObject *> objects;
	ObjectsVBO *trianglesVBO;
	ObjectsVBO *linesVBO;
	ObjectsVBO *pointsVBO;
	float lastLevelOfDetail;
	float line_width, point_size;
	int stipple_pattern, stipple_factor;
	std::vector<class ObjectInstances *> instances;
	const chimera::ColorGroup *material;

	bool buildGraphics();
	bool updateLevelOfDetail();
	bool limitMaximumInstanceElements();
	bool buildVBO();
	void buildInstances();
	void clearObjects();
	void clearVBO();
	void clearInstances();
	void x3dWriteSpheres(std::ostream &, unsigned indent,
			     chimera::X3DScene *) const;
	void x3dWriteCylinders(std::ostream &, unsigned indent,
			       chimera::X3DScene *) const;
	void x3dWriteDiscs(std::ostream &, unsigned indent,
			   chimera::X3DScene *) const;
	void x3dWriteTriangles(std::ostream &, unsigned indent,
			       chimera::X3DScene *) const;
	void x3dWriteExtrusions(std::ostream &, unsigned indent,
				chimera::X3DScene *) const;
	void x3dWriteLines(std::ostream &, unsigned indent,
			   chimera::X3DScene *) const;
	void x3dWriteSprings(std::ostream &, unsigned indent,
			     chimera::X3DScene *) const;
	void x3dWritePoints(std::ostream &, unsigned indent,
			    chimera::X3DScene *) const;
};

class Extrusion {
public:
	virtual ~Extrusion() {};
	typedef std::vector<std::pair<float,float> > OutlinePoints;
	virtual const OutlinePoints &outline() = 0;
	virtual const OutlinePoints &outline_normals() = 0;
	bool closed_outline, smooth_outline;
	virtual void path(float f,		// f ranges from 0 to 1.
			  chimera::Point *center,
			  chimera::Vector *xaxis, float *xscale,
			  chimera::Vector *yaxis, float *yscale) = 0;
	virtual int path_steps() = 0;
};

} // end namespace molecule

#endif
