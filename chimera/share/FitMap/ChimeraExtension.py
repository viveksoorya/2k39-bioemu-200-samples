# -----------------------------------------------------------------------------
#
from chimera.extension import EMO, manager

# -----------------------------------------------------------------------------
#
class Fit_Map_EMO(EMO):

    def name(self):
        return 'Fit in Map'
    def description(self):
        return 'Move atomic model or map to best fit locations in a map'
    def categories(self):
        return ['Volume Data']
    def icon(self):
        return None
    def activate(self):
        self.module('gui').show_fit_map_dialog()
        return None

manager.registerExtension(Fit_Map_EMO(__file__))

# -----------------------------------------------------------------------------
#
def fit_map(cmdname, args):
    from FitMap import fitcmd
    fitcmd.fitmap_command(cmdname, args)
def unfit_map(cmdname, args):
    from FitMap.move import position_history
    position_history.undo()
    
from Midas import midas_text as mt
mt.addCommand('fitmap', fit_map, unfit_map, help = True)

# -----------------------------------------------------------------------------
#
def fit_map_cb():
    from FitMap import fitmap as F
    F.move_selected_atoms_to_maximum()
def fit_map_rotation_only_cb():
    from FitMap import fitmap as F
    F.move_selected_atoms_to_maximum(optimize_translation = False)
def fit_map_shift_only_cb():
    from FitMap import fitmap as F
    F.move_selected_atoms_to_maximum(optimize_rotation = False)
def move_atoms_to_maxima():
    from FitMap import fitmap as F
    F.move_atoms_to_maxima()

from Accelerators import add_accelerator
add_accelerator('ft', 'Move model to maximize density at selected atoms',
                fit_map_cb)
add_accelerator('fr', 'Rotate model to maximize density at selected atoms',
                fit_map_rotation_only_cb)
add_accelerator('fs', 'Shift model to maximize density at selected atoms',
                fit_map_shift_only_cb)
add_accelerator('mX', 'Move selected atoms to local maxima',
                move_atoms_to_maxima)
