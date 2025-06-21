// Copyright (c) 1998-2005 The Regents of the University of California.
// All rights reserved.
//
// Redistribution and use in source and binary forms are permitted
// provided that the above copyright notice and this paragraph are
// duplicated in all such forms and that any documentation,
// distribution and/or use acknowledge that the software was developed
// by the Computer Graphics Laboratory, University of California,
// San Francisco.  The name of the University may not be used to
// endorse or promote products derived from this software without
// specific prior written permission.
// 
// THIS SOFTWARE IS PROVIDED ``AS IS'' AND WITHOUT ANY EXPRESS OR
// IMPLIED WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE IMPLIED
// WARRANTIES OF MERCHANTIBILITY AND FITNESS FOR A PARTICULAR PURPOSE.
// IN NO EVENT SHALL THE REGENTS OF THE UNIVERSITY OF CALIFORNIA BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
// OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF THIS SOFTWARE.

#ifndef chimera_WrapPySymbol_h
# define chimera_WrapPySymbol_h

# include <Python.h>
# include <otf/WrapPy2.h>
# include "Symbol.h"


namespace otf {

// Convert Symbol objects to Python strings
// Needed for example, in wrapped Color::list().

template <> inline PyObject*
pyObject(chimera::Symbol _x) { return PyUnicode_Decode(_x.c_str(), _x.size(), "utf-8", "replace"); }

} // namespace chimera

#endif
