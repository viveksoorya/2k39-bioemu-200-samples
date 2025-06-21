#ifndef chimera_ChainTrace_h
#define	chimera_ChainTrace_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

namespace molecule {

class PseudoBondMgr;

class MOLECULE_IMEX ChainTrace: public PseudoBondGroup  {
	friend class PseudoBondMgr;
public:
		virtual ~ChainTrace();
public:
	inline bool		trackMolecule() const;
	void		setTrackMolecule(bool);

	virtual PyObject* wpyNew() const;
private:
	bool		trackMolecule_;
	ChainTrace(PseudoBondMgr *, Symbol category);
};

} // namespace molecule

#endif
