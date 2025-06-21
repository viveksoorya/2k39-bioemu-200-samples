#ifndef chimera_CoordSet_h
#define	chimera_CoordSet_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <vector>
#include <algorithm>

#include <otf/WrapPy2.h>
#include "_molecule_config.h"
#include <_chimera/TrackChanges.h>
#include "Coord.h"
#include "PseudoBondMgr.h"


extern "C" {
typedef struct _object PyObject;
}

namespace molecule {
class Molecule;

class MOLECULE_IMEX CoordSet: public otf::WrapPyObj  {
public:
	void		addCoord(Coord element);
	void		removeCoord(Coord *element);
	typedef std::vector<Coord> Coords;
	inline const Coords	&coords() const;
	const Coord	*findCoord(size_t) const;
	Coord		*findCoord(size_t);
	PyObject	*xyzArray() const;		// Numpy array of xyz
	PseudoBondMgr	*pseudoBondMgr() const;

	inline int	id() const;
	void		fill(const CoordSet *source);
	void		load(const Coords &crds);

	virtual void	trackReason(const NotifierReason &reason) const;
	struct Reason: public NotifierReason {
                Reason(const char *r): NotifierReason(r) {}
        };
	static Reason		COORD_CHANGED;

	virtual PyObject* wpyNew() const;
	virtual void	wpyAssociate(PyObject* o) const;
private:
	friend class Molecule;
	void	operator=(const CoordSet &);	// disable
		CoordSet(const CoordSet &);	// disable
		virtual ~CoordSet();
	std::vector<Coord>	Coords_;
	PseudoBondMgr	*PseudoBondMgr_;
	int	csid;

	static TrackChanges::Changes *const
			changes;
	CoordSet(Molecule *, int key);
	CoordSet(Molecule *, int key, int size);
};

} // namespace molecule

#endif
