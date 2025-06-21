#ifndef chimera_Atom_h
#define	chimera_Atom_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <map>
#include <vector>
#include <string>

#include "Element.h"
#include "CoordSet.h"
#include <otf/WrapPy2.h>
#include "_molecule_config.h"
#include <_chimera/Selectable.h>
#include <_chimera/Color.h>
#include <_chimera/TrackChanges.h>
#include "RibbonSpline.h"
#include "chimtypes.h"

namespace molecule {

class Ring;
static const Selector	SelAtom = chimera::SelVertex;

class MOLECULE_IMEX Atom: public Selectable  {
public:
	// Properties
	inline Symbol		name() const;
	void			setName(Symbol s);
	Residue			*residue() const;
	inline Molecule		*molecule() const;

	inline Element		element() const;
	void			setElement(Element e);
	// Atom_idatm overrides setElement, so using "old-fashioned" inlining
	// to work around the fact that wrappy isn't smart enough not to
	// elide the following implementations
	void			setElement(int e) { setElement(Element(e)); }
	void			setElement(const char *e) { setElement(Element(e)); }

	inline char		altLoc() const;
	inline void		setAltLoc(char al);
	std::vector<Atom *>	allLocations() const;

	int			serialNumber() const;
	void			setSerialNumber(int n);
	float			bfactor() const;
	void			setBfactor(float bfactor);
	bool			haveBfactor() const;
	bool			anisoU(float *u11, float *u12, float *u13,
				       float *u22, float *u23, float *u33) const;
	void			setAnisoU(float u11, float u12, float u13,
					  float u22, float u23, float u33);
	PyObject		*anisoU() const;  // Numpy 3x3 array or None
	void			setAnisoU(PyObject *u);
	float			occupancy() const;
	void			setOccupancy(float occupancy);
	bool			haveOccupancy() const;

	// Coordinates
	static const unsigned int UNASSIGNED = ~0u;
	inline unsigned int	coordIndex() const;
	const Coord		&coord() const;
	const Coord		&coord(const CoordSet *cs) const;
	void			setCoord(const Coord &c);
	void			setCoord(const Coord &c, CoordSet *cs);
	Coord			xformCoord() const;
	Coord			xformCoord(const CoordSet *cs) const;

	// Display state.
	enum DrawMode { Dot, Sphere, EndCap, Ball };
	inline const Color	*color() const;
	void			setColor(/*NULL_OK*/ const Color *);
	inline const Color	*shownColor() const;
	inline DrawMode		drawMode() const;
	void			setDrawMode(DrawMode);
	inline bool		display() const;
	void			setDisplay(bool);
	inline bool		shown() const;
	inline bool		hide() const;
	void			setHide(bool);
	float			radius() const;
	void			setRadius(float);
	float			defaultRadius() const;
	void			revertDefaultRadius();
	float			endCapRadius() const;
	inline float		lastSize() const;	// last depicted size
	inline bool		vdw() const;
	void			setVdw(bool);
	void			clearVdwPoints();
	typedef std::pair<Point, Vector> VDWPoint;
	const std::vector<VDWPoint>	&vdwPoints();
	inline const Color	*vdwColor() const;
	void			setVdwColor(/*NULL_OK*/ const Color *color);

	// Bonds
	void			addBond(Bond *element);
	void			removeBond(Bond *element);
	typedef std::vector<Bond *> Bonds;
	inline Bonds 		bonds() const;
	std::vector<Bond *>	primaryBonds() const;
	inline size_t 		numBonds() const;
	typedef std::map<Atom*, Bond *> BondsMap;
	inline const BondsMap	&bondsMap() const;
	typedef std::vector<Atom*> BondKeys;
	inline BondKeys		neighbors() const;
	Bond			*findBond(Atom*) const;
	inline Bond		*connectsTo(Atom *a) const;

	// Pseudobonds
	void			addPseudoBond(PseudoBond *element);
	void			removePseudoBond(PseudoBond *element);
	typedef std::vector<PseudoBond *> PseudoBonds;
	inline const PseudoBonds &pseudoBonds() const;
	PseudoBond		*findPseudoBond(size_t s) const;

	// Connectivity
	std::vector<Atom *>	primaryNeighbors() const;
	inline Atom		*rootAtom(bool ignoreBreakPoints) const;
	inline Atom		*traverseFrom(bool ignoreBreakPoints) const;
	const Atom 		*bondedToMainchain(RibbonResidueClass *rrc) const;
	// Is this atom connected to "otherAtom" with a Bond/PseudoBond
	// of type "category" (possibly considering the current trajectory
	// frame)?
	bool			associated(const Atom *otherAtom,
					   Symbol category) const;

	// How many Bonds/PseudoBonds of type "category" link this atom
	// to "otherAtom" (if specified, otherwise any atom), given the
	// trajectory frame (if applicable)?
	std::vector<PseudoBond *>	associations(Symbol category,
					  const Atom *otherAtom = NULL) const;

	// Type of atom bonding pattern
	inline Symbol		idatmType() const;
	inline void		setIdatmType(Symbol);
	inline void		setIdatmType(const char *);
	inline void		setIdatmType(const std::string &);
	inline void		setComputedIdatmType(const char *);
	inline bool		idatmIsExplicit() const;
	enum IdatmGeometry {
		Ion=0, Single=1, Linear=2, Planar=3, Tetrahedral=4
	};
	struct IdatmInfo {
		IdatmGeometry	geometry;
		int		substituents;
		std::string	description;
	};
	typedef std::map<std::string, IdatmInfo> IdatmInfoMap;
	static const IdatmInfoMap &getIdatmInfoMap();
	int			coordination(int valueIfUnknown = 0) const;

