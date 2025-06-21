#ifndef molecule_Spline_object_h
# define molecule_Spline_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Spline.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Spline_objectType;

struct Spline_object: public PyObject {
	PyObject* _inst_dict;
	Spline* _inst_data;
	Spline* _inst() { return _inst_data; }
};

MOLECULE_IMEX extern Spline* getInst(Spline_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Spline>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Spline_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Spline* _o);
template <> inline PyObject* pyObject(molecule::Spline const* _o) { return pyObject(const_cast<molecule::Spline*>(_o)); }

} // namespace otf

#endif
