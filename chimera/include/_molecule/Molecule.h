#ifndef chimera_Molecule_h
#define	chimera_Molecule_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <vector>
#include <map>
#include <vector>
#include <list>
#include <set>
#include <sstream>
#include <utility>
#include <otf/WrapPy2.h>
#include "Root.h"
#include "Ring.h"
#include "_molecule_config.h"
#include <_chimera/Selectable.h>
#include <_chimera/Model.h>
#include <_chimera/Color.h>
#include <_chimera/LineType.h>
#include "br.h"
#include "Atom.h"
#include "Bond.h"
#include "Residue.h"
#include "chimtypes.h"

namespace molecule {

class CoordSet;
class PseudoBondMgr;
class RibbonResidue;

static const Selector	SelMolecule = chimera::SelGraph;

class MOLECULE_IMEX Molecule: public Model  {
public:
	Molecule();
	virtual ~Molecule();

	Atom	*newAtom(Symbol n, Element e, int coordIndex=-1);
	void	deleteAtom(Atom *element);
	typedef std::vector<Atom *> Atoms;
	inline const Atoms	&atoms() const;
	inline size_t		numAtoms() const;
	Atom	*findAtom(size_t) const;
	PyObject	*atomCoordinatesArray() const;	// Numpy array of xyz

	Bond	*newBond(Atom *a0, Atom *a1);
	Bond	*newBond(Atom *a[2]);
	void	deleteBond(Bond *element);
	typedef std::vector<Bond *> Bonds;
	inline const Bonds	&bonds() const;
	inline size_t		numBonds() const;
	Bond	*findBond(size_t) const;

	CoordSet	*newCoordSet(int key);
	CoordSet	*newCoordSet(int key, int size);
	void	deleteCoordSet(CoordSet *element);
	typedef std::map<int, CoordSet *> CoordSets;
	inline const CoordSets	&coordSets() const;
	CoordSet	*findCoordSet(int) const;

	Residue	*newResidue(Symbol t, MolResId rid,
			Residue *neighbor=NULL, bool after=true);
	Residue	*newResidue(Symbol t, Symbol chain, int pos, char insert,
			Residue *neighbor=NULL, bool after=true);
	void	deleteResidue(Residue *element);
	typedef std::vector<Residue *> Residues;
	inline const Residues	&residues() const;
	inline size_t		numResidues() const;
	Residue	*findResidue(size_t) const;

	typedef std::vector<Root *> Roots;
	inline const Roots 	&roots(bool ignoreBreakPoints);
	Root		*rootForAtom(const Atom *,
			  bool ignoreBreakPoints);
	void		useAsRoot(Atom *newRoot);
	
	typedef std::pair<Bonds::const_iterator, Bonds::const_iterator>
	  TraverseBonds;
	TraverseBonds	traverseBonds(Root *root);
	
	typedef std::pair<Atoms::const_iterator, Atoms::const_iterator>
	  TraverseAtoms;
	TraverseAtoms	traverseAtoms(Root *root);

	typedef std::vector<Atom *> AtomGroup;
	typedef std::vector<AtomGroup> AtomGroups;
	void atomGroups(AtomGroups *atomGroups, int numAtoms) const;

	// PseudoBonds for trajectories are handled on a per-CoordSet basis;
	// pseudoBondMgr() returns the PseudoBondMgr appropriate for the given
	// CoordSet (which, if it isn't in a trajectory, is the global singleton
	// PseudoBondMgr).  The CoordSet argument defaults to the current
	// coordinate set.
	PseudoBondMgr *pseudoBondMgr(CoordSet *cs = NULL) const;

	// find rings: 'crossResidues' regulates whether or not to look for
	//	rings crossing residue boundaries; 'allSizeThreshold', if
	//	requests an exhaustive listing of rings no larger than the
	//	given size (larger minimal rings will still be returned)
	typedef std::set<Ring> Rings;
	const Rings &rings(bool crossResidues = false, unsigned int allSizeThreshold = 0,
			std::set<const Atom *> *ignore = NULL);

	bool		mg_RecomputeRings;

	std::vector<Atom *>	primaryAtoms() const;

	inline void		setIdatmValid(bool);
	inline bool		idatmValid() const;

	void	computeIdatmTypes();

	void		setActiveCoordSet(const CoordSet *a);
	inline CoordSet	*activeCoordSet() const;
	Atoms		indexedAtoms(PyObject *indices) const;

	inline bool			structureAssigned() const;
	inline void			setStructureAssigned(bool b);

