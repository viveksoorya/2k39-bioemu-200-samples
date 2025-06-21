# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

"""
Command handlers for animation package
- scenes contains visual state properties
- keyframes is a list of sequential scenes (allowing for repetition)
"""

import re
import Midas

# Using generic import for 'Animate' rather than specific 'scenes' and
# 'keyframes' imports because session support might replace the instances.
import Animate
import Scenes
import Keyframes
#from Scenes import scenes
#from Keyframes import keyframes

DEBUG = 0

if DEBUG:
	import sys
	REFS = sys.getrefcount(Scenes.scenes)
	ID = id(Scenes.scenes)
	print 'Commands.scenes:\t %d, %d' % (ID, REFS)
	REFS = sys.getrefcount(Keyframes.keyframes)
	ID = id(Keyframes.keyframes)
	print 'Commands.keyframes:\t %d, %d' % (ID, REFS)


#------------------------------------------------------------------------------
# Parse and dispatch animation commands
#
# See http://plato.cgl.ucsf.edu/trac/chimera/wiki/AnimationCommands
#

def processAnimateArg(fields):
	'Parse a scene-expression for the animate command'
	# A scene-expression comprises:
	# [frames[,transName]] sceneName
	# It can look like any of the following:
	# sceneName
	# frames sceneName
	# frames,transName sceneName
	#
	frames = None
	transName = None
	sceneName = None
	# fields is a list and we pop items off it, so the while loop that
	# calls this function will terminate.
	if DEBUG:
		print fields
	arg = fields.pop(0)
	argSplit = arg.split(',')
	if len(argSplit) == 2:
		# this must be: 'frames,transName sceneName'
		try:
			frames = int(argSplit[0])
		except:
			# Let's not allow anything like: ' ,transName'
			doAnimateUse()
		transName = argSplit[1]
		if transName == '':
			# Let's not allow anything like: 'frames, '
			doAnimateUse()
		# If we get here, then the NEXT field MUST be a sceneName
		sceneName = fields.pop(0)
	elif len(argSplit) == 1:
		# this could be one of:
		# sceneName
		# frames sceneName
		try:
			if DEBUG:
				print arg, fields
			# maybe it's 'frames sceneName'
			frames = int(arg)
			# If we get here, then the NEXT field MUST be a sceneName
			sceneName = fields.pop(0)
		except:
			# assume it's only 'sceneName'
			sceneName = arg
	else:
		doAnimateUse()
	return frames, transName, sceneName

def processAnimate(cmdName, args):
	'Parse and dispatch animate commands'
	if DEBUG:
		print 'processAnimate cmdName:', cmdName
		print 'processAnimate args:', args
	if not args:
		doAnimateUse()
		return
	fields = args.split()
	if cmdName == 'animate':
		# animate [master-frames[,master-trans]] scene1 \
		#	[[ frames1_2[,trans1_2]] scene2] \
		#	[[ frames2_3[,trans2_3]] scene3] \
		#	... \
		#	[[ framesN-1_N[,transN-1_N]] sceneN]
		#
		# Parse the first scene-expression (it's required);
		# processAnimateArg will pop items off fields
		masterFrames, masterTrans, scene1 = processAnimateArg(fields)
		if not masterFrames:
			masterFrames = 1
		if not masterTrans:
			masterTrans = 'snap'
		if not scene1:
			# The first scene is required
			doAnimateUse()
		# Shall we always snap to the first scene?
		frames = 1
		transName = 'snap' # TODO: double check this when it's implemented!!
		sceneName = scene1
		sceneParameters = [(frames, transName, sceneName)]
		# Parse the rest of the optional scene-expressions
		while fields:
			# processAnimateArg will pop items off fields
			frames, transName, sceneName = processAnimateArg(fields)
			if not frames:
				frames = masterFrames
			if not transName:
				transName = masterTrans
			sceneParameters.append((frames, transName, sceneName))
		doAnimate(sceneParameters)
		#except:
		#	doAnimateUse(cmdName)
	else:
		# Something is REALLY wrong with command parsing
		raise chimera.error('Unknown command: %s' % cmdname)

