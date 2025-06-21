# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: midas_text.py 42520 2024-04-25 17:04:11Z pett $

from __future__ import with_statement
import chimera
import re
import os
import sys
from chimera import help
from chimera import replyobj
from OpenSave import OpenModal, SaveModal, tildeExpand
from chimera import selection, specifier
from chimera import APPQUIT, ChimeraSystemExit
from chimera import CancelOperation

import Midas
from Midas import MidasError
from chimera.oslParser import OSLSyntaxError

aliases = {}
userSurfCategories = {}
savedSelection = selection.ItemizedSelection()

def makeCommand(text, reportAliasExpansion=True):
	text = text.strip()
	if not text or text[0] == '#':
		return False
	text = expandAliases(text, reportAliasExpansion)
	code = None
	if len(text) > 1 and "alias".startswith(text[:5]):
		# an alias; don't honor command-splitting on ';'
		splitText = (text,)
	else:
		splitText = _splitUnquoted(text, ';')
	anyWaitable = False
	for cmdText in splitText:
		cmd = cmdText.strip()
		if len(cmd) == 0:
			continue
		if cmd[0] == '#':
			continue
		if cmd[0] == '~':
			tilde = 1
			cmd = cmd[1:].strip()
		else:
			tilde = 0
		# DWEBER: below 'for' loop might be faster with re:
		#m = re.match('^[a-zA-Z0-9]+', cmd)
		#cmd = cmd[:m.end()]
		#args = cmd[m.end():].strip()
		args = ''
		for i in range(1,len(cmd)):
			if not cmd[i].isalnum():
				args = cmd[i:].strip()
				cmd = cmd[:i]
				break
		l = len(cmd)
		for c, f, uf, w in cmdList:
			if c[:l] == cmd:
				if not tilde:
					f(c, args)
					anyWaitable = anyWaitable or w
					if f == doWait:
						anyWaitable = False
					break
				elif uf is not None:
					uf('un' + c, args)
					anyWaitable = anyWaitable or w
					break
				else:
					cmd = '~' + cmd
		else:
			raise MidasError, \
				'Unrecognized command: "%s"' % cmd
		import chimera.update
		chimera.update.checkForChanges()
	return anyWaitable

scripting = False
def processCommandFile(filename, emulateRead=False, usingString=False):
	""" called by 'source' and 'read' commands """
	if usingString:
		import StringIO
		f = StringIO.StringIO(filename)
	else:
		from OpenSave import osOpen
		f = osOpen(filename)
		if f == None:
			error("Cannot read file '%s'" % filename)
			return
	global scripting
	recursive = scripting
	scripting = True
	if not chimera.nogui:
		# process presses of the Escape key
		chimera.tkgui.app.winfo_toplevel().bind("<Escape>", _escCB)
		global _scriptPause, _scriptAbort
		_scriptPause = _scriptAbort = False
	try:
		_processFile(f, emulateRead, filename)
	except CancelOperation:
		if not chimera.nogui:
			# need to get this message shown _after_ the
			# status from opening models...
			def _afterOpenStatus(*args):
				replyobj.status("script aborted")
				from chimera.triggerSet import ONESHOT
				return ONESHOT
			chimera.triggers.addHandler('post-frame',
						_afterOpenStatus, None)
	finally:
		f.close()
		if not chimera.nogui:
			# stop processing Escape key
			chimera.tkgui.app.winfo_toplevel().bind("<Escape>")
		if not recursive:
			scripting = False

def _escCB(event):
	global _scriptPause, _scriptAbort
	if event.state:
		_scriptPause = not _scriptPause
	else:
		_scriptAbort = True
	return 'break'

def _processFile(f, emulateRead, filename):
	from chimera.update import checkForChanges
	for lineno, line in enumerate(f.readlines()):
		if Midas.echoCommands():
			eline = '%d  %s' % (lineno+1, line.rstrip())
			replyobj.info(eline + '\n')
			replyobj.status(eline)
		try:
			if makeCommand(line):
				# update needed
				if emulateRead:
					checkForChanges()
				else:
					Midas.wait(1)
		except (MidasError, OSLSyntaxError), s:
			fn = filename
			if isinstance(fn, unicode):
				fn = fn.encode('utf8')
			replyobj.error('Error while sourcing %s, line %d:\n\n\t"%s"\n\n%s' % (fn, lineno, line[:-1], s))
			from chimera import triggers, COMMAND_ERROR
			triggers.activateTrigger(COMMAND_ERROR, (line, s))
			return
		if chimera.nogui:
			continue
		with chimera.update.blockFrameUpdates():
			# allow Escape key presses to be processed
			# but only restrict processing during our own
			# update() calls, otherwise modal dialogs will
			# be hosed
			from _chimera import restrictEventProcessing
			restrictEventProcessing("\x1b")
			# a timer event (which can't be restricted)
			# _could_ throw an exception, so...
			try:
				chimera.tkgui.app.update()
			finally:
				restrictEventProcessing("")
		needClear = False
		if _scriptPause and not chimera.nogui:
			replyobj.status("Script paused; hit shift-"
				"Escape to continue, Escape to abort",
				color="blue")
			needClear = True
		while _scriptPause and not _scriptAbort:
			from time import sleep
			sleep(0.05)
			chimera.tkgui.app.update()
			# if only allowing unpausing is desired,
			# use the below code instead of the line above
			"""
			with chimera.update.blockFrameUpdates():
				restrictEventProcessing("\x1b")
				try:
					chimera.tkgui.app.update()
				finally:
					restrictEventProcessing("")
			"""
		if needClear:
			replyobj.status("")
		if _scriptAbort:
			from chimera import triggers, SCRIPT_ABORT
			triggers.activateTrigger(SCRIPT_ABORT,
						 (filename, lineno, line))
			raise CancelOperation("cancel script")

def expandAliases(text, doReport):
	# expand aliases

	# don't expand if command itself is 'alias' or '~alias'
	if len(text) > 1 and "alias".startswith(text[:5]) \
	or len(text) > 2 and "~alias".startswith(text[:6]):
		return text
	# prevent semi-colons from messing up alias expansion...
	text = text.replace(';', ' ; ')

	expanded = []
	done = 0
	# expand aliases with positional arguments last...
	aliasOrder = aliases.keys()
	aliasOrder.sort(lambda a1, a2: cmp(a1[0] != "^", a2[0] != "^")
					or cmp("$1" in aliases[a1], "$1" in aliases[a2]))
	while not done:
		for alias in aliasOrder:
			if alias in expanded:
				continue
			expansion = aliases[alias]
			if alias[0] == "^":
				segments = text.split(" ; ")
				processedSegments = []
				matched = False
				for segment in segments:
					if not segment or segment.isspace():
						continue
					parts = segment.split(None, 1)
					if len(parts) == 1:
						cmd = parts[0]
						remainder = ""
					else:
						(cmd, remainder) = parts
					if cmd != alias[1:]:
						processedSegments.append(segment)
						continue
					processedSegments.append(
						_subExpand(expansion, remainder).replace(';', ' ; '))
					matched = True
				if not matched:
					continue
				text = " ; ".join(processedSegments)
				break

			words = text.split()
			if alias not in words:
				continue
			i = 0
			while i < len(words):
				startLen = len(words)
				if words[i] == alias:
					words[i:] = _subExpand(expansion,
								words[i+1:])
				if len(words) > startLen:
					i += len(words) - startLen
				i += 1
			text = " ".join(words)
			break
		else:
			done = 1
		if not done:
			expanded.append(alias)
			if doReport:
				message("Expanded alias '%s' to '%s'"
						% (alias, aliases[alias]))
				message("Resulting command is: %s" % text)
	return text

def _subExpand(expansion, remainder):
	if "$1" not in expansion:
		# not an alias that takes arguments
		if isinstance(remainder, basestring):
			return expansion + " " + remainder
		return [expansion] + remainder
	maxSub = 1
	while "$%d" % (maxSub+1) in expansion:
		maxSub += 1
	rejoin = isinstance(remainder, basestring)
	if rejoin:
		# split so we can join later
		remainder = remainder.split()
	if len(remainder) < maxSub:
		raise MidasError, "Not enough arguments given to expand alias"
	for i in range(maxSub, 0, -1): # replace $23 before $2
		expansion = expansion.replace("$%d" % i,
				remainder[i-1].replace('_', ' ').replace('\ ', '_'))
	remainder = remainder[maxSub:]
	if rejoin:
		return expansion + " ".join(remainder)
	return [expansion] + remainder

def first_arg(args):
	if args and args[0] in ["'", '"']:
		i = args.find(args[0], 1)
		if i == -1:
			raise MidasError("Unmatched quote in argument")
		return args[1:i], args[i + 1:].lstrip()
	tmp = args.split(None, 1)
	if not tmp:
		return "", ""
	if len(tmp) == 1:
		return tmp[0], ""
	return tmp

def keyword_match(keyword, keywords, unique=False):
	"""match keyword in list of keywords allowing prefix matching"""
	if not keyword:
		raise MidasError("Missing keyword")
	keyword = keyword.lower()
	if not unique:
		for i, k in enumerate(keywords):
			if k.startswith(keyword):
				return i
	else:
		matches = [(i, k) for i, k in enumerate(keywords) if k.startswith(keyword)]
		if len(matches) == 1:
			return matches[0][0]
		for i, k in enumerate(keywords):
			if k == keyword:
				return i
		raise MidasError("Keyword '%s' matches multiple known"
			" keywords: %s" % (
				keyword, " ".join([m[1] for m in matches])))
	raise MidasError("Keyword '%s' doesn't match any known keywords" % keyword)

def message(msg):
	replyobj.info(msg + "\n")
def warn(warning):
	replyobj.warning(warning + "\n")
def error(error):
	if chimera.nogui or scripting:
		replyobj.error(error)
	else:
		replyobj.status(error, color='red')
def clearError():
	replyobj.status("")

def doAtomSpecFunc(cmdName, args):
	# function that expects an atom spec argument
	exec 'Midas.%s(%s)' % (cmdName, repr(getSpecs(args)))

def doModelFunc(cmdName, args):
	# function that expects model numbers as arguments
	exec 'Midas.%s(%s)' % (cmdName, repr(getSpecs(args, modelLevel=1)))

def doArglessFunc(cmdName, args):
	# function that expects no arguments
	if args != "":
		raise MidasError, \
		"'%s' function takes no arguments" % cmdName
	exec 'Midas.%s()' % cmdName

def doExtensionFunc(extFunc, typed, invalid=[], specInfo=[]):
	"""Call a function based on user-typed arguments

	   doExtensionFunc introspects the function 'extFunc' to
	   determine its positional and keyword arguments.  The first
	   arguments in the user-typed 'typed' string are taken as
	   the positional arguments, and the remainder of the string
	   is assumed to be (space separated, quoting handled) key/value
	   pairs and are matched up to the appropriate keywords.
	   'invalid' is a list of arguments that are not valid for
	   the user to provide and are therefore screened from the
	   introspected arguments.  'specInfo' is a list of 3-tuples
	   specifying arguments that expect lists of atoms/residues/models
	   as values and that therefore are typed as atom specifiers.
	   Each 3-tuple consists of:

	   	- The keyword the user types or, for positional
			arguments, what the argument name should
			be treated as for type-guessing purposes
			(in either case it should end in "spec")
		- The real argument name used by the function (this
			will automatically be added to 'invalid')
		- The method name applied to the selection generated
			by the specifier to extract the desired list
			(typically 'atoms', 'residues', 'molecules',
			or 'models')

	   Keyword argument names can be typed in any case by the user
	   and will be matched to the appropriate keyword regardless
	   of its case.

	   The user need only type enough characters to uniquely
	   distinguish a keyword argument name.  Nonetheless, you
	   may want to provide a "front end" function to your actual
	   workhorse function, where the keyword arguments have more
	   user-friendly names.

	   Arguments values use some heuristic rules to convert to
	   their most "natural" type.  However, argument names can
	   influence how the value is handled.  In particular, if
	   the argument name ends in...

	   	- "color":  the argument is treated as a color name
			and converted to a MaterialColor
		- "spec":  the argument is assumed to be an atom
			specifier and the value type is a Selection
		- "file":  the argument is file; the user can provide
			"browse" or "browser" as the typed value and
			get a file browser for choosing the file.
			If the argment name ends in "savefile", a
			save-style browser will be used.

	"""
	args, testKw = _prepKeywords(extFunc, invalid[:], specInfo)
	kw = {}
	processedArgs = []
	keyword = None
	if args:
		guideline = args[0]
	else:
		guideline = None
	while typed:
		value, typed = _parseTyped(guideline, typed, specInfo)
		if len(processedArgs) < len(args):
			if isinstance(value, basestring):
				value = convertType(value)
			processedArgs.append(value)
			if len(processedArgs) < len(args):
				guideline = args[len(processedArgs)]
			else:
				guideline = None
			continue
		if keyword is None:
			guideline, keyword = _getRealKw(value, testKw)
			continue
		if isinstance(value, basestring):
			value = convertType(value)
		if keyword in kw:
			# multiple keyword instances: create list
			prevVal = kw[keyword]
			if isinstance(prevVal, list):
				prevVal.append(value)
				value = prevVal
			else:
				value = [prevVal, value]
		kw[keyword] = value
		keyword = guideline = None
	if len(processedArgs) < len(args):
		missingTyped = []
		for arg in args[0 - len(args) + len(processedArgs):]:
			for typedName, trueName, method in specInfo:
				if arg == trueName:
					missingTyped.append(typedName)
					break
			else:
				missingTyped.append(arg)
		raise MidasError, "Missing required argument(s): %s" % (
						", ".join(missingTyped))
	extFunc(*tuple(processedArgs), **kw)

def Unimplemented(cmdName, args):
	# for legitimate midas commands that aren't implemented
	raise MidasError, '"%s" is not yet implemented' % (cmdName)

def NoVdwopt(cmdName, args):
	# parts of vdwopt are implemented
	warn('"vdwopt" is not yet implemented.\n\n'
		'However, "vdwopt density" is available as "vdwdensity"\n'
		'and "vdwopt define" is available as "vdwdefine".')

_aliasMenu = None
from chimera import preferences
KNOWN_ALIASES = "aliases menu"
aliasMenuPrefs = preferences.addCategory("aliases menu",
	preferences.HiddenCategory, optDict={KNOWN_ALIASES: {}})

