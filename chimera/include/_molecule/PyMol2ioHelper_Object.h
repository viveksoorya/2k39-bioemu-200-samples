#ifndef molecule_PyMol2ioHelper_object_h
# define molecule_PyMol2ioHelper_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "PyMol2ioHelper.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject PyMol2ioHelper_objectType;

struct PyMol2ioHelper_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	PyMol2ioHelper* _inst() { return static_cast<PyMol2ioHelper*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern PyMol2ioHelper* getInst(PyMol2ioHelper_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::PyMol2ioHelper>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::PyMol2ioHelper_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::PyMol2ioHelper* _o);
template <> inline PyObject* pyObject(molecule::PyMol2ioHelper const* _o) { return pyObject(const_cast<molecule::PyMol2ioHelper*>(_o)); }

} // namespace otf

#endif
