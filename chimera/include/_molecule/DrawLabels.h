#ifndef Chimera_DrawLabels_h
# define Chimera_DrawLabels_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

# include <string>
# include <vector>

#include <GL/glu.h>	// use gluProject()

# include <_chimera/Color.h>
# include <_chimera/Selectable.h>
# include <_chimera/LensViewer.h>
# include <_chimera/X3DScene.h>
# include "chimtypes.h"

namespace molecule {

class LabelGraphics
{
public:
	LabelGraphics();
	~LabelGraphics();

	// all label models must be the same (eg., NULL if otherwise different)
	void	addLabel(const std::string &label, const Point &p,
			 const Vector &offset, const Color *color,
			 const Selectable *sel, const Model *m);

	bool	drawLabels(const LensViewer *lv, bool picking = false) const;
	void	clear();

	void	x3dNeeds(/* INOUT*/ X3DScene *scene) const;
	void	x3dWrite(std::ostream &out, unsigned indent,
					/* INOUT*/ X3DScene *scene) const;
private:

	class LabelInfo {
	  public:
		LabelInfo(const std::string &l, const Point &p, const Vector &o,
			  const Color *c, const Selectable *s);
		~LabelInfo();

		std::string label;
		Point coord;
		Vector offset;
		const Color *color;
		const Selectable *sel;
		mutable float scale;
	};

	typedef std::vector<LabelInfo> liVec;
	mutable liVec		labels;
	const Model		*labelModel;

	// billboard correction for all views
	mutable Xform bb_invmxf;	// inverse model-view transform
	mutable Real bb_angle;		// angle and
	mutable Vector bb_axis;		// axis of invmxf
};

} // namespace molecule

# endif /* WrapPy */

#endif