	// Rings
	typedef std::vector<const Ring *> Rings;
	const Rings 		&rings(bool crossResidues = false,
				       unsigned int allSizeThreshold = 0,
				       std::set<const Atom *> *ignore = NULL) const;
	// return vector of Rings (instead of Ring *) to make wrappy happy
	std::vector<Ring>	minimumRings(bool crossResidues = false) const;
	std::vector<Ring>	allRings(bool crossResidues = false, int sizeThreshold = 0) const;

	// Labels
	inline const std::string &
				label() const;
	void			setLabel(const std::string &s);
	inline const Vector	&labelOffset() const;
	void			setLabelOffset(const Vector &offset);
	inline float		minimumLabelRadius() const;
	void			setMinimumLabelRadius(float radius);
	inline const Color	*labelColor() const;
	void			setLabelColor(/*NULL_OK*/ const Color *color);
	const Point		&labelCoord() const;
	Vector			currentLabelOffset() const;

	// Surface
	inline const Color	*surfaceColor() const;
	void			setSurfaceColor(/*NULL_OK*/ const Color *color);
	inline float		surfaceOpacity() const;
	void			setSurfaceOpacity(float opacity);
	inline bool		surfaceDisplay() const;
	void			setSurfaceDisplay(bool display);
	inline Symbol		surfaceCategory() const;
	void			setSurfaceCategory(Symbol category);


	// Selection
	std::string	oslIdent(Selector start = SelDefault, Selector end = SelDefault) const;
	Selectable::Selectables oslChildren() const;
	Selectable::Selectables oslParents() const;
	bool		oslTestAbbr(OSLAbbreviation *a) const;
	inline Selector	oslLevel() const;
	static const Selector	selLevel = SelAtom;

	// Track changes
	void		trackReason(const NotifierReason &reason) const;
	struct Reason: public NotifierReason {
                Reason(const char *r): NotifierReason(r) {}
        };
	static Reason		ALTLOC_CHANGED;
	static Reason		NAME_CHANGED;
	static Reason		ELEMENT_CHANGED;
	static Reason		SERIAL_NUMBER_CHANGED;
	static Reason		BFACTOR_CHANGED;
	static Reason		OCCUPANCY_CHANGED;
	static Reason		IDATM_TYPE_CHANGED;
	static Reason		COLOR_CHANGED;
	static Reason		DRAW_MODE_CHANGED;
	static Reason		DISPLAY_CHANGED;
	static Reason		HIDE_CHANGED;
	static Reason		RADIUS_CHANGED;
	static Reason		VDW_CHANGED;
	static Reason		VDW_POINTS_CHANGED;
	static Reason		VDW_COLOR_CHANGED;
	static Reason		LABEL_CHANGED;
	static Reason		LABEL_OFFSET_CHANGED;
	static Reason		MINIMUM_LABEL_RADIUS_CHANGED;
	static Reason		LABEL_COLOR_CHANGED;
	static Reason		SURFACE_COLOR_CHANGED;
	static Reason		SURFACE_OPACITY_CHANGED;
	static Reason		SURFACE_DISPLAY_CHANGED;
	static Reason		SURFACE_CATEGORY_CHANGED;

	// Python
	bool	registerField(Symbol field, int value);
	bool	registerField(Symbol field, double value);
	bool	registerField(Symbol field, const std::string &value);
	bool	getRegField(Symbol field, int *value) const;
	bool	getRegField(Symbol field, double *value) const;
	bool	getRegField(Symbol field, std::string *value) const;

	virtual void	wpyAssociate(PyObject* o) const;
	virtual PyObject* wpyNew() const;

private:
	Symbol		name_;
	Molecule	*Molecule_;
	Residue		*Residue_;
	std::map<Atom*, Bond *>	Bonds_;
	std::vector<PseudoBond *>	PseudoBonds_;
	Element		element_;
	mutable unsigned int index_;
	char		alternateLocation;
	int		serialNumber_;
	float		bfactor_;
	bool		haveBfactor_;
	float		*anisoU_;
	float		occupancy_;
	bool		haveOccupancy_;
	const Color	*color_;
	DrawMode	drawMode_;
	bool		display_;
	bool		hide_;
	bool		vdw_;
	bool		vdwValid_;
	bool		surfaceDisplay_;
	std::vector<VDWPoint>	vdwPoints_;
	float		radius_;
	const Color	*vdwColor_;
	std::string	label_;
	Vector		labelOffset_;
	float		minimumLabelRadius_;
	const Color	*labelColor_;
	const Color	*surfaceColor_;
	float		surfaceOpacity_;
	Symbol		surfaceCategory_;
	mutable float	lastSize_;
	mutable Atom	*mg_Root, *mg_From;
          // Root = corresponding root for traversal _not_ ignoring breakpoints
          // From = previous node in that traversal
	Rings		mg_Rings;
	Symbol		explicitIdatmType_;
	mutable Symbol	computedIdatmType_;

	Atom(Molecule *, Symbol n, Element e);
	void	operator=(const Atom &);	// disable
	Atom(const Atom &);	// disable
	virtual ~Atom();

	int		newCoord(const Coord &c) const;

	inline void	setMajorChange();
	inline void	setMinorSurfaceChange();
	inline void	setMajorSurfaceChange();

	static TrackChanges::Changes *const changes;
	static IdatmInfoMap	*_idatmMap;
	static struct IdatmTable {
		const char *idatmType;
		IdatmInfo info;
	} idatmInfos[];

	friend class Bond;
	friend class PseudoBondGroup;
	friend class Residue;
	friend class Molecule;
	friend class MoleculeLensModel;
	friend class PDBio; // to correct element types if needed
};

typedef std::vector<Atom *> Atoms;

} // namespace molecule

#endif
