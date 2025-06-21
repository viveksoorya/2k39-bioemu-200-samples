#ifndef Chimera_TemplateResidue_h
# define Chimera_TemplateResidue_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "_molecule_config.h"
# include "TemplateAtom.h"
# include "templates/TmplResidue.h"
# include "chimtypes.h"

namespace molecule {

// can't use TmplResidue directly because its copy constructor
// is private, which screws up wrappy
class MOLECULE_IMEX TemplateResidue : public otf::WrapPyObj
{
	// DON'T CACHE
	TemplateResidue(const TemplateResidue&);		// disable
	TemplateResidue& operator=(const TemplateResidue&);	// disable
	const TmplResidue *tmplResidue_;
# ifdef WrapPy
	TemplateResidue();
# endif
public:
# ifndef WrapPy
	TemplateResidue(const TmplResidue *t);

	virtual PyObject* wpyNew() const;
# endif
	virtual ~TemplateResidue();
	long hash() const;
	bool operator==(const TemplateResidue &r) const
				{ return r.tmplResidue_ == tmplResidue_; }

	typedef std::map<Symbol, TemplateAtom *, std::less<Symbol> > AtomsMap;
	// ATTRIBUTE: atomsMap
	const AtomsMap &atomsMap() const;
private:
	mutable AtomsMap *atoms_;
};

} // namespace molecule

#endif
