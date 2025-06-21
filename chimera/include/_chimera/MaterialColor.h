#ifndef Chimera_MaterialColor_h
# define Chimera_MaterialColor_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include <otf/WrapPy2.h>
# include "Array.h"
# include "_chimera_config.h"
# include "Material.h"
# include "Color.h"
# include <GfxInfo.h>

namespace chimera {

class CHIMERA_IMEX MaterialColor: public Color
{
	MaterialColor(const MaterialColor&);		// disable
	MaterialColor& operator=(const MaterialColor&);	// disable
public:
	MaterialColor(Material *material = NULL);
	MaterialColor(double red, double green, double blue,
						Material *material = NULL);
# ifndef WrapPy
	MaterialColor(const Array<double, 3> &rgb,
						Material *material = NULL);
# endif
	MaterialColor(double red, double green, double blue, double alpha,
						Material *material = NULL);
# ifndef WrapPy
	MaterialColor(const Array<double, 4> &rgba,
						Material *material = NULL);
# endif
	MaterialColor(const MaterialColor &m0, const MaterialColor &m1,
						double fraction);
	virtual	~MaterialColor();
# ifndef WrapPy
	virtual Array<double, 4>	rgba() const;
	virtual bool	isTranslucent() const throw ();
# endif

# ifndef WrapPy
	// We sort colors to group colors that have the same material
	// so we can use glColor instead of glMaterial to switch colors.
	virtual void	draw() const throw ();
	virtual ColorGroup *colorGroup() const;
	virtual void	x3dWrite(std::ostream& out, unsigned indent, unsigned count) const;
	virtual void	notify(const NotifierReason &reason) const;

	virtual void	wpyAssociate(PyObject* o) const;
	virtual PyObject* wpyNew() const;
# endif
	// ATTRIBUTE: material
	Material	*material() const;

# ifndef WrapPy
	Array<double, 3>
			ambientDiffuse() const;
# endif
	void		ambientDiffuse(/*OUT*/ double *red, /*OUT*/ double *green,
						/*OUT*/ double *blue) const;
# ifndef WrapPy
	void		setAmbientDiffuse(const Array<double, 3> &ad);
# endif
	void		setAmbientDiffuse(double red, double green, double blue);
	double		opacity() const;
	void		setOpacity(double o);

	// Ignore the material
	virtual bool	operator<(const Color &c) const {
				if (typeid(*this) != typeid(c))
					return typeid(*this).before(typeid(c));
				const MaterialColor &mc = static_cast<const MaterialColor &>(c);
				if (ambDiff[0] < mc.ambDiff[0])
					return true;
				else if (ambDiff[0] > mc.ambDiff[0])
					return false;
				else if (ambDiff[1] < mc.ambDiff[1])
					return true;
				else if (ambDiff[1] > mc.ambDiff[1])
					return false;
				else if (ambDiff[2] < mc.ambDiff[2])
					return true;
				else if (ambDiff[2] > mc.ambDiff[2])
					return false;
				else
					return ambDiff[3] < mc.ambDiff[3];
			}
	virtual bool	operator==(const Color &c) const {
				if (typeid(*this) != typeid(c))
					return false;
				const MaterialColor &mc = static_cast<const MaterialColor &>(c);
				return ambDiff[0] == mc.ambDiff[0]
					&& ambDiff[1] == mc.ambDiff[1]
					&& ambDiff[2] == mc.ambDiff[2]
					&& ambDiff[3] == mc.ambDiff[3];
			}
private:
	void		commonInit();
	Material	*mat;
	GLdouble	ambDiff[4];
	static TrackChanges::Changes *const
			changes;
};

# ifndef WrapPy

inline Material *
MaterialColor::material() const
{
	return mat;
}

inline ColorGroup *
MaterialColor::colorGroup() const
{
	return mat;
}

# endif /* WrapPy */

} // namespace chimera

#endif