def doAdjust(cmdName, args):
	if len(args) < 2:
		raise MidasError("Missing required args; type 'help adjust' for info")
	cmdType, args = args.split(None, 1)
	cmdType = cmdType.lower()
	cmdNum = None
	for index, syms in enumerate([["angle", "bangle", "bondangle"],
			["length", "blength", "bondlength"]]):
		for sym in syms:
			if sym.startswith(cmdType):
				cmdNum = index
				break
		else:
			continue
		break
	if cmdNum == 0:
		if not args:
			raise MidasError("Missing 'degrees' arg; type 'help adjust' for info")
		try:
			degrees, spec = args.split(None, 1)
		except ValueError:
			degrees = args
			spec = ""

		try:
			degrees = float(degrees)
		except ValueError:
			raise MidasError("Specified bond angle is not a number")

		try:
			sel = specifier.evalSpec(getSpecs(spec))
		except:
			raise MidasError("Atom spec specifying angle bonds is mangled")
		if isinstance(sel, selection.OSLSelection):
			isel = selection.ItemizedSelection()
			isel.add(sel.atoms())
			isel.addImplied(ordered=True)
			sel = isel
		bonds = sel.bonds(ordered=True)
		if len(bonds) != 2:
			raise MidasError("Atom spec doesn't select exactly two bonds")

		from BuildStructure import setBondAngle, BondInCycleError, BondsNotAdjacentError
		try:
			setBondAngle(bonds[0], bonds[1], degrees)
		except (BondInCycleError, BondsNotAdjacentError), v:
			raise MidasError(unicode(v))
	elif cmdNum == 1:
		if not args:
			raise MidasError("No bond length specified; type 'help adjust' for info")
		try:
			bl, args = args.split(None, 1)
		except ValueError:
			bl = args
			args = ""
		try:
			bl = float(bl)
		except ValueError:
			raise MidasError("specified bond length is not a number")
		kw = {'status': replyobj.status}
		try:
			sideKw, rem = args.split(None, 1)
		except ValueError:
			pass
		else:
			if "movingSide".startswith(sideKw):
				if not rem:
					raise MidasError("No value given for 'side' keyword")
				sideVal, args = rem.split(None, 1)
				if "smaller".startswith(sideVal.lower()):
					sideVal = "smaller side"
				elif "larger".startswith(sideVal.lower()):
					sideVal = "larger side"
				else:
					raise MidasError("'side' value must be 'smaller' or 'larger'")
				kw['movingSide'] = sideVal
				if not args:
					raise MidasError("No bond length specified; type 'help adjust' for info")
		try:
			bondSel = specifier.evalSpec(getSpecs(args))
		except:
			raise MidasError("atom spec for bonds to adjust is mangled")
		bonds = bondSel.bonds()
		if not bonds:
			if isinstance(bondSel, selection.OSLSelection):
				isel = selection.ItemizedSelection()
				isel.add(bondSel.atoms())
				bondSel = isel
			bondSel.addImplied()
			bonds = bondSel.bonds()
		if not bonds:
			raise MidasError("atom spec selects no bonds")
		from BuildStructure import setBondLength
		for bond in bonds:
			setBondLength(bond, bl, **kw)
	else:
		raise MidasError("First arg (%s) wrong; type 'help adjust' for info" % cmdType)

ALIAS_MENU_LABEL = "Aliases"
def _getAliasMenu():
	global _aliasMenu
	if not _aliasMenu and not chimera.nogui:
		from chimera.tkgui import addMenu
		_aliasMenu = addMenu(**{'label': ALIAS_MENU_LABEL, 'underline': 1})
		knownAliases = aliasMenuPrefs[KNOWN_ALIASES]
		for k, v in knownAliases.items():
			# weed out aliases erroneously placed in menu
			if "$1" in v:
				del knownAliases[k]
		keys = knownAliases.keys()
		keys.sort()
		for key in keys:
			doAlias("alias", "^%s %s" % (key, knownAliases[key]), menuInit=True)
	return _aliasMenu
if aliasMenuPrefs[KNOWN_ALIASES]:
	chimera.registerPostGraphicsFunc(_getAliasMenu)

def doAlias(cmdName, args, menuInit=False, remember=True):
	parts = args.split(None, 1)
	if len(parts) == 1:
		if aliases.has_key(parts[0]):
			replyobj.status("Alias for '%s' is: %s" %
				(parts[0], aliases[parts[0]]), log=True)
			return
		raise MidasError, "No such alias: '%s'" % parts[0]
	if not args:
		message("Current aliases are:")
		for alias, expand in aliases.items():
			message("%s: %s" % (alias, expand))
		return

	alias, text = parts
	redefinition = alias in aliases

	aliases[alias] = text
	if alias[0] == "^" and not chimera.nogui and "$1" not in text:
		aliasMenu = _getAliasMenu()
		knownAliases = aliasMenuPrefs[KNOWN_ALIASES].copy()
		def command(alias=alias):
			try:
				return makeCommand(alias[1:], reportAliasExpansion=False)
			except MidasError, e:
				from chimera import UserError
				raise UserError(str(e))
		if redefinition:
			knownAliases[alias[1:]] = text
			aliasMenu.entryconfigure(aliasMenu.index(alias[1:]),
														command=command)
		else:
			if alias[1:] not in knownAliases:
				knownAliases[alias[1:]] = text
			if menuInit:
				aliasMenu.add_command(label=alias[1:], command=command)
			else:
				keys = knownAliases.keys()
				keys.sort()
				# some fancy footwork for indexing due to possible tearoff
				keyIndex = keys.index(alias[1:])
				if keyIndex == len(keys) - 1:
					aliasMenu.add_command(label=alias[1:], command=command)
				else:
					aliasMenu.insert_command(aliasMenu.index(keys[keyIndex+1]),
							label=alias[1:], command=command)
		if remember:
			# force preference to update
			aliasMenuPrefs[KNOWN_ALIASES] = knownAliases

def doUnalias(cmdName, args):
	if not args:
		for alias in aliases.keys():
			doUnalias("~alias", alias)
		return
	alias = args
	try:
		text = aliases[alias]
	except KeyError:
		raise MidasError("No such alias ('%s)" % args)
	del aliases[alias]
	if alias[0] == "^" and not chimera.nogui and "$1" not in text:
		aliasMenu = _getAliasMenu()
		knownAliases = aliasMenuPrefs[KNOWN_ALIASES].copy()
		del knownAliases[alias[1:]]
		aliasMenu.delete(aliasMenu.index(alias[1:]))
		# force preference to update
		aliasMenuPrefs[KNOWN_ALIASES] = knownAliases
		if not knownAliases:
			from chimera.tkgui import deleteMenu
			global _aliasMenu
			_aliasMenu = None
			deleteMenu(ALIAS_MENU_LABEL)

def doAlign(cmdName, args):
	if args and args[0].isalpha() and args[1:].isdigit():
		Midas.align(objID=args)
	else:
		Midas.align(getSpecs(args))
			
def doAngle(cmdName, args):
	argWords = args.split()
	from Commands import bool_arg
	dihedral = _parseKeywordArg(argWords, 'dihedral', 'angle', bool_arg)
	if dihedral is None:
		dihedral = True
	objs = argWords
	if len(objs) == 2 \
	and objs[0][0].isalpha() and objs[0][1:].isdigit() \
	and objs[1][0].isalpha() and objs[1][1:].isdigit():
		Midas.angle(objIDs=objs)
	else:
		Midas.angle(getSpecs(' '.join(objs)), dihedral = dihedral)

def doBackground(cmdName, args):
	arg, args = first_arg(args)
	if not cmd:
		raise MidasError('missing arguments to %s command' % cmdName)
	# TODO: add angle and offset when supported by LensViewer code
	KEYWORDS = ['solid', 'gradient', 'image', 'scale', 'opacity',
			'discrete', 'hls', 'rgb',
			'stretched', 'tiled', 'zoomed', 'centered' ]
	kw_args = {}
	while 1:
		i = keyword_match(arg, KEYWORDS)	# let prefixes match
		kw = KEYWORDS[i]

		if kw == 'solid':
			colorName, args = parseColorName(args)
			kw_args['color'] = colorName
		elif kw == 'gradient':
			# parse comma-separated color names that might have
			# spaces in them
			colors = []
			candidates = args.split(',')
			while candidates:
				candidate = candidates[0].strip()
				color, arg = parseColorName(candidate,
							failReturnsNone=True)
				if color is None:
					break
				colors.append(color)
				if arg:
					candidates[0] = arg
					break
				candidates = candidates[1:]
			if colors:
				kw_args['gradient'] = colors
				args = " ".join(candidates)
			else:
				arg, args = first_arg(args)
				kw_args['gradient'] = arg
		elif kw == 'image':
			arg, args = first_arg(args)
			if not arg:
				if chimera.nogui:
					raise MidasError("Cannot use"
						" argument-less "
						"'background image' command"
						" in nogui mode")
				om = OpenModal(title="Command-line Background")
				pathsAndTypes = om.run(chimera.tkgui.app)
				om.destroy()
				if pathsAndTypes == None: return
				elif not pathsAndTypes:
					raise MidasError('No file chosen for background image')
				path = pathsAndTypes[0][0]
			else:
				path = tildeExpand(arg)
			kw_args['image'] = path
		elif kw in ('scale', 'angle', 'offset', 'opacity'):
			arg, args = first_arg(args)
			kw_args[kw] = _parseFloat(arg, cmdName, kw)
		elif kw == 'discrete':
			from chimera import palettes
			kw_args['interpolation'] = palettes.DISCRETE
		elif kw == 'hls':
			from chimera import palettes
			kw_args['interpolation'] = palettes.HLS
		elif kw == 'rgb':
			from chimera import palettes
			kw_args['interpolation'] = palettes.RGB
		elif kw == 'stretched':
			kw_args['tiling'] = chimera.viewer.Stretched
		elif kw == 'tiled':
			kw_args['tiling'] = chimera.viewer.Tiled
		elif kw == 'zoomed':
			kw_args['tiling'] = chimera.viewer.Zoomed
		elif kw == 'centered':
			kw_args['tiling'] = chimera.viewer.Centered

		arg, args = first_arg(args)
		if arg == '':
			break
	if ('color' not in kw_args
	and 'gradient' not in kw_args
	and 'image' not in kw_args):
		raise MidasError('set background to a color, a gradient, or an image')
	try:
		Midas.background(**kw_args)
	except ValueError, e:
		raise MidasError(str(e))

def doUnbond(cmdName, args):
	Midas.unbond(getSpecs(args))

def doBondColor(cmdName, args):
	if not args:
		raise MidasError, 'No color specified'
	colorName, spec = parseColorName(args)
	if not spec:
		specs = getSpecs("")
	else:
		specs = getSpecs(spec)
	Midas.bondcolor(colorName, specs)

def doBondDisplay(cmdName, args):
	argList = args.split(None, 1)
	if len(argList) == 2:
		modeName, spec = argList
	elif len(argList) == 1:
		modeName = argList[0]
		spec = ""
	else:
		error("Usage: bonddisplay mode [atom_spec]")
		return
	if modeName == "always" or modeName == "on":
		mode = chimera.Bond.Always
	elif modeName == "never" or modeName == "off":
		mode = chimera.Bond.Never
	elif modeName == "smart" or modeName == "default":
		mode = chimera.Bond.Smart
	else:
		error("bonddisplay: mode must be one of \"always\", "
			"\"never\", or \"smart\"")
		return
	Midas.bonddisplay(mode, getSpecs(spec))

def doBondUncolor(cmdName, args):
	Midas.unbondcolor(getSpecs(args))

def doCd(cmdName, args):
	fullPath = tildeExpand(args)
	try:
		os.chdir(fullPath)
	except OSError, v:
		raise MidasError(v)
	from OpenSave import getRememberer
	getRememberer().rememberDir(fullPath)

def doClip(cmdName, args):
	argWords = args.split()
	from Commands import bool_arg
	from_center = _parseKeywordArg(argWords, 'fromCenter', cmdName, bool_arg)
	if len(argWords) > 3:
		raise MidasError('wait_frames argument not implemented')
	if len(argWords) < 1:
		raise MidasError('required clipping plane argument missing')
	a0 = argWords[0]
	if a0 in ('on', 'off'):
		Midas.enableClipping(a0 == 'on')
		return
	if a0[0] not in ('h', 'y'):
		raise MidasError('clip plane must be "hither" or "yon"')
	if len(argWords) < 2:
		raise MidasError('"Unit-less" clip not implemented')
	if len(argWords) == 3:
		Midas.clip(argWords[0], float(argWords[1]),
				frames=int(argWords[2]),
				from_center=from_center)
		return
	Midas.clip(argWords[0], float(argWords[1]), from_center=from_center)

def doUnclip(cmdName, args):
	if ' ' in args:
		raise MidasError, "mangled clipping plane name: %s" % args
	if not args:
		raise MidasError, 'required clipping plane argument missing'
	Midas.unclip(args)

def doClose(cmdName, args):
	args = args.strip()
	if len(args) == 0:
		raise MidasError("argument must be model spec, "
				 "'session' or 'all'")
	if args in ["session", "all"]:
		Midas.close(args)
	else:
		specs = getSpecs(args, modelLevel=True)
		try:
			models = specifier.evalSpec(specs).models()
		except:
			raise MidasError("argument must be model spec, "
					 "'session' or 'all'")
		ids = set([(m.id, m.subid) for m in models])
		closureList = []
		for id, subid in ids:
			closureList.extend(chimera.openModels.list(id, subid))
		Midas.close(closureList)

def doCofr(cmdName, args):
	args = args.split()
	kw = {}
	_parseCoordinateSystemArg(args, kw, cmdName)
	where = 'fixed'
	if len(args) == 0:
		where = 'report'
	elif args[0] in ('fixed', 'front', 'independent', 'models', 'view'):
		where = args[0]
		args = args[1:]
	if where == 'fixed' and args:
		where, cs = parseCenterArg(args[0], cmdName)
		if cs:
			where = cs.xform.apply(where)
		elif 'coordinateSystem' in kw:
			where = kw['coordinateSystem'].xform.apply(where)
	Midas.cofr(where)

def doColor(cmdName, args):
	if not args:
		raise MidasError, 'No color specified'
	ci = [args.find(r) for r in Midas.ColorSuffixes if r in args]
	if ci:
		commaIndex = min(ci)
		colorName, spec = parseColorName(args[:commaIndex])
		spec += args[commaIndex:]
	else:
		colorName, spec = parseColorName(args)
	if cmdName.startswith("ribcol"):
		mods = ",r"
		cmdName = "color"
	else:
		mods = ""
		while spec and spec[0] == ",":
			try:
				mod, spec = spec.split(None, 1)
				mods += mod
			except ValueError:
				mods += spec
				spec = ""
				break
	modelLevel = (cmdName == "modelcolor"
			or cmdName == "modelcolour"
			or cmdName == "ribinsidecolor"
			or cmdName == "ribinsidecolour")
	if not spec:
		specs = getSpecs("")
	else:
		specs = getSpecs(spec, modelLevel=modelLevel)
	exec 'Midas.%s(%s, %s)' % (cmdName, repr(colorName + mods), repr(specs))

def doColordef(cmdName, args):
	if not args:
		raise MidasError("No color name specified for colordef")
	if args == "list":
		Midas.colordef("list", None)
		return
	defColor, args = parseColorName(args, failReturnsNone=True)
	if defColor == None:
		defColor, args = parseColorName(args)
	else:
		if not args:
			# inquiry for rgb values
			Midas.colordef(defColor, None)
			return
	fromColor, args = parseColorName(args, failReturnsNone=True)
	if fromColor == None:
		from Midas import _colorEditorSynonyms
		if args[0] == '#' or args in _colorEditorSynonyms:
			Midas.colordef(defColor, args)
			return
		argWords = args.split()
		if len(argWords) not in [3,4]:
			argWords = [a.strip() for a in args.split(",")]
		if len(argWords) not in [3,4]:
			raise MidasError("Need color name or RGB or RGBA values to define"
				" color '%s'" % defColor)
		argNames = ['red', 'green', 'blue', 'alpha'][:len(argWords)]
		colorVals = tuple(_parseFloat(f, cmdName, arg)
						for f, arg in zip(argWords, argNames))
		Midas.colordef(defColor, colorVals)
		return
	if args:
		raise MidasError("Extra text at end of command")
	Midas.colordef(defColor, fromColor)

