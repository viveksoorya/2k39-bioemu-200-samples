#ifndef Chimera_PDBrun_h
# define Chimera_PDBrun_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include "chimtypes.h"
# include <vector>

#ifdef WrapPy
namespace chimera {
class Viewer : public otf::WrapPyObj
{
	// ABSTRACT
};
}
#endif

namespace molecule {

void	pdbWrite(const std::vector<Molecule *> &mList,
		 const Xform &xform,
		 const std::string &filename,
		 bool allFrames = false,
		 bool displayedOnly = false,
		 bool selectedOnly = false,
		 PyObject *selectionSet = NULL,
		 bool asPQR = false,
		 bool h36 = true);
void	pdbWrite(const std::vector<Molecule *> &mList,
		 const Xform &xform,
		 std::ostream &out,
		 bool allFrames = false,
		 bool displayedOnly = false,
		 bool selectedOnly = false,
		 PyObject *selectionSet = NULL,
		 bool asPQR = false,
		 bool h36 = true);
# ifndef WrapPy
void	pdbrun(bool all, bool conect, bool nouser,
	       bool surface, bool nowait, bool markedOnly,
	       std::map<Atom *,	std::vector<Symbol> > &marks,
	       std::vector<Symbol> &activeMarks,
	       const chimera::Viewer &v,
	       const std::string &shellCommand, bool h36 = true);
# endif
	// temporary until wrappy handles maps/vectors...
void	pdbrunNoMarks(bool all, bool conect, bool nouser,
		      bool surface, bool nowait,
		      const chimera::Viewer &v,
		      const std::string &shellCommand, bool h36 = true);
}

#endif
