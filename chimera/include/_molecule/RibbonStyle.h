#ifndef chimera_RibbonStyle_h
#define	chimera_RibbonStyle_h
#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

#include <vector>
#include <_chimera/Notifier.h>
#include <_chimera/TrackChanges.h>

namespace molecule {

class MOLECULE_IMEX RibbonStyle: public NotifierList, public otf::WrapPyObj  {
public:
		virtual ~RibbonStyle();
public:
	virtual float		width(float t) const = 0;
	virtual float		thickness(float t) const = 0;
	virtual void		setSize(const std::vector<float> &sz,
							bool fromConstructor=false) = 0;
	virtual std::vector<float>
				size() const = 0;

	virtual void	notify(const NotifierReason &reason) const;
	struct Reason: public NotifierReason {
                Reason(const char *r): NotifierReason(r) {}
        };
	static Reason		SIZE_CHANGED;

	virtual PyObject* wpyNew() const;
private:
	RibbonStyle(const RibbonStyle&);		// disable
	RibbonStyle& operator=(const RibbonStyle&);	// disable
private:
protected:
	static TrackChanges::Changes *const changes;
public:
	virtual void	wpyAssociate(PyObject* o) const;
public:
	RibbonStyle();
};

} // namespace molecule

#endif
