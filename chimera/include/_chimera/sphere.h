#ifndef Chimera_sphere_h
# define Chimera_sphere_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include "Geom3d.h"
# include <vector>
# include "_chimera_config.h"

namespace chimera {

struct CHIMERA_IMEX Sphere {
	// IMPLICIT COPY CONSTRUCTOR
	const Point& center() const;
	void	setCenter(const Point& p);
	Real radius() const;
	void	setRadius(Real r);
	Real radiusSq() const;
	void	setRadiusSq(Real rsq);
	void	merge(const Sphere& s);
	void	xform(const Xform& x);
	bool	inside(const Point& xyz) const;
private:
	Point m_center;
	Real m_radius;
	Real m_radius_sq;
};

#ifndef WrapPy
inline const Point&
Sphere::center() const
{
	return m_center;
}

inline Real
Sphere::radius() const
{
	return m_radius;
}

inline Real
Sphere::radiusSq() const
{
	return m_radius_sq;
}
#endif

typedef std::vector<Vector> SpherePts;

CHIMERA_IMEX extern const SpherePts &
		sphere_pts(double radius, double density);

} // namespace chimera

#endif