def doConic(cmdName, args):
	chimeraRoot = os.environ.get("CHIMERA")
	# only force 'nowait' on win32 where otherwise Chimera will hang
	# until the conic image is dismissed
	if sys.platform == 'win32' and "-W" not in args:
		nowait = "nowait "
	else:
		nowait = ""
	doPdbrun('pdbrun', ('%s"' % nowait)
		+ os.path.join(chimeraRoot, 'bin', 'conic') + '" ' + args)

def doCopy(cmdName, args):
	argWords = args.split(None, 1)
	keywordArgs = {}
	stereo = False
	KEYWORDS = (
		"printer", "file", "supersample",
		"width", "height", "units", "dpi",
		"tiff", "tiff-fast", "png", "jpeg", "ppm", "ps", "eps",
		"raytrace", "rtwait", "rtclean",
		"stereo",
		# obselete keywords
		"date", "box", "flat", "bg",
		"background", "intensity", "title",
	)
	while len(argWords) > 0:
		i = keyword_match(argWords[0], KEYWORDS)
		option = KEYWORDS[i]
		if option in ("date", "box", "flat", "bg",
				"background", "intensity", "title"):
			raise MidasError("%s keyword not implemented" % option)
		if option in ("printer", "file", "supersample", "width", "height", "units", "dpi"):
			if len(argWords) < 2:
				raise MidasError("Argument (to '%s') missing"
								% option)
			furtherArgs = argWords[1].split(None, 1)
			if option in ("width", "height", "dpi"):
				try:
					arg = float(furtherArgs[0])
					if arg < 1:
						raise ValueError("")
				except ValueError:
					raise MidasError("%s argument must"
					   " be positive" % option)
			elif option == "supersample":
				try:
					arg = int(furtherArgs[0])
					if arg < 0 or arg > 4:
						raise ValueError("")
				except ValueError:
					raise MidasError("%s argument must"
					   " be >= 0 and <= 4" % option)
			elif option == "units":
				UNITS = ('pixels', 'points', 'inches',
						'millimeters', 'centimeters')
				try:
					i = keyword_match(furtherArgs[0], UNITS)
				except MidasError:
					raise MidasError("unknown units: %s" %
							furtherArgs[0])
				arg = UNITS[i]
			else:
				arg = furtherArgs[0]
			keywordArgs[option] = arg
			argWords = furtherArgs
		elif option == "tiff":
			keywordArgs["format"] = "TIFF"
		elif option == "tiff-fast":
			keywordArgs["format"] = "TIFF-fast"
		elif option == "png":
			keywordArgs["format"] = "Stereo PNG" if stereo else "PNG"
			stereo = False
		elif option == "jpeg":
			keywordArgs["format"] = "Stereo JPEG" if stereo else "JPEG"
			stereo = False
		elif option == "ppm":
			keywordArgs["format"] = "PPM"
		elif option == "ps":
			keywordArgs["format"] = "PS"
		elif option == "eps":
			keywordArgs["format"] ="EPS"
		elif option == "raytrace":
			keywordArgs["raytrace"] = True
		elif option == "rtwait":
			keywordArgs["rtwait"] = True
		elif option == "rtclean":
			keywordArgs["rtclean"] = True
		elif option == "stereo":
			stereo = True
		if len(argWords) > 1:
			argWords = argWords[1].split(None, 1)
		else:
			argWords = ()
	if stereo:
		raise MidasError("")
	Midas.copy(**keywordArgs)

def doUncolor(cmdName, args):
	which = ""
	if cmdName.startswith("unribcol"):
		args = ",r " + args if args else ",r"
		cmdName = "uncolor"
	if len(args) == 0:
		# ~color with no args
		specs = getSpecs("")
	else:
		mods = ""
		while args and args[0] == ",":
			try:
				mod, args = args.split(None, 1)
				mods += mod
			except ValueError:
				mods += args
				args = ""
				break
		which = [ci for ci in mods.split(',')[1:] if ci]
	exec 'Midas.%s(%s, %s)' % (cmdName, repr(which), repr(getSpecs(args)))

def doUndistance(cmdName, args):
	if not args or args == "all":
		Midas.undistance("all")
		return
	exec 'Midas.undistance(%s)' % repr(getSpecs(args))

def doDefine(cmdName, args):
	usage = "Usage: %s axis|plane|centroid [keyword args] spec" % cmdName
	if not args:
		raise MidasError(usage)
	argWords = args.split()
	geom = argWords.pop(0)
	if "axis".startswith(geom):
		geom = "axis"
		gkw = ["perHelix", "helicalCorrection", "massWeighting"]
	elif "plane".startswith(geom):
		geom = "plane"
		gkw = ["thickness", "padding"]
	elif "centroid".startswith(geom):
		geom = "centroid"
		gkw = ["massWeighting"]
	else:
		raise MidasError(usage)

	keywords = ["name", "number", "radius", "color", "raiseTool"] + gkw
	name = geom
	kw = {}
	while len(argWords) > 1:
		arg = argWords[0].lower()
		for keyword in keywords:
			if keyword.lower().startswith(arg):
				arg = keyword
				break
		else:
			break
		argWords.pop(0)
		val = argWords.pop(0)
		if val[0] in ["'", '"']:
			while val[-1] != val[0] and argWords:
				val += " " + argWords.pop(0)
			if val[-1] != val[0]:
				raise MidasError("Unmatched quote in command")
			val = val[1:-1]
		if arg == "name":
			kw[arg] = val
		elif arg == "number":
			try:
				kw[arg] = int(val)
			except ValueError:
				raise MidasError("value of '%s' must be an integer" % arg)
		elif arg in ["radius", "thickness", "padding"]:
			try:
				kw[arg] = float(val)
			except ValueError:
				raise MidasError("value of '%s' must be a real number" % arg)
		elif arg == "color":
			from Midas import convertColor
			colorName, typed = parseColorName(" ".join([val] + argWords))
			kw[arg] = convertColor(colorName)
			argWords = typed.split()
		#elif arg in ["perHelix", "helicalCorrection", "massWeighting", "showTool"]:
		else:
			try:
				kw[arg] = eval(val.capitalize())
			except:
				raise MidasError("value of '%s' must be true or false" % arg)
	if "padding" in kw:
		kw['radiusOffset'] = kw.pop('padding')
	Midas.define(geom, getSpecs(" ".join(argWords)), **kw)

def doUndefine(cmdName, args):
	if not args:
		args = "axes planes centroids"
	geomIDs = []
	axes = planes = centroids = False
	for arg in args.split():
		if "axes".startswith(arg):
			axes = True
		elif "planes".startswith(arg):
			planes = True
		elif "centroids".startswith(arg):
			centroids = True
		elif arg[0] not in "ap" or not arg[1:].isdigit():
			raise MidasError("%s argument must be: axes, planes, centroids,"
				" or geometry ID" % cmdName)
		else:
			geomIDs.append(arg)
	Midas.undefine(geomIDs, axes=axes, planes=planes, centroids=centroids)

def doDistance(cmdName, args):
	kw = {}
	objIDs = []
	if args:
		parts = args.split(None, 1)
		if parts[0] == "signed":
			kw["signed"] = True
			if len(parts) > 1:
				args = parts[1]
				parts = args.split(None, 1)
			else:
				raise MidasError("Must supply object IDs after 'signed'")
		if len(parts) > 1:
			obj, rem = parts
			if obj[0].isalpha() and obj[1:].isdigit():
				objIDs.append(obj)
				objArgs = None
				selArgs = maybeObj = rem
			else:
				rem, obj = args.rsplit(None, 1)
				objArgs = rem
				selArgs = args
				maybeObj = obj
			if maybeObj[0].isalpha() and maybeObj[1:].isdigit():
				objIDs.append(maybeObj)
				args = objArgs
			else:
				args = selArgs
	if args == None:
		sel = None
	else:
		sel = getSpecs(args)
	Midas.distance(sel, objIDs=objIDs, **kw)

def doEcho(cmdName, args):
	print args
	if not chimera.nogui:
		replyobj.status(args)

def doExport(cmdName, args):
	argWords = args.split(None, 1)
	keywordArgs = []
	format = None
	filename = None
	while len(argWords) > 0:
		if argWords[0] == "format":
			if len(argWords) < 2:
				raise MidasError("Argument (to '%s') missing"
								% argWords[0])
			following = argWords[1].split(None, 1)
			arg = following[0]
			keywordArgs.append('%s="%s"' % (argWords[0], arg))
			argWords = following
		elif argWords[0] == "list":
			keywordArgs.append('list=True')
		elif not filename:
			filename = argWords[0]
			keywordArgs.append('filename="%s"' % filename)
		else:
			raise MidasError("Extra export arguments '%s'"
							% ' '.join(argWords))
		if len(argWords) > 1:
			argWords = argWords[1].split(None, 1)
		else:
			argWords = ()
	exec 'Midas.export(%s)' % ', '.join(keywordArgs)

def doGetcrd(cmdName, args):
	xformed = False
	if args:
		fields = args.split()
		xf = fields[0]
		if len(xf) <= len("xformed") and xf == "xformed"[:len(xf)]:
			xformed = True
			args = " ".join(fields[1:])
	Midas.getcrd(getSpecs(args), xformed=xformed)

def doHelp(cmdName, args):
	if not args:
		from chimera.SearchDocs import SearchDialog
		from chimera import dialogs
		dialogs.display(SearchDialog.name)
		return
	if args.lower() == "commands":
		help.display("UsersGuide/framecommand.html")
		return
	try:
		helpType = helpInfo[args]
	except KeyError:
		raise MidasError, \
			"Cannot provide help for unknown command '%s'" % args
	if helpType is True:
		helpTopic = args
		if "colour" in helpTopic:
			helpTopic = helpTopic.replace("colour", "color")
		if "centre" in helpTopic:
			helpTopic = helpTopic.replace("centre", "center")
		help.display("UsersGuide/midas/%s.html" % helpTopic)
	elif helpType is None:
		raise MidasError, 'No help available for "%s"' % args
	else:
		help.display(helpType)

def doKsdssp(cmdName, args):
	energy = hlen = slen = "None"
	verbose = False
	argWords = args.split()
	while argWords:
		opt = argWords[0]
		if opt == "-v":
			verbose = True
			argWords = argWords[1:]
		else:
			if len(argWords) < 2:
				break
			arg = argWords[1]
			if opt == "-c":
				energy = arg
			elif opt == "-h":
				hlen = arg
			elif opt == "-s":
				slen = arg
			elif opt == "-S":
				warn("-S option not yet available, use -v")
			else:
				break
			argWords = argWords[2:]
	exec 'Midas.ksdssp(%s, %s, %s, %s, %s)' % (repr(getSpecs(' '.join(
					argWords))), energy, hlen, slen, verbose)

def doLabel(cmdName, args):
	if not chimera.nogui and cmdName != 'rlabel':
		replyobj.status("note: use 'rlabel' to label residues")
	offset = None
	argWords = args.split(None, 1)
	if len(argWords) < 2:
		pass
	elif argWords[0] == 'offset':
		argWords = argWords[1].split(None, 1)
		if len(argWords) <= 1:
			args = ''
		else:
			args = argWords[1]
		if 'default'.startswith(argWords[0]):
			offset = 'default'
		else:
			argWords = argWords[0].split(',')
			if len(argWords) != 3:
				raise MidasError("%s offset needs 3 comma-separated numbers" % cmdName)
			argNames = ['x offset', 'y offset', 'z offset']
			xyz = tuple(_parseFloat(f, cmdName, arg)
					for f, arg in zip(argWords, argNames))
			offset = chimera.Vector(*xyz)
	func = getattr(Midas, cmdName)
	func(sel=getSpecs(args), offset=offset, warnLarge=not scripting)

def doLabelopt(cmdName, args):
	try:
		key, val = tuple(args.split(None, 1))
	except ValueError:
		raise MidasError("Usage: labelopt [res]info label-val")
	if key not in ["info", "resinfo"]:
		raise MidasError('unknown option "%s"' % key)
	if val[0] in ["'", '"'] and val[0] == val[-1] and len(val) > 1:
		val = val[1:-1]
	Midas.labelopt(key, val)

def doLinewidth(cmdName, args):
	if not args:
		raise MidasError, 'No linewidth specified'
	argWords = args.split(None, 1)
	if len(argWords) < 2:
		specs = getSpecs("")
	else:
		specs = getSpecs(argWords[1])
	try:
		linewidth = float(argWords[0])
	except:
		raise MidasError, 'width must be numeric'
	exec 'Midas.linewidth(%g, %s)' % (linewidth, repr(specs))

def doLongbond(cmdName, args):
	if args:
		raise MidasError("'longbond' command no longer takes arguments")
	Midas.longbond()

def doMatch(cmdName, args):
	argWords = args.split()
	if len(argWords) == 0:
		raise MidasError, 'missing atom spec'
	iterate = None
	selected = showMatrix = False
	move = True
	specs = []
	while argWords:
		if argWords[0] in ['selected', 'active']:
			selected = True
			argWords = argWords[1:]
		elif argWords[0] == "iterate":
			if len(argWords) < 2:
				raise MidasError("'iterate' keyword requires"
					" cutoff distance argument")
			try:
				iterate = float(argWords[1])
			except ValueError:
				raise MidasError("'iterate' argument must be"
					" a number")
			if iterate < 0.0:
				raise MidasError("'iterate' argument must be"
					" a positive number")
			argWords = argWords[2:]
		elif argWords[0].lower().startswith("show"):
			if len(argWords) < 2:
				raise MidasError("'showMatrix' keyword requires"
					" true/false argument")
			try:
				showMatrix = bool(eval(argWords[1].capitalize()))
			except:
				raise MidasError("'showMatrix' keyword requires"
					" true/false argument")
			argWords = argWords[2:]
		elif argWords[0] == "move":
			if len(argWords) < 2:
				raise MidasError("'move' keyword requires an argument")
			move = _parseMoveOption(argWords[1])
			argWords = argWords[2:]
		else:
			specs.append(argWords[0])
			argWords = argWords[1:]
	if iterate:
		iterInfo = "iterate %g" % iterate
	else:
		iterInfo = "no iteration"
	spec1, spec2 = _parseAtomSpecs(specs)
	replyobj.info('Executing %s %s, %s\n' % (cmdName, specs, iterInfo))
	Midas.match(getSpecs(spec1), getSpecs(spec2), selected=selected,
		    iterate=iterate, showMatrix=showMatrix, move=move)

