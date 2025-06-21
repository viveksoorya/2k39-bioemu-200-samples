#ifndef molecule_Ring_object_h
# define molecule_Ring_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Ring_objectType;

struct Ring_object: public PyObject {
	PyObject* _inst_dict;
	double _inst_data[(sizeof (Ring) + sizeof (double) - 1) / sizeof (double)];
	bool _initialized;
	Ring* _inst() { return reinterpret_cast<Ring*>(_inst_data); }
};

MOLECULE_IMEX extern Ring* getInst(Ring_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Ring>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Ring_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Ring* _o);
template <> inline PyObject* pyObject(molecule::Ring _o) { return pyObject(&_o); }
template <> inline PyObject* pyObject(molecule::Ring const* _o) { return pyObject(const_cast<molecule::Ring*>(_o)); }

} // namespace otf

#endif
