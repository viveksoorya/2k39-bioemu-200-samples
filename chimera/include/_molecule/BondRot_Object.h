#ifndef molecule_BondRot_object_h
# define molecule_BondRot_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject BondRot_objectType;

struct BondRot_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	BondRot* _inst() { return static_cast<BondRot*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern BondRot* getInst(BondRot_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::BondRot>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::BondRot_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::BondRot* _o);
template <> inline PyObject* pyObject(molecule::BondRot const* _o) { return pyObject(const_cast<molecule::BondRot*>(_o)); }

} // namespace otf

#endif
