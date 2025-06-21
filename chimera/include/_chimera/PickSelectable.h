#ifndef Chimera_PickSelectable_h
# define Chimera_PickSelectable_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include "LensViewer.h"
# include "Selectable.h"
# include "_chimera_config.h"

namespace chimera {

CHIMERA_IMEX bool setPickSelectable(const Selectable *s);
CHIMERA_IMEX void clearPickSelectable();

CHIMERA_IMEX Selectable *singleObjectPick(float midX, float midY,
					  float xSize, float ySize,
					  bool labelsOnly, LensViewer *v);
CHIMERA_IMEX void multiLayerPick(float midX, float midY,
				 float xSize, float ySize,
				 LensViewer *v,
				 /*OUT*/ std::vector<Selectable *> &picked);

#ifndef WrapPy
static const int pickDiameterPixels = 9; // single pick range
static const int minDragPickPixels = 9;	// min x,y mouse drag for region picking
static const int maxDragPickLayers = 100;
#endif

} // namespace chimera

#endif
