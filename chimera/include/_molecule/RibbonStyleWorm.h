#ifndef chimera_RibbonStyleWorm_h
#define	chimera_RibbonStyleWorm_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include "Spline.h"

namespace molecule {

class MOLECULE_IMEX RibbonStyleWorm: public RibbonStyle  {
public:
		~RibbonStyleWorm();
public:
	virtual float		width(float t) const;
	inline virtual float		thickness(float t) const;
	virtual void		setSize(const std::vector<float> &sz,
							bool fromConstructor=false);
	virtual std::vector<float>
				size() const;
	// Below are used by updateRibbonData()
	float			radius() const;
	void			setPrevRadius(float w);
	void			setNextRadius(float w);
	void			updateSpline();

	virtual PyObject* wpyNew() const;
private:
	RibbonStyleWorm(const RibbonStyleWorm&);		// disable
	RibbonStyleWorm& operator=(const RibbonStyleWorm&);	// disable
private:
	float	prev_, width_, next_;
	Spline	*spline_;
public:
	RibbonStyleWorm(const std::vector<float> &sz);
};

} // namespace molecule

#endif
