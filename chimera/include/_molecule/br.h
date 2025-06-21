#ifndef bondrot_br_h
# define bondrot_br_h

// Bond Rotation support

// Every root atom has its own Component -- except Components are
// lazily created.  Since there is a root atom for each component
// of the Molecule, there will be one for each bond rotation,
// ligand, -mer, water, etc.  Many of these transformations will
// be the same (i.e., the identity transformation).

// Bond rotations can be nested.  Thus we need to maintain a
// transformation hierarchy.  The bond rotations are the glue
// between the transformations in the hierarchy.

# include <vector>
# include <otf/WrapPy2.h>
# include <_chimera/Notifier.h>
# include <_chimera/TrackChanges.h>
# include "chimtypes.h"
# include "_molecule_config.h"

namespace molecule {

class Atom;
class Bond;
class Molecule;

class Component;
class BondRot;

class MOLECULE_IMEX Component
{
	// per-component (graph-wise) of molecule
	Component	&operator=(const Component &);	// disable
	Component(const Component &);			// disable
public:
	// If root Atom is deleted (or any other in component), we
	// need to potentially subdivide this component into many.  First
	// reset root to be root of parent's bond to component, then ....
	//
	Atom		*rootAtom;	// identifying Atom
	int		size;		// number of atoms in component
	int		totalSize;	// + number of atoms in children
	BondRot		*parentRot;
	typedef std::vector<BondRot *> Rots;
	Rots		childRots;

	Component(Atom *r, int sz):
			rootAtom(r), size(sz), totalSize(sz), parentRot(0) {}
	void		repair();
	void		adjustTotalSize(int delta);
	void		xform(const Xform &xf, BondRot *stop);
	void		addChild(BondRot *br, Component *c, Atom *a);
};

class MOLECULE_IMEX BondRot: public NotifierList, public otf::WrapPyObj
{
	// A bond rotation becomes invalid if it no longer separates a graph
	// (molecule) into several components or if its bond is deleted.
	friend class Molecule;
	friend class Component;
	BondRot	&operator=(const BondRot &);	// disable
	BondRot(const BondRot &);		// disable
public:
	explicit	BondRot(Bond *b);
			~BondRot();
	void		destroy();
	Atom		*biggerSide() const;

	// ATTRIBUTE: bond
	Bond		*bond() const { return bond_; }
	void		xformParent(const Xform &xf);
	void		xformChildren(const Xform &xf, BondRot *stop = NULL);

	double		angle() const;
	void		setAngle(double angle, Atom *anchor);
	void		adjustAngle(double delta, Atom *anchor);
	void		reset();

# ifndef WrapPy
	virtual void	wpyAssociate(PyObject* o) const;
	virtual PyObject* wpyNew() const;
	virtual void	notify(const NotifierReason &reason) const;

	struct MOLECULE_IMEX Reason: public NotifierReason {
		Reason(const char *r): NotifierReason(r) {}
	};
	// notifier reasons
	static Reason CHANGED;
# endif /* ifndef WrapPy */
private:
	Component*	parentComponent;
	Atom*		parentAtom;
	Component*	childComponent;
	Atom*		childAtom;
	Molecule*	molecule;
	Bond*		bond_;
	static TrackChanges::Changes *const changes;
	// angle_ is from first atom towards second atom in bond
	double		angle_;
	void		repair(bool parent);
};

}

#endif
