# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- vi:fenc=utf-8:et:sw=4:sts=4

Programming Architecture for Animate Extension

General Architecture

 * MVC design
    - MVC model elements are SceneState.py (chimera models)
    - MVC view is AnimationGUI.py (ScenesCanvas.py and KeyFramesCanvas.py)
    - MVC controller is Scenes.py and KeyFramesList.py

Scenes

 * Users modify the Chimera display and save it as a 'scene'
 * All scene implementations are in Scene*.py
    - Scenes.py is an ordered dictionary of 'scene_name':scene_state
      (so, the scene names are unique).  On creating a new scene, Scenes.py
      instantiates a new instance of SceneState.py.
    - SceneState.py saves all the state properties for a scene (model in MVC).
      SceneState.py imports SceneTransitions.py to instantiate a transition
      class for each scene.  It may be possible, although not yet required, to
      instantiate more than one transition class for any scene (or keyframe).
    - SceneTransitions.py restores the properties of a saved scene, with
      intelligent transitions from the 'current' Chimera display to the
      saved state.
 * User interfaces to Scenes.py
    - Midas commands
        > See ChimeraExtension.py, which calls functions of AmationCommands.py
    - GUI (ScenesCanvas.py)
        > AnimationGUI.py imports ScenesCanvas.py (and KeyFramesCanvas.py)
    - triggers coordinate changes between the state
      model (Scenes.py) and the GUI (ScenesCanvas.py)
    - triggers coordinate changes between the state models (SceneState.py),
      the controller (Scenes.py), and GUI (ScenesCanvas.py)
    - See all methods listed with: $ grep "def " Scene*.py 

Keyframes

 * Keyframes are the elements of an animation sequence
    - the order of keyframes is important
    - animation depends on:
        > the duration of a keyframe transition
        > the keyframe transition parameters (transition style)
 * Users can link a keyframe to any scene
    - a keyframe is a reference to a scene
        > all the state and transition properties are in the scene object
        > for any scene destroyed, all keyframes referring to it are destroyed
        > without model-data persistence for scenes, users are notified
          of consequences to closing chimera models
    - more than one keyframe can link to the same scene
        > allows repetition of scenes in the animation sequence
        > allows variations in transition parameters for each scene
    - scene transitions do not depend on the keyframe sequence, because the
      design of a transition is based on auto-detection of any 'current' display
      state prior to the restoration of a saved state
        > a set of transition parameters can be set for a keyframe, to be
          used as arguments to the SceneTransitions.py methods
 * All keyframe implementations are in KeyFrame*.py
    - KeyFramesList.py is an ordered list of scenes
 * User interfaces to KeyFramesList.py:
    - Midas commands
        > See ChimeraExtension.py, which calls functions of AmationCommands.py
    - GUI (KeyFramesCanvas.py)
        > AnimationGUI.py imports KeyFramesCanvas.py
    - triggers coordinate changes between the state models (SceneState.py),
      the controller (KeyFramesList.py), and GUI (KeyFramesCanvas.py)
    - See all methods listed with: $ grep "def " Key*.py 


GUI Components

Most of the GUI widgets are Pmw objects.  To facilitate use, most widgets are
associated with balloon help.  Some GUI buttons raise additional dialogs.

 * AnimationGUI.py
    - imports ScenesCanvas.py and KeyFramesCanvas.py
    - registers the GUI with chimera.dialogs

 * ScenesCanvas.py
    - MVC design
        > MVC model elements are SceneState.py
        > MVC controller is Scenes.py
        > MVC view is ScenesCanvas.py
    - Access to scenes and keyframes via __init__:
        self.scenes = Animate.AnimationCommands.scenes
        self.keyframes = Animate.AnimationCommands.keyframes
    - A scrollable canvas for scene states
    - Canvas contains 'scene buttons'
        > buttons are populated from self.scenes
        > each button has a title (name) and a thumbnail
        > left-click to restore the chimera display
        > right-click menu enables functionality, such as update, delete, etc.
        > callbacks can modify self.scenes and self.keyframes
    - Utility buttons at the top of the canvas
        > buttons to add or remove scenes
    - Incoming triggers basically update the canvas
    - Outgoing triggers can change model data and chimera display

 * KeyFramesCanvas.py
    - MVC design
        > MVC model elements are SceneState.py
        > MVC controller is KeyFramesList.py
        > MVC view is KeyFramesCanvas.py
    - Access to scenes and keyframes via __init__:
        self.scenes = Animate.AnimationCommands.scenes
        self.keyframes = Animate.AnimationCommands.keyframes
    - A scrollable canvas for 'keyframe buttons'
        > buttons are keyframe entries that refer to scenes
        > each button has a title (name), a keyframe index, and a thumbnail
        > left-click to restore the chimera display
        > right-click menu enables functionality, such as delete, move, etc.
        > callbacks can modify self.keyframes and self.scenes
    - Utility buttons at the top of the canvas
        > buttons to add, remove, and reorder keyframes
        > buttons to control animation playback of a keyframe sequence
    - Incoming triggers basically update the canvas
    - Outgoing triggers can change model data and chimera display

Triggers

 * Most classes have a triggerIn() and a triggerOut() method
    - triggerIn() is registered to receive triggers (usually in __init__)
    - triggerOut() is called to activate triggers

 * A list of triggers defined (Feb, 2011):
    - KeyFramesList.py: ['append', 'insert', 'move', 'remove', 'display']
    - Scenes.py: ['append', 'display', 'remove', 'update']
    - SceneState.py: ['scene_invalid', 'scene_transition', 'scene_displayed']
    - SceneTransitions.py: ['transition_started', 'transition_complete']
    - Update this list with: $ grep -n -E "self\.triggers.?=" *.py

 * Trigger handlers 
    - Find registered handlers with: $ grep -n -C 1 "addHandler(" *.py

