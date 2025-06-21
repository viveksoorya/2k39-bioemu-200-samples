#ifndef RIBBONSPLINE_H
#define	RIBBONSPLINE_H

#include <map>
#include <string>
#include <otf/WrapPy2.h>
#include "_molecule_config.h"
#include "chimtypes.h"

namespace molecule {

extern void initRibbonResidueClasses();

class RibbonResidueClass;
typedef std::map<std::string, RibbonResidueClass *> RibbonResidueClasses;

class MOLECULE_IMEX RibbonResidueClass : public otf::WrapPyObj {
public:
	typedef std::map<Symbol, float> Position;
private:
	Symbol	guide_;
	Symbol	plane_;
	bool		planeNormal_;		// false = binormal
	bool		isNucleic_;		// false ~ amino acid
	Position	position_;

	static RibbonResidueClasses classes_;
	friend void initRibbonResidueClasses();
public:
				RibbonResidueClass(const Symbol &g,
							const Symbol &p,
							bool pn,
							bool n);
				RibbonResidueClass(const char *g,
							const char *p,
							bool pn,
							bool n);
	const Symbol	&guide() const;
	const Symbol	&plane() const;
	bool			isNucleic() const;
	bool			planeNormal() const;
	bool			hasPosition(const Symbol &name) const;
	std::pair<bool, float>	position(const Symbol &name) const;
	void			addPosition(const Symbol &name, float d);
	void			removePosition(const Symbol &name);
	const Position		&positions() const;
	// some convenience functions so not everyone need to use Symbol
	std::pair<bool, float>	position(const char *name) const;
	void			addPosition(const char *name, float d);
	void			removePosition(const char *name);

	virtual PyObject *	wpyNew() const;

	static const RibbonResidueClasses &
				classes();
	static void		registerClass(const char *name,
						RibbonResidueClass *klass);
	static void		deregisterClass(const char *name);
};

inline const Symbol &
RibbonResidueClass::guide() const
	{ return guide_; }

inline const Symbol &
RibbonResidueClass::plane() const
	{ return plane_; }

inline bool
RibbonResidueClass::isNucleic() const
	{ return isNucleic_; }

inline bool
RibbonResidueClass::planeNormal() const
	{ return planeNormal_; }
	
inline const RibbonResidueClass::Position &
RibbonResidueClass::positions() const
	{ return position_; }
	
inline std::pair<bool, float>
RibbonResidueClass::position(const char *name) const
	{ return position(Symbol(name)); }

inline void
RibbonResidueClass::addPosition(const char *name, float d)
	{ addPosition(Symbol(name), d); }

inline void
RibbonResidueClass::removePosition(const char *name)
	{ removePosition(Symbol(name)); }

inline const RibbonResidueClasses &
RibbonResidueClass::classes()
	{ return classes_; }

} // namespace molecule

#endif
