# Author: Shawn Waldon
# Written as part of the SketchBio project, which is funded
# by the NIH (award number 50-P41-EB002025).
import chimera.extension

#
#
def write_vtk(path):
    import ExportVTK
    ExportVTK.write_scene_as_vtk(path)

descrip = 'Export scene as an input file for the <a href="http://vtk.org/">Visualization Toolkit</a>.  This file contains atom coordinates and associated data and molecular surfaces so that the objects can be processed and rendered with VTK.'

from chimera import exports
exports.register('VTK', '*.vtk', '.vtk', write_vtk, descrip)