def processScene(cmdName, args):
	'Parse and dispatch scene commands'
	if DEBUG:
		print 'processScene cmdName:', cmdName
		print 'processScene args:', args
	if not args:
		doSceneUse(cmdName)
		return
	fields = args.split()
	if cmdName == 'scene':
		# Scene command syntax:
		# scene list
		# scene <name> save
		# scene <name> reset [N-frames]
		try:
			if fields[0] == 'list':
				doSceneList()
				return
			name = fields[0]
			action = fields[1]
			if action == 'save':
				doSceneSave(name)
				return
			if action == 'reset':
				frames = 1
				if len(fields) > 2:
					frames = int(fields[2])
				doSceneReset(name, frames)
				return
			# If we get this far, something is wrong
			doSceneUse(cmdName)
		except:
			doSceneUse(cmdName)
	elif cmdName == 'unscene':
		# ~scene <name>
		# ~scene all
		try:
			name = fields[0]
			if name == 'all':
				doSceneClear()
			else:
				doSceneDelete(name)
		except:
			doSceneUse(cmdName)
	else:
		# Something is REALLY wrong with command parsing
		raise chimera.error('Unknown command: %s' % cmdname)

def processTransitionArgs(fields, key, Nargs=1):
	'For transition key, returns a list of transition arguments or None'
	if key in fields:
		iArgs = fields.index(key) + 1
		return fields[iArgs:iArgs + Nargs]

def processTransition(cmdName, args):
	'Parse and dispatch transition commands'
	if DEBUG:
		print 'processTransition cmdName:', cmdName
		print 'processTransition args:', args
	if not args:
		doTransitionUse(cmdName)
		return
	fields = args.split()
	if cmdName == 'transition':
		# Transition command syntax:
		# transition ( list | <name> [color ...][visibility ...][style ...][position ...] )"
		# [color ...] := color ( linear | abrupt )
		# [visibility ...] := visibility abrupt
		# [style ...] := style abrupt
		# [position ...] := position ( linear | abrupt )
		#
		# A possible definition for color:
		# color ( linear [f1,f2] | sigmoid [f1,f2] | abrupt f )
		# where f are % fractions of the transition from the preceding scene
		# (0%) to the next scene (100%). A percentage is easier to type than
		# values in the 0-1 range.
		#
		#try:
		name = fields.pop(0)
		if name == 'list':
			doTransitionList()
			return
		kw = {
			# parameter: Nargs required
			'color': 1, 			# get 1 argument
			'position': 1, 	 	 	# get 1 argument
			'style': 1, 	 	 	# get 1 argument
			'visibility': 1, 	 	# get 1 argument
		}
		for key, Nargs in kw.items():
			# returns a list of transition args or None
			kw[key] = processTransitionArgs(fields, key, Nargs)
		doTransitionSave(name, **kw)
		#except:
		#	doTransitionUse(cmdName)
	elif cmdName == 'untransition':
		# ~transition ( <name> | all )
		#try:
		name = fields[0]
		if name == 'all':
			doTransitionClear()
		else:
			doTransitionDelete(name)
		#except:
		#	doTransitionUse(cmdName)
	else:
		# Something is REALLY wrong with command parsing
		raise chimera.error('Unknown command: %s' % cmdname)


#------------------------------------------------------------------------------
# Animate commands

def doAnimate(sceneParameters):
	print sceneParameters
	raise Midas.MidasError('animate: not implemented yet')

def doAnimateUse():
	# animate [master-frames[,master-trans]] scene1 \
	#	[[ frames1_2[,trans1_2]] scene2] \
	#	[[ frames2_3[,trans2_3]] scene3] \
	#	... \
	#	[[ framesN-1_N[,transN-1_N]] sceneN]
	msg = "animate [master-frames[,master-trans]] scene1 ... [[framesN[,transN]] sceneN]"
	raise Midas.MidasError(msg)


#------------------------------------------------------------------------------
# Scene commands

def doSceneClear():
	"Remove all scenes."
	Scenes.scenes.clear()

def doSceneDelete(name):
	"Remove a scene."
	Scenes.scenes.remove(name)

