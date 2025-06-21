#ifndef chimera_Ring_h
#define	chimera_Ring_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <set>

namespace molecule {

class Bond;

class MOLECULE_IMEX Ring {
public:
	Ring(std::set<Bond *> &ringBonds);
	~Ring();

	void	addBond(Bond *element);
	void	removeBond(Bond *element);
	typedef std::set<Bond *> Bonds;
	inline const Bonds	&bonds() const;

	// Only bonds, not atoms, are stored "naturally" in the ring.
	// Nonetheless, it is convenient to get the atoms easily...
	typedef std::set<Atom *> Atoms;
	const Atoms &atoms() const;

	// atoms()/bonds() don't return their values in ring order;
	// these do...
	const std::vector<Bond *> orderedBonds() const;
	const std::vector<Atom *> orderedAtoms() const;

	bool aromatic() const;

	bool operator<(const Ring &) const;
	bool operator==(const Ring &) const;
	long hash() const;

	// determine plane equation Ax+By+Cz+D=0 using algorithm in
	// Foley and van Damm 2nd edition, pp. 476-477
	// avgErr is average distance from plane to ring vertex,
	// maxErr is the largest such distance
	void planarity(double planeCoeffs[4], double *avgErr = 0,
	  double *maxErr = 0) const;
private:
	std::set<Bond *>	Bonds_;
	mutable Atoms		Atoms_;
};

} // namespace molecule

#endif