def _parseMoveOption(mopt):
	e = ("'move' keyword requires an argument"
	     " molecules|chains|residues|atoms|true|false|<atom-spec>")
	if isinstance(mopt, int):
		return bool(mopt)
	if len(mopt) == 0:
		raise MidasError(e)
	m0 = mopt[0].lower()
	mt = {'m':'molecules', 'c':'chains', 'r':'residues', 'a':'atoms',
	      't':True, 'f':False}
	if m0 in mt:
		return mt[m0]
	try:
		move = specifier.evalSpec(mopt).atoms()
	except:
		raise MidasError(e)
	return move

def doMatrixcopy(cmdName, args):
	argWords = args.split()

	mo = _parseKeywordArg(argWords, 'moving', 'matrixcopy')
	if mo is None:
		moving = None
	else:
		moving = modelsFromSpec(mo, 'moving')
	if len(argWords) != 2:
		raise MidasError, 'two model numbers required'
	fm = modelsFromSpec(argWords[0], 'from_model')
	tm = modelsFromSpec(argWords[1], 'to_model')
	Midas.matrixcopy(fm, tm, moving = moving)

def doMatrixget(cmdName, args):
	if not args:
		if chimera.nogui:
			raise MidasError("Cannot use argless 'matrixget'"
						" command in nogui mode")
		sm = SaveModal(title="Command-line Matrixget")
		pathsAndTypes = sm.run(chimera.tkgui.app)
		sm.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise MidasError, 'No file chosen for matrixget'
		path = pathsAndTypes[0][0]
	else:
		path = tildeExpand(args)
	Midas.matrixget(path)

def doMatrixset(cmdName, args):
	if not args:
		if chimera.nogui:
			raise MidasError("Cannot use argless 'matrixset'"
					" command in nogui mode")
		om = OpenModal(title="Command-line Matrixset")
		pathsAndTypes = om.run(chimera.tkgui.app)
		om.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise MidasError, 'No file chosen for matrixset'
		path = pathsAndTypes[0][0]
	else:
		path = tildeExpand(args)
	Midas.matrixset(path)

def doMove(cmdName, args):
	argWords = args.split()

	if len(argWords) == 0:
		raise MidasError('required axis argument missing')

	kw = {}
	_parseMovementKeywordArgs(argWords, 0, kw, cmdName)
        
        cofr = (kw['axis'] == 'cofr')
        if cofr:
                if 'coordinateSystem' in kw:
                        raise MidasError('Cannot use coordinateSystem option with move cofr')
                if 'models' in kw:
                        from chimera import selection, openModels
                        sel = selection.ItemizedSelection()
                        sel.add(kw['models'])
                        from . import boundingSphere
                        b = boundingSphere(sel)
                        shift = openModels.cofr - b.center
                        kw['x'],kw['y'],kw['z'] = shift.data()
                        del kw['axis']
                else:
                        raise MidasError('move cofr requires models argument')
        else:
                kw['x'],kw['y'],kw['z'] = kw.pop('axis').data()
	if 'center' in kw:
		kw.pop('center')

	n = len(argWords)
	if n >= 2 and not cofr:
		d = _parseFloat(argWords[1], cmdName, 'distance')
		from math import sqrt
		na = sqrt(kw['x']*kw['x']+kw['y']*kw['y']+kw['z']*kw['z'])
		if na > 0:
			for a in ('x', 'y', 'z'):
				kw[a] *= d/na
	if n >= 3:
		kw['frames'] = _parseInt(argWords[2], cmdName, 'frames')
                if cofr:
                        f = float(kw['frames'])
                        kw['x'],kw['y'],kw['z'] = kw['x']/f,kw['y']/f,kw['z']/f
	if n > 3:
		raise MidasError('wait_frames argument not implemented')
	Midas.move(**kw)

def doMsMs(cmdName, args):
	argWords = args.split(None, 1)
	if len(argWords) < 2:
		raise MidasError, 'missing category name'
	if argWords[0] == "new":
		newCmdName = 'msms new'
		func = doSurfaceNew
	elif argWords[0] in ("del","delete"):
		newCmdName = 'msms del'
		func = doSurfaceDelete
	elif argWords[0] in ("cat","category"):
		newCmdName = 'msms cat'
		func = doSurfaceCategory
	elif argWords[0] in ("color","colormode"):
		newCmdName = 'msms color'
		func = doSurfaceColor
	elif argWords[0] in ("repr","represent","representation"):
		newCmdName = 'msms repr'
		func = doSurfaceRepr
	else:
		raise MidasError, 'unknown msms keyword "%s"' % argWords[0]
	func(newCmdName, argWords[1])

def doNamesel(cmdName, args):
	Midas.namesel(args.strip())

def doNeon(cmdName, args):
	chimeraRoot = os.environ.get("CHIMERA")
	if sys.platform == "win32":
		conicExe = "conic.exe"
	else:
		conicExe = "conic"
	doPreneon('pdbrun', ' | "' +
		os.path.join(chimeraRoot, 'bin', conicExe) + '" ' + args)

def testPath(text, wildcarding):
	from glob import glob
	expanded = tildeExpand(text)
	if wildcarding:
		return glob(expanded)
	if os.path.exists(expanded):
		return [expanded]
	return []

def doOpen(cmdName, args):
	argWords = args.split()

	fileNames = prefix = None
	modelNum = -1
	noprefs = False
	wildcarding = True
	while len(argWords) > 0:
		text = " ".join(argWords)
		paths = testPath(text, wildcarding)
		if paths:
			fileNames = paths
			break
		colonPos = text.find(':')
		if colonPos != -1 and " " not in text[:colonPos]:
			paths = testPath(text[colonPos+1:], wildcarding)
			if paths:
				fileNames = paths
				prefix = text[:colonPos]
				break
		keyword = argWords[0]
		argWords = argWords[1:]
		if keyword == 'original':
			warn("'original' keyword ignored")
		elif keyword in ['surface', 'ms']:
			raise MidasError, 'opening surfaces unimplemented'
		elif keyword == 'noprefs':
			noprefs = True
		elif keyword == 'nowildcard':
			wildcarding = False
		else:
			match = re.match('#?(\d+)$', keyword)
			if match != None:
				if modelNum != -1:
					raise MidasError("Cannot specify"
						" multiple model numbers")
				modelNum = int(match.group(1))
			else:
				fileNames = [keyword] + argWords
				break

	if modelNum < 0:
		modelArg = ''
	else:
		modelArg = ', model=%d' % (modelNum)

	if fileNames is None:
		if chimera.nogui:
			raise MidasError, "Cannot use argless 'open' command"\
							" in nogui mode\n"
		om = OpenModal(title="Command-line Open")
		pathsAndTypes = om.run(chimera.tkgui.app)
		om.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise MidasError, 'No file chosen for open'
		fileNames = [pt[0] for pt in pathsAndTypes]

	for fileName in fileNames:
		if prefix:
			fileName = prefix + ":" + fileName
		exec 'Midas.open(%s%s, noprefs=%s)' % (repr(fileName),
							modelArg, noprefs)

def doPause(cmdName, args):
	if not args:
		Midas.pause()
		return
	if args.lower() != "end":
		raise MidasError("Usage: pause [end]")
	Midas.pause(end=True)

def doPdbrun(cmdName, args):
	argWords = args.split(None, 1)
	keywordArgs = {}
	while len(argWords) > 1 and argWords[0] in ["all", "conect",
				"nouser", "noobj", "nowait", "surface"]:
		keywordArgs[argWords[0]] = True
		argWords = argWords[1].split(None, 1)

	if len(argWords) < 1:
		raise MidasError, "command to execute missing"
	if argWords[0][:5] == "mark=":
		raise MidasError, "'mark=' not yet implemented"

	if len(argWords) > 1:
		cmd = argWords[0] + " " + argWords[1]
	else:
		cmd = argWords[0]
	Midas.pdbrun(cmd, **keywordArgs)

def doPerFrame(cmdName, args):
	argWords = _splitQuoted(args)
	frames = _parseKeywordArg(argWords, 'frames', cmdName, int)
	interval = _parseKeywordArg(argWords, 'interval', cmdName, int)
	vRanges = _parseKeywordArg(argWords, 'range', cmdName, multiple=True)
	zeroPadWidth = _parseKeywordArg(argWords, 'zeroPadWidth', cmdName, int)
	valueRanges = [_parsePerFrameRange(r) for r in vRanges]
	from Commands import bool_arg
	showCommands = _parseKeywordArg(argWords, 'showCommands', cmdName,
					bool_arg)
	if len(argWords) == 0 or len(argWords) > 2 or argWords[0] == '':
		raise MidasError("Usage: %s command [zeroPadWidth]" % cmdName)
	command = argWords[0]
	if len(argWords) == 2:
		if zeroPadWidth is None:
			try:
				zeroPadWidth = int(argWords[1])
			except ValueError:
				raise MidasError('%s zeroPadWidth ("%s") is not an integer' %
						 (cmdName, argWords[1]))
		else:
			raise MidasError('%s extra argument ("%s")' %
					 (cmdName, argWords[1]))

	Midas.perFrame(command, frames, interval, valueRanges, zeroPadWidth,
		       showCommands)

def _parsePerFrameRange(r):
	try:
		valueRange = [float(x) for x in r.split(',')]
	except ValueError:
		valueRange = None
	if valueRange is None or len(valueRange) not in (2,3):
		raise MidasError('range must be <rmin>,<rmax>[,<rstep>], '
				 'got "%s"' % r)
	return valueRange

def doUnPerFrame(cmdName, args):
	if args:
		raise MidasError("Usage: %s" % cmdName)
	Midas.stopPerFrame()
		
def doPreneon(cmdName, args):
	chimeraRoot = os.environ.get("CHIMERA")
	doPdbrun('pdbrun', 'nowait conect surface "' +
		os.path.join(chimeraRoot, 'bin', 'neon') + '" ' + args)

def doPreset(cmdName, args):
	parts = args.split(None, 1)
	if len(parts) == 0:
		raise MidasError("usage: preset apply|list ...")
	cmd = parts[0]
	if len(parts) == 1:
		opt = ""
	else:
		opt = parts[1]
	if "list".startswith(cmd):
		from chimera import preset, replyobj
		mgr = preset.get()
		type = opt.strip()
		if not type:
			presets = mgr.listPresets()
		else:
			presets = mgr.listPresets(type)
		for type, n, label in presets:
			replyobj.info("Preset %s %d %s\n" % (
					_quote(type), n, _quote(label, True)))
		from chimera import dialogs, tkgui
		dialogs.display(tkgui._ReplyDialog.name)
	elif "apply".startswith(cmd):
		from chimera import preset
		mgr = preset.get()
		vals = opt.split()
		if len(vals) != 2:
			raise MidasError("usage: preset apply type number|name")
		type = vals[0]
		try:
			mgr.applyPreset(type, vals[1])
		except KeyError, s:
			raise MidasError, s
	else:
		raise MidasError, "unknown subcommand '%s' for 'preset'" % cmd

def _quote(s, always=False):
	l = [ '"' ]
	needQuotes = always
	for c in s:
		if c in '"\\':
			l.append('\\')
		elif c in ' \t':
			needQuotes = True
		l.append(c)
	if needQuotes:
		l.append('"')
		return ''.join(l)
	else:
		return s

def doRangeColor(cmdName, args):
	try:
		attrName, rem = args.split(None, 1)
	except ValueError:
		raise MidasError, \
			"Missing required args (try 'help %s')" % cmdName
	colorItems = ""
	if ',' in attrName:
		attrName, colorItems = attrName.split(',', 1)

	try:
		isKey, rem2 = rem.split(None, 1)
	except ValueError:
		key = False
	else:
		if isKey == "key":
			key = True
			rem = rem2
		else:
			key = False
	wayPoints = []
	noValue=None
	while rem:
		try:
			val, rem = rem.split(None, 1)
		except ValueError:
			break
		if val not in ["min", "mid", "max", "novalue"]:
			try:
				if '.' in val:
					val = float(val)
				else:
					val = int(val)
			except ValueError:
				rem = " ".join([val, rem])
				break
		color, rem = parseColorName(rem)
		if val == "novalue":
			noValue = color
		else:
			wayPoints.append((val, color))

	if len(wayPoints) < 2:
		raise MidasError, "Less than two value/color pairs provided (try 'help %s')" % cmdName

	spec = getSpecs(rem)
	Midas.rangeColor(attrName, colorItems, wayPoints, noValue, spec,
							showKey=key)

def doRead(cmdName, args):
	processCommandFile(tildeExpand(args), emulateRead=True)

def doRepr(cmdName, args):
	# handle 'represent', 'bondrepresent', 'ribrepr',
	# and 'ribscale' commands
	argWords = args.split(None, 1)
	if len(argWords) == 0:
		raise MidasError, "missing representation argument"
	if len(argWords) == 1:
		argWords.append("")
	if cmdName[0] == "b":
		expectedKeywords = ["stick", "wire"]
		cmd = "bondrepr"
	elif cmdName[:3] == "rep":
		expectedKeywords = ["bs", "b+s", "stick", "wire", "cpk",
							"sphere"]
		cmd = "represent"
	elif cmdName[:4] == "ribr":
		# Just pass the ribbon representation through
		# since it might be a custom style
		cmd = "ribrepr"
		_checkForQuote(args, argWords)
		expectedKeywords = [argWords[0]]
		if argWords[0] == "none":
			raise MidasError, \
			  'use "~ribbon" to undisplay ribbons'
	elif cmdName[:4] == "ribc":
		cmd = "ribclass"
		_checkForQuote(args, argWords)
		expectedKeywords = [ argWords[0] ]
	else:
		cmd = "ribscale"
		_checkForQuote(args, argWords)
		expectedKeywords = [ argWords[0] ]
	if argWords[0] not in expectedKeywords:
		raise MidasError(
		  'unknown representation type ("%s")' % argWords[0])
	exec 'Midas.%s("%s", %s)' % (cmd, argWords[0],
					repr(getSpecs(argWords[1])))

def doReprDisplay(cmdName, args):
	# handle 'aromatic', and 'fillring' commands
	if cmdName == 'aromatic':
		expectedKeywords = ["off", "circle", "disk"]
	else:
		expectedKeywords = ["unfilled", "thin", "thick", "off"]
	parts = args.split(None, 1)
	if len(parts) == 0:
		style = None
	elif len(parts) == 1:
		if parts[0] in expectedKeywords:
			style = parts[0]
			args = ""
		else:
			style = None
	else:
		if parts[0] in expectedKeywords:
			style, args = parts
		else:
			style = None
	exec 'Midas.%s(style=%s, sel=%s)' % (cmdName, repr(style),
							repr(getSpecs(args)))

def doRibspline(cmdName, args):
	from Midas import ribspline
	doExtensionFunc(ribspline, args,
				specInfo=[("spec", "models", "molecules")])

def doBond(cmdName, args):
	Midas.bond(getSpecs(args))

def _checkForQuote(args, argWords):
	if args[0] == '"' or args[0] == "'":
		quote = args[0]
	else:
		quote = None
	if quote:
		end = args.find(quote, 1)
		if end < 0:
			raise MidasError, "unterminated quote"
		argWords[0] = args[1:end]
		argWords[1] = args[end + 1:].lstrip()

