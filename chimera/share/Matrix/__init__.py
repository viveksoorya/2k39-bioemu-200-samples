#
# Operations with 3 by 4 matrices where first 3 columns are a rotation and the
# 4th column is a translation.  Rotation is applied and then translation.
#
# The 3 by 4 matrices are called "transforms" and are represented with tuples,
# or lists, or numpy arrays.  Another representation is the Chimera Xform
# class implemented in C++.
#
# Vectors and points are represented as tuples, lists, numpy arrays, or
# Chimera C++ objects Point and Vector.
#

# Operations on vectors
from matrix import apply_matrix
from matrix import apply_matrix_without_translation
from matrix import apply_inverse_matrix
from matrix import transform_points
from matrix import transform_vectors
from matrix import xform_xyz
from matrix import xform_points
from matrix import xform_vectors
from matrix import cross_product
from matrix import cross_products
from matrix import normalize_vector
from matrix import normalize_vectors
from matrix import norm
from matrix import maximum_norm
from matrix import inner_product
from matrix import vector_angle
from matrix import length
from matrix import distance
from matrix import linear_combination
from matrix import linear_combination_3
from matrix import vector_sum
from matrix import point_bounds
from _volume import inner_product_64
from matrix import project_to_axis

# Operations on transform and xform matrices.
from matrix import invert_matrix
from matrix import multiply_matrices
from matrix import matrix_products
from matrix import transpose            # For square matrices
from matrix import transpose_matrix     # Rotation part only, 3x4 -> 3x4.
from matrix import zero_translation
from matrix import coordinate_transform
from matrix import coordinate_transform_list
from matrix import coordinate_transform_xforms
from matrix import orthogonalize
from matrix import interpolate_xforms
from matrix import fractional_xform

# Comparing and converting transforms.
from matrix import xforms_differ
from matrix import same_xform
from matrix import xform_matrix
from matrix import chimera_xform

# Creating transform matrices
from matrix import identity_matrix
from matrix import translation_matrix
from matrix import scale_matrix
from matrix import rotation_transform
from matrix import rotation_from_axis_angle
from matrix import vector_rotation_transform
from matrix import cross_product_transform
from matrix import orthonormal_frame
from matrix import skew_axes
from matrix import euler_xform
from matrix import euler_rotation

# Transform properties
from matrix import is_identity_matrix
from matrix import rotation_axis_angle
from matrix import axis_center_angle_shift
from matrix import axis_point_adjust
from matrix import shift_and_angle
from matrix import determinant
from matrix import cell_angles_and_rotation
from matrix import cell_angles
from matrix import euler_angles
from matrix import transformation_description

# Miscellaneous
from matrix import sign
