#ifndef Chimera_PdbOrder_h
# define Chimera_PdbOrder_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

#include <vector>
#include "chimtypes.h"

namespace molecule {

extern const std::vector<Symbol> &pdbOrder(Symbol resName);

} // namespace molecule

#endif