	typedef std::string PDBHKeyType;
	typedef std::vector<std::string> PDBHValueType;
	typedef std::map<PDBHKeyType, PDBHValueType> PDBHeadersType;
	PDBHeadersType pdbHeaders;
	int		pdbVersion;
	inline void	addPDBHeader(const PDBHKeyType &, const std::string &);
	inline void	setPDBHeader(const PDBHKeyType &, PDBHValueType);
	inline void	setAllPDBHeaders(PDBHeadersType);
	bool	asterisksTranslated;

	Residue			*findResidue(const MolResId&, const char *type = NULL) const;
	void			moveResAfter(const Residue *from, const Residue *to);

	void	pruneShortBonds();

	bool	lowerCaseChains;

	std::vector<std::string> mol2comments, mol2data;

	bool	registerField(Symbol field, int value);
	bool	registerField(Symbol field, double value);
	bool	registerField(Symbol field, const std::string &value);
	bool	getRegField(Symbol field, int *value) const;
	bool	getRegField(Symbol field, double *value) const;
	bool	getRegField(Symbol field, std::string *value) const;

	void		computeSecondaryStructure(
				float	energyCutoff = -0.5,
				int	minHelixLength = 3,
				int	minStrandLength = 3,
				std::ostream *info = NULL);


	enum {
		KSDSSP_3DONOR		= 0x0001,
		KSDSSP_3ACCEPTOR	= 0x0002,
		KSDSSP_3GAP		= 0x0004,
		KSDSSP_3HELIX		= 0x0008,
		KSDSSP_4DONOR		= 0x0010,
		KSDSSP_4ACCEPTOR	= 0x0020,
		KSDSSP_4GAP		= 0x0040,
		KSDSSP_4HELIX		= 0x0080,
		KSDSSP_5DONOR		= 0x0100,
		KSDSSP_5ACCEPTOR	= 0x0200,
		KSDSSP_5GAP		= 0x0400,
		KSDSSP_5HELIX		= 0x0800,
		KSDSSP_PBRIDGE		= 0x1000,
		KSDSSP_ABRIDGE		= 0x2000,

		KSDSSP_PARA		= 1,
		KSDSSP_ANTI		= 2
	};

	struct Ksdssp_coords {
		const Coord	*c, *n, *ca, *o, *h;
	};

	inline bool	showStubBonds() const;
	void		setShowStubBonds(bool show);
	inline float	lineWidth() const;
	void		setLineWidth(float lw);
	inline float	stickScale() const;
	void		setStickScale(float ss);
	inline float	pointSize() const;
	void		setPointSize(float ps);
	inline float	ballScale() const;
	void		setBallScale(float bs);
	inline float	vdwDensity() const;
	void		setVdwDensity(float dens);
	inline LineType	lineType() const;
	void		setLineType(LineType linetype);
	void		lineTypeWireStipple(int *factor, int *pattern) const;
	inline void	wireStipple(/*OUT*/ int *factor, /*OUT*/ int *pattern) const;
	void		setWireStipple(int factor, int pattern);
	inline bool	autochain() const;
	void		setAutochain(bool yes);
	inline const Color	*surfaceColor() const;
	void		setSurfaceColor(/*NULL_OK*/ const Color *c);
	inline float	surfaceOpacity() const;
	void		setSurfaceOpacity(float opacity);
	void		incrHyds();
	void		decrHyds();
	inline int	numHyds() const;
	inline bool	aromaticDisplay() const;
	void		setAromaticDisplay(bool d);
	inline LineType	aromaticLineType() const;
	void		setAromaticLineType(LineType lt);
	inline Color	*aromaticColor() const;
	void		setAromaticColor(/*NULL_OK*/ Color *color);
	enum AromaticMode { Circle, Disk };
	inline AromaticMode	aromaticMode() const;
	void		setAromaticMode(AromaticMode mode);
	bool		hasFilledRing() const;
	enum ResidueLabelPos { CentroidAll, CentroidBackbone, PrimaryAtom };
	inline ResidueLabelPos	residueLabelPos() const;
	void		setResidueLabelPos(ResidueLabelPos mode);

	// virtual functions from Model
	virtual bool	computeBounds(/*OUT*/ Sphere *s, /*OUT*/ BBox *box) const;
	virtual bool	frontPoint(const Point &p1, const Point &p2, /*OUT*/ float *frac) const;
	// virtual functions from Selectable
	Selectable::Selectables oslChildren() const;
	Selectable::Selectables oslParents() const;

	void		surfaceCheck();
	inline void		addSurfaceNotification(const void *tag, const Notifier *n);
	inline void		removeSurfaceNotification(const void *tag);

	struct SurfaceReason: public NotifierReason {
		SurfaceReason(const char *r): NotifierReason(r) {}
	};
	// notifier reasons
	static SurfaceReason SURFACE_MINOR;	// don't recompute surface verts
	static SurfaceReason SURFACE_MAJOR;	// recompute surface vertices

