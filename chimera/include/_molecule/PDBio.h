#ifndef chimera_PDBio_h
#define	chimera_PDBio_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <iostream>
#include <vector>
#include <map>
#include <set>
#include <sstream>
#include <deque>
#include <string>
#include <stdlib.h>
#include <otf/WrapPy2.h>
#include "pdb/PDB.h"
#include "_molecule_config.h"
#include "Residue.h"
#include "chimtypes.h"

namespace molecule {

class MOLECULE_IMEX PDBio: public otf::WrapPyObj  {
public:
		virtual ~PDBio();
public:
	inline static Real	bondLengthTolerance();
	inline static void	setBondLengthTolerance(Real t);
	static bool	standardResidue(const std::string &);
	static bool	standardResidue(Symbol type) {
				return standardResidue(type.str());
			}
	static void	addStandardResidue(const std::string &);
	static void	removeStandardResidue(const std::string &);
	static void	setAtomOrderFunc(const std::vector<Symbol>&
			  (*orderFunc)(Symbol));
	static std::vector<std::string> recordOrder;
	enum What {
		ATOMS, ATOMQRS, COVALENT_BONDS, HYDROGEN_BONDS, SALT_BRIDGES,
		HEADERS, ALL_CONECT, SECONDARY_STRUCTURE,
		ALL_FRAMES, DELIMITER_MODEL, NUM_FLAGS
	};
	std::vector<Molecule *> readPDBstream(std::istream &input,
		const char *filename, int *lineNum, std::ostream *errOut=NULL);
	std::vector<Molecule *> readPDBfile(const char *filename,
		std::ostream *errOut=NULL);
	void		writePDBstream(const std::vector<const Molecule *>
				&mols, std::ostream &os, const char *filename);
	void		writePDBfile(const std::vector<const Molecule *> &,
							const char *filename);
	inline bool		ok();
	inline std::string	error();
	inline bool		explodeNMR();
	inline void		setExplodeNMR(bool b);
	std::vector<bool>	&whatToDo() { return what; }
	std::vector<bool>	&readMask() { return rMask; }
	std::vector<bool>	&writeMask() { return wMask; }
	bool		(*readPDB())(PDB *, Molecule *,
				const std::map<int, Atom *> *)
				{ return rFunc; }
	void		setReadPDB(bool (*r)(PDB *, Molecule *,
					const std::map<int, Atom *> *))
				{ rFunc = r; }
	void		setPostprocessAtom(void (*)(PDB *, Molecule *,
				Residue *, Atom *,
				const std::map<int, Atom *> *));
private:
	std::vector<bool>	what;
	std::vector<bool>	rMask, wMask;
	bool		(*rFunc)(PDB *, Molecule *,
				const std::map<int, Atom *> *);
	bool		wFunc;
private:
	bool		explode;
	std::string	ioErr;
	static Real	tolerance;
	int		outModelNum;
	static const std::vector<Symbol>& (*orderFunc)(Symbol);
	bool		readOneMolecule(std::istream &, Molecule *,
				const char *, int *,
				std::map<int, Atom *, std::less<int> > &,
				std::vector<Residue *> *,
				std::vector<Residue *> *,
				std::vector<PDB> *,
				std::vector<PDB::Conect_> *,
				std::vector<PDB> *,
				std::set<MolResId> *,
				bool *, std::ostream *);
	static void	assignSecondaryStructure(Molecule *m,
				const std::vector<PDB> &ss,
				std::ostream *errOut);
	void		writeCoordSet(std::ostream &, const Molecule *,
				const CoordSet *, 
				std::map<Atom *, int> *rev_asn, std::set<Atom *> *written);
	void		writeConect(std::ostream &, const Molecule *,
				const CoordSet *,
				std::map<Atom *, int> *rev_asn, std::set<Atom *> *written);
	void	(*postprocessAtom)(PDB *, Molecule *, Residue *, Atom *,
				const std::map<int, Atom *> *);
	static void	addImpliedHBonds(Molecule *, std::vector<Residue *> *,
				std::vector<Residue *> *, std::ostream *);
public:
	static void	connectMolecule(Molecule *, std::vector<Residue *> *,
				std::vector<Residue *> *, std::set<Atom *> *,
				std::set<MolResId> *);
public:
	static void addHBond(std::map<int, Atom *> &atomSerialNums,
			int from, int to, std::ostream *);
	static void addHBond(Atom *, Atom *);
private:
	void	writeHBondConect(Atom *, std::ostream &, const Molecule *,
			const CoordSet *, std::map<Atom *, int> *) const;
public:
private:
	void	writeMetalComplexConect(Atom *, std::ostream &, const Molecule *,
			const CoordSet *, std::map<Atom *, int> *) const;
public:
	virtual PyObject* wpyNew() const;
	static const std::vector<std::string> &getRecordOrder();
	typedef bool (*preWFtype)(std::ostream &, PDB *, bool *,
		PDB *, const Molecule *, const CoordSet *, Atom *,
		const std::map<Atom *, int> *);
	typedef void (*postWFtype)(std::ostream &, PDB *, bool *,
		PDB *, const Molecule *, const CoordSet *, Atom *,
		const std::map<Atom *, int> *);
	void addPreWriteFunc(int, preWFtype);
	void addPostWriteFunc(int, postWFtype);
private:
	static bool readANISOU(PDB *, Molecule *,
					const std::map<int, Atom *> *);
	static void writeANISOU(std::ostream &, PDB *, bool *, PDB *,
		const Molecule *, const CoordSet *, Atom *,
		const std::map<Atom *, int> *);
public:
	static PDBio *writer; // kludge for wFunc
	std::map<int, std::vector<preWFtype> > preWFuncs;
	std::map<int, std::vector<postWFtype> > postWFuncs;
public:
	PDBio();
	PDBio(const std::vector<bool> &w);
	PDBio(const std::vector<bool> &w, const std::vector<bool> &rm,
						const std::vector<bool> &wm);
};

} // namespace molecule

#endif
