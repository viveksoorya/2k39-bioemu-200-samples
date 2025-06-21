#ifndef molecule_ReadGaussianFCF_object_h
# define molecule_ReadGaussianFCF_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject ReadGaussianFCF_objectType;

struct ReadGaussianFCF_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	ReadGaussianFCF* _inst() { return static_cast<ReadGaussianFCF*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern ReadGaussianFCF* getInst(ReadGaussianFCF_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::ReadGaussianFCF>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::ReadGaussianFCF_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::ReadGaussianFCF* _o);
template <> inline PyObject* pyObject(molecule::ReadGaussianFCF const* _o) { return pyObject(const_cast<molecule::ReadGaussianFCF*>(_o)); }

} // namespace otf

#endif
