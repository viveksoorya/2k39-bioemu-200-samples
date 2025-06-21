#ifndef chimera_Residue_h
#define	chimera_Residue_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <map>
#include <set>
#include <vector>

#include "Atom.h"
#include "chimtypes.h"
#include "_molecule_config.h"
#include "MolResId.h"
#include "Residue_template.h"
#include "RibbonXSection.h"
#include "RibbonStyle.h"
#include "RibbonData.h"
#include "RibbonSpline.h"
#include "Spline.h"

namespace molecule {

class Atom;
class Molecule;

static const Selector	SelResidue = chimera::SelSubgraph;

class MOLECULE_IMEX Residue: public Selectable  {
public:
	Molecule		*molecule() const;

	inline bool		operator==(const Residue &r) const;
	inline bool		operator<(const Residue &r) const;

	// Atoms
	void			addAtom(Atom *element);
	void			removeAtom(Atom *element);
	typedef std::vector<Atom *> Atoms;
	inline Atoms 		atoms() const;
	inline size_t		numAtoms() const;
	int			heavyAtomCount() const;
	typedef std::multimap<Symbol, Atom *> AtomsMap;
	inline const AtomsMap	&atomsMap() const;
	typedef std::set<Symbol> AtomKeys;
	inline AtomKeys		atomNames() const;
	Atom			*findAtom(Symbol) const;
	Atom			*findAtom(Symbol name, char altLoc) const;
	typedef std::pair<AtomsMap::const_iterator, AtomsMap::const_iterator>	RangeAtoms;
	RangeAtoms		findRangeAtoms(Symbol) const;

	bool			bondedTo(const Residue *r,
					 bool checkNever=false) const;
	std::vector<Residue *>	bondedResidues() const;

	// Properties
	inline Symbol		type() const;
	inline void		setType(Symbol t);
	inline const MolResId	&id() const;
	inline void		setId(MolResId &mid);
	inline bool		isHelix() const;
	void			setIsHelix(bool b);
	inline bool		isSheet() const;
	void			setIsSheet(bool b);
	inline bool		isStrand() const;
	void			setIsStrand(bool b);
	inline int		ssId() const;
	inline void		setSsId(int id);
	inline bool		isHet() const;
	inline void		setIsHet(bool);
	char			bestAltLoc() const;
	PyObject		*kdHydrophobicity() const;
	bool			isIsolated() const;
	bool			isMetal() const;
	bool			hasSurfaceCategory(Symbol category) const;
	bool			hasNucleicAcidSugar() const;

	// Labels
	inline const std::string &label() const;
	void			setLabel(const std::string &);
	inline const Vector	&labelOffset() const;
	void			setLabelOffset(const Vector &offset);
	inline const Color	*labelColor() const;
	void			setLabelColor(/*NULL_OK*/ const Color *color);
	Point			labelCoord() const;
	Vector			currentLabelOffset() const;

	// Filled rings
	inline bool		fillDisplay() const;
	void			setFillDisplay(bool d);
	enum FillMode { Thin, Thick };
	inline FillMode		fillMode() const;
	void			setFillMode(FillMode mode);
	inline const Color	*fillColor() const;
	void			setFillColor(/*NULL_OK*/ const Color *color);

	// Ribbons
	bool			hasRibbon() const;
	enum RibbonDrawMode { Ribbon_2D, Ribbon_Edged, Ribbon_Round,
			      Ribbon_Custom };
	inline bool		ribbonDisplay() const;
	void			setRibbonDisplay(bool display);
	inline const Color	*ribbonColor() const;
	void			setRibbonColor(/*NULL_OK*/ const Color *);
	const Color		*shownRibbonColor() const;
	inline RibbonDrawMode	ribbonDrawMode() const;
	void			setRibbonDrawMode(RibbonDrawMode);
	inline RibbonXSection	*ribbonXSection() const;
	void			setRibbonXSection(/*NULL_OK*/ RibbonXSection *xs);
	inline RibbonStyle	*ribbonStyle() const;
	void			setRibbonStyle(/*NULL_OK*/ RibbonStyle *s);
	inline RibbonData	*ribbonData() const;
	void			setRibbonData(/*NULL_OK*/ RibbonData *d);
	RibbonResidueClass	*ribbonResidueClass() const;
	void			setRibbonResidueClass(/*NULL_OK*/ RibbonResidueClass *c);
	enum RS { RS_TURN, RS_HELIX, RS_SHEET, RS_ARROW, RS_NUCLEIC };
	RibbonXSection		*ribbonFindXSection(RibbonDrawMode mode) const;
	RS			ribbonFindStyleType() const;
	RibbonStyle		*ribbonFindStyle() const;
	GeometryVector		ribbonCenters() const;
	GeometryVector		ribbonNormals() const;
	GeometryVector		ribbonBinormals() const;
	static RibbonStyle	*getDefaultRibbonStyle(int ss);

