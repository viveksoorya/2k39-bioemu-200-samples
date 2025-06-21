#ifndef molecule_MolResId_object_h
# define molecule_MolResId_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject MolResId_objectType;

struct MolResId_object: public PyObject {
	PyObject* _inst_dict;
	double _inst_data[(sizeof (MolResId) + sizeof (double) - 1) / sizeof (double)];
	bool _initialized;
	MolResId* _inst() { return reinterpret_cast<MolResId*>(_inst_data); }
};

MOLECULE_IMEX extern MolResId* getInst(MolResId_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::MolResId>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::MolResId_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::MolResId* _o);
template <> inline PyObject* pyObject(molecule::MolResId _o) { return pyObject(&_o); }
template <> inline PyObject* pyObject(molecule::MolResId const* _o) { return pyObject(const_cast<molecule::MolResId*>(_o)); }

} // namespace otf

#endif
