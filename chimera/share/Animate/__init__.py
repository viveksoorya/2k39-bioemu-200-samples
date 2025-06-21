# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

"""
To access the Animation GUI instance while running chimera, use:
aniGUI = chimera.dialogs.find('Animation')
aniGUI.keyframesGUI
aniGUI.scenesGUI
"""

import chimera
#import Scenes
#import Keyframes
#import Transitions

# --- Main data models
# - scenes are primary, they contain visual state and transform properties
#   - scenes is a set of unique scene states, identified by name
# - keyframes are scenes in an animation timeline
#   - it's a list of scene names, linked into scene functionality
#   - keyframes are not unique, they may contain any kind of repetition pattern
#   - a keyframe has a separate transition instance from its associated scene
#scenes = Scenes.Scenes()
#keyframes = Keyframes.Keyframes()

## Create a set of transitions, with a couple of default styles.
#transitions = Transitions.Transitions()
##transitions.append(name, frames, mode, properties)
#transitions.append('scene', 1, 'linear', ['all'])
#transitions.append('keyframe', 20, 'linear', ['all'])
#transitions.append('custom_scene', 1, 'linear', ['all'])


# The GUI resets the 'statusFunc' to redirect animation status
# messages into the GUI status bar.  When the GUI is unmapped
# it will switch back to using chimera.replyobj.status.
statusFunc = chimera.replyobj.status
def status(*args, **kwargs):
	'A conduit for animation status messages.'
	global statusFunc
	statusFunc(*args, **kwargs)

# Code for tracking whether changes have been made to scenes,
# actions or timeline so that we know whether to warn user when
# CONFIRM_APP_QUIT and CONFIRM_CLOSE_SESSION triggers are fired.
_changed = set()
def clearChanged():
	_changed.clear()
def addChanged(c):
	_changed.add(c)
def _confirm(trigger, myData, msgList):
	if _changed:
		msgList.append("Animation %s changed since last session save."
				% " and ".join(_changed))
chimera.triggers.addHandler(chimera.CONFIRM_CLOSE_SESSION, _confirm, None)
chimera.triggers.addHandler(chimera.CONFIRM_APPQUIT, _confirm, None)

# Get some constants into the package scope
from Scenes import SCENE_TOOL_SAVE, SCENE_TOOL_RESTORE
import Session
