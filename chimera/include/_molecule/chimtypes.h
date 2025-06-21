#ifndef molecule_chimtypes_h
# define molecule_chimtypes_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <_chimera/Array.h>
# include <_chimera/Camera.h>
# include <_chimera/Geom3d.h>
# include <_chimera/LensModel.h>
# include <_chimera/LensViewer.h>
# include <_chimera/LineType.h>
# include <_chimera/LODControl.h>
# include <_chimera/OpenModels.h>
# include <_chimera/Selectable.h>
# include <_chimera/sphere.h>

namespace molecule {
using chimera::Array;
using chimera::BBox;
using chimera::Camera;
using chimera::Color;
using chimera::ColorGroup;
using chimera::ColorGroupSet;
using chimera::ColorSet;
using chimera::CustomLine;
using chimera::Dash;
using chimera::GfxState;
using chimera::Lens;
using chimera::LensModel;
using chimera::LensViewer;
using chimera::LineType;
using chimera::LODControl;
using chimera::Model;
using chimera::Notifier;
using chimera::NotifierList;
using chimera::NotifierReason;
using chimera::OpenModels;
using chimera::OpenState;
using chimera::OSLAbbreviation;
using chimera::OSLAbbrTest;
using chimera::Plane;
using chimera::Point;
using chimera::Selector;
using chimera::Selectable;
using chimera::SelDefault;
using chimera::SolidLine;
using chimera::Sphere;
using chimera::Symbol;
using chimera::TrackChanges;
using chimera::Texture;
using chimera::Vector;
using chimera::Xform;
using chimera::X3DScene;

using chimera::BBox;
using chimera::Point;
using chimera::PointAdd;
using chimera::Vector;
using chimera::Xform;

using chimera::Real;

using chimera::cross;
using chimera::degrees;
using chimera::distance;
using chimera::lerp;
using chimera::radians;
using chimera::sqdistance;
}

#endif
