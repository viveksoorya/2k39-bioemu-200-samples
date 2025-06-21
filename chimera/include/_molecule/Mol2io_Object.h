#ifndef molecule_Mol2io_object_h
# define molecule_Mol2io_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Mol2io_objectType;

struct Mol2io_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	Mol2io* _inst() { return static_cast<Mol2io*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern Mol2io* getInst(Mol2io_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Mol2io>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Mol2io_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Mol2io* _o);
template <> inline PyObject* pyObject(molecule::Mol2io const* _o) { return pyObject(const_cast<molecule::Mol2io*>(_o)); }

} // namespace otf

#endif
