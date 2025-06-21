#ifndef chimera_Root_h
#define	chimera_Root_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <otf/WrapPy2.h>
#include "_molecule_config.h"

namespace molecule {

class Atom;
class Residue;

class MOLECULE_IMEX Root: public otf::WrapPyObj  {
public:
		virtual ~Root();
	Atom	*atom() const;
	Residue *residue() const;

	virtual PyObject* wpyNew() const;

	struct GraphSize { int numBonds; int numAtoms; };
	int		bondIndex;
	int		atomIndex;
	GraphSize	size;
	Root		*superRoot;
private:
	Atom	*Atom_;

	Root();  // private constructor
	Root(const Root&);		// disable
	Root& operator=(const Root&);	// disable
	
	friend class Molecule;
};

} // namespace molecule

#endif
