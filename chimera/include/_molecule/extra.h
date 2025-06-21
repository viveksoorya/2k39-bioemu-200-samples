#ifndef Chimera_extra_h
# define Chimera_extra_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <vector>
# include <set>
# include "chimtypes.h"
# include "_molecule_config.h"
# include "Atom.h"

extern "C" {
typedef struct _object PyObject;
}

namespace molecule {

class Atom;
class Bond;
class Residue;
class Root;
class TemplateResidue;
class Molecule;
class CoordSet;

MOLECULE_IMEX extern std::vector<Bond *> bondsBetween(Residue *r0, Residue *r1, bool onlyOne = false);
MOLECULE_IMEX extern PyObject *numpyArrayFromAtoms(std::vector<const Atom *> atoms, CoordSet *crdSet=NULL, bool xformed=false);
MOLECULE_IMEX extern PyObject *fillCoordSet(CoordSet *cs, std::vector<Atom *> atoms, PyObject *crds);
MOLECULE_IMEX extern PyObject *RMSD_fillMatrix(PyObject *M, PyObject *Si, PyObject *Sj);
MOLECULE_IMEX extern PyObject *RMSD_matrix(double l, double m, double n, double s);
MOLECULE_IMEX extern PyObject *eigenMatrix(double q0, double q1, double q2, double q3);
MOLECULE_IMEX extern std::set<Residue *> atomsBonds2Residues(std::vector<const Atom *> atoms, std::vector<const Bond *> bonds);
MOLECULE_IMEX extern TemplateResidue *restmplFindResidue(Symbol name, bool start, bool end);
MOLECULE_IMEX extern void connectMolecule(Molecule *m);
MOLECULE_IMEX extern std::vector<Atom *> metalAtoms(Molecule *m);
MOLECULE_IMEX extern std::vector<Atom *> ionLikeAtoms(Molecule *m);
MOLECULE_IMEX extern std::vector<Bond *> longBonds(Molecule *m);
MOLECULE_IMEX extern bool isProtein(Molecule *m);
MOLECULE_IMEX extern void assignCategory(Molecule *m, Root *r, Symbol cat);
MOLECULE_IMEX extern void categorizeSolventAndIons(const std::vector<Atom *> &atoms);
MOLECULE_IMEX extern std::vector<Molecule *> bondMolecules(const std::vector<const Bond *> &bonds);
MOLECULE_IMEX extern void setAtomDisplay(Molecule *m, bool display);
MOLECULE_IMEX extern void setAtomDrawMode(Molecule *m, Atom::DrawMode mode);
MOLECULE_IMEX extern void setBondDrawMode(Molecule *m, Bond::DrawMode mode);
MOLECULE_IMEX extern void upgradeAtomDrawMode(Molecule *m, Atom::DrawMode mode);
MOLECULE_IMEX extern void upgradeBondDrawMode(Molecule *m, Bond::DrawMode mode);
MOLECULE_IMEX extern void colorByElement(Molecule *m, bool carbonNone = false);
MOLECULE_IMEX extern void reportSizes();

} // namespace molecule

#endif