def doSceneList():
	"Display names of all the scenes to the status bar."
	Scenes.scenes.status()

def doSceneSave(name):
	"Save a scene."
	if Scenes.scenes.exists(name):
		Scenes.scenes.update(name)
	else:
		Scenes.scenes.append(name)

def doSceneReset(name, frames=0):
	"""
	Reset the display to a saved scene state.
	- 'name' refers to a saved scene (scene <name> save)
	- 'frames' is the number of transition frames to display (default is 0)
	"""
	Scenes.scenes.show(name, frames)

#def doScene2KeyFrame(cmdName, args):
#	"Add a scene into animation keyframes."
#	if args:
#		Keyframes.keyframes.append(args)
#	else:
#		Keyframes.keyframes.append()

def doSceneUse(cmdName):
	if cmdName == 'scene':
		msg = "scene list | scene <name> save | scene <name> reset [N-frames]"
	elif cmdName == 'unscene':
		msg = '~scene <name> | ~scene all'
	else:
		msg = 'unknown command'
	raise Midas.MidasError(msg)

def doSceneWrite(name):
	"Write a scene to the file system"
	Scenes.scenes.write(name)


#------------------------------------------------------------------------------
# Keyframe commands

def doKeyFrameAdd(cmdName, args):
	"Add a keyframe."
	arg_words = tuple(args.split())
	if len(arg_words) == 0:
		Keyframes.keyframes.append()
	elif len(arg_words) == 1:
		name = arg_words[0]
		Keyframes.keyframes.append(name=name)
	elif len(arg_words) == 2:
		name = arg_words[0]
		try:
			index = int(arg_words[1])
		except ValueError:
			error = 'Args error: kfadd [name] [index]\n'
			error += 'name as string, index as int'
			Midas.MidasError(error)
		# Note call to 'insert' method when an index is given
		Keyframes.keyframes.insert(name=name, index=index)
	else:
		error = 'Args error: kfadd [name] [index]'
		Midas.MidasError(error)

def doKeyFrameClear(cmdName, args):
	"Remove all keyframes."
	Keyframes.keyframes.clear()

def doKeyFrameDel(cmdName, args):
	"Remove a keyframe."
	arg_words = tuple(args.split())
	if len(arg_words) == 0:
		Keyframes.keyframes.remove()
	elif len(arg_words) == 1:
		name = arg_words[0]
		Keyframes.keyframes.remove(name=name)
	elif len(arg_words) == 2:
		name = arg_words[0]
		if re.match('.*None.*', arg_words[1]):
			index = None
		else:
			try:
				index = int(arg_words[1])
			except ValueError:
				error = 'Args error: kfdel [name] [index]'
				Midas.MidasError(error)
		Keyframes.keyframes.remove(name=name, index=index)

def doKeyFrameMove(cmdName, args):
	'''
	Move a keyframe.
	kfmove indexFrom [indexTo]
	The index values are integers.
	With no 'indexTo' value, the keyframe at
	'indexFrom' is moved to the end of the list.
	'''
	arg_words = args.split()
	try:
		if len(arg_words) == 2:
			indexFrom = int(arg_words[0])
			indexTo = int(arg_words[1])
			Keyframes.keyframes.move(indexFrom, indexTo)
		elif len(arg_words) == 1:
			indexFrom = int(arg_words[0])
			Keyframes.keyframes.move(indexFrom)
		else:
			raise ValueError
	except ValueError:
		error = 'Args error: kfmove indexFrom [indexTo]\n'
		error += 'Index values must be integers'
		Midas.MidasError(error)

def doKeyFrameMovie(cmdName, args):
	"""
	Animate keyframes.
	- 'args' is a single movie command.
	- no 'args' defaults to the 'play' command.
	- available commands include:
		- first: display first keyframe
		- last: display last keyframe
		- next: display next keyframe
		- previous: display previous keyframe
		- play: start animation
		- stop: stop animation
		- pause: toggle pause status on/off
				pause can be enabled only during play
		- loop: toggle loop status on/off
				when looping, the 'previous', 'next' and 'play' commands will
				wrap around the beginning or end of the keyframe sequence
		- record: toggle record status on/off
				recording starts with 'play', finishes with 'stop'
	"""
	arg_words = args.split()
	if len(arg_words) > 1:
		error = 'Args error: kfshow [name] [index] [frames] [mode]'
		raise Midas.MidasError(error)
	else:
		command = arg_words[0]
		Keyframes.keyframes.movie(command, 'MIDAS')

