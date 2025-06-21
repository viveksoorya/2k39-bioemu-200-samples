#ifndef molecule_RibbonStyleFixed_object_h
# define molecule_RibbonStyleFixed_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject RibbonStyleFixed_objectType;

struct RibbonStyleFixed_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	RibbonStyleFixed* _inst() { return static_cast<RibbonStyleFixed*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern RibbonStyleFixed* getInst(RibbonStyleFixed_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::RibbonStyleFixed>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::RibbonStyleFixed_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::RibbonStyleFixed* _o);
template <> inline PyObject* pyObject(molecule::RibbonStyleFixed const* _o) { return pyObject(const_cast<molecule::RibbonStyleFixed*>(_o)); }

} // namespace otf

#endif