	// Selections
	std::string		oslIdent(Selector start = SelDefault,
					 Selector end = SelDefault) const;
	Selectable::Selectables oslChildren() const;
	Selectable::Selectables oslParents() const;
	bool			oslTestAbbr(OSLAbbreviation *a) const;
	inline Selector		oslLevel() const;
	static const Selector	selLevel = SelResidue;

	// Track changes
	void		trackReason(const NotifierReason &reason) const;
	struct Reason: public NotifierReason {
                Reason(const char *r): NotifierReason(r) {}
        };
	static Reason	RESIDUE_CHANGED;
	static Reason	TYPE_CHANGED;
	static Reason	MOLRESID_CHANGED;
	static Reason	HELIX_CHANGED;
	static Reason	SHEET_CHANGED;
	static Reason	STRAND_CHANGED;
	static Reason	HET_CHANGED;
	static Reason	LABEL_CHANGED;
	static Reason	LABEL_OFFSET_CHANGED;
	static Reason	LABEL_COLOR_CHANGED;
	static Reason	FILL_DISPLAY_CHANGED;
	static Reason	FILL_MODE_CHANGED;
	static Reason	FILL_COLOR_CHANGED;
	static Reason	RIBBON_DISPLAY_CHANGED;
	static Reason	RIBBON_COLOR_CHANGED;
	static Reason	RIBBON_DRAWMODE_CHANGED;
	static Reason	RIBBON_XSECTION_CHANGED;
	static Reason	RIBBON_STYLE_CHANGED;
	static Reason	RIBBON_DATA_CHANGED;
	static Reason	RIBBON_RESIDUE_CLASS_CHANGED;

	// Python
	virtual PyObject	*wpyNew() const;
	virtual void		wpyAssociate(PyObject* o) const;
	bool	registerField(Symbol field, int value);
	bool	registerField(Symbol field, double value);
	bool	registerField(Symbol field, const std::string &value);
	bool	getRegField(Symbol field, int *value) const;
	bool	getRegField(Symbol field, double *value) const;
	bool	getRegField(Symbol field, std::string *value) const;

	// return atoms that received assignments from the template
	std::vector<Atom *>	templateAssign(
				  void (*assignFunc)(Atom *, const char *),
				  const char *app,
				  const char *templateDir,
				  const char *extension
				) const;
	std::vector<Atom *>	templateAssign(
				  void (Atom::*assignFunc)(const char *),
				  const char *app,
				  const char *templateDir,
				  const char *extension
				) const;
	std::vector<Atom *>	templateAssign(assigner, 
				  const char *app,
				  const char *templateDir,
				  const char *extension
				) const;

private:
	friend class Molecule;
	void	operator=(const Residue &);	// disable
		Residue(const Residue &);	// disable
		virtual ~Residue();

	std::multimap<Symbol, Atom *>	Atoms_;
	Molecule	*Molecule_;

	Symbol		type_;
	MolResId	rid;

	bool		isHelix_;
	bool		isSheet_;
	int		ssId_;
	bool		isHet_;

	// need to be able to change MolResIds
	friend class PDBio;

	static TrackChanges::Changes *const changes;
	inline void		setMajorChange();
	typedef std::map<std::string, double> hpInfoMap;
	static hpInfoMap kdHpMap;

	std::string	label_;
	Vector		labelOffset_;
	const Color	*labelColor_;
	friend class MoleculeLensModel;
	mutable const Atom *labelAtom_;	// cached from MoleculeLensModel

	bool		fillDisplay_;
	FillMode	fillMode_;
	const Color	*fillColor_;

	const Color	*ribbonColor_;
	RibbonDrawMode	ribbonDrawMode_;
	bool		ribbonDisplay_;
	RibbonXSection	*ribbonXSection_;
	RibbonStyle	*ribbonStyle_;
	RibbonData	*ribbonData_;
	mutable RibbonResidueClass *ribbonResidueClass_;
	void		assignRibbonResidueClass() const;

	Residue(Molecule *, Symbol t, MolResId rid);
	Residue(Molecule *, Symbol t, Symbol chain, int pos, char insert);
};

} // namespace molecule

#endif
