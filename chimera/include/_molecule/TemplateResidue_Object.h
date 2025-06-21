#ifndef molecule_TemplateResidue_object_h
# define molecule_TemplateResidue_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "TemplateResidue.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject TemplateResidue_objectType;

struct TemplateResidue_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	TemplateResidue* _inst() { return static_cast<TemplateResidue*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern TemplateResidue* getInst(TemplateResidue_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::TemplateResidue>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::TemplateResidue_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::TemplateResidue* _o);
template <> inline PyObject* pyObject(molecule::TemplateResidue const* _o) { return pyObject(const_cast<molecule::TemplateResidue*>(_o)); }

} // namespace otf

#endif
