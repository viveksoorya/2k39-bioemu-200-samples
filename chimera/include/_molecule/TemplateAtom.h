#ifndef Chimera_TemplateAtom_h
# define Chimera_TemplateAtom_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "Element.h"
# include "_molecule_config.h"
# include "chimtypes.h"
# include "templates/TmplAtom.h"

namespace molecule {
class TemplateAtom;
class TemplateBond;
typedef Point TmplCoord;

class MOLECULE_IMEX TemplateAtom : public otf::WrapPyObj
{
	// DON'T CACHE
	TemplateAtom(const TemplateAtom&);		// disable
	TemplateAtom& operator=(const TemplateAtom&);	// disable
private:
	const TmplAtom *tmplAtom_;
# ifdef WrapPy
			TemplateAtom();
# endif
public:
# ifndef WrapPy
	TemplateAtom(const TmplAtom *a);

	virtual PyObject* wpyNew() const;
# endif
	virtual ~TemplateAtom();
	long hash() const;
	bool operator==(const TemplateAtom &a) const;
	typedef std::map<TemplateAtom*, TemplateBond *, std::less<TemplateAtom*> > BondsMap;
	// ATTRIBUTE: bondsMap
	const BondsMap	&bondsMap() const;
	const TmplCoord	&coord() const;
	// ATTRIBUTE: name
	Symbol		name() const;
	// ATTRIBUTE: element
	Element		element() const;
	// ATTRIBUTE: idatmType
	Symbol		idatmType() const;
private:
	mutable BondsMap *bonds_;
	mutable TmplCoord *coord_;
};

} // namespace molecule

#endif
