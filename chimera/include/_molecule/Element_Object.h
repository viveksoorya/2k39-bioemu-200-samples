#ifndef molecule_Element_object_h
# define molecule_Element_object_h
# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# define PY_SSIZE_T_CLEAN 1
#include <Python.h>
# include "Mol.h"
#include <otf/WrapPy2.h>
namespace molecule {

MOLECULE_IMEX extern PyTypeObject Element_objectType;

struct Element_object: public PyObject {
	PyObject* _inst_dict;
	double _inst_data[(sizeof (Element) + sizeof (double) - 1) / sizeof (double)];
	bool _initialized;
	Element* _inst() { return reinterpret_cast<Element*>(_inst_data); }
};

MOLECULE_IMEX extern Element* getInst(Element_object* self);

} // namespace molecule

namespace otf {

template <> inline bool
WrapPyType<molecule::Element>::check(PyObject* _o, bool noneOk)
{
	if (noneOk && _o == Py_None)
		return true;
	return PyObject_TypeCheck(_o, &molecule::Element_objectType);
}

template <> MOLECULE_IMEX PyObject* pyObject(molecule::Element* _o);
template <> inline PyObject* pyObject(molecule::Element _o) { return pyObject(&_o); }
template <> inline PyObject* pyObject(molecule::Element const* _o) { return pyObject(const_cast<molecule::Element*>(_o)); }

} // namespace otf

#endif
