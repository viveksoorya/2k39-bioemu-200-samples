#ifndef molecule_Molecule_object_h
# define molecule_Molecule_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Molecule_objectType;

struct Molecule_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	Molecule* _inst() { return static_cast<Molecule*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern Molecule* getInst(Molecule_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Molecule>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Molecule_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Molecule* _o);
template <> inline PyObject* pyObject(molecule::Molecule const* _o) { return pyObject(const_cast<molecule::Molecule*>(_o)); }

} // namespace otf

#endif
