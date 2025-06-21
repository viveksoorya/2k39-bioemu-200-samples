// --- UCSF Chimera Copyright ---
// Copyright (c) 2011 Regents of the University of California.
// All rights reserved.  This software provided pursuant to a
// license agreement containing restrictions on its disclosure,
// duplication and use.  This notice must be embedded in or
// attached to all copies, including partial copies, of the
// software or any revisions or derivations thereof.
// --- UCSF Chimera Copyright ---

#ifndef chimera_dome_config_h
# define chimera_dome_config_h

# ifndef _DOME_DLL
#  define _DOME_IMEX
# elif defined(_DOME_EXPORT)
#  define _DOME_IMEX __declspec(dllexport)
# else
#  define _DOME_IMEX __declspec(dllimport)
# endif

#endif
