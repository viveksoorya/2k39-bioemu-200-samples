#ifndef Chimera_Spline_h
# define Chimera_Spline_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

#include "_molecule_config.h"
#include <stdexcept>
#include "chimtypes.h"

namespace molecule {

//
// Code is based on
//	Section 11.2, "Parametric Cubic Curves", in
//	Chapter 11, "Representing Curves and Surfaces", of
//	Computer Graphics, Principles and Practice,
//	Foley, van Dam, Feiner, Hughes
//	Second Edition,
//	Addison-Wesley Publishing Company, 1990.
//	pages 478-516.
//

typedef Real		BasisMatrix[4][4];

class MOLECULE_IMEX GeometryVector {
	Vector	vector_[4];
	// SEQUENCE METHODS
public:
				GeometryVector();
				GeometryVector(const GeometryVector &gv);
				GeometryVector(const Vector &g0,
						const Vector &g1,
						const Vector &g2,
						const Vector &g3);
	Vector	&operator[](unsigned n) { return vector_[n]; }
	const Vector
				&operator[](unsigned n) const
						{ return vector_[n]; }
	// at() is range-checked version of operator[]
	Vector	&at(unsigned n) {
					if (n >= 4)
						throw std::out_of_range(
							"index out of range");
					return vector_[n];
				}
	const Vector
				&at(unsigned n) const {
					if (n >= 4)
						throw std::out_of_range(
							"index out of range");
					return vector_[n];
				}
	const Vector
				&vector(int n) const { return vector_[n]; }
	void			setVector(int n, const Vector &v)
						{ vector_[n] = v; }
};

class MOLECULE_IMEX Spline {
	Real	matrix_[4][3];
public:
	enum SplineType {
		BSpline, Bezier, Cardinal, Hermite
	};
public:
				Spline(SplineType basisType,
					const GeometryVector &geometry,
					double param = 0.0);
	virtual			~Spline(void);
	Point	coordinate(Real t) const;
	Vector	tangent(Real t) const;
private:
	void			apply(const Real tvec[4],
					Real answer[3]) const;
public:
	static GeometryVector	makeGeometryVector(SplineType basisType,
					const GeometryVector &cp);
};

# ifndef WrapPy

MOLECULE_IMEX extern BasisMatrix	BSplineBasis;
MOLECULE_IMEX extern BasisMatrix	BezierBasis;
MOLECULE_IMEX extern BasisMatrix	CardinalBasis;
MOLECULE_IMEX extern BasisMatrix	HermiteBasis;

# endif /* WrapPy */

} // namespace molecule

#endif
