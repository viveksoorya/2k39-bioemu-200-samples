#ifndef molecule_Atom_object_h
# define molecule_Atom_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Atom_objectType;

struct Atom_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	Atom* _inst() { return static_cast<Atom*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern Atom* getInst(Atom_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Atom>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Atom_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Atom* _o);
template <> inline PyObject* pyObject(molecule::Atom const* _o) { return pyObject(const_cast<molecule::Atom*>(_o)); }

} // namespace otf

#endif
