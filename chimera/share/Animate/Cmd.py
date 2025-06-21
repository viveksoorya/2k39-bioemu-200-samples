# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

'''Implements command management for cmds, properties, etc. Linked to
CmdButton in the GUI.'''

import chimera
import Tkinter

import cPickle as pickle
import hashlib

import Cmds
import Icons
from . import addChanged

DEBUG = 0

# only Cmd classes listed in the cmds dictionary at the end of this module
# by name are included in the Actions palette

def getImgSizePref():
	from Animate import Preferences
	pref = Preferences.get()
	return pref['scene_imgSize']

class Cmd(object):

	@property
	def imgSize(self):
		return getImgSizePref()

	'''Implements the command syntax and manages the parameters for a specific
	Chimera command. An instance of Cmd is managed by an Action.'''
	def __init__(self):
		self.paramDict = {}
		self._inKeyFrames = False

	def addedToKeyFrames(self):
		self._inKeyFrames = True

	def removedFromKeyFrames(self):
		self._inKeyFrames = False

	@property
	def dispname(self):
		return self.name

	def update(self):
		'update all parameters. called on triggers or prop dialog Apply()'
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyobj.warning(msg)

	def balloon_msg(self):
		'string for balloon help which shows current parameters'
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyobj.warning(msg)

#	def cmd_unset(self):
#		self.cmd_str = ''

class RollCmd(Cmd):
	prop_dialog = None
	name = 'Roll'
	cmd = 'turn'
	img_file = 'chimera48.png'
	# roll [ axis [ angle [ frames ]]] [ models model-spec ] [ coordinateSystem N ] [ center center ]

	def __init__(self):
		'use class vars for settings shared by all instances of this command'
		Cmd.__init__(self)
		self.loadParams()

	# Using default pickle method so no __getstate__

	def __setstate__(self, pickleDict):
		Cmd.__init__(self)
		try:
			self.action = pickleDict['action']
		except KeyError:
			pass
		try:
			paramDict = pickleDict['paramDict']
		except KeyError:
			self.loadParams()
		else:
			# Backwards compatibility with sessions saved before changing
			# roll parameters
			if paramDict.has_key('tilt'):
				self.paramDict = paramDict
			else:
				self.loadParams()
				try:
					angle = paramDict['precession'].value
				except KeyError:
					angle = 0
				if angle == 0:
					self.paramDict['precession'].value = 'false'
				else:
					self.paramDict['precession'].value = 'true'
					self.paramDict['tilt'].value = angle

	def callback(self):
		'''return the function to register for this command'''
		from Midas import _movement
		return _movement

	def cb_param(self):
		'''generate and return a param dict for this command'''
		from Midas import turnParam
		kw = {
			"axis": self.paramDict['axis'].value,
			"angle": self.paramDict['angle'].value,
			"frames": self.action.frames,
		}
		try:
			precession = self.paramDict['precession'].value
		except KeyError:
			precession = None
		if precession == 'true':
			kw["precessionTilt"] = self.paramDict['tilt'].value
		return turnParam(**kw)

	def loadParams(self):
		p = ChoiceParam({'name':'axis', 'required':True,
			'def_val':'y', 'choices'	: ['x', 'y', 'z'],
			'gui' :{
				'label': 'Axis of rotation',
				'widget':Tkinter.OptionMenu, }
				})
		self.paramDict[p.name] = p

		p = FloatParam({'name':'angle', 'required':True, 'def_val':3.0})
		self.paramDict[p.name] = p

		p = IntParam({'name':'degrees', 'required':False, 'def_val':360,
			'gui' : {
				'label': 'Degrees to rotate',
				'widget':Tkinter.Entry, }
				})
		self.paramDict[p.name] = p

		p = ChoiceParam({'name':'precession', 'required':True,
			'def_val':'false', 'choices'	: ['true', 'false'],
			'gui' :{
				'label': 'Precess around axis',
				'widget':Tkinter.OptionMenu, }
				})
		self.paramDict[p.name] = p

		p = IntParam({'name':'tilt', 'required':False, 'def_val':10,
			'gui' : {
				'label': 'Precession tilt',
				'widget':Tkinter.Entry, }
				})
		self.paramDict[p.name] = p
	paramOrder = [ "degrees", "axis", "precession", "tilt" ]

	def update(self):
		'''modify angle based on user's defined total degrees to Roll.'''
		try:
			self.paramDict['angle'].value = \
				float(self.paramDict['degrees'].value) / float(self.action.frames)
			if self._inKeyFrames:
				addChanged("timeline")
		except ZeroDivisionError: # can occur during Action delete
			pass

	def balloon_msg(self):
		msg = "\nRoll %0.1f degrees around the %s axis" % \
			(self.paramDict['degrees'].value, self.paramDict['axis'].value)
		return msg

