// --- UCSF Chimera Copyright ---
// Copyright (c) 2000 Regents of the University of California.
// All rights reserved.  This software provided pursuant to a
// license agreement containing restrictions on its disclosure,
// duplication and use.  This notice must be embedded in or
// attached to all copies, including partial copies, of the
// software or any revisions or derivations thereof.
// --- UCSF Chimera Copyright ---
//
// $Id: ChimeraPath.h 36241 2012-04-26 00:10:51Z goddard $

#ifndef CHIMERA_CHIMERAPATHFINDER
# define CHIMERA_CHIMERAPATHFINDER

# include <string>
# include "PathFinder.h"
# include "chimerapath_config.h"

namespace chimera {
	
CHIMERAPATH_IMEX extern void setPathFinder(const std::string &dataRoot,
		const std::string &package, const std::string &env,
		bool hideData = true,
		bool useDotDefault = true, bool useHomeDefault = true);
CHIMERAPATH_IMEX extern const PathFinder *pathFinder();

} // end namespace chimera

#endif
