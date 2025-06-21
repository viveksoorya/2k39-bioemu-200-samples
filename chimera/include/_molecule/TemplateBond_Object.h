#ifndef molecule_TemplateBond_object_h
# define molecule_TemplateBond_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "TemplateBond.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject TemplateBond_objectType;

struct TemplateBond_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	TemplateBond* _inst() { return static_cast<TemplateBond*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern TemplateBond* getInst(TemplateBond_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::TemplateBond>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::TemplateBond_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::TemplateBond* _o);
template <> inline PyObject* pyObject(molecule::TemplateBond const* _o) { return pyObject(const_cast<molecule::TemplateBond*>(_o)); }

} // namespace otf

#endif
