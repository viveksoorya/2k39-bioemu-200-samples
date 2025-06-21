#ifndef molecule_RibbonDraw_h
#define molecule_RibbonDraw_h

#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

# include "DrawShapes.h"		// use Shapes
# include "Molecule.h"			// use Molecule

namespace molecule {

void buildRibbonGraphics(Molecule *mol, Shapes &s);

} // namespace molecule

#endif