#def doKeyFrameShow(args):
#	"""
#	Show the state of a single keyframe.
#	- 'args' contains valid names of keyframe states
#	- an empty 'args' will display the 'default' keyframe (if it exists)
#	- if 'args' names a valid keyframe state, it may also end with an int to
#	  specify how many transition steps to interpolate between the current
#	  state and the named keyframe state.
#	- 'args' may also end with a transition 'mode' (linear is the default)
#	"""
#	Midas.midas_text.doExtensionFunc(Keyframes.keyframes.show, args)

'''
Hi Darren,

	If you want to restore just some attributes of a scene with the scene restore
	command you might have an optional command argument to specify which
	properties to restore.  The command syntax could use just one argument which
	takes a string with single characters indicating what to restore.  The mcopy
	command that copies molecule attributes is an example of this command syntax.

		Tom

http://www.cgl.ucsf.edu/chimera/current/docs/UsersGuide/midas/mcopy.html

mcopy source target [ settings [c][s][v][l][x][p] | a ]

Characters after the settings keyword (default csv) control which attributes are
copied:

		c - colors (model-level and atom-level, see coloring hierarchy)
		s - atom/bond and ribbon display styles
		v - visibility (model-level, residue-level ribbon, and atom-level display,
				see display hierarchy)
		l - atom and residue labels
		x - atomic coordinates, untransformed
		p - placement (model transformation)
		a - all of the above
'''

def doKeyFrameShow(cmdName, args):
	"""
	Show the state of a single keyframe.
	- 'args': kf_name, kf_index, frames, mode
	- no 'args' will display the 'last' keyframe (if it exists).
	- 'kf_name': a valid name of a keyframe state (pointer to a scene).
	- 'kf_index': a valid index into the keyframes list;
					only used when kf_name is not given or not a valid scene;
					there may be multiple instances of a keyframe in the key
					frame list, but they all point to a single scene, so the
					specific kf_index is not necessary.
	- 'frames': an integer to specify how many transition steps to
				interpolate between the display state and the keyframe state.
	- 'mode': a string to specify the transition mode;
				'linear' is the only option at present;
				some transitions are discrete (regardless of this setting);
				additional options could allow subsets of transition parameters
				(such as motion, color, or model style), or variations in
				the interpolation methods available.
	"""
	# TODO: What are the transition 'mode' arguments?
	arg_words = args.split()
	if len(arg_words) == 0:
		Keyframes.keyframes.show()
	elif len(arg_words) == 1:
		name = arg_words[0]
		Keyframes.keyframes.show(name=name)
	else:
		# Extract the name and index parameters
		name = arg_words[0]
		if re.match('.*None.*', arg_words[1]):
			index = None
		else:
			try:
				index = int(arg_words[1])
			except ValueError:
				error = 'Args error: kfshow [name] [index] [frames] [mode]'
				Midas.MidasError(error)
		# Extract the frames parameter
		if len(arg_words) >= 3:
			if re.match('.*None.*', arg_words[2]):
				frames = None
			else:
				try:
					frames = int(arg_words[2])
				except ValueError:
					error = 'Args error: kfshow [name] [index] [frames] [mode]'
					Midas.MidasError(error)
		if len(arg_words) == 2:
			Keyframes.keyframes.show(name=name, index=index)
		elif len(arg_words) == 3:
			Keyframes.keyframes.show(name=name, index=index, frames=frames)
		elif len(arg_words) == 4:
			mode = arg_words[3]
			Keyframes.keyframes.show(name=name, index=index, frames=frames, mode=mode)
		else:
			error = 'Args error: kfshow [name] [index] [frames] [mode]'
			raise Midas.MidasError(error)

