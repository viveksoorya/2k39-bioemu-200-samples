def mdacmd(cmdname, args):
	from MDA import mdacommand
	mdacommand(cmdname, args)

from Midas.midas_text import addCommand
addCommand('mda', mdacmd, help = True) #someday!			


