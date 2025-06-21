#ifndef chimera_SideViewer_object_h
# define chimera_SideViewer_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "SideViewer.h"
#include <otf/WrapPy2.h>
namespace chimera {

CHIMERA_IMEX extern PyTypeObject SideViewer_objectType;

struct SideViewer_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	SideViewer* _inst() { return static_cast<SideViewer*>(_inst_data); }
	PyObject* _weaklist;
};

CHIMERA_IMEX extern SideViewer* getInst(SideViewer_object* self);

} // namespace chimera

namespace otf {

template <> inline bool
WrapPyType<chimera::SideViewer>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &chimera::SideViewer_objectType);
}

template <> CHIMERA_IMEX PyObject* pyObject(chimera::SideViewer* _o);
template <> inline PyObject* pyObject(chimera::SideViewer const* _o) { return pyObject(const_cast<chimera::SideViewer*>(_o)); }

} // namespace otf

#endif