	inline void		setMinorSurfaceChange();
	inline void		setMajorSurfaceChange();
	static Reason	ATOMS_MOVED;	// some atoms moved
	inline void		setAtomMoved(Atom *);
	typedef std::set<Atom *> AtomsMoved;
	inline const AtomsMoved &atomsMoved() const;
	inline const Rings	&minimumRings(bool crossResidues = false);
	inline const Rings	&allRings(bool, int);
	void		reorderResidues(const std::vector<Residue *> &);

	virtual PyObject* wpyNew() const;

	static const float
			DefaultBondRadius;	// = 0.2f
	static const double
			DefaultOffset;		// use default offset
	virtual void	updateCheck(const NotifierReason &reason);
	virtual void	wpyAssociate(PyObject* o) const;
	virtual void    setColor(const Color *c);

	static Reason	LINE_WIDTH_CHANGED;
	static Reason	STICK_SCALE_CHANGED;
	static Reason	POINT_SIZE_CHANGED;
	static Reason	BALL_SCALE_CHANGED;
	static Reason	VDW_DENSITY_CHANGED;
	static Reason	LINE_TYPE_CHANGED;
	static Reason	WIRE_STIPPLE_CHANGED;
	static Reason	SURFACE_COLOR_CHANGED;
	static Reason	SURFACE_OPACITY_CHANGED;
	static Reason	SHOW_STUB_BONDS_CHANGED;
	static Reason	AUTOCHAIN_CHANGED;
	static Reason	ACTIVE_COORD_SET_CHANGED;
	static Reason	AROMATIC_DISPLAY_CHANGED;
	static Reason	AROMATIC_LINE_TYPE_CHANGED;
	static Reason	AROMATIC_COLOR_CHANGED;
	static Reason	AROMATIC_MODE_CHANGED;
	static Reason	RESIDUE_LABEL_POS_CHANGED;

	inline bool		ribbonHidesMainchain() const;
	inline void		setRibbonHidesMainchain(bool b);
	inline const Color	*ribbonInsideColor() const;
	inline void		setRibbonInsideColor(/*NULL_OK*/ const Color *);
	bool		updateRibbonData();
	inline void		ribbonAtomMoved(const Atom *a);
	Residue		*residueAfter(const Residue *r) const;
	Residue		*residueBefore(const Residue *r) const;
	const Point	&ribbonCoordinates(const Atom *a) const;
	void		setRibbonCoordinates(const Atom *a, const Point &p);
	enum RT { RT_BSPLINE, RT_CARDINAL };
	inline RT		ribbonType() const;
	inline void		setRibbonType(RT rt);
	// ribbonStiffness is currently used for setting Cardinal spline tension
	inline double		ribbonStiffness() const;
	inline void		setRibbonStiffness(double param);
	// RSM is currently only used if ribbonType == RT_Cardinal
	enum RSM { RSM_STRAND = 0x1, RSM_COIL = 0x2 };
	inline int		ribbonSmoothing() const;
	inline void		setRibbonSmoothing(int mask);

	void		updateRibbonAtoms();
	inline void		invalidateRibbonData();
	inline bool		hasValidRibbonData() const;

	Component	*getComponent(Atom *atom, bool create);
	const BondRot	*findBondRot(Bond *bond) const;
	void		removeComponent(Component *atom);

	void		printComponent(std::ostream &os, Component *c, int indent);
	void		printComponents(std::ostream &os);
	inline bool		inDestructor();

private:

	std::vector<Atom *>	Atoms_;
	std::vector<Bond *>	Bonds_;
	std::map<int, CoordSet *>	CoordSets_;
	std::vector<Residue *>	Residues_;

	bool			inDestructor_;

	typedef std::map<Atom *, Component *> Components;
	Components		components;
	typedef std::map<Bond *, BondRot *> BondRots;
	BondRots		bondRots;

	bool			idatmValid_;

	CoordSet	*activeCS;

	bool		structureAssigned_;

	float		lineWidth_;
	float		stickScale_;
	float		pointSize_;
	float		ballScale_;
	float		vdwDensity_;
	LineType	lineType_;
	int		stipple[2];
	const Color	*surfaceColor_;
	float		surfaceOpacity_;
	AtomsMoved	atomsMoved_;
	bool		showStubBonds_;
	bool		autochain_;
	bool		minorSurfaceChange;
	bool		majorSurfaceChange;
	NotifierList	surfNL;
	static TrackChanges::Changes *const
			changes;
	virtual void	trackReason(const NotifierReason &reason) const;
	int		numHyds_;
	bool		aromaticDisplay_;
	LineType	aromaticLineType_;
	Color		*aromaticColor_;
	AromaticMode	aromaticMode_;
	ResidueLabelPos	residueLabelPos_;

