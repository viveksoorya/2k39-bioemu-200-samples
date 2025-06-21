# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#

# To save animation sessions:
#	1. Save scene names, description and states, including:
#		model ID, model type, model state, state handlers
#	2. Save keyframe name sequence (link to scene states)
#	3. Save keyframe transitions
# Other animation components can be regenerated from these essentials.

import base64
import cPickle as pickle

import chimera
import SimpleSession
import Animate
import Scenes
import Keyframes
import Transitions

def AnimateInit():
	Keyframes.keyframes.clear()
	Scenes.scenes.clear()
	Transitions.transitions.clear()
	Transitions.transitions.append('scene', 1, 'linear', ['all'])
	Transitions.transitions.append('custom_scene', 1, 'linear', ['all'])
	Transitions.transitions.append('keyframe', 20, 'linear', ['all'])

#
# chimera.CLOSE_SESSION
#
def sessionClose(trigger, a1, a2):
	AnimateInit()
	from . import clearChanged
	clearChanged()
chimera.triggers.addHandler(chimera.CLOSE_SESSION, sessionClose, None)


#
# Track whether session restore is in progress
#
def sessionRestoring(trigger, funcData, trigData):
	# Create a tracking attribute that can be checked by other methods
	# to ensure that Chimera is in the process of restoring a session.
	Animate.sessionRestoring = funcData
	if Animate.sessionRestoring:
		# This is done to avoid problems of linking to Chimera model data.
		# When a session is restored, the current model data may be closed
		# and replaced with models from the saved session.  That process
		# can invalidate the animation objects.
		AnimateInit()
	else:
		# TODO: enable this after the 2011 site visit!
		return
		# A session has been restored.  To enable modification of the
		# session state and a quick return to the session state, without
		# restoring it again, we can save a new scene called 'session'.
		# This is one example of a possible undo/redo feature.
		try:
			Scenes.scenes.append('session')
		except:
			# TODO: try to handle some exceptions
			pass

chimera.triggers.addHandler(chimera.BEGIN_RESTORE_SESSION,
	sessionRestoring, True)
chimera.triggers.addHandler(chimera.END_RESTORE_SESSION,
	sessionRestoring, False)

#
# SimpleSession.RESTORE_SESSION
#

def restoreTransitions(trBase64Pickle):
	'Restore animation session'
	# It's essential that transitions are restored first (scenes & keyframes
	# refer to them).  Sessions save only essential details and each scene 
	# and keyframe is recreated by methods in Scenes.scenes and 
	# Keyframes.keyframes
	#
	# It's important to leave the pickle.loads until the last minute.
	trSession = pickle.loads(base64.b64decode(trBase64Pickle))
	for trName in trSession.names():
		tr = trSession.transitionGet(trName)
		#Transitions.transitions.append(trName, tr.frames, tr.mode, tr.properties)
		Transitions.transitions.transitionDict[trName] = tr
		# Replace the transition with the saved transition

