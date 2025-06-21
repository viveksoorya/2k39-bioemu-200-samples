#ifndef Chimera_SessionPDBio_h
# define Chimera_SessionPDBio_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "_molecule_config.h"
# include "Mol.h"
# include "PDBio.h"

namespace molecule {

class MOLECULE_IMEX SessionPDBio: public PDBio
{
public:
	SessionPDBio();
	virtual ~SessionPDBio();
	typedef long long sesLong;
	std::vector<Molecule *> readSessionPDBfile(const char *filename,
				/*OUT*/ std::map<sesLong, Atom *> *sessionIDs);
	std::vector<Molecule *> readSessionPDBstream(std::istream &input,
				const char *filename, /*INOUT*/ int *lineNum,
				/*OUT*/ std::map<sesLong, Atom *> *sessionIDs);
# ifndef WrapPy
	virtual PyObject* wpyNew() const;
# endif
};

} // namespace molecule

#endif
