#ifndef chimera_RibbonXSection_h
#define	chimera_RibbonXSection_h

#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <otf/WrapPy2.h>
#include <vector>
#include "_molecule_config.h"
#include "chimtypes.h"

namespace molecule {

class MOLECULE_IMEX RibbonXSection: public NotifierList, public otf::WrapPyObj  {
public:
	virtual ~RibbonXSection();
public:
	const std::vector<std::pair<float, float> >	&outline() const;
	void		setOutline(const std::vector<std::pair<float, float> >
					&o);
	void		addOutlineVertex(float x, float y);
	const std::vector<std::pair<float, float> > &outlineNormals() const;
	bool		smoothWidth() const;
	void		setSmoothWidth(bool sw);
	bool		smoothLength() const;
	void		setSmoothLength(bool sl);
	bool		closed() const;
	void		setClosed(bool c);

	virtual PyObject* wpyNew() const;

	virtual void	notify(const NotifierReason &reason) const;
	struct Reason: public NotifierReason {
                Reason(const char *r): NotifierReason(r) {}
        };
	static Reason		OUTLINE_CHANGED;
	static Reason		SMOOTH_WIDTH_CHANGED;
	static Reason		SMOOTH_LENGTH_CHANGED;
	static Reason		CLOSED_CHANGED;

	static RibbonXSection *line();
	static RibbonXSection *square();
	static RibbonXSection *circle();
private:
	std::vector<std::pair<float, float> > outline_;
	mutable std::vector<std::pair<float, float> > normals_;
	bool		smoothWidth_;
	bool		smoothLength_;
	bool		closed_;
protected:
	static TrackChanges::Changes *const changes;
public:
	RibbonXSection(bool sw, bool sl, bool c);
	RibbonXSection(int n, const float (*o)[2],
				bool sw, bool sl, bool c);
	RibbonXSection(const std::vector<std::pair<float, float> > &o,
				bool sw, bool sl, bool c);
};

} // namespace molecule

#endif
