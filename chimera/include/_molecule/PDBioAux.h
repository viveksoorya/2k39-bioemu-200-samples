#ifndef molecule_PDBioAux_h
# define molecule_PDBioAux_h

# include "_molecule_config.h"
# include <string>

namespace molecule {

MOLECULE_IMEX extern void	PDBioCanonicalizeAtomName(std::string *aname, bool *translated);
MOLECULE_IMEX extern void	PDBioCanonicalizeResidueName(std::string *rname);

} // namespace molecule

#endif
