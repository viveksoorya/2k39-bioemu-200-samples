#ifndef molecule_GeometryVector_object_h
# define molecule_GeometryVector_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Spline.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject GeometryVector_objectType;

struct GeometryVector_object: public PyObject {
	PyObject* _inst_dict;
	double _inst_data[(sizeof (GeometryVector) + sizeof (double) - 1) / sizeof (double)];
	bool _initialized;
	GeometryVector* _inst() { return reinterpret_cast<GeometryVector*>(_inst_data); }
};

MOLECULE_IMEX extern GeometryVector* getInst(GeometryVector_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::GeometryVector>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::GeometryVector_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::GeometryVector* _o);
template <> inline PyObject* pyObject(molecule::GeometryVector _o) { return pyObject(&_o); }
template <> inline PyObject* pyObject(molecule::GeometryVector const* _o) { return pyObject(const_cast<molecule::GeometryVector*>(_o)); }

} // namespace otf

#endif
