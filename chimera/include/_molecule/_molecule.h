#ifndef _molecule_h
# define _molecule_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

// include Python.h first so standard defines are the same
# define PY_SSIZE_T_CLEAN 1
# include <Python.h>
# include <new>
# include <otf/WrapPy2.h>
# include <_chimera/_chimera.h>

#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif
# include "_molecule_config.h"
# include "Atom_Object.h"
# include "Bond_Object.h"
# include "BondRot_Object.h"
# include "ChainTrace_Object.h"
# include "CoordSet_Object.h"
# include "Element_Object.h"
# include "GeometryVector_Object.h"
# include "Root_GraphSize_Object.h"
# include "Atom_IdatmInfo_Object.h"
# include "Mol2io_Object.h"
# include "MolResId_Object.h"
# include "Molecule_Object.h"
# include "PDBio_Object.h"
# include "PseudoBond_Object.h"
# include "PseudoBondGroup_Object.h"
# include "PseudoBondMgr_Object.h"
# include "PyMol2ioHelper_Object.h"
# include "ReadGaussianFCF_Object.h"
# include "Residue_Object.h"
# include "RibbonData_Object.h"
# include "RibbonResidueClass_Object.h"
# include "RibbonStyle_Object.h"
# include "RibbonStyleFixed_Object.h"
# include "RibbonStyleTapered_Object.h"
# include "RibbonStyleWorm_Object.h"
# include "RibbonXSection_Object.h"
# include "Ring_Object.h"
# include "Root_Object.h"
# include "SessionPDBio_Object.h"
# include "Spline_Object.h"
# include "TemplateAtom_Object.h"
# include "TemplateBond_Object.h"
# include "TemplateResidue_Object.h"

namespace molecule {

MOLECULE_IMEX extern void _moleculeError();
extern int _moleculeDebug;

} // namespace molecule

#endif
