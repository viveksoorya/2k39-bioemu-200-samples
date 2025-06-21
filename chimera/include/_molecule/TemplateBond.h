#ifndef Chimera_TemplateBond_h
# define Chimera_TemplateBond_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "_molecule_config.h"
# include "chimtypes.h"
# include "templates/TmplBond.h"

namespace molecule {

class MOLECULE_IMEX TemplateBond : public otf::WrapPyObj
{
	// DON'T CACHE
	TemplateBond(const TemplateBond&);		// disable
	TemplateBond& operator=(const TemplateBond&);	// disable
private:
	const TmplBond *tmplBond_;
# ifdef WrapPy
	TemplateBond();
# endif
public:
# ifndef WrapPy
	TemplateBond(const TmplBond *b);

	virtual PyObject* wpyNew() const;
# endif
	virtual ~TemplateBond();
	long hash() const;
	bool operator==(const TemplateBond &b) const;
	Real length() const;
	Real sqlength() const;
};

} // namespace molecule

#endif
