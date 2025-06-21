#ifndef molecule_ChainTrace_object_h
# define molecule_ChainTrace_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject ChainTrace_objectType;

struct ChainTrace_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	ChainTrace* _inst() { return static_cast<ChainTrace*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern ChainTrace* getInst(ChainTrace_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::ChainTrace>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::ChainTrace_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::ChainTrace* _o);
template <> inline PyObject* pyObject(molecule::ChainTrace const* _o) { return pyObject(const_cast<molecule::ChainTrace*>(_o)); }

} // namespace otf

#endif
