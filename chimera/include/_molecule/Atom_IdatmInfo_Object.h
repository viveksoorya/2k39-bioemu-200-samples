#ifndef molecule_Atom_IdatmInfo_object_h
# define molecule_Atom_IdatmInfo_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Atom_IdatmInfo_objectType;

struct Atom_IdatmInfo_object: public PyObject {
	double _inst_data[(sizeof (Atom::IdatmInfo) + sizeof (double) - 1) / sizeof (double)];
	bool _initialized;
	Atom::IdatmInfo* _inst() { return reinterpret_cast<Atom::IdatmInfo*>(_inst_data); }
};

MOLECULE_IMEX extern Atom::IdatmInfo* getInst(Atom_IdatmInfo_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Atom::IdatmInfo>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Atom_IdatmInfo_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Atom::IdatmInfo* _o);
template <> inline PyObject* pyObject(molecule::Atom::IdatmInfo _o) { return pyObject(&_o); }
template <> inline PyObject* pyObject(molecule::Atom::IdatmInfo const* _o) { return pyObject(const_cast<molecule::Atom::IdatmInfo*>(_o)); }

} // namespace otf

#endif
