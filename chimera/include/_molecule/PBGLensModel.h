#ifndef Chimera_PBGLensModel_h
# define Chimera_PBGLensModel_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

# include <_chimera/Model.h>
# include <_chimera/LensModel.h>
# include "DrawLabels.h"		// use LabelGraphics
# include "DrawShapes.h"		// use Shapes
# include "Mol.h"

extern "C" {
typedef struct _object PyObject;
}

namespace molecule {

class PseudoBondGroup;

class PBGLensModel: public LensModel {
public:
	PBGLensModel(Lens *lens, PseudoBondGroup *pgp);
	virtual void	draw(const LensViewer *viewer, LensViewer::DrawPass pass) const;
	virtual void	drawPick(const LensViewer *viewer) const;
	virtual void	drawPickLabels(const LensViewer *viewer) const;
	virtual bool	drawLast() const { return true; }
	virtual bool	validXform() const;
	virtual void	invalidateCache();
	virtual void	invalidateSelection();
	virtual void	invalidateLOD();
	virtual void	x3dNeeds(/*INOUT*/ X3DScene *scene) const;
	virtual void	x3dWrite(std::ostream &out, unsigned indent,
					/*INOUT*/ X3DScene *scene) const;

	PseudoBondGroup	*model() const;

	void		updateColor(const Color *, const NotifierReason &);
	void		updateColorGroup(ColorGroup *, const NotifierReason &);
	void		updatePBG(const NotifierReason &);
	void		updateLOD(const NotifierReason &reason);

private:
	// No remove function in Notifiers because we use one instance
	// for every instance we want to be notified about.
	class ColorNotifier: public Notifier {
	public:
		void update(const void *tag, void *cgInst,
					const NotifierReason &reason) const;
	};
	class ColorGroupNotifier: public Notifier {
	public:
		void update(const void *tag, void *cgInst,
					const NotifierReason &reason) const;
	};
	class PBGNotifier: public Notifier {
	public:
		void update(const void *tag, void *,
					const NotifierReason &reason) const;
	};
	class LODNotifier: public Notifier {
	public:
		void update(const void *tag, void *lodInst,
					const NotifierReason &reason) const;
	};

	virtual		~PBGLensModel();
	PseudoBondGroup	*pbg;
	mutable Shapes		bondDrawing;	// cyl, wires
	mutable LabelGraphics	labelDrawing;	// labels
	mutable bool		dirty;
	mutable bool		dirtySelection;
	mutable ColorSet	colorsUsed;
	mutable ColorGroupSet	cgsUsed;
	ColorNotifier		colorNotifier;
	ColorGroupNotifier	cgNotifier;
	PBGNotifier		pbgNotifier;
	LODNotifier		lodNotifier;
	void		buildDisplayList(const LensViewer *) const;
	void		monitorColor(const Color *color) const;
	void		addConnector(Bond::DrawMode dm,
				 const Color *c0, const Point &p0, bool cap0,
				 const Color *c1, const Point &p1, bool cap1,
				 float radius, const Selectable *sel) const;
};

} // namespace molecule

# endif /* WrapPy */

#endif