def restoreScenes(scBase64Pickle):
	'Restore animation session'
	# It's essential that scenes are restored first (keyframes reference them).
	# Sessions save only essential details and each scene and keyframe 
	# is recreated by methods in Scenes.scenes and Keyframes.keyframes
	#
	# It's important to leave the pickle.loads until the last minute.
	scSession = pickle.loads(base64.b64decode(scBase64Pickle))
	#
	# If all the __getstate__ and __setstate__ methods in the Animate
	# classes all do their work correctly, it should be possible to
	# substitute Scenes.scenes with the unpickled scenes.
	# However, cannot do this yet.
	#Scenes.scenes.clear()
	#Scenes.scenes = scSession
	## Update the GUI etc.
	#for name in sorted(Scenes.scenes.names()):
	#	sc = Scenes.scenes.getScene_by_name(name)
	#	Scenes.scenes.triggerOut('scene_append', sc)
	#
	# The GUI code requires refs to Scenes.scenes!  Most of it contains
	# or should contain property getters that return the current instance 
	# of Scenes.scenes.
	#
	scns = Scenes.scenes
	scns.restoreMaps(scSession)
	from chimera import dialogs
	from Ilabel.gui import IlabelDialog
	d = dialogs.find(IlabelDialog.name)
	from Ilabel import LabelsModel as getLabelsModel
	from Ilabel.Arrows import ArrowsModel as getArrowsModel
	labelsInfo = None
	arrowsInfo = None
	for name in sorted(scSession.names()):
		# Place the restored scene into scenes
		scns.restoreScene(scSession, name)
		sc = scns.getScene_by_name(name)
		if sc.saveStateVer == 1:
			s = sc.state.state
			if s.has_key("labels") and s["labels"]:
				hasLabels = True
				if labelsInfo is None:
					labelsInfo = getLabelsModel().sessionInfo()
			else:
				hasLabels = False
			if s.has_key("arrows") and s["arrows"]:
				hasArrows = True
				if arrowsInfo is None:
					arrowsInfo = getArrowsModel().getRestoreInfo()
			else:
				hasArrows = False
			if hasLabels or hasArrows:
				sc.state.updateLabels(sc)
				#if hasLabels:
				#	del s["labels"]
				#if hasArrows:
				#	del s["arrows"]
				if d is not None:
					d._saveScene(None, None, sc)
			sc.saveStateVer = 2
	if labelsInfo is not None:
		getLabelsModel().destroy()
		getLabelsModel().restoreSession(labelsInfo)
	if arrowsInfo is not None:
		getArrowsModel().restore(arrowsInfo)
	# Cleanup the scSession trigger handlers
	scSession.modelHandlers('delete')

def restoreKeyframes(kfBase64Pickle):
	'Restore animation session'
	# It's essential that scenes are restored first (keyframes refer them).
	# Sessions save only essential details and each scene and keyframe 
	# is recreated by methods in Scenes.scenes and Keyframes.keyframes
	#
	# It's important to leave the pickle.loads until the last minute.
	# this call restores to the global instance of keyframes
	kfSession = pickle.loads(base64.b64decode(kfBase64Pickle))
	from . import clearChanged
	clearChanged()


#
# SimpleSession.SAVE_SESSION
#

# Global string - python code to restore animation session
restoring_code = \
"""
trPickle = %s
scPickle = %s
kfPickle = %s
def restoreAnimation():
	'A method to unpickle and restore animation objects'
	# Scenes must be unpickled after restoring transitions, because each
	# scene links to a 'scene' transition. Likewise, keyframes must be 
	# unpickled after restoring scenes, because each keyframe links to a scene.
	# The unpickle process is left to the restore* functions, it's 
	# important that it doesn't happen prior to calling those functions.
	import SimpleSession
	from Animate.Session import restoreTransitions
	from Animate.Session import restoreScenes
	from Animate.Session import restoreKeyframes
	SimpleSession.registerAfterModelsCB(restoreTransitions, trPickle)
	SimpleSession.registerAfterModelsCB(restoreScenes, scPickle)
	SimpleSession.registerAfterModelsCB(restoreKeyframes, kfPickle)
try:
	restoreAnimation()
except:
	reportRestoreError('Error in Animate.Session')
"""

# This function is adapted from SimpleSession/save.py:
def pickled(obj):
	objEncPickle = base64.b64encode(pickle.dumps(obj, protocol=2))
	# It's important to leave the pickle.loads until the last minute.
	#return "cPickle.loads(base64.b64decode(%s))" % repr(data)
	return repr(objEncPickle)

def sessionSave(trigger, x, file):
	'Save animation session'
	from Transitions import transitions
	from Scenes import scenes
	from Keyframes import keyframes
	# The 'restoring_code' string defines a function that will restore
	# Animation during session restore processing.  It contains two
	# string place holders (%s), the first one is for scenes and the
	# second one is for keyframes.
	trPickle = pickled(transitions)
	scPickle = pickled(scenes)
	kfPickle = pickled(keyframes)
	file.write(restoring_code % (trPickle, scPickle, kfPickle))
	from . import clearChanged
	clearChanged()

chimera.triggers.addHandler(SimpleSession.SAVE_SESSION, sessionSave, None)
