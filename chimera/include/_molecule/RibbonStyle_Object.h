#ifndef molecule_RibbonStyle_object_h
# define molecule_RibbonStyle_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject RibbonStyle_objectType;

struct RibbonStyle_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	RibbonStyle* _inst() { return static_cast<RibbonStyle*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern RibbonStyle* getInst(RibbonStyle_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::RibbonStyle>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::RibbonStyle_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::RibbonStyle* _o);
template <> inline PyObject* pyObject(molecule::RibbonStyle const* _o) { return pyObject(const_cast<molecule::RibbonStyle*>(_o)); }

} // namespace otf

#endif
