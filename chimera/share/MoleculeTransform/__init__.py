# -----------------------------------------------------------------------------
# Apply a rotation and translation to atoms.
#
def transform_atom_coordinates(atoms, xform):

    for a in atoms:
        a.setCoord(xform.apply(a.coord()))

# -----------------------------------------------------------------------------
# Apply a rotation and translation to model coordinate axes.
#
def transform_coordinate_axes(model, xform):

    model.openState.localXform(xform)

# -----------------------------------------------------------------------------
#
from Matrix import euler_xform, euler_rotation
