#ifndef molecule_RibbonXSection_object_h
# define molecule_RibbonXSection_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject RibbonXSection_objectType;

struct RibbonXSection_object: public PyObject {
	PyObject* _inst_dict;
	otf::WrapPyObj* _inst_data;
	RibbonXSection* _inst() { return static_cast<RibbonXSection*>(_inst_data); }
	PyObject* _weaklist;
};

MOLECULE_IMEX extern RibbonXSection* getInst(RibbonXSection_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::RibbonXSection>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::RibbonXSection_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::RibbonXSection* _o);
template <> inline PyObject* pyObject(molecule::RibbonXSection const* _o) { return pyObject(const_cast<molecule::RibbonXSection*>(_o)); }

} // namespace otf

#endif
