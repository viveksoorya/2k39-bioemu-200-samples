#ifndef RESDISTCONN_H
#define RESDISTCONN_H

#include <set>
#include "chimtypes.h"

namespace molecule {

class Atom;
class Residue;

void connectResidueByDistance(Residue *, std::set<Atom *> *,
			      Real bondRatio = 1, Real bondTolerance = 0.4);

Real bondedDist(Atom *a, Atom *b, Real bondRatio = 1, Real bondTolerance = 0.4);

}

#endif
