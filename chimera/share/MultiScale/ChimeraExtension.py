import chimera.extension

class MultiScale_EMO(chimera.extension.EMO):
  def name(self):
    return 'Multiscale Models'
  def description(self):
    return 'Show multiscale model dialog'
  def categories(self):
    return ['Higher-Order Structure']
  def icon(self):
    return self.path('multiscale_icon.png')
  def activate(self):
    self.module().show_multiscale_model_dialog()
    return None

# -----------------------------------------------------------------------------
#
emo = MultiScale_EMO(__file__)
chimera.extension.manager.registerExtension(emo)

# -----------------------------------------------------------------------------
#
execfile(emo.path('accelerators.py'), {})     # Register keyboard shortcuts
execfile(emo.path('viper_file_reader.py'), {})      # Register file reader

# -----------------------------------------------------------------------------
#
def show_biounit(molecules):

  # Display hexamers and smaller without MultiScale surfaces.
  msmall = []
  for m in molecules:
    import Molecule
    mc = len(Molecule.biological_unit_matrices(m))
    if mc > 1 and mc <= 6:
      from SymmetryCopies.symcmd import symmetry_copies
      symmetry_copies([m], 'biomt')
      msmall.append(m)

  # Display 7-mers and larger with MultiScale surfaces.
  mlist = [m for m in molecules if m not in msmall]
  import MultiScale
  MultiScale.show_biological_unit(mlist, show_dialog = False)

from ModelPanel import addButton
addButton('biological unit', show_biounit, balloon = 'Display the biological oligomer using\nREMARK 350 BIOMT matrices in the PDB file header.')
