#ifndef molecule_TemplateAtom_object_h
# define molecule_TemplateAtom_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "TemplateAtom.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject TemplateAtom_objectType;

struct TemplateAtom_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	TemplateAtom* _inst() { return static_cast<TemplateAtom*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern TemplateAtom* getInst(TemplateAtom_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::TemplateAtom>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::TemplateAtom_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::TemplateAtom* _o);
template <> inline PyObject* pyObject(molecule::TemplateAtom const* _o) { return pyObject(const_cast<molecule::TemplateAtom*>(_o)); }

} // namespace otf

#endif