def doReset(cmdName, args):
	argWords = _splitQuoted(args)
	args = {}
	from Commands import openstate_arg, models_arg
	hold = _parseKeywordArg(argWords, 'holdSteady', cmdName, openstate_arg)
	args['holdSteady'] = hold
	move = _parseKeywordArg(argWords, 'moveModels', cmdName, models_arg)
	args['moveModels'] = move
	n = len(argWords)
	if n >= 1:
		args['name'] = argWords[0]
	if n >= 2:
		try:
			args['frames'] = int(argWords[1])
		except ValueError:
			raise MidasError("frame count should be an integer")
	if n >= 3:
		args['mode'] = argWords[2]
	if n > 3:
		raise MidasError, 'too many arguments'
	Midas.reset(**args)

def doRock(cmdName, args):
	argWords = args.split()

	kw = {'axis': 'y', 'magnitude': 30}

	cycle = _parseKeywordArg(argWords, 'cycle', cmdName, int)
	if cycle is None:
		cycle = 136
	if cycle < 2:
		raise MidasError('minimum rock cycle is 2 frames')
	kw['frequency'] = cycle/2 + 2

	_parseMovementKeywordArgs(argWords, 0, kw, cmdName)

	n = len(argWords)
	if n >= 2:
		kw['magnitude'] = _parseFloat(argWords[1], cmdName, 'magnitude') * 10
	if n >= 3:
		kw['frames'] = _parseInt(argWords[2], cmdName, 'frames')
	if n > 3:
		raise MidasError, 'wait_frames argument not implemented'
	Midas.rock(**kw)

def doRoll(cmdName, args):
	# 'turn' also calls this
	argWords = args.split()

	kw = {'axis':'y'}
	t = _parseKeywordArg(argWords, 'precessionTilt', cmdName, float)
	if not t is None:
		kw['precessionTilt'] = t

	_parseMovementKeywordArgs(argWords, 0, kw, cmdName)

	n = len(argWords)
	if n >= 2:
		kw['angle'] = _parseFloat(argWords[1], cmdName, 'angle')
	if n >= 3:
		kw['frames'] = _parseInt(argWords[2], cmdName, 'frames')
	if n > 3:
		raise MidasError, 'wait_frames argument not implemented'
	f = getattr(Midas, cmdName)
	f(**kw)

# Parse center, models, axis and coordinateSystem keyword arguments.
def _parseMovementKeywordArgs(argWords, axisArgIndex, kw, cmdName):
	_parseCoordinateSystemArg(argWords, kw, cmdName)
	a = 0
	ccs = acs = None
	while a < len(argWords):
		w = argWords[a].lower()
		if 'models'.startswith(w):
			if a+1 >= len(argWords):
				raise MidasError('%s missing models argument' %
						 cmdName)
			kw['models'] = modelsFromSpec(argWords[a+1], 'models')
			del argWords[a:a+2]
		elif w.startswith('ce') and 'center'.startswith(w):
			if a+1 >= len(argWords):
				raise MidasError('%s missing center argument'
						 % cmdName)
			kw['center'], ccs = parseCenterArg(argWords[a+1],
							   cmdName)
			del argWords[a:a+2]
		else:
			a += 1

	# Parse axis argument
	if len(argWords) > axisArgIndex:
                axis_arg = argWords[axisArgIndex]
                if axis_arg == 'cofr':
                        kw['axis'] = 'cofr'
                else:
                        axis, axisPoint, acs = _parseAxis(axis_arg, cmdName)
                        kw['axis'] = axis
                        if not 'center' in kw and axisPoint:
                                # Use axis point if no center specified.
                                kw['center'] = axisPoint
                                ccs = acs

	# If no coordinate system specified use axis or center coord system.
	cs = (ccs or acs)
	if not 'coordinateSystem' in kw and cs: 
		kw['coordinateSystem'] = cs
		xf = cs.xform.inverse()
		if 'center' in kw and not ccs:
			kw['center'] = xf.apply(kw['center'])
		if 'axis' in kw and not acs:
			kw['axis'] = xf.apply(kw['axis'])

	# Convert axis and center to requested coordinate system.
	if 'coordinateSystem' in kw:
		xf = kw['coordinateSystem'].xform.inverse()
		if 'center' in kw and ccs:
			kw['center'] = xf.apply(ccs.xform.apply(kw['center']))
		if 'axis' in kw and acs:
			kw['axis'] = xf.apply(acs.xform.apply(kw['axis']))

def _parseCoordinateSystemArg(argWords, kw, cmdName):
	a = 0
	while a < len(argWords):
		w = argWords[a].lower()
		if 'coordinatesystem'.startswith(w):
			if a+1 >= len(argWords):
				raise MidasError('%s missing coordinateSystem argument' % cmdName)
			os = openStateFromSpec(argWords[a+1],
					       'coordinateSystem')
			kw['coordinateSystem'] = os
			del argWords[a:a+2]
		else:
			a += 1

def _parseKeywordArg(argWords, kwName, cmdName, type=None, multiple=False):
	args = []
	a = 0
	while a < len(argWords):
		w = argWords[a].lower()
		if kwName.lower().startswith(w):
			if a+1 >= len(argWords):
				raise MidasError('%s missing %s argument' %
						 (cmdName, kwName))
			arg = argWords[a+1]
			del argWords[a:a+2]
			if not type is None:
				try:
					arg = type(arg)
				except:
					raise MidasError('%s illegal %s value "%s"' % (cmdName, kwName, arg))
			if multiple:
				args.append(arg)
			else:
				return arg
		else:
			a += 1
	return args if multiple else None

def openStateFromSpec(spec, name):
	if isinstance(spec, int):
		spec = '#%d' % spec
	elif len(spec) > 0 and spec[0].isdigit():
		spec = '#' + spec
	try:
		sel = specifier.evalSpec(spec)
	except:
		raise MidasError, 'Invalid %s model specifier "%s"' % (name, spec)
	osset = set([m.openState for m in sel.models()])
	if len(osset) == 0:
		raise MidasError, 'No models specified by "%s" for %s' % (spec, name)
	elif len(osset) > 1:
		raise MidasError, '%d models specified by "%s" for %s, require exactly 1' % (len(osset), spec, name)
	return osset.pop()

def modelsFromSpec(spec, name):
	if len(spec) > 0 and spec[0].isdigit():
		spec = '#' + spec
	try:
		sel = specifier.evalSpec(spec)
	except:
		raise MidasError, 'Invalid %s model specifier' % name
	mlist = sel.models()
	if len(mlist) == 0:
		raise MidasError, 'No models specified by %s argument' % name
	return mlist

# Parse 3 numbers separated by commas or an atom spec as a point.
def parseCenterArg(arg, cmdName):
	coordSys = None
	from chimera import openModels as om
	cofrMethods = {'view': om.CenterOfView,
		       'models': om.CenterOfModels,
		       'front': om.FrontCenter,
		       }
	if arg in cofrMethods:
		c = om.computeCofr(cofrMethods[arg])
		return c, coordSys
	try:
		xyz = [float(x) for x in arg.split(',')]
	except ValueError:
		xyz = None
	if xyz and len(xyz) == 3:
		c = chimera.Point(*xyz)
	else:
		try:
			sel = specifier.evalSpec(arg)
		except:
			raise MidasError, '%s center must be 3 numbers separated commas or an atom specifier' % cmdName
		if hasattr(sel, 'addImplied'):
			sel.addImplied()  # Include atoms for selected bonds.
		s = Midas.boundingSphere(sel)
		if s is None:
			raise MidasError, '%s center specifier is empty' % cmdName
		coordSys = sel.graphs()[0].openState
		c = coordSys.xform.inverse().apply(s.center)
	return c, coordSys

def _parseAxis(arg, cmdName):
	from chimera import Vector
	axes = {'x':(1,0,0), 'y':(0,1,0), 'z':(0,0,1)}
	axisPoint = coordSys = None
	if arg in axes:
		axis = Vector(*axes[arg])
	else:
		try:
			axis = Vector(*[float(x) for x in arg.split(',')])
		except:
			axis, axisPoint, coordSys = _parseAtomBondAxis(arg)
		if axis is None and arg[0] == 'a' and arg[1:].isdigit():
			# defined axis
			from StructMeasure.Geometry import geomManager
			items = geomManager.items
			try:
				obj = [item for item in items if item.id == arg][0]
			except IndexError:
				raise MidasError("No such defined axis: %s" % arg)
			from StructMeasure.Axes import Axis
			axis = obj.xformDirection()
			axisPoint = obj.xformCenter()
	if axis is None or len(axis) != 3:
		raise MidasError, '%s axis argument must be "x", "y", or "z" or 3 numbers separated by commas, a defined axis (see "define" command), or a specifier for a bond or pair of atoms' % (cmdName)
	return axis, axisPoint, coordSys

def _parseAtomBondAxis(arg):
	try:
		sel = specifier.evalSpec(arg)
	except:
		return None, None, None
	alist = sel.atoms()
	blist = sel.bonds()
	if len(blist) == 1:
		p1, p2 = [a.xformCoord() for a in blist[0].atoms]
		axis = p2 - p1
		m = blist[0].molecule
	elif len(alist) == 2:
		p1, p2 = [a.xformCoord() for a in alist]
		axis = p2 - p1
		m = alist[0].molecule
	else:
		return None, None, None
	xf = m.openState.xform.inverse()
	return xf.apply(axis), xf.apply(p1), m.openState

def _parseFloat(arg, cmdName, argName):
	try:
		f = float(arg)
	except ValueError:
		raise MidasError, '%s %s argument must be a number' % (cmdName, argName)
	return f

def _parseInt(arg, cmdName, argName):
	try:
		i = int(arg)
	except ValueError:
		raise MidasError, '%s %s argument must be an integer' % (cmdName, argName)
	return i

def doRotation(cmdName, args):
	adjust = reverse = frames = None
	if args:
		words = args.split()
		try:
			rotID = int(words[0])
			words.pop(0)
		except ValueError:
			rotID = None
		if words and rotID is not None:
			try:
				adjust = float(words[0])
				words.pop(0)
			except ValueError:
				pass
			else:
				if words:
					try:
						frames = int(words.pop(0))
					except ValueError:
						raise MidasError("Number of frames must be an integer")
				if words:
					raise MidasError("Extra text at end of command")
		if words:
			reverse = "reverse".startswith(words[0])
			if reverse:
				words.pop(0)
	else:
		words = None
	if not words and adjust is None:
		raise MidasError("No rotation atoms specified")
	exec 'Midas.rotation(%s, rotID=%s, reverse=%s, adjust=%s, frames=%s)' % (
		repr(getSpecs(" ".join(words))), repr(rotID), repr(reverse),
		repr(adjust), repr(frames))

def doUnnamesel(cmdName, args):
	selName = args.strip()
	if not selName:
		raise MidasError("~namesel requires a selection name argument")
	Midas.unnamesel(selName)

def doUnrotation(cmdName, args):
	try:
		id = int(args)
	except ValueError:
		raise MidasError("Need to specify an integer rotation ID")
	Midas.unrotation(id)

def doRunScript(cmdName, cmdArgs):
	if not cmdArgs:
		raise MidasError("No script name provided")
	words = cmdArgs.split()
	if words[0] in ("browse", "browser"):
		if chimera.nogui:
			raise MidasError("Cannot use file browser in nogui mode")
		om = OpenModal(title="runscript Script Location",
			filters=[("Python", ["*"+ext for ext in chimera.fileInfo.extensions("Python")])],
			defaultFilter="Python")
		pathsAndTypes = om.run(chimera.tkgui.app)
		om.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise MidasError('No file chosen for runscript command')
		scriptPath = pathsAndTypes[0][0]
	else:
		scriptPath = os.path.expanduser(words[0])
	scriptArgs = []
	quoteArg = None
	for word in words[1:]:
		if quoteArg:
			quoteArg += ' ' + word
			if quoteArg[0] == quoteArg[-1]:
				scriptArgs.append(quoteArg[1:-1])
				quoteArg = None
			continue
		if word[0] in ['"', "'"]:
			if len(word) > 1 and word[0] == word[-1]:
				word = word[1:-1]
			else:
				quoteArg = word
				if len(word) == 1:
					quoteArg += ' '
				continue
		scriptArgs.append(word)
	if quoteArg:
		raise MidasError("Unmatched quote in argument list")
	scriptDir, scriptFile = os.path.split(scriptPath)
	if not scriptDir:
		scriptDir = '.'
	if not os.path.exists(scriptPath):
		raise MidasError("No such script: %s" % scriptPath)
	scriptGlobals = {
		'__name__': "__main__",
		'__file__': scriptFile,
		'chimera': chimera,
		'arguments': tuple(scriptArgs)
	}
	oldArgv = sys.argv
	sys.argv = [scriptPath] + scriptArgs
	sys.path.append(scriptDir)
	try:
		execfile(scriptPath, scriptGlobals)
	finally:
		sys.argv = oldArgv
		sys.path.reverse()
		sys.path.remove(scriptDir)
		sys.path.reverse()

def doSave(cmdName, args):
	if not args:
		if chimera.nogui:
			raise MidasError, "Cannot use argless 'save' command"\
							" in nogui mode\n"
		sm = SaveModal(title="Command-line Save",
				filters=[("Python", ["*.py"], ".py")])
		pathsAndTypes = sm.run(chimera.tkgui.app)
		sm.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise MidasError, 'No file chosen for save'
		path = pathsAndTypes[0][0]
	else:
		path = tildeExpand(args)
	Midas.save(path)

def doSavepos(cmdName, args):
	if args:
		args = args.strip()
		if ((args.startswith('"') and args.endswith('"')) or
		    (args.startswith("'") and args.endswith("'"))):
			args = args[1:-1]
		Midas.savepos(args)
		return
	Midas.savepos()

def doScale(cmdName, args):
	argWords = tuple(args.split())
	if len(argWords) > 2:
		raise MidasError('wait_frames argument not implemented')
	if len(argWords) < 1:
		raise MidasError('required scaling factor argument missing')
	if len(argWords) == 2:
		try:
			scaleFactor = float(argWords[0])
			numFrames = int(argWords[1])
		except ValueError:
			raise MidasError("scale-factor must be positive real number"
				" and #frames must be integer")
		exec 'Midas.scale(%f, frames=%d)' % (scaleFactor, numFrames)
		return
	Midas.scale(float(args))

def doSection(cmdName, args):
	argWords = tuple(args.split())
	if len(argWords) > 2:
		raise MidasError, 'wait_frames argument not implemented'
	if len(argWords) < 1:
		raise MidasError, 'required distance argument missing'
	if len(argWords) == 2:
		exec 'Midas.section(%s, frames=%s)' % argWords
		return
	try:
		val = float(args)
	except ValueError:
		raise MidasError("distance must be a number (not %s)" % args)
	Midas.section(val)

def doSelect(cmdName, args):
	# the next thirteen lines would be 3 lines if Unicode strings supported the two-arg
	# translate method
	if args == "all":
		allModelSelect(True, ids=args)
		return
	if args:
		try:
			sargs = str(args)
		except:
			# untranslatable Unicode
			pass
		else:
			if sargs.translate(None, '.-, ').isdigit():
				allModelSelect(True, ids=args)
				return
	Midas.chimeraSelect(getSpecs(args))

