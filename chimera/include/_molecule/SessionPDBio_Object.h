#ifndef molecule_SessionPDBio_object_h
# define molecule_SessionPDBio_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "SessionPDBio.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject SessionPDBio_objectType;

struct SessionPDBio_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	SessionPDBio* _inst() { return static_cast<SessionPDBio*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern SessionPDBio* getInst(SessionPDBio_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::SessionPDBio>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::SessionPDBio_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::SessionPDBio* _o);
template <> inline PyObject* pyObject(molecule::SessionPDBio const* _o) { return pyObject(const_cast<molecule::SessionPDBio*>(_o)); }

} // namespace otf

#endif
