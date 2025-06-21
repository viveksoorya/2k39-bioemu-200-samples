# -----------------------------------------------------------------------------
# Register topography command to surface from volume plane.
#
def struts(*args):
    import Struts
    Struts.struts_command(*args)
def unstruts(*args):
    import Struts
    Struts.unstruts_command(*args)
from Midas.midas_text import addCommand
addCommand('struts', struts, unstruts, help = True)
