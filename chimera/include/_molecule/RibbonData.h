#ifndef chimera_RibbonData_h
#define	chimera_RibbonData_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <otf/WrapPy2.h>
#include "chimtypes.h"

namespace molecule {
class Residue;

class MOLECULE_IMEX RibbonData: public otf::WrapPyObj  {
public:
		~RibbonData();
public:
	friend class Residue;
	friend class Atom;
	inline const Point &	center() const;
	inline void		setCenter(const Point &c);
	inline const Vector &	normal() const;
	inline void		setNormal(const Vector &n);
	inline const Vector &	binormal() const;
	inline void		setBinormal(const Vector &bn);
	inline void		flipNormals();
	inline bool		flipped() const;
	inline RibbonData	*prev() const;
	inline void		setPrev(/*NULL_OK*/ RibbonData *p);
	inline RibbonData	*next() const;
	inline void		setNext(/*NULL_OK*/ RibbonData *n);
	inline Residue		*prevResidue() const;
	inline void		setPrevResidue(/*NULL_OK*/ Residue *r);
	inline Residue		*nextResidue() const;
	inline void		setNextResidue(/*NULL_OK*/ Residue *r);
	inline Atom		*guide() const;
	inline void		setGuide(/*NULL_OK*/ Atom *a);

	virtual PyObject* wpyNew() const;
private:
	RibbonData(const RibbonData&);			// disable
	RibbonData& operator=(const RibbonData&);	// disable
private:
	Point	center_;
	Vector	normal_;
	Vector	binormal_;
	RibbonData		*next_;
	RibbonData		*prev_;
	Residue			*nextResidue_;
	Residue			*prevResidue_;
	Atom			*guide_;
	bool			flipped_;
public:
	RibbonData();
};

} // namespace molecule

#endif
