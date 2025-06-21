#ifndef molecule_PseudoBondGroup_object_h
# define molecule_PseudoBondGroup_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject PseudoBondGroup_objectType;

struct PseudoBondGroup_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	PseudoBondGroup* _inst() { return static_cast<PseudoBondGroup*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern PseudoBondGroup* getInst(PseudoBondGroup_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::PseudoBondGroup>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::PseudoBondGroup_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::PseudoBondGroup* _o);
template <> inline PyObject* pyObject(molecule::PseudoBondGroup const* _o) { return pyObject(const_cast<molecule::PseudoBondGroup*>(_o)); }

} // namespace otf

#endif
