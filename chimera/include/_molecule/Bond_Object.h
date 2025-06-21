#ifndef molecule_Bond_object_h
# define molecule_Bond_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Bond_objectType;

struct Bond_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	Bond* _inst() { return static_cast<Bond*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern Bond* getInst(Bond_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Bond>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Bond_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Bond* _o);
template <> inline PyObject* pyObject(molecule::Bond const* _o) { return pyObject(const_cast<molecule::Bond*>(_o)); }

} // namespace otf

#endif
