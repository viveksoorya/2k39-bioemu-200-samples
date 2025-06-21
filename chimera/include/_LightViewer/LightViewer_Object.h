#ifndef _LightViewer_LightViewer_object_h
# define _LightViewer_LightViewer_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "LightViewer.h"
#include <otf/WrapPy2.h>
namespace _LightViewer {

extern PyTypeObject LightViewer_objectType;

struct LightViewer_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	LightViewer* _inst() { return static_cast<LightViewer*>(_inst_data); }
	PyObject* _weaklist;
};

extern LightViewer* getInst(LightViewer_object* self);

} // namespace _LightViewer

namespace otf {

template <> inline bool
WrapPyType<_LightViewer::LightViewer>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &_LightViewer::LightViewer_objectType);
}

template <> PyObject* pyObject(_LightViewer::LightViewer* _o);
template <> inline PyObject* pyObject(_LightViewer::LightViewer const* _o) { return pyObject(const_cast<_LightViewer::LightViewer*>(_o)); }

} // namespace otf

#endif
