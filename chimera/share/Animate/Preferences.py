# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#

# preferences for animate recording
import os
from collections import OrderedDict

import chimera
from chimera import tkoptions
from chimera import preferences

import Animate

#
# --- Animate preferences ---
#

ANIMATE = 'Animation'


SCENE_NAME = 'Scene name prefix'
class SceneNameOption(tkoptions.StringOption):
	default = ''
	balloon = 'An optional name prefix, for auto-generation of scene names.'

SCENE_IMGSIZE = 'Scene thumbnail size'
class SceneImgSizeOption(tkoptions.IntOption):
	default = 48
	balloon = 'A scene thumbnail image size (x,y).'

TRANSITION_NAME = 'Transition name prefix'
class TransitionNameOption(tkoptions.StringOption):
	default = 'tr'
	balloon = 'A name prefix, for auto-generation of transition names.'

ORPHAN_DIALOG = 'Warn about model closure'
class OrphanDialogOption(tkoptions.BooleanOption):
	default = True
	balloon = 'Show confirmation dialog when model in scene closes.'
#
#EXPERIMENTAL = 'Experimental features'
#class ExperimentalOption(tkoptions.BooleanOption):
#	default = False
#	balloon = 'Enable experimental features for animation.'

ANIMATION_NOTICE = "Animation prototype"
class AnimationNotice(tkoptions.BooleanOption):
	default = True
	balloon = 'Notify of prototype status of Animation'

## skip this; we don't yet care about the timeline (1.6)
#def animationPrefsCB(option):
#	"Apply preference immediately by restarting animation if it exists."
#	from chimera.dialogs import find, display
#	dialog = find("Animation", create=0) # check for existence
#	if not dialog:
#		return
#	# close and restart Animation; no animation notice this time
#	# remove any scene and keyframe buttons, etc. before destroying.
#	if hasattr(dialog, 'kfGUI'):
#		dialog.kfGUI.destroy_keyframe_buttons()
#	if hasattr(dialog, 'scGUI'):
#		dialog.scGUI.destroy_scene_buttons()
#	dialog.destroy()
#	# dialog = find("Animate", create=1)
#	display("Animation")

def animationImgsizeCB(option):
	"modify the Scene.imgSize as requested"
#	Animate.Scene.Scene().imgSize = (option.value, option.value)
	Animate.Scene.Scene._imgSizeSet((option.value, option.value))
	Animate.Cmd.Cmd.imgSize = (option.value, option.value)
	# for button in lightboxscenes
		# button.sceneImageUpdate()
	# for button in lightboxkeyframes
		# button.sceneImageUpdate()
	from chimera.dialogs import find, display
	dialog = find("Animation", create=0) # check for existence
	if not dialog:
		return
	if hasattr(dialog, 'scGUI'):
		dialog.scGUI.lightbox_image_update()
	if hasattr(dialog, 'cmdGUI'):
		dialog.cmdGUI.lightbox_image_update()
	if hasattr(dialog, 'kfGUI'):
		dialog.kfGUI.lightbox_image_update()

animatePreferences = {
	SCENE_NAME:
		(SceneNameOption, SceneNameOption.default, None),
	SCENE_IMGSIZE:
		(SceneImgSizeOption, SceneImgSizeOption.default, animationImgsizeCB),
	TRANSITION_NAME:
		(TransitionNameOption, TransitionNameOption.default, None),
	ORPHAN_DIALOG:
		(OrphanDialogOption, OrphanDialogOption.default, None),
#	EXPERIMENTAL:
#		(ExperimentalOption, ExperimentalOption.default, None),
	ANIMATION_NOTICE:
		(AnimationNotice, AnimationNotice.default, None)
}

animatePreferencesOrder = [
	SCENE_NAME,
	SCENE_IMGSIZE,
	TRANSITION_NAME,
	ORPHAN_DIALOG,
#	 EXPERIMENTAL,
	# ANIMATION_NOTICE
]

#chimera.preferences.register(self, category, options, inherit=[], convert=[], **kw)
#    method of chimera.preferences.base.Preferences instance
#    Register preferences.
#    
#    "options" should be either (1) a dictionary whose key is
#    the name of the options and whose values are 3-tuples of
#    the form (uiOptionType, defaultValue, callback) or a 4-tuples
#    of the form (uiOptionType, defaultValue, callback, UIkeywords),
#    or a 5-tuple of the form (uiOptionType, defaultValue, callback,
#    UIkeywords, preferencesOptionKeywords), or (2) a list of those
#    dictionaries, optionally interspersed with preference Option
#    subclasses that will be used for the subsequent options.
#    
#    The uiOptionType should be a subclass of tkOptions.Option:
#    BooleanOption, StringOption, etc. The defaultValue should be
#    of the appropriate type. If callback is None, then (presumably)
#    a preferences change doesn't have any effect until the
#    application is restarted.  UIkeywords is a keyword dictionary
#    that is passed in to the GUI option when it is created.
#    preferencesOptionKeywords is a keyword dictionary that is
#    passed to the preferences option.
#

preferences.register(ANIMATE, animatePreferences)
preferences.setOrder(ANIMATE, animatePreferencesOrder)

def get():
	'Return the preference settings in a dictionary.'
	scene_name = preferences.get(ANIMATE, SCENE_NAME)
	scene_imgSize = preferences.get(ANIMATE, SCENE_IMGSIZE)
	transition_name = preferences.get(ANIMATE, TRANSITION_NAME)
	orphan_dialog = preferences.get(ANIMATE, ORPHAN_DIALOG)
#	experimental = preferences.get(ANIMATE, EXPERIMENTAL)
	animation_notice = preferences.get(ANIMATE, ANIMATION_NOTICE)
	pref = {
		'scene_name': scene_name,
		'scene_imgSize': (scene_imgSize, scene_imgSize),
		'transition_name': transition_name,
		'orphan_dialog': orphan_dialog,
#		'experimental': experimental,
		'animation_notice': animation_notice,
	}
	return pref

def set():
	'Display the preferences dialog.'
	pref = chimera.dialogs.display('preferences')
	pref.menu.invoke(index=ANIMATE)