def doUnselect(cmdName, args):
	# the next thirteen lines would be 3 lines if Unicode strings supported the two-arg
	# translate method
	if args == "all":
		allModelSelect(False, ids=args)
		return
	if args:
		try:
			sargs = str(args)
		except:
			# untranslatable Unicode
			pass
		else:
			if sargs.translate(None, '.-,').isdigit():
				allModelSelect(False, ids=args)
				return
	Midas.unchimeraSelect(getSpecs(args))

def doSet(cmdName, args):
	if args == "":
		raise MidasError, "No keywords given to 'set' command"

	# Value is arg count.
	kw = {'autoColor':0,
	      'bgColor':1,
	      'bgTransparency':0,
	      'depthCue':0,
	      'dcColor':1,
	      'dcStart':1,
	      'dcEnd':1,
	      'echo':0,
	      'eyeSeparation':1,
	      'fieldOfView':1,
	      'flatTransparency':0,
	      'fullscreen':0,
	      'independent':0,
	      'lightQuality':1,
	      'maxFrameRate':1,
	      'projection':1,
	      'screenDistance':1,
	      'screenWidth':1,
	      'shadows':0,
	      'showCofR':0,
	      'silhouette':0,
	      'silhouetteColor':1,
	      'silhouetteWidth':1,
	      'singleLayer':0,
	      'subdivision':1,
	      'subdivisionPixels':1,
	      }
	import Commands
	abbr = Commands.abbreviation_table(kw.keys())
	
	argWords = args.split()
	while len(argWords) > 0:
		k = abbr.get(argWords[0].lower().replace('_','').replace('colour','color'))
		if k is None:
			raise MidasError('no such "set" variable '
					 '(or not implemented): %s'
					 % argWords[0])
		cmdName = 'set' + k[0].upper() + k[1:]
		cmd = getattr(Midas, cmdName, None)
		if cmd is None:
			raise MidasError('"set" variable not implemented: %s'
					 % argWords[0])
		if kw[k] > 0:
			if len(argWords) < 2:
				raise MidasError('no value given for "set %s"'
						 % argWords[0])
			cmd(" ".join(argWords[1:]))
			argWords = argWords[2:]
			break
		else:
			cmd()
			argWords = argWords[1:]

def doUnset(cmdName, args):
	if args == "":
		raise MidasError, "No keywords given to 'set' command"

	kw = {'autoColor':0,
	      'bgTransparency':0,
	      'depthCue':0,
	      'echo':0,
	      'flatTransparency':0,
	      'fullscreen':0,
	      'independent':0,
	      'singleLayer':0,
	      'shadows':0,
	      'showCofR':0,
	      'silhouette':0,
	      'subdivisionPixels':0,
	      }
	import Commands
	abbr = Commands.abbreviation_table(kw.keys())

	argWords = args.split()
	while len(argWords) > 0:
		k = abbr.get(argWords[0].lower().replace('_','').replace('colour','color'))
		if k is None:
			raise MidasError('no such "unset" variable '
					 '(or not implemented): %s'
					 % argWords[0])
		cmdName = 'unset' + k[0].upper() + k[1:]
		cmd = getattr(Midas, cmdName, None)
		if cmd is None:
			raise MidasError('"unset" variable not implemented: %s'
					 % argWords[0])
		cmd()
		argWords = argWords[1:]

def doSetAttr(cmdName, args):
	usage = "%s atom|residue|molecule|surface|pseudobond|group attrName attrVal atomspec" % cmdName
	try:
		level, name, rem = args.split(None, 2)
	except ValueError:
		raise MidasError("Usage: %s" % usage)

	value, spec = _parseTyped(name, rem)
	if isinstance(value, basestring):
		value = convertType(value, noneOkay=True)
	Midas.setAttr(level, name, value, getSpecs(spec))

def doUnsetAttr(cmdName, args):
	try:
		level, name = args.split(None, 1)
	except ValueError:
		raise MidasError(
			"Usage: %s atom|residue|molecule|surface|pseudobond|group attrName" % cmdName)
	Midas.unsetAttr(level, name)

def doRainbow(cmdName, args):
	argWords = args.split()

	kw = {}
	if argWords:
		if argWords[0] in ['residue', 'residues']:
			argWords = argWords[1:]
		elif argWords[0] in ['model', 'models']:
			kw['changeAt'] = 'models'
			argWords = argWords[1:]
		elif argWords[0] in ['chain', 'chains']:
			kw['changeAt'] = 'chains'
			argWords = argWords[1:]
		elif argWords[0] in ['helix', 'helices']:
			kw['changeAt'] = 'helix'
			argWords = argWords[1:]
		elif argWords[0] in ['strand', 'strands']:
			kw['changeAt'] = 'strand'
			argWords = argWords[1:]
		elif argWords[0] in ['sse']:
			kw['changeAt'] = 'sse'
			argWords = argWords[1:]

	remainder = " ".join(argWords)
	if ',' in args and remainder[0] not in "#:@" \
	and not remainder[0].isdigit():
		colors = []
		candidates = remainder.split(',')
		while candidates:
			candidate = candidates[0].strip()
			color, rem = parseColorName(candidate)
			colors.append(color)
			if rem:
				candidates[0] = rem
				break
			candidates = candidates[1:]
		remainder = " ".join(candidates)
		kw['colors'] = colors
	Midas.rainbow(sel=getSpecs(remainder, modelLevel=1), **kw)

def doSleep(cmdName, args):
	import time
	try:
		t = float(args)
	except:
		raise MidasError(
			"'sleep' takes the number of seconds as an argument")
	time.sleep(t)

def doStart(cmdName, args):
	ext = args.strip()
	if not ext:
		raise MidasError, "Please specify the name of an extension"
	from chimera import extension, replyobj
	startExtensions = [ ext ]
	extension.startup(startExtensions)
	if startExtensions:
		replyobj.error("Starting extension '%s' failed\n" % ext)
	else:
		msg = "Extension '%s' started\n" % ext
		replyobj.status(msg)
		replyobj.message(msg)

def doStereo(cmdName, args):
	argWords = args.split()
	domeTiltAngle = _parseKeywordArg(argWords, 'tilt', cmdName)
	if domeTiltAngle:
		try:
			domeTiltAngle = float(domeTiltAngle)
		except ValueError:
			raise MidasError('Dome tilt angle must be a number,'
					 ' got "%s"' % domeTiltAngle)
	domeParallaxAngle = _parseKeywordArg(argWords, 'parallax', cmdName)
	if domeParallaxAngle:
		try:
			domeParallaxAngle = float(domeParallaxAngle)
		except ValueError:
			raise MidasError('Dome parallax angle must be a number,'
					 ' got "%s"' % domeParallaxAngle)

	mode = ' '.join(argWords)
	if mode not in chimera.StereoKwMap:
		raise MidasError('Unrecognized stereo mode: %s' % mode)
	Midas.stereo(mode, domeTiltAngle, domeParallaxAngle)

def doUnstereo(cmdName, args):
	Midas.stereo("mono")

def doStop(cmdName, args):
	if not chimera.nogui:
		neverAsk = scripting
		argWords = args.split(None, 1)
		confirmList = [ "now", "noask", "confirmed", "yes", "really" ]
		if len(argWords) == 1 and argWords[0] in confirmList:
			neverAsk = True
		chimera.tkgui._confirmExit(neverAsk=neverAsk)
		return
	chimera.triggers.activateTrigger(APPQUIT, None)
	raise ChimeraSystemExit, 0

def doSurface(cmdName, args):
	words = args.split()
	kw = {}
	from Commands import bool_arg
	for kname, vtype in (('method',None), ('visiblePatches', int),
			     ('probeRadius',float), ('vertexDensity',float),
			     ('allComponents',bool_arg), ('grid', float),
			     ('category', str), ('warnLarge', bool_arg)):
		v = _parseKeywordArg(words, kname, cmdName, vtype)
		if not v is None:
			kw[kname] = v

	if len(words) == 0:
		kw['category'] = "main"
		atomSpec="#"
	else:
		if not 'category' in kw:
			kw['category'] = 'all categories'
		specs = "".join(words)
		atomSpec = getSpecs(specs)
        if not scripting and 'warnLarge' not in kw:
                kw['warnLarge'] = True
	Midas.surface(atomSpec, **kw)

def doUnsavepos(cmdName, args):
	Midas.unsavepos(args)

def doUnsurface(cmdName, args):
	if not args:
		Midas.unsurface("#")
		return
	from Categorizer import categories
	if args in categories or userSurfCategories.has_key(args):
		exec 'Midas.unsurface("@/surfaceCategory=%s")' % args
		return
	Midas.unsurface(getSpecs(args))

def doSurfaceNew(cmdName, args):
	# create a new surface
	argWords = args.split(None, 1)
	if len(argWords) == 1:
		argWords.append("")
	Midas.surfaceNew(argWords[0], getSpecs(argWords[1]))

def doSurfaceDelete(cmdName, args):
	# delete an existing surface
	argWords = args.split(None, 1)
	if len(argWords) == 1:
		argWords.append("")
	Midas.surfaceDelete(argWords[0], getSpecs(argWords[1]))

def doSurfaceCategory(cmdName, args):
	# assign surface categories for atoms
	if not args:
		raise MidasError("Usage: surfcat category_name atom-spec")
	argWords = args.split(None, 1)
	userSurfCategories[argWords[0]] = 1
	if len(argWords) == 1:
		argWords.append("")
	Midas.surfaceCategory(argWords[0], getSpecs(argWords[1]))

def doSurfaceColor(cmdName, args):
	argWords = args.split(None, 1)
	if not argWords:
		raise MidasError("No surface-coloring mode specified")
	if len(argWords) == 1:
		argWords.append("")
	if argWords[0] not in ["bymodel", "byatom", "custom"]:
		raise MidasError(
			'unknown surface coloring mode ("%s")' % argWords[0])
	Midas.surfacecolormode(argWords[0], getSpecs(argWords[1]))

def doSurfaceRepr(cmdName, args):
	# change chimera representation styles for surfaces
	argWords = args.split(None, 1)
	styles = ["solid", "filled", "mesh", "dot"]
	if not argWords:
		raise MidasError("Must specify repr type (one of: %s)"
							% ", ".join(styles))
	if len(argWords) == 1:
		argWords.append("")
	if argWords[0] not in styles:
		raise MidasError('Unknown representation type ("%s")'
							% argWords[0])
	Midas.surfacerepresent(argWords[0], getSpecs(argWords[1]))

def doSurfaceTransparency(cmdName, args):
	argWords = args.split(None, 2)
	try:
		transp = float(argWords[0])
	except ValueError:
		raise MidasError("Transparency value must be between"
			" 0 and 100 (inclusive)")
	except IndexError:
		raise MidasError("Transparency percentage argument is missing")
	if len(argWords) >= 2:
		spec = argWords[1]
	else:
		spec = ""
	if len(argWords) >= 3:
		try:
			frames = int(argWords[2])
		except ValueError:
			raise MidasError("Frames value must be an integer")
	else:
		frames = None
	Midas.surfacetransparency(transp, getSpecs(spec), frames)

def doUnsurfaceTransparency(cmdName, args):
	# set transparency to None
	argWords = args.split(None, 1)
	if len(argWords) >= 1:
		spec = argWords[0]
	else:
		spec = ""
	if len(argWords) >= 2:
		try:
			frames = int(argWords[1])
		except ValueError:
			raise MidasError("Frames value must be an integer")
	else:
		frames = None
	Midas.surfacetransparency(None, getSpecs(spec), frames)

def doSwapRes(cmdName, args):
	def usage():
		raise MidasError(
			'Usage: swapna new_res_type atomspec [preserve true|false]')
	if not args:
		usage()
	argWords = args.split()
	if len(argWords) == 1:
		argWords.append("")
	if len(argWords) > 3 and argWords[-2] == "preserve":
		try:
			preserve = eval(argWords[-1].capitalize())
		except NameError:
			usage()
		res = argWords[0]
		spec = " ".join(argWords[1:-2])
	else:
		res = argWords[0]
		spec = " ".join(argWords[1:])
		preserve = True
	Midas.swapres(res, getSpecs(spec), preserve=preserve)

def doSystem(cmdName, args):
	os.system(args)

def doTColor(cmdName, args):
	if not args:
		raise MidasError, 'No texture color specified'
	argWords = args.split(None, 1)
	if len(argWords) < 2:
		specs = getSpecs("")
	else:
		specs = getSpecs(argWords[1])
	color = argWords[0]
	Midas.tColor(color, specs)

def doTexture(cmdName, args):
	argWords = tuple(args.split(None, 1))
	if argWords[0] == "color":
		exec 'Midas.textureColor("%s","%s")' % tuple(
		  argWords[1].split(None, 1))
		return
	elif argWords[0] == "new":
		otherArgs = argWords[1].split()
		if len(otherArgs) > 2:
			raise MidasError, \
			  "Too many arguments for texture new command"
		elif len(otherArgs) == 1:
			Midas.textureNew(otherArgs[0])
			return
		exec 'Midas.textureNew("%s", %s)' % tuple(otherArgs)
		return
	elif argWords[0] == "use":
		Midas.textureUse(argWords[1])
		return
	elif argWords[0] == "map":
		mapArgs = []
		for assignment in argWords[1].split():
			try:
				index, name = assignment.split('=', 1)
			except ValueError:
				raise MidasError, \
				  'No "=" found in assignment string'
			try:
				i = int(index)
			except ValueError:
				raise MidasError, \
				  "Left side of map must be an integer"
			mapArgs.append("color" + index + '="'+name+'"')
		exec 'Midas.textureMap(%s)' % ", ".join(mapArgs)
		return
	raise MidasError, 'unknown texture keyword "%s"' % argWords[0]

def doThickness(cmdName, args):
	argWords = tuple(args.split())
	if len(argWords) > 2:
		raise MidasError, 'wait_frames argument not implemented'
	if len(argWords) < 1:
		raise MidasError(
			'clip plane separation reporting not implemented')
	if len(argWords) == 2:
		exec 'Midas.thickness(%s, frames=%s)' % argWords
		return
	Midas.thickness(float(args))

def doTransparency(cmdName, args):
	argWords = args.split()
	frames = _parseKeywordArg(argWords, 'frames', cmdName, int)
	if frames:
		args = ' '.join(argWords)
	argWords = args.split(None, 1)
	if len(argWords) == 0:
		raise MidasError('No transparency specified')
	else:
		t = argWords[0]
		tfields = t.split(',')
		if len(tfields) == 0:
			raise MidasError('No transparency value given')
		try:
			trans = float(tfields[0])
		except ValueError:
			raise MidasError('Transparency must be a number'
					 ' , got "%s"' % tfields[0])
		items = tfields[1:]
	for itype in items:
		if not (',%s' % itype) in Midas.ColorSuffixes:
			raise MidasError('Unrecognized transparency specifier '
					 + itype)
	specs = getSpecs("") if len(argWords) <= 1 else getSpecs(argWords[1])
	Midas.transparency(trans, specs, items, frames)

def doUntransparency(cmdName, args):
	args = args.lstrip()
	tval = '0' if args and args[0] == ',' else '0 '
	args = tval + args
	doTransparency(cmdName, args)

