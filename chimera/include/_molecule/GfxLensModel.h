#ifndef Chimera_GfxLensModel_h
# define Chimera_GfxLensModel_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include "LensModel.h"
# include <set>
# include <GfxInfo.h>

extern "C" {
typedef struct _object PyObject;
}

namespace molecule {

class Lens;
class Model;
class GfxModel;
class ColorGroup;

class GfxLensModel: public LensModel {
public:
	GfxLensModel(Lens *lens, GfxModel *gfx);
	virtual void	draw(const Viewer *, Viewer::DrawPass) const;
	virtual void	drawPick(const Viewer *) const;
	virtual void	invalidateCache();
	virtual void	invalidateSelection();
	virtual bool	bsphere(Sphere *s) const;
	virtual bool	bbox(BBox *box) const;

	Model		*model() const;

	void		updateModel(const NotifierReason &);
	void		updateColorGroup(ColorGroup *, const NotifierReason &);
private:
	virtual		~GfxLensModel();
	class ModelNotifier: public Notifier {
	public:
		void update(const void *tag, void *,
					const NotifierReason &reason) const {
			GfxLensModel *gfxlm = static_cast<GfxLensModel *>
						(const_cast<void *>(tag));
			gfxlm->updateModel(reason);
		}
	};
	GfxModel	*gfx;
	ModelNotifier	modelNotifier;
	mutable bool	dirty;
};

} // namespace molecule

#endif
