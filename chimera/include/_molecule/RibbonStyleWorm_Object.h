#ifndef molecule_RibbonStyleWorm_object_h
# define molecule_RibbonStyleWorm_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject RibbonStyleWorm_objectType;

struct RibbonStyleWorm_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	RibbonStyleWorm* _inst() { return static_cast<RibbonStyleWorm*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern RibbonStyleWorm* getInst(RibbonStyleWorm_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::RibbonStyleWorm>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::RibbonStyleWorm_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::RibbonStyleWorm* _o);
template <> inline PyObject* pyObject(molecule::RibbonStyleWorm const* _o) { return pyObject(const_cast<molecule::RibbonStyleWorm*>(_o)); }

} // namespace otf

#endif