def doVdwDefine(cmdName, args):
	argWords = args.split(None, 3)
	def floatable(x):
		try:
			float(x)
		except:
			return False
		return True
	if len(argWords) < 1 or not floatable(argWords[0]):
		raise MidasError('Usage: vdwdefine [+/-]radius [atomSpec]')
	if len(argWords) < 2:
		argWords.append("")
	if argWords[0][0] in "+-":
		# increment/decrement radii
		keyArg = ", increment=True"
	else:
		keyArg = ""
	exec 'Midas.vdwdefine(%s, %s%s)' % (argWords[0],
			repr(getSpecs(argWords[1])), keyArg) in globals(), {}

def doVdwDensity(cmdName, args):
	argWords = args.split(None, 1)
	if len(argWords) < 1:
		raise MidasError, "missing density argument required"
	if len(argWords) < 2:
		argWords.append("")
	exec 'Midas.vdwdensity(%s, %s)' % (argWords[0],
					repr(getSpecs(argWords[1])))

def doWait(cmdName, args):
	if args:
		try:
			Midas.wait(int(args))
		except ValueError:
			raise MidasError("'wait' argument ('%s') is not an integer" % args)
	else:
		Midas.wait()

def doWindow(cmdName, args):
	Midas.window(getSpecs(args))

def doWindoworigin(cmd_name, args):
	if not args:
		Midas.windoworigin()
		return
	try:
		x, y = map(int, args.split())
	except:
		raise MidasError, 'Syntax error: %s [<x-in-pixels> <y-in-pixels>]' % cmd_name
	Midas.windoworigin((x, y))

def doWindowsize(cmd_name, args):
	# The status line and command entry box at the bottom of the
	# main Chimera window prevent the window from being resized by
	# this code to a width smaller than about 450 pixels.  The
	# status line can be turned off using Favorites / Preferences
	# / Messages / Show status line, and the command-line can be
	# hidden with Tools / Command-line / hide.  Commands can
	# still be typed with the command-line hidden.
	if not args:
		Midas.windowsize()
		return
	try:
		width, height = map(int, args.split())
	except:
		raise MidasError, 'Syntax error: %s [<width-in-pixels> <height-in-pixels>]' % cmd_name
	Midas.windowsize((width, height))

def doUnwindowsize(cmd_name, args):
	if args:
		raise MidasError, "too many arguments to ~windowsize"
	Midas.unwindowsize()

def doWrite(cmdName, args):
	argWords = args.split(None, 1)
	relModel = None
	allFrames = False
	dispOnly = selOnly = False
	resNum = False
	format = "pdb"
	atomTypes = "sybyl"
	snStyle = "h36"
	while len(argWords) > 1:
		if argWords[0] == "relative":
			following = argWords[1].split(None, 1)
			relModel = getModelId(following[0])
			argWords = following[1].split(None, 1)
		elif argWords[0] == "trajectory":
			argWords = argWords[1].split(None, 1)
			allFrames = True
		elif argWords[0] == "surface":
			raise MidasError, "writing surfaces not yet supported"
		elif argWords[0] == "displayed":
			argWords = argWords[1].split(None, 1)
			dispOnly = True
		elif argWords[0] == "selected":
			argWords = argWords[1].split(None, 1)
			selOnly = True
		elif argWords[0] == "format":
			format, remainder = argWords[1].split(None, 1)
			format = format.lower()
			if format not in ["pdb", "pqr", "mol2", "sph"]:
				raise MidasError("'format' value must either"
					" be 'pdb', 'pqr', 'mol2' or 'sph'")
			argWords = remainder.split(None, 1)
		elif argWords[0].lower() == "atomtypes":
			atomTypes, remainder = argWords[1].split(None, 1)
			atomTypes = atomTypes.lower()
			if atomTypes not in ["gaff", "sybyl", "amber"]:
				raise MidasError("'atomTypes' value must either"
					" be 'sybyl', 'gaff', or 'amber'")
			argWords = remainder.split(None, 1)
		elif argWords[0] == "noresnum":
			argWords = argWords[1].split(None, 1)
		elif argWords[0] == "resnum":
			resNum = True
			argWords = argWords[1].split(None, 1)
		elif argWords[0] in ("serial", "serialNumbering"):
			snStyle, remainder = argWords[1].split(None, 1)
			snStyle = snStyle.lower()
			if snStyle not in ("h36", "amber"):
				raise MidasError("'serialNumbering' value must"
					" be either 'h36' or 'amber'")
			argWords = remainder.split(None, 1)
		else:
			break
	if not argWords:
		raise MidasError("Must supply model number as an argument")
	writeModel = getModelId(argWords[0])
	if len(argWords) == 1:
		if chimera.nogui:
			raise MidasError, "Cannot use argless 'write' command"\
							" in nogui mode\n"
		if format == "pdb":
			filters = [("PDB", ["*.pdb"], ".pdb")]
		elif format == "pdb":
			filters = [("PQR", ["*.pqr"], ".pqr")]
		elif format == "mol2":
			filters = [("Mol2", ["*.mol2"], ".mol2")]
		else:
			filters = [("Text", ["*.txt"], ".txt")]
		sm = SaveModal(title="Command-line Write", filters=filters)
		pathsAndTypes = sm.run(chimera.tkgui.app)
		sm.destroy()
		if pathsAndTypes == None:
			return
		elif not pathsAndTypes:
			raise MidasError, 'No file chosen for write'
		filename = pathsAndTypes[0][0]
	else:
		filename = tildeExpand(argWords[1])
	exec 'Midas.write(%s, %s, %s, allFrames=%s, dispOnly=%s, selOnly=%s,' \
		' format=%s, resNum=%s, atomTypes=%s, serialNumbering=%s)' % (writeModel,
		relModel, repr(filename), repr(allFrames), repr(dispOnly),
		repr(selOnly), repr(format), repr(resNum), repr(atomTypes), repr(snStyle))

def getModelId(s):
	if isinstance(s, basestring) and len(s) > 0 and s[0] == '#':
		n = s[1:]
	else:
		n = s
	try:
		if n.find('.') < 0:
			major = int(n)
			minor = None
		else:
			a, b = n.split('.', 1)
			major = int(a)
			minor = int(b)
	except ValueError:
		raise MidasError, "\"%s\" is not a model number" % s
	return (major, minor)

def getSpecs(args, modelLevel=False):
	args = args.strip()
	if len(args) <= 0:
		return "#"
	if modelLevel and args[0].isdigit():
		args = '#' + args

	# replace what seem to be residue names with '::' syntax
	if args.find('::') < 0 and \
	args.find(':start') < 0 and \
	args.find(':all') < 0 and \
	args.find(':end') < 0 :
		args = re.sub(r':(?=\s*[a-zA-Z])', '::', args)

	return args

def doRMSD(cmdName, args):
	argWords = args.split()
	if len(argWords) == 0:
		raise MidasError, 'missing atom spec'
	replyobj.info('Executing %s %s\n' % (cmdName, argWords))
	spec1, spec2 = _parseAtomSpecs(argWords)
	exec 'Midas.rmsd(%s, %s)' % ( repr(getSpecs(spec1)), repr(getSpecs(spec2)))

def doChirality(cmdName, args):
	exec 'Midas.chirality(args)'

def doAddAA(cmdName, args):
	exec 'Midas.addaa(args)'


cmdList = [
	#	command name	function	~function	changes display
	(	'addaa',	doAddAA,	None,		True	),
	(	'addgrp',	Unimplemented,	Unimplemented,	True	),
	(	'adjust',	doAdjust,	None,	True	),
	(	'alias',	doAlias,	doUnalias,	False	),
	(	'align',	doAlign,	None,		True	),
	(	'angle',	doAngle,	Unimplemented,	False	),
	(	'aromatic',	doReprDisplay,	doAtomSpecFunc,	True	),
	(	'assign',	Unimplemented,	Unimplemented,	False	),
	(	'background',	doBackground,	Unimplemented,	True	),
	(	'bond',		doBond,		doUnbond,	True	),
	(	'bondcolor',	doBondColor,	doBondUncolor,	True	),
	(	'bondcolour',	doBondColor,	doBondUncolor,	True	),
	(	'bonddisplay',	doBondDisplay,	None,		True	),
	(	'bondrepresent',doRepr,		None,		True	),
	(	'bs',		Unimplemented,	Unimplemented,	False	),
	(	'cd',		doCd,		None,		False	),
	(	'center',	doAtomSpecFunc,	None,		True	),
	(	'centre',	doAtomSpecFunc,	None,		True	),
	(	'chain',	doAtomSpecFunc, Unimplemented,	True	),
	(	'chirality',	doChirality,	None,		False	),
	(	'clip',		doClip,		doUnclip,	True	),
	(	'close',	doClose,	None,		True	),
	(	'cofr',		doCofr,		doArglessFunc,	False	),
	(	'color',	doColor,	doUncolor,	True	),
	(	'colour',	doColor,	doUncolor,	True	),
	(	'colordef',	doColordef,	None,		False	),
	(	'colourdef',	doColordef,	None,		False	),
	(	'colorrename',	Unimplemented,	Unimplemented,	False	),
	(	'colourrename',	Unimplemented,	Unimplemented,	False	),
	(	'conic',	doConic,	None,		False	),
	(	'copy',		doCopy,		None,		False	),
	(	'define',	doDefine,	doUndefine,		True	),
	(	'delete',	doAtomSpecFunc,	None,		True	),
	(	'delegate',	Unimplemented,	Unimplemented,	False	),
	(	'density',	Unimplemented,	Unimplemented,	False	),
	(	'devopt',	Unimplemented,	Unimplemented,	False	),
	(	'display',	doAtomSpecFunc,	doAtomSpecFunc,	True	),
	(	'discern',	Unimplemented,	Unimplemented,	False	),
	(	'distance',	doDistance,	doUndistance,	True	),
	(	'echo',		doEcho,		None,		False	),
	(	'export',	doExport,	None,		False	),
	(	'fillring',	doReprDisplay,	doAtomSpecFunc,	True	),
	(	'fix',		Unimplemented,	Unimplemented,	False	),
	(	'fixreverse',	Unimplemented,	Unimplemented,	False	),
	(	'focus',	doAtomSpecFunc,	doArglessFunc,	True	),
	(	'freeze',	doArglessFunc,	None,		True	),
	(	'gd',		Unimplemented,	Unimplemented,	False	),
	(	'getcrd',	doGetcrd,	None,		False	),
	(	'help',		doHelp,		None,		False	),
	(	'intensity',	Unimplemented,	Unimplemented,	True	),
	(	'ksdssp',	doKsdssp,	None,		True	),
	(	'label',	doLabel,	doAtomSpecFunc,	True	),
	(	'labelopt',	doLabelopt,	None,		False	),
	(	'label3d',	Unimplemented,	Unimplemented,	False	),
	(	'linewidth',	doLinewidth,	None,		True	),
	(	'longbond',	doLongbond,	doArglessFunc,	True	),
	(	'makemark',	Unimplemented,	Unimplemented,	True	),
	(	'makems',	Unimplemented,	Unimplemented,	True	),
	(	'mark',		Unimplemented,	Unimplemented,	True	),
	(	'match',	doMatch,	None,		True	),
	(	'matrixcopy',	doMatrixcopy,	None,		True	),
	(	'matrixget',	doMatrixget,	None,		False	),
	(	'matrixset',	doMatrixset,	None,		True	),
	(	'midasmovie',	Unimplemented,	Unimplemented,	False	),
	(	'midaspush',	Unimplemented,	Unimplemented,	False	),
	(	'midaspop',	Unimplemented,	Unimplemented,	False	),
	(	'modeldisplay',	doModelFunc,	doModelFunc,	True	),
	(	'modelcolor',	doColor,	None,		True	),
	(	'modelcolour',	doColor,	None,		True	),
	(	'move',		doMove,		None,		True	),
	(	'mrotate',	Unimplemented,	Unimplemented,	False	),
	(	'msms',		doMsMs,		None,		True	),
	(	'namesel',	doNamesel,	doUnnamesel,		False	),
	(	'neon',		doNeon,		None,		False	),
	(	'noeshow',	Unimplemented,	Unimplemented,	True	),
	(	'objdisplay',	doModelFunc,	doModelFunc,	True	),
	(	'open',		doOpen,		doClose,	True	),
	(	'pause',	doPause,	None,		False	),
	(	'pdb2site',	Unimplemented,	Unimplemented,	False	),
	(	'pdbopen',	Unimplemented,	Unimplemented,	False	),
	(	'pdbrun',	doPdbrun,	None,		False	),
	(	'perframe',	doPerFrame,	doUnPerFrame,	False	),
	(	'pickatom',	Unimplemented,	Unimplemented,	False	),
	(	'pickabort',	Unimplemented,	Unimplemented,	False	),
	(	'preset',	doPreset,	None,		True	),
	(	'preneon',	doPreneon,	None,		False	),
	(	'rainbow',	doRainbow,	None,		True	),
	(	'rangecolor',	doRangeColor,	None,		True	),
	(	'rangecolour',	doRangeColor,	None,		True	),
	(	'read',		doRead,		None,		False	),
	(	'record',	Unimplemented,	Unimplemented,	False	),
	(	'represent',	doRepr,		None,		True	),
	(	'reset',	doReset,	None,		True	),
	(	'reverse',	Unimplemented,	Unimplemented,	False	),
	(	'ribbon',	doAtomSpecFunc,	doAtomSpecFunc,	True	),
	(	'ribbackbone',	doModelFunc,	doModelFunc,	True	),
	(	'ribbonjr',	Unimplemented,	None,		False	),
	(	'ribcolor',	doColor,	doUncolor,	True	),
	(	'ribcolour',	doColor,	doUncolor,	True	),
	(	'ribinsidecolor',  doColor,	doUncolor,	True	),
	(	'ribinsidecolour', doColor,	doUncolor,	True	),
	(	'ribrepr',	doRepr,		None,		True	),
	(	'ribscale',	doRepr,		None,		True	),
	(	'ribclass',	doRepr,		None,		True	),
	(	'ribspline',	doRibspline,	None,		True	),
	(	'rlabel',	doLabel,	doAtomSpecFunc,	True	),
	(	'rmsd',		doRMSD,		None,		False	),
	(	'rock',		doRock,		None,		False	),
	(	'roll',		doRoll,		None,		False	),
	(	'rotation',	doRotation,	doUnrotation,	False	),
	(	'runscript',	doRunScript,	None,		False	),
	(	'run',		Unimplemented,	Unimplemented,	False	),
	(	'save',		doSave,		None,		False	),
	(	'savepos',	doSavepos,	doUnsavepos,	False	),
	(	'scale',	doScale,	doArglessFunc,	True	),
	(	'section',	doSection,	None,		True	),
	(	'select',	doSelect,	doUnselect,	True	),
	(	'set',		doSet,		doUnset,	True	),
	(	'setattr',	doSetAttr,	doUnsetAttr,	False	),
	(	'setcom',	Unimplemented,	Unimplemented,	False	),
	(	'show',		doAtomSpecFunc,	doAtomSpecFunc,	True	),
	(	'sleep',	doSleep,	None,		False	),
	(	'speed',	Unimplemented,	Unimplemented,	False	),
	(	'start',	doStart,	Unimplemented,	False	),
	(	'stereo',	doStereo,	doUnstereo,	True	),
	(	'stereoimg',	Unimplemented,	Unimplemented,	False	),
	(	'stop',		doStop,		None,		False	),
	(	'surface',	doSurface,	doUnsurface,	True	),
	(	'surfnew',	doSurfaceNew,	doSurfaceDelete,True	),
	(	'surfdelete',	doSurfaceDelete,	None,	True	),
	(	'surfcat',	doSurfaceCategory,	None,	True	),
	(	'surfcolor',	doSurfaceColor,	None,		True	),
	(	'surfcolour',	doSurfaceColor,	None,		True	),
	(	'surfrepr',	doSurfaceRepr,	None,		True	),
	(	'surftransparency',	doSurfaceTransparency,	doUnsurfaceTransparency,	True	),
	(	'swapna',	doSwapRes,	None,		True	),
	(	'system',	doSystem,	None,		False	),
	(	'tcolor',	doTColor,	None,		True	),
	(	'tcolour',	doTColor,	None,		True	),
	(	'texture',	doTexture,	None,		False	),
	(	'thickness',	doThickness,	None,		True	),
	(	'transparency',	doTransparency,	doUntransparency,	True	),
	(	'turn',		doRoll,		None,		True	),
	(	'unset',	doUnset,	None,		True	),
	(	'update',	Unimplemented,	Unimplemented,	True	),
	(	'vdw',		doAtomSpecFunc,	doAtomSpecFunc,	True	),
	(	'vdwdefine',	doVdwDefine,	doAtomSpecFunc,	True	),
	(	'vdwdensity',	doVdwDensity,	None,		True	),
	(	'vdwopt',	NoVdwopt,	None,		True	),
	(	'version',	doArglessFunc,	None,		False	),
	(	'wait',		doWait,		None,		False	),
	(	'watch',	Unimplemented,	Unimplemented,	True	),
	(	'watchopt',	Unimplemented,	Unimplemented,	True	),
	(	'window',	doWindow,	None,		True	),
	(	'windoworigin',	doWindoworigin,	None,		False	),
	(	'windowsize',	doWindowsize,	doUnwindowsize,	False	),
	(	'write',	doWrite,	None,		False	),
]

