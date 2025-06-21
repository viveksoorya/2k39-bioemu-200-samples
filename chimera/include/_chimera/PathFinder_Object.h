#ifndef chimera_PathFinder_object_h
# define chimera_PathFinder_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include <PathFinder.h>
#include <otf/WrapPy2.h>
namespace chimera {

CHIMERA_IMEX extern PyTypeObject PathFinder_objectType;

struct PathFinder_object: public PyObject {
	PyObject* _inst_dict;
	double _inst_data[(sizeof (PathFinder) + sizeof (double) - 1) / sizeof (double)];
	bool _initialized;
	PathFinder* _inst() { return reinterpret_cast<PathFinder*>(_inst_data); }
};

CHIMERA_IMEX extern PathFinder* getInst(PathFinder_object* self);

} // namespace chimera

namespace otf {

template <> inline bool
WrapPyType<chimera::PathFinder>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &chimera::PathFinder_objectType);
}

template <> CHIMERA_IMEX PyObject* pyObject(chimera::PathFinder* _o);
template <> inline PyObject* pyObject(chimera::PathFinder _o) { return pyObject(&_o); }
template <> inline PyObject* pyObject(chimera::PathFinder const* _o) { return pyObject(const_cast<chimera::PathFinder*>(_o)); }

} // namespace otf

#endif
