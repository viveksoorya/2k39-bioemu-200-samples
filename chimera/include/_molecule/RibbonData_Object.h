#ifndef molecule_RibbonData_object_h
# define molecule_RibbonData_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject RibbonData_objectType;

struct RibbonData_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	RibbonData* _inst() { return static_cast<RibbonData*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern RibbonData* getInst(RibbonData_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::RibbonData>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::RibbonData_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::RibbonData* _o);
template <> inline PyObject* pyObject(molecule::RibbonData const* _o) { return pyObject(const_cast<molecule::RibbonData*>(_o)); }

} // namespace otf

#endif
