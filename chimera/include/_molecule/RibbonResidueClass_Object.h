#ifndef molecule_RibbonResidueClass_object_h
# define molecule_RibbonResidueClass_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject RibbonResidueClass_objectType;

struct RibbonResidueClass_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	RibbonResidueClass* _inst() { return static_cast<RibbonResidueClass*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern RibbonResidueClass* getInst(RibbonResidueClass_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::RibbonResidueClass>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::RibbonResidueClass_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::RibbonResidueClass* _o);
template <> inline PyObject* pyObject(molecule::RibbonResidueClass const* _o) { return pyObject(const_cast<molecule::RibbonResidueClass*>(_o)); }

} // namespace otf

#endif
