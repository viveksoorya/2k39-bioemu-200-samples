#ifndef molecule_PseudoBondMgr_object_h
# define molecule_PseudoBondMgr_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject PseudoBondMgr_objectType;

struct PseudoBondMgr_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	PseudoBondMgr* _inst() { return static_cast<PseudoBondMgr*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern PseudoBondMgr* getInst(PseudoBondMgr_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::PseudoBondMgr>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::PseudoBondMgr_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::PseudoBondMgr* _o);
template <> inline PyObject* pyObject(molecule::PseudoBondMgr const* _o) { return pyObject(const_cast<molecule::PseudoBondMgr*>(_o)); }

} // namespace otf

#endif
