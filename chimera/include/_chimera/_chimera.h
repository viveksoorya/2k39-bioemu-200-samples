#ifndef _chimera_h
# define _chimera_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

// include Python.h first so standard defines are the same
# define PY_SSIZE_T_CLEAN 1
# include <Python.h>
# include <new>
# include <otf/WrapPy2.h>

#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif
# include "_chimera_config.h"
# include "BBox_Object.h"
# include "Camera_Object.h"
# include "TrackChanges_Changes_Object.h"
# include "Color_Object.h"
# include "ColorGroup_Object.h"
# include "DirectionalLight_Object.h"
# include "LODControl_Object.h"
# include "Lens_Object.h"
# include "LensViewer_Object.h"
# include "Light_Object.h"
# include "Material_Object.h"
# include "MaterialColor_Object.h"
# include "Model_Object.h"
# include "NoGuiViewer_Object.h"
# include "OGLFont_Object.h"
# include "OSLAbbreviation_Object.h"
# include "OpenModels_Object.h"
# include "OpenState_Object.h"
# include "PathFinder_Object.h"
# include "PixelMap_Object.h"
# include "Plane_Object.h"
# include "Point_Object.h"
# include "PositionalLight_Object.h"
# include "Selectable_Object.h"
# include "SharedState_Object.h"
# include "SideViewer_Object.h"
# include "Sphere_Object.h"
# include "SpotLight_Object.h"
# include "Texture_Object.h"
# include "TextureColor_Object.h"
# include "TrackChanges_Object.h"
# include "Vector_Object.h"
# include "Viewer_Object.h"
# include "X3DScene_Object.h"
# include "Xform_Object.h"

namespace chimera {

CHIMERA_IMEX extern void _chimeraError();
extern int _chimeraDebug;

} // namespace chimera

#endif
