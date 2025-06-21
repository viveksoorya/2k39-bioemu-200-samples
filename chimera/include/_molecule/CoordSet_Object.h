#ifndef molecule_CoordSet_object_h
# define molecule_CoordSet_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject CoordSet_objectType;

struct CoordSet_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	CoordSet* _inst() { return static_cast<CoordSet*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern CoordSet* getInst(CoordSet_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::CoordSet>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::CoordSet_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::CoordSet* _o);
template <> inline PyObject* pyObject(molecule::CoordSet const* _o) { return pyObject(const_cast<molecule::CoordSet*>(_o)); }

} // namespace otf

#endif
