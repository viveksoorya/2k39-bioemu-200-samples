#ifndef chimera_Bond_h
#define	chimera_Bond_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <otf/WrapPy2.h>
#include "_molecule_config.h"
#include <_chimera/Selectable.h>
#include <_chimera/Color.h>
#include <_chimera/TrackChanges.h>
#include "chimtypes.h"
#include "Atom.h"
#include "Molecule.h"

namespace molecule {

class Ring;
static const Selector	SelBond = chimera::SelEdge;

class MOLECULE_IMEX Bond: public Selectable  {
public:
	typedef Array<Atom *, 2> Atoms;
	inline const Atoms	&atoms() const;
	Atom			*findAtom(size_t) const;

	inline Atom		*otherAtom(const Atom *a) const;
	inline bool		contains(const Atom *) const;

	inline Real		length() const;
	inline Real		sqlength() const;

	inline Molecule		*molecule() const;
	inline const Color	*color() const;
	void			setColor(/*NULL_OK*/ const Color *);
	enum DrawMode { Wire, Stick, Spring };
	inline DrawMode		drawMode() const;
	void			setDrawMode(DrawMode);
	enum DisplayMode { Never, Always, Smart };
	inline DisplayMode	display() const;
	void			setDisplay(DisplayMode);
	bool			shown() const;
	inline float		radius() const;
	void			setRadius(float);
	inline bool		halfbond() const;
	void			setHalfbond(bool);
	inline const std::string &label() const;
	void			setLabel(const std::string &s);
	inline const Vector	&labelOffset() const;
	void			setLabelOffset(const Vector &offset);
	inline const Color	*labelColor() const;
	Point			labelCoord() const;
	Vector			currentLabelOffset() const;
	void			setLabelColor(/*NULL_OK*/ const Color *);

	std::string		oslIdent(Selector start = SelDefault,
					Selector end = SelDefault) const;
	Selectable::Selectables oslChildren() const;
	Selectable::Selectables oslParents() const;
	bool			oslTestAbbr(OSLAbbreviation *a) const;
	inline Selector		oslLevel() const;
	static const Selector	selLevel = SelBond;

	typedef std::vector<const Ring *> Rings;
	const Rings		&rings(bool crossResidues = false,
				       unsigned int allSizeThreshold = 0) const;
	// return vector of Ring (instead of Ring *) to make wrappy happy
	std::vector<Ring>	minimumRings(bool crossResidues = false) const;
	std::vector<Ring>	allRings(bool crossResidues = false,
					 int sizeThreshold = 0) const;

	inline Atom		*getBreakPoint() const;
	void			setBreakPoint(Atom *a);
	inline void		clearBreakPoint();
	inline Bond		*traverseFrom(bool ignoreBreakPoints) const;

	bool	registerField(Symbol field, int value);
	bool	registerField(Symbol field, double value);
	bool	registerField(Symbol field, const std::string &value);
	bool	getRegField(Symbol field, int *value) const;
	bool	getRegField(Symbol field, double *value) const;
	bool	getRegField(Symbol field, std::string *value) const;


	virtual PyObject	*wpyNew() const;
	virtual void		wpyAssociate(PyObject* o) const;

	void		trackReason(const NotifierReason &reason) const;
	struct Reason: public NotifierReason {
                Reason(const char *r): NotifierReason(r) {}
        };
	static Reason		COLOR_CHANGED;
	static Reason		DRAW_MODE_CHANGED;
	static Reason		DISPLAY_CHANGED;
	static Reason		RADIUS_CHANGED;
	static Reason		HALFBOND_CHANGED;
	static Reason		LABEL_CHANGED;
	static Reason		LABEL_OFFSET_CHANGED;
	static Reason		LABEL_COLOR_CHANGED;
private:
	Array<Atom *, 2>	Atoms_;

	const Color	*color_;
	DrawMode	drawMode_;
	DisplayMode	display_;
	bool		halfbond_;
	float		radius_;
	std::string	label_;
	Vector		labelOffset_;
	const Color	*labelColor_;

	Atom		*mg_BreakPoint;
          // NULL if this edge can be crossed during traversals,
          // otherwise set to one of the endpoints (that endpoint
          // will not consider this edge during a traversal)
	
	mutable Bond	*mg_From;
	void		mg_bondInit(Atom *, Atom*);

	Rings		mg_Rings;

	inline void	setMajorChange();

	friend class Atom;
	friend class Molecule;

	Bond(Molecule *, Atom *a0, Atom *a1);
	Bond(Molecule *, Atom *a[2]);
	Bond(const Bond &);	// disable
	void	basicInitWithAtoms(Atom *, Atom *);
	virtual ~Bond();
	void	operator=(const Bond &);	// disable

	static TrackChanges::Changes *const changes;
};

} // namespace molecule

#endif