	bool		ribbonHidesMainchain_;
	bool		ribbonDataValid_;
	const Color *	ribbonInsideColor_;
	typedef std::vector<RibbonData *> RibbonDataList;
	RibbonDataList	ribbonDataList_;
	inline void		clearRibbonData();

	RT		ribbonType_;
	double		ribbonStiffness_;
	int		ribbonSmoothing_;	// Mask ORed from RSM_* values

	typedef std::set<RibbonStyle *>	RibbonStyleSet;
	RibbonStyleSet	ribbonStyleSet_;
	class RibbonStyleNotifier : public Notifier {
	public:
                void update(const void *tag, void *style,
                                        const NotifierReason &reason) const;
	}		ribbonStyleNotifier;
	void 		updateRibbonStyle(RibbonStyle *s,
							const NotifierReason &);
	friend class RibbonStyleNotifier;

	typedef std::set<RibbonXSection *> RibbonXSectionSet;
	RibbonXSectionSet	ribbonXSectionSet_;
	class RibbonXSectionNotifier : public Notifier {
	public:
                void update(const void *tag, void *xsection,
                                        const NotifierReason &reason) const;
	}		ribbonXSectionNotifier;
	void 		updateRibbonXSection(RibbonXSection *xs,
							const NotifierReason &);
	friend class RibbonXSectionNotifier;

	static Reason	RIBBON_HIDES_MAINCHAIN_CHANGED;
	static Reason	RIBBON_INSIDE_COLOR_CHANGED;
	static Reason	RIBBON_TYPE_CHANGED;

	typedef std::map<const Atom *, Point> ACMap;
	mutable ACMap	acMap;
	
	mutable Roots		mg_BaseRoots, mg_SuperRoots;
	// "base" roots consider breakpoints, "super" roots ignore breakpoints

	Atoms			mg_travAtoms;
	Bonds			mg_travBonds;
	bool			mg_RecomputeRoots;

	bool			mg_LastCrossResidues;
	unsigned int		mg_LastAllSizeThreshold;
	std::set<const Atom *>	*mg_Ignore;
	Rings			mg_Rings;

	friend class Atom; // these friend declarations needed due to hokey way
	friend class Bond; // their destructors mark the traversal list dirty

	friend class Component;
	friend class BondRot;

	Molecule(const Molecule&);		// disable
	Molecule& operator=(const Molecule&);	// disable

	// virtual functions from Model
	virtual LensModel	*newLensModel(Lens *);

	void	ksdssp_addImideHydrogens() const;
	void	ksdssp_findHBonds() const;
	void	ksdssp_findTurns(int) const;
	void	ksdssp_markHelices(int) const;
	void	ksdssp_findHelices() const;
	void	ksdssp_findBridges() const;
	void	ksdssp_makeSummary(std::ostream *) const;
	void	ksdssp_computeChain(std::ostream *);
	bool	ksdssp_hBondedTo(Ksdssp_coords *, Ksdssp_coords *) const;
	Coord *	ksdssp_addImideHydrogen(Ksdssp_coords *, Ksdssp_coords *) const;

	void		removeBondRot(BondRot *br);		// bookkeeping
	void		addBondRotForBond(Bond *b, BondRot *br); // bookkeeping
	void		removeBondRotForBond(Bond *b);	// bookkeeping
	bool		dirtyComponentRoots;
	void		computeComponentSize(Component *c);
	void		computeComponentSizes();
	void		rerootComponents();
	void		collapseComponents(Component *c0, Component *c1);
	
	void			mg_deleteRoots();
	inline void 		mg_validateRoots();
	void 			mg_traversalOrganize();
	Root::GraphSize 	mg_traverse(Atom *root, Bond *from,
					std::map<Atom *, bool> &atomVisited,
					std::map<Bond *, bool> &bondVisited,
					std::list<std::pair<Atom *, Bond *> > &breakAtoms,
					std::list<std::pair<Bond *, Atom *> > &breakBonds);
	// so Bonds can get Roots recomputed when graph breakpoints get set
	inline void	mg_setRootsInvalid();

	void 		mg_findAtomGroups(std::vector<Atom *> *workingGroup,
				std::vector<std::vector<Atom *> > *groups,
				int groupSize, int remainingSize,
				std::map<Atom*, bool> &checkedAsEndNode,
				std::map<Atom*, bool> &inCurrentGroup) const;

	void		_flipRibbonNormals(std::map<Residue *, RibbonResidue> &rrMap);
	void		_dumpRibbon() const;
};

} // namespace molecule

#endif