#def doKeyFrameSave(args):
#	"Add a keyframe (modifies global 'keyframes' dict)."
#	doExtensionFunc(Keyframes.keyframes.append, args)

def doKeyFrameSave(cmdName, args):
	"Save a keyframe to the file system."
	if args:
		Keyframes.keyframes.save(args)
	else:
		Keyframes.keyframes.save()

def doKeyFrameStatus(cmdName, args):
	"Display names of all the keyframes to the status bar."
	Keyframes.keyframes.status()
#	if args:
#		# What could these args be?
#		# If there are any, parse them into kw args.
#		Keyframes.keyframes.kf_list(args)
#	else:
#		Keyframes.keyframes.kf_list()

def doKeyFrameTransition(cmdName, args):
	"""
	Set the transition parameters for a keyframe.
	- 'args': kf_name, kf_index, frames, mode, commands:"Midas commands"
	- 'kf_name': a valid name of a keyframe state (pointer to a scene).
	- 'kf_index': a valid index into the keyframes list;
					only used when kf_name is not given or not a valid scene;
					there may be multiple instances of a keyframe in the key
					frame list, but they all point to a single scene, so the
					specific kf_index is not necessary.
	- 'frames': an integer to specify how many transition steps to
				interpolate between the display state and the keyframe state.
	- 'mode': a string to specify the transition mode;
				'linear' is the only option at present;
				some transitions are discrete (regardless of this setting);
				additional options could allow subsets of transition parameters
				(such as motion, color, or model style), or variations in
				the interpolation methods available.
	- 'commands': a series of midas commands, enclosed in double quotes
	"""
	# TODO: What are the transition 'mode' arguments?
	arg_words = args.split()
	if len(arg_words) == 0:
		return
	elif len(arg_words) == 1:
		name = arg_words[0]
	else:
		# Extract the name and index parameters
		name = arg_words[0]
		if re.match('.*None.*', arg_words[1]):
			index = None
		else:
			try:
				index = int(arg_words[1])
			except ValueError:
				error = 'Args error: kfshow [name] [index] [frames] [mode]'
				Midas.MidasError(error)
		# Extract the frames parameter
		if len(arg_words) >= 3:
			if re.match('.*None.*', arg_words[2]):
				frames = None
			else:
				try:
					frames = int(arg_words[2])
				except ValueError:
					error = 'Args error: kfshow [name] [index] [frames] [mode]'
					Midas.MidasError(error)
		if len(arg_words) == 2:
			Keyframes.keyframes.show(name=name, index=index)
		elif len(arg_words) == 3:
			Keyframes.keyframes.show(name=name, index=index, frames=frames)
		elif len(arg_words) == 4:
			mode = arg_words[3]
			Keyframes.keyframes.show(name=name, index=index, frames=frames, mode=mode)
		else:
			error = 'Args error: kfshow [name] [index] [frames] [mode]'
			raise Midas.MidasError(error)


#------------------------------------------------------------------------------
# Transition commands

# TODO: Implement a new transition class to define transition options, then
#		call the relevant methods on that class.  The transition class will
# 		be called by a transitions class that will manage a set of transition
#		instances (identified by transition names).  The transitions class
#		will be similar to the scenes class.

def doTransitionClear():
	raise Midas.MidasError('transition clear: not implemented yet')

def doTransitionDelete(name):
	raise Midas.MidasError('transition delete: not implemented yet')

def doTransitionList():
	raise Midas.MidasError('transition list: not implemented yet')

def doTransitionSave(name, **kwargs):
	print 'name: ', name
	print 'kwargs: ', kwargs
	# Examples:
	# kwargs:  {'color': None, 'position': None, 'style': None, 'visibility': None}
	# kwargs:  {'color': None, 'position': None, 'style': ['abrupt'], 'visibility': None}
	raise Midas.MidasError('transition save: not implemented yet')

def doTransitionUse(cmdName):
	if cmdName == 'transition':
		msg = "transition ( list | <name> [color ...][visibility ...][style ...][position ...] )"
	elif cmdName == 'untransition':
		msg = '~transition ( <name> | all )'
	else:
		msg = 'unknown command'
	raise Midas.MidasError(msg)
