#ifndef _molecule_RingCalc_h
#define _molecule_RingCalc_h

#include "Molecule.h"

namespace molecule {

void calculateRings(const Molecule &mol, bool crossResidues,
		    unsigned int allSizeThreshold, Molecule::Rings &mg_Rings,
			std::set<const Atom *> *ignore);

} // namespace molecule

#endif
