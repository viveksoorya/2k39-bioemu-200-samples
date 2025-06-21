#ifndef Chimera_MoleculeLensModel_h
# define Chimera_MoleculeLensModel_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

# include <_chimera/Model.h>
# include <_chimera/LensModel.h>
// include Mol.h for Molecule.h
# include "Mol.h"
# include "ChainTrace.h"
# include "chimtypes.h"
# include "DrawLabels.h"		// use LabelGraphics
# include "DrawShapes.h"		// use Shapes

extern "C" {
typedef struct _object PyObject;
}

namespace molecule {

class PseudoBondGroup;

typedef std::vector<Point> Points;
typedef std::vector<Vector> Normals;
typedef std::vector<const Color *> Colors;


struct RingAromaticInfo
{
	Molecule::Atoms atoms;
	Real radius;
	const Color *color;
	Point center;
	Vector normal;
	RingAromaticInfo(): radius(0), color(0) {}
};

struct RingFillInfo
{
	Molecule::Atoms atoms;
	double radius;		// radius of cylinders
	const Color *single;	// non-NULL if single color
	Points tpoints;		// 3 points per triangle
	Normals tnormals;	// one normal per triangle
	Colors tcolors;		// one color per triangle
	bool translucent;
	RingFillInfo(): radius(0), single(0), translucent(false) {}
};

// TODO: investigate further how bond rotations screw up caching

class MoleculeLensModel: public LensModel
{
public:
	MoleculeLensModel(Lens *lens, Molecule *molecule);
	virtual void	draw(const LensViewer *viewer, LensViewer::DrawPass pass) const;
	virtual void	drawPick(const LensViewer *viewer) const;
	virtual void	drawPickLabels(const LensViewer *viewer) const;
	virtual void	invalidateCache();
	virtual void	invalidateLOD();
	virtual void	invalidateSelection();
	virtual void	x3dNeeds(/*INOUT*/ X3DScene *scene) const;
	virtual void	x3dWrite(std::ostream &out, unsigned indent,
					/*INOUT*/ X3DScene *scene) const;

	Molecule	*model() const;

	void		updateModel(Model *, const NotifierReason &);
	void		updateColorGroup(ColorGroup *, const NotifierReason &);
	void		updateColor(const Color *, const NotifierReason &);
	void		updateLOD(const NotifierReason &);
private:
	class ModelNotifier: public Notifier {
	public:
		void update(const void *tag, void *model,
					const NotifierReason &reason) const;
	};
	class ColorGroupNotifier: public Notifier {
	public:
		void update(const void *tag, void *cgInst,
					const NotifierReason &reason) const;
	};
	class ColorNotifier: public Notifier {
	public:
		void update(const void *tag, void *colorInst,
					const NotifierReason &reason) const;
		// No remove function because we use one instance for every
		// Color we want to be notified about.
	};
	class LODNotifier: public Notifier {
	public:
		void update(const void *tag, void *lodInst,
					const NotifierReason &reason) const;
	};

	virtual		~MoleculeLensModel();
	Molecule	*mol;
	mutable Shapes		atomDrawing;	// Spheres, cyl, wires, points
	mutable LabelGraphics	labelDrawing;
	mutable bool		dirty;
	mutable bool		dirtySelection;
	mutable ColorGroupSet	cgsUsed;
	ColorGroupNotifier	cgNotifier;
	mutable ColorSet	colorsUsed;
	mutable GLuint		lowResDL;
	mutable bool		vdwPointsShown;
	ColorNotifier	colorNotifier;
	ModelNotifier	modelNotifier;
	LODNotifier	lodNotifier;
	void		buildLowRes() const;
	void		buildGraphics(const LensViewer *lv) const;
	void		buildAtomGraphics() const;
	void		buildBondGraphics(std::set<Atom *> &chained,
					     std::set<Bond *> &shownBonds) const;
	void		addBondDrawing(Bond::DrawMode drawMode,
				       const chimera::Point &p1,
				       const chimera::Point &p2,
				       float radius, bool cap1, bool cap2,
				       const chimera::Color *color,
				       const chimera::Selectable *sel) const;
	void		buildAutoChainGraphics(std::set<Atom *> &chained) const;
	void		buildResidueLabelGraphics() const;
	void		buildRingGraphics(std::set<Bond *> &shownBonds) const;
	void		buildVDWPointGraphics() const;
	void		drawVDWPoints() const;
	void		monitorColor(const Color *color) const;
	void		unmonitorColors() const;
	void		computeRibbonGraphics(const LensViewer *lv) const;

	mutable bool	dirtyRings;
	void		buildRingGraphics() const;
	void		computeRingInfo(const std::set<Bond *> &shownBonds) const;

	mutable ChainTrace	*chain;
	typedef std::vector<RingAromaticInfo> AromaticInfo;
	mutable AromaticInfo aromaticInfo;
	typedef std::vector<RingFillInfo> FillInfo;
	mutable FillInfo fillInfo;
};

} // namespace molecule

# endif /* WrapPy */

#endif
