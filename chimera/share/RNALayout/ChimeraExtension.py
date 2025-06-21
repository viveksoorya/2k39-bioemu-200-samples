# -----------------------------------------------------------------------------
# Register rna command.
#
def rna_cmd(cmdname, args):
  import RNALayout
  RNALayout.rna_command(cmdname, args)
from Midas.midas_text import addCommand
addCommand('rna', rna_cmd, help = True)
