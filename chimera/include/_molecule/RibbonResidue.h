#ifndef chimera_RibbonResidue_h
#define	chimera_RibbonResidue_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

namespace molecule {

class MOLECULE_IMEX RibbonResidue {
public:
		~RibbonResidue();
public:
private:
	RibbonResidue& operator=(const RibbonResidue&);	// disable
	//RibbonResidue(const RibbonResidue& r); // allow in std::map by value
private:
public:
	Atom			*guide;
	Atom			*plane;
	Residue			*prev;
	Residue			*next;
	Vector	curvatureProjection;
	Vector	localCurvature;
	Vector	normal;
	Vector	binormal;
public:
	RibbonResidue();
};

} // namespace molecule

#endif