#class MoveCmd(Cmd):
#	prop_dialog = None
#		# move  axis distance  frames
#	def __init__(self):
#		'use class vars for settings shared by all instances of this command'
#		MoveCmd.name		 = 'Move'
#		MoveCmd.cmd			 = 'move'
#		MoveCmd.img_file	 = 'chimera48.png'
#		MoveCmd.cmd_fmt		 = ' %s %f 1' # handles only axis, distance, frames=1
#		MoveCmd.param_order	 = ['axis', 'distance']
#		Cmd.__init__(self)
#		self.loadParams()
#
#	def loadParams(self):
#		p = ChoiceParam({'name':'axis', 'required':True,
#			'def_val':'y', 'choices'	: ['x', 'y', 'z'],
#			'gui' :{
#				'label': 'Axis of motion',
#				'widget':Tkinter.OptionMenu, }
#				})
#		self.paramDict[p.name] = p
#
#		p = FloatParam({'name':'distance', 'required':True, 'def_val':1.0})
#		self.paramDict[p.name] = p
#
#		p = FloatParam({'name':'totalDistance', 'required':False, 'def_val':1.0,
#			'gui' : {
#				'label': 'Distance to move',
#				'widget':Tkinter.Entry, }
#				})
#		self.paramDict[p.name] = p
#
#	def update(self):
#		'''modify distance based on the frames available.'''
#		self.paramDict['distance'].value = \
#			float(self.paramDict['totalDistance'].value) / float(self.action.frames)
#
#	def balloon_msg(self):
#		msg = "\nMove %d along the %s axis" % \
#			(self.paramDict['distance'].value, self.paramDict['axis'].value)
#		return msg


class RockCmd(Cmd):
	prop_dialog = None
		# rock  <axis> <angle> <frames> cycle <frames/cycle>
	def __init__(self):
		'use class vars for settings shared by all instances of this command'
		RockCmd.name		 = 'Rock'
		RockCmd.cmd			 = 'rock'
		RockCmd.img_file	 = 'chimera48.png'
#		RockCmd.cmd_fmt		 = ' %s %d %d cycle %d' # handles axis, angle, frames, frames/cycle
#		RockCmd.param_order	 = ['axis', angle 'frames', 'cycle']
		Cmd.__init__(self)
		self.loadParams()

	# Using default pickle method so no __getstate__

	def __setstate__(self, pickleDict):
		Cmd.__init__(self)
		try:
			self.action = pickleDict['action']
		except KeyError:
			pass
		self.loadParams()
		try:
			paramDict = pickleDict['paramDict']
		except KeyError:
			pass
		else:
			self.paramDict.update(paramDict)

	def callback(self):
		'''return the function to register for this command'''
		from Midas import _flight
		return _flight

	def cb_param(self):
		'''generate and return a param dict for this command'''
		from Midas import rockParam
		return rockParam(self.paramDict['axis'].value, self.paramDict['angle'].value,
			self.paramDict['cycle'].value, self.action.frames)

	def loadParams(self):
		p = ChoiceParam({'name':'axis', 'required':True,
			'def_val':'y', 'choices'	: ['x', 'y', 'z'],
			'gui' :{
				'label': 'Axis of rotation',
				'widget':Tkinter.OptionMenu, }
				})
		self.paramDict[p.name] = p

		p = IntParam({'name':'cycle', 'required':True, 'def_val':20})
		self.paramDict[p.name] = p

		p = FloatParam({'name':'angle', 'required':True, 'def_val':60,
			'gui': {
				'label': 'Angle to rock through',
				'widget':Tkinter.Entry, }
			})
		self.paramDict[p.name] = p

		p = FloatParam({'name':'reps', 'required':True, 'def_val':1,
			'gui' : {
				'label': 'Times to rock',
				'widget':Tkinter.Entry, }
				})
		self.paramDict[p.name] = p
	paramOrder = [ "angle", "axis", "reps" ]

	def update(self):
		'''modify cycle based on user's defined number of cycles.'''
		self.paramDict['cycle'].value = \
			int(self.action.frames / float((self.paramDict['reps'].value) * 2) + 2)
		if self._inKeyFrames:
			addChanged("timeline")

	def balloon_msg(self):
		msg = "\nRock %0.1f times though %0.1f degrees around the %s axis" % \
			(self.paramDict['reps'].value, self.paramDict['angle'].value,
			self.paramDict['axis'].value)
		return msg

class Param(object):
	'''Implements a superclass for Cmd parameter_xforms.'''
	def __init__(self, param_dict):
		for k, v in param_dict.items():
			setattr(self, k, v)
		self.value = self.def_val

		# abstract vars
		self.type = None
		self.typestr = "abstract"

	def validate(self, var):
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyobj.warning(msg)
		return False

	def convert_to_type(self, val):
		'convert to the proper type for this Param; set in subclass'
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyobj.warning(msg)
		return False

class ParamError(Exception):
	pass

class StrParam(Param):
	def __init__(self, param_dict):
		Param.__init__(self, param_dict)
		self.type = str
		self.typestr = "string"

	def validate(self, val):
		if not isinstance(val, str):
			return False
		# trigger the Cmd to validate further
		return True

	def convert_to_type(self, val):
		return str(val)

class IntParam(Param):
	def __init__(self, param_dict):
		Param.__init__(self, param_dict)
		self.type = int
		self.typestr = "integer"

	def validate(self, val):
		try:
			val = int(val)
		except ValueError:
			return False
		# trigger the Cmd to validate further
		return True

	def convert_to_type(self, val):
		try:
			return int(val)
		except ValueError:
			raise ParamError("bad type after validation (int) %s" % (val))

class FloatParam(Param):
	def __init__(self, param_dict):
		Param.__init__(self, param_dict)
		self.type = float
		self.typestr = "float"

	def validate(self, val):
		try:
			val = float(val)
		except ValueError:
			return False
		# trigger the Cmd to validate further
		return True

	def convert_to_type(self, val):
		try:
			return float(val)
		except ValueError:
			raise ParamError("bad type after validation (float) %s" % (val))

class ChoiceParam(Param):
	def __init__(self, param_dict):
		Param.__init__(self, param_dict)

	def validate(self, val):
		if not val in self.choices:
			return False
		# trigger the Cmd to validate further
		return True

	def convert_to_type(self, val):
		return val

cmds = {'Rock':RockCmd, 'Roll':RollCmd}