helpInfo = {}
for cmd, f1, f2, w in cmdList:
	helpInfo[cmd] = True

def addCommand(command, cmdFunc, revFunc=None, help=None, changesDisplay=True):
	"""add a command to the interpreter

	   'command' is the command name; 'cmdFunc' is the function to
	   call when command is invoked, and 'revFunc' (if any) is the
	   function to call for ~command.  cmdFunc and revFunc are both
	   called with two string arguments:  the command name and the
	   argument string typed by the user.  'help' is None if no help
	   is provided, True if the command has help integrated with the
	   other built-in commands (i.e. is listed in the User's Guide
	   table of contents of commands), or is a string or tuple that
	   can be used as an argument to chimera.help's display() function
	   (an URL or package/URL tuple).  So that script execution knows
	   whether the display needs updating after a command, the
	   'changesDisplay' boolean should be set to True if the command
	   typically changes things in the main graphics window and False
	   otherwise.

	   cmdFunc and revFunc are typically simple wrapper functions that
	   in turn call the doExtensionFunc() command.  See the doExtensionFunc
	   doc string for details on usage.

	   One usually registers the new command from the extension's
	   ChimeraExtension.py file so that it is available to the
	   interpreter without the extension being imported.  Don't import
	   your extension directly from within your ChimeraExtension.py!
	   Doing so will slow Chimera startup.  Instead, you will import
	   your extension from _within_ your cmdFunc (and revFunc) functions.
	   See FindHBond's ChimeraExtension.py for an example of typical usage
	   [except for the 'help' arg, since FindHBond's help is integrated
	   with the built-in commands].

	   You will want to use the doExtensionFunc() command to handle
	   parsing the text and calling your command.  You may have to
	   provide a 'shim' function that works better (more "user friendly"
	   keywords, etc.) than your normal API for use with doExtensionFunc().
	   See the doExtensionFunc() doc string for details.
	"""
	global cmdList
	if [c for c in cmdList if c[0] == command]:
		cmdList = [c for c in cmdList if c[0] != command]       # replace command
	cmdList.append((command, cmdFunc, revFunc, changesDisplay))
	helpInfo[command] = help

def parseColorName(candidate, failReturnsNone=False):
	from chimera.colorTable import getColorByName
	if not candidate:
		if failReturnsNone:
			return None, candidate
		raise MidasError("No color name specified")
	if candidate[0] in ['"', "'"]:
		quoted, rem = findQuoted(candidate)
		return eval(quoted), rem
	words = candidate.strip().split()
	for end in range(len(words), 0, -1):
		colorName = " ".join(words[:end])
		try:
			getColorByName(colorName)
		except KeyError:
			continue
		return colorName, " ".join(words[end:])
	if failReturnsNone:
		return None, " ".join(words)
	return words[0], " ".join(words[1:])

def convertType(value, noneOkay=False):
	if len(value) > 1 and value[0] in ['"', "'"] and value[-1] == value[0]:
		return value[1:-1]
	evalVals = ["true", "false"]
	if noneOkay:
		evalVals.append("none")
	if value.lower() in evalVals:
		return eval(value.capitalize())
	try:
		return int(value)
	except ValueError:
		try:
			return float(value)
		except ValueError:
			"""
			try:
				return tuple([float(x.strip()) for x in value.split(",")])
			except ValueError:
				return value
			"""
			return value

def allModelSelect(activity, ids=None, id=None, subid=None):
	"""a 'select' where all models with the proper ids are activated

	   activity:  boolean controlled whether to activate or deactivate

	   ids: a string.  Either 'all' or comma-separated model ids/subids;
	   	if 'all' and activity is True, activate all models and
		remember previous activation states; if 'all' and activity
		is False, restore remembered activation states; otherwise
	   	parsed into individual id/subids and this routine called
		again for each one

	   id: model id to activate/deactivate.  If subid is None, then all'
	   	submodels.  if None (and ids is None), then all models.

	   subid:  used in tandem with id
	"""
	if ids:
		if ids == 'all':
			if activity:
				savedSelection.clear()
				savedSelection.add(filter(lambda m:
						m.openState.active,
						chimera.openModels.list()))
				allModelSelect(True)
			else:
				savedGraphs = savedSelection.graphs(asDict=True)
				for m in chimera.openModels.list():
					m.openState.active = m in savedGraphs
		else:
			try:
				idList = ids.replace(',', ' ').split()
				tuples = []
				for idString in idList:
					if '.' in idString:
						major, minor = \
							idString.split('.')
						id = int(major)
						if '-' in minor:
							start, end = [int(x)
								for x in
								minor.split('-')
								]
							for subid in range(
							start, end+1):
								tuples.append(
								(id, subid))
						else:
							tuples.append((id,
								int(minor)))
					else:
						if '-' in idString:
							start, end = [int(x)
								for x in
								idString.split(
									'-')]
							for id in range(start,
									end+1):
								tuples.append(
								(id, None))
						else:
							tuples.append((int(
								idString),None))

			except:
				raise MidasError, "Could not parse model list"
			for id, subid in tuples:
				allModelSelect(activity, id=id, subid=subid)
		return
	if id is None:
		models = chimera.openModels.list()
	elif subid is None:
		models = chimera.openModels.list(id=id)
	else:
		models = chimera.openModels.list(id=id, subid=subid)
	for model in models:
		model.openState.active = activity

def _prepKeywords(command, invalid, specInfo):
	import inspect
	allArgs, v1, v2, defaults = inspect.getargspec(command)
	if defaults is None:
		defaults = ()
	args = allArgs[:len(allArgs) - len(defaults)]
	import types
	if type(command) == types.MethodType:
		# pop off 'self'
		args = args[1:]
	kw = allArgs[len(allArgs) - len(defaults):]
	for typedKw, real, selAttr in specInfo:
		if real not in invalid:
			invalid.append(real)
	for inv in invalid:
		try:
			kw.remove(inv) # not valid from command line
		except ValueError:
			if inv not in args:
				raise
	testKw =  [ (k.lower(), k) for k in kw ]
	for typedKw, real, selAttr in specInfo:
		if real not in args:
			testKw.append((typedKw.lower(), real))
		else:
			args[args.index(real)] = typedKw
	return args, testKw

def _getRealKw(k, testKw):
	matches = [tkw for tkw in testKw if tkw[0].startswith(k.lower())]

	if len(matches) == 0:
		raise MidasError(
			"Keyword '%s' doesn't match any known keywords" % k)
	if len(matches) > 1:
		exactMatches = [m for m in matches if m[0] == k.lower()]
		if len(exactMatches) == 1:
			matches = exactMatches
		else:
			raise MidasError("Keyword '%s' matches multiple known"
					" keywords: %s" % (k,
					" ".join([m[0] for m in matches])))
	return matches[0]

def _parseTyped(guideline, typed, specInfo=[]):
	origTyped = typed
	if guideline is None:
		# expecting a keyword
		try:
			keyword, typed = typed.split(None, 1)
		except:
			raise MidasError, "No value provided for keyword '%s'" \
									% typed
		if not keyword.replace('_', '').isalnum():
			raise MidasError, "Non-alphanumeric, non-underscore " \
				" character in keyword '%s'" % keyword
		if keyword[0].isdigit():
			raise MidasError, "Leading digit in keyword '%s'" % (
									keyword)
		return keyword, typed
	# expecting an arg or a keyword value
	guideline = guideline.lower()
	for typedName, argName, method in specInfo:
		if guideline == argName.lower():
			guideline = typedName.lower()
			break
	if typed[0] in ["'", '"']:
		value, typed = findQuoted(typed)
		unquoted = eval(value)
	else:
		try:
			value, typed = typed.split(None, 1)
		except ValueError:
			value, typed = typed, ""
		unquoted = value
	if guideline.endswith("color"):
		from Midas import convertColor
		colorName, typed = parseColorName(origTyped)
		value = convertColor(colorName)
	elif guideline.endswith("file"):
		if value in ["browse", "browser"]:
			if chimera.nogui:
				raise MidasError, "Cannot use file browser"\
							" in nogui mode"
			import OpenSave
			if guideline.endswith("savefile"):
				browserClass = OpenSave.SaveModal
			else:
				browserClass = OpenSave.OpenModal
			d = browserClass(title="File for %s" %
						guideline.capitalize())
			pathsAndTypes = d.run(chimera.tkgui.app)
			d.destroy()
			if pathsAndTypes == None:
				raise MidasError, \
						"Command canceled from browser"
			elif not pathsAndTypes:
				raise MidasError, 'No file chosen in browser'
			value = pathsAndTypes[0][0]
		else:
			value = unquoted
	elif guideline.endswith("spec"):
		for typedKw, real, selAttr in specInfo:
			if guideline != typedKw.lower():
				continue
			try:
				sel = specifier.evalSpec(unquoted)
			except:
				if selAttr:
					mod = selAttr[:-1]
				else:
					mod = "atom"
				raise MidasError("Invalid %s specifier syntax:"
						" '%s'" % (mod, unquoted))
				raise MidasError, sys.exc_value
			if selAttr is None:
				value = sel
			else:
				value = getattr(sel, selAttr)()
			break

	return value, typed

def _parseAtomSpecs(argWords):
	from chimera.specifier import pickSynonyms
	if len(argWords) < 2 and not (
			len(argWords) == 1 and argWords[0] in pickSynonyms):
		raise MidasError, 'either "sel" or at least two space-separated atom specs are required'
	if len(argWords) == 1:
		spec1 = argWords[0]
		spec2 = ""
	else:
		halfSpecs, rem = divmod(len(argWords), 2)
		if rem != 0:
			raise MidasError, 'an even number of space-separated atom specs are required'
		if halfSpecs == 0:
			raise MidasError, 'missing atom spec'
		spec1 = " ".join(argWords[0:halfSpecs])
		spec2 = " ".join(argWords[halfSpecs:])
	return (spec1, spec2)

def findQuoted(text):
	try:
		endQuote = text[1:].index(text[0]) + 1
	except ValueError:
		raise MidasError, "Unmatched quote in %s" % text
	return text[:endQuote+1], text[endQuote+1:].strip()

def _splitQuoted(text, keepQuotes = False):
	fields = text.split()
	argWords = []
	while fields:
		argWords.append(_nextField(fields, keepQuotes))
	return argWords

def _nextField(fields, keepQuotes = False):
	f0 = fields[0]
	q = f0[0]
	if q == '"' or q == "'":
		for e in range(len(fields)):
			if fields[e].endswith(q):
				qf = ' '.join(fields[:e+1])
				f = qf if keepQuotes else qf[1:-1]
				del fields[:e+1]
				return f
	del fields[0]
	return f0

def _splitUnquoted(text, sep):
	if not sep in text:
		return [text]
	if not '"' in text and not "'" in text:
		return text.split(sep)

	fields = _splitQuoted(text, keepQuotes = True)
	def quoted(s):
		return len(s) >=2 and ((s[0] == '"' and s[-1] == '"') or
				       (s[0] == "'" and s[-1] == "'"))
	keep = sum(([quoted(f)]*f.count(sep) for f in fields), [])

	tsplit = []
	s = n = 0
	for k in keep:
		e = text.index(sep,n)
		if not k:
			tsplit.append(text[s:e])
			s = e+1
		n = e+1
	tsplit.append(text[s:])
	return tsplit
				
#
# session save/restore stuff
#

import SimpleSession
def _saveSession(trigger, x, sessionFile):
	restoring_code = \
"""
def restoreMidasText():
	from Midas import midas_text
	midas_text.aliases = %s
	midas_text.userSurfCategories = %s

try:
	restoreMidasText()
except:
	reportRestoreError('Error restoring Midas text state')

""" % (repr(aliases), repr(userSurfCategories))
	sessionFile.write(restoring_code)
chimera.triggers.addHandler(SimpleSession.SAVE_SESSION, _saveSession, None)

# okay, direct assignment to aliases/userSurfCategories was a bad idea,
# horrible kludge to fix it...
def beginRestore(*args):
	global _sesHide_aliases, _sesHide_surfCats
	global aliases, userSurfCategories
	_sesHide_aliases = aliases
	_sesHide_surfCats = userSurfCategories
	aliases = {}
	userSurfCategories = {}

def endRestore(*args):
	global _sesHide_aliases, _sesHide_surfCats
	global aliases, userSurfCategories
	try:
		_sesHide_surfCats.update(userSurfCategories)
	except NameError:
		# ancient session with no BEGIN_RESTORE trigger, give up...
		return
	userSurfCategories = _sesHide_surfCats
	aliases, _sesHide_aliases = _sesHide_aliases, aliases
	for item in _sesHide_aliases.items():
		doAlias("alias", " ".join(item), remember=False)
	del _sesHide_aliases, _sesHide_surfCats
chimera.triggers.addHandler(SimpleSession.BEGIN_RESTORE_SESSION, beginRestore, None)
chimera.triggers.addHandler(SimpleSession.END_RESTORE_SESSION, endRestore, None)


# get some additional commands registered...
from chimera import writeSel
del writeSel
