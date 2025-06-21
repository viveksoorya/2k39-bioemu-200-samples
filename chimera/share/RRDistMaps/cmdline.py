# --- UCSF Chimera Copyright ---
# Copyright (c) 2014 Regents of the University of California.
# All rights reserved. This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use. This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

def run(cmdName, args):
	"""Commands are expected to be in form of:
	registered_command subcommand subcommand_arguments ...
	We extract the subcommand and try to match it to
	commands listed in "_optArgsTable" below and call
	the matching function with the rest of the arguments
	"""

	fields = args.split(None, 1)
	if len(fields) > 1:
		opt, args = fields
	elif len(fields) == 0:
		from chimera import UserError
		raise UserError ("\'%s\' requires arguments; "
				 "use \'help %s\' for more information"
				% (cmdName, cmdName))
	else:
		opt = fields[0]
		args = ''
	bestMatch = None
	for optName in _optArgsTable.iterkeys():
		if optName.startswith(opt):
			if bestMatch is not None:
				from chimera import UserError
				raise UserError('option \'%s\' is ambiguous' % opt)
			else:
				bestMatch = optName
	if bestMatch is None:
		from chimera import UserError
		raise UserError('unknown option \'%s\';'
				'use \'help %s\'for more information'
				% (opt, cmdName))
	func, kw = _optArgsTable[bestMatch]
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(func,args, **kw)

def rrdmRaise(molecules=None):
	"""This raises the RRdm Dialog"""
	import gui
	gui.display()

def rrdmHide(molecules=None):
	"""Hide the RRdm Dialog"""
	import gui
	gui.hide()

# Supply args for each command
_optArgsTable = {
	'raise':(rrdmRaise, {}),
	'hide': (rrdmHide, {}),
}
