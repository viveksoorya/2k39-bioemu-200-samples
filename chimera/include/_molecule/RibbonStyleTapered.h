#ifndef chimera_RibbonStyleTapered_h
#define	chimera_RibbonStyleTapered_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <otf/WrapPy2.h>
#include "RibbonStyle.h"

namespace molecule {

class MOLECULE_IMEX RibbonStyleTapered: public RibbonStyle  {
public:
		~RibbonStyleTapered();
public:
	virtual float		width(float t) const;
	virtual float		thickness(float t) const;

	virtual PyObject* wpyNew() const;

	virtual void		setSize(const std::vector<float> &sz,
							bool fromConstructor=false);
	virtual std::vector<float>
				size() const;
private:
	RibbonStyleTapered(const RibbonStyleTapered&);		// disable
	RibbonStyleTapered& operator=(const RibbonStyleTapered&);	// disable
private:
	float	widthStart_, widthSpan_;
	float	thicknessStart_, thicknessSpan_;
public:
	RibbonStyleTapered(const std::vector<float> &sz);
};

} // namespace molecule

#endif
