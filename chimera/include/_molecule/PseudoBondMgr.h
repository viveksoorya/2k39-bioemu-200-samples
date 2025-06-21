#ifndef chimera_PseudoBondMgr_h
#define	chimera_PseudoBondMgr_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <map>
#include <vector>
#include <otf/WrapPy2.h>
#include "_molecule_config.h"
#include "CoordSet.h"
#include "PseudoBondGroup.h"
#include "ChainTrace.h"
#include "chimtypes.h"

namespace molecule {

class MOLECULE_IMEX PseudoBondMgr: public otf::WrapPyObj  {
	CoordSet	*CoordSet_;
	std::map<Symbol, PseudoBondGroup *>	PseudoBondGroups_;
public:
		virtual ~PseudoBondMgr();
	CoordSet	*coordSet() const;
	PseudoBondGroup	*newPseudoBondGroup(Symbol category);
	ChainTrace	*newChainTrace(Symbol category);
	void	deletePseudoBondGroup(PseudoBondGroup *element);
	void	recategorize(PseudoBondGroup *pbg, Symbol newCategory);
	typedef std::vector<PseudoBondGroup *> PseudoBondGroups;
	inline PseudoBondGroups pseudoBondGroups() const;
	typedef std::map<Symbol, PseudoBondGroup *> PseudoBondGroupsMap;
	inline const PseudoBondGroupsMap	&pseudoBondGroupsMap() const;
	typedef std::vector<Symbol> PseudoBondGroupKeys;
	inline PseudoBondGroupKeys	categories() const;
	PseudoBondGroup	*findPseudoBondGroup(Symbol) const;
public:
	// a single PseudoBondMgr manages all PseudoBonds for Molecules
	// with single coordinate sets (i.e. non-trajectories).  This
	// singleton manager is accessed with the mgr() class member
	// function, below
	static PseudoBondMgr 	*mgr(); // singleton instance of PseudoBondMgr
private:
	static PseudoBondMgr *_mgr;
public:
	virtual PyObject* wpyNew() const;
private:
	PseudoBondMgr();
	PseudoBondMgr(const PseudoBondMgr&);		// disable
	PseudoBondMgr& operator=(const PseudoBondMgr&);	// disable
public:
	PseudoBondMgr(CoordSet *);
};

} // namespace molecule

#endif
