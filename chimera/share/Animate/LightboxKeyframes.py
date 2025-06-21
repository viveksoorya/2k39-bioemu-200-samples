# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import Pmw
import Tkinter
from PIL.ImageTk import PhotoImage

import chimera
from Midas.MidasEditor import MidasEditor

# access the 'scenes' dict and 'keyframes' list
import Animate
import Icons
from Lightbox import Lightbox
from LightboxButton import KeyframeButton
from Action import Action
from LightboxButton import ActionButton

from Keyframes import MOVIE_PLAY, MOVIE_PAUSE, MOVIE_STOP, MOVIE_NEXT_PREV

# TODO: create transition buttons

DEBUG = 0

class LightboxKeyframes(Lightbox):
	'A GUI for keyframes'

	# action settings
	NO_ACTION = 0
	MULTI_SELECT = 1
	MULTI_MOVE = 2
	MOVE = 3 # single kf
	RIPPLE_MOVE = 4 # shift-drag action

	# scaling/zoom
	PixelsPerFrame = 1

	def __init__(self, parent, status=None, showCB=None):
		# Populate the parent with a group container,
		# a lightbox display, and get handles to scenes and keyframes
		Lightbox.__init__(self, parent, "Timeline")
		#
		# Reconfigure the lightbox layout
		# Set the lightbox to one row of keyframe buttons
		self.lightbox.configure(
			hscrollmode='static',
			vscrollmode='none')

		# support searching tags for keytitles; only compile once
		# primary assumption: ':' only appears in the keytitle tag and it's first
		import re
		self.re = re.compile('\S+:\S+')

		# Enable Tkdnd functions
		#
		# Try to use the frame, so we can use the grid_location method
		# on it to place the tkdnd object into the grid.  For now, the clipper
		# is the most visible 'canvas' for dropping things into.
		#
		self.dnd_widget = self.lightbox.component('clipper')
		self.dnd_widget.dnd_accept = self.dnd_accept
		self.dnd_widget.dnd_commit = self.dnd_commit
		self.dnd_widget.dnd_enter = self.dnd_enter
		self.dnd_widget.dnd_leave = self.dnd_leave
		self.dnd_widget.dnd_motion = self.dnd_motion


		# Set the canvas height to contain one row of keyframe buttons
		from Animate import Preferences
		pref = Preferences.get()
		w, h = pref['scene_imgSize']
		clipper = self.lightbox.component('clipper')
		clipper.configure(height=h * 3)
#		clipper.configure(height=h * 4)

		# keyboard commands for timeline
		Tkinter.Widget.bind(self.canvas, "<Right>", self.keyframes.movie_plusOne)

		# Create popup menu for keyframes
		self.kfMenu = Tkinter.Menu(self.canvas, tearoff=False)

		# Animation movie commands; this list has an
		# order that defines the layout of GUI buttons
		# (see 'create_utilities' and 'create_movie_button' methods).
		self.movie_commands = self.keyframes.movie_commands
		# Create boolean variables to track movie play-back status;
		# This should mirror the status in the keyframes
		self.movie_status = {}
		# play is a regular button; there is no stop button
		for cmd in self.movie_commands:
			if cmd in ['play', 'stop']:
				continue
			self.movie_status[cmd] = Tkinter.BooleanVar()
			self.movie_status[cmd].set(False)
		self.movie_status['play'] = MOVIE_STOP
		#
		# Add utility dialogs (activated by utility buttons below).
		self.dialog_create(self.group_interior)
		self.dialog_notebook(self.group_interior, "Key Frames")
		# Populate the parent with some utility buttons
		self.command_button = {}
		self.create_utilities(self.group_interior)

		# hard coded offset for now
		self.tl_start = 20
		self.time_line()
		# move/insert helpers
		self.action = self.NO_ACTION
		self.select_box = None
		self.insert_frame = 0
		self._left_selected_kfb = None
		self._right_selected_kfb = None

		# play helpers
		self._frame_line = self.canvas.create_line(self.tl_start, 0,
			self.tl_start, h * 3, state=Tkinter.HIDDEN, tags=('frame_line'),
			fill='red')
		self.playType = None # support how to resume and continue

		self.triggerInit()
		self.keyframePopup = [
			('Properties', self.kf_transitionCB),
			('', None),
			('Delete', self.kf_deleteCB)
			]
		self.actionPopup = [
			('Properties', self.ac_propertiesCB),
			('', None),
			('Delete', self.ac_deleteCB)
			]

		self.from_xy = (0, 0)
		self.select_from_xy = (0, 0)
		Tkinter.Widget.bind(self.canvas, "<1>", self.mouseDown)
		Tkinter.Widget.bind(self.canvas, "<Control-Button-1>", self.cntrlMouseDown)
		Tkinter.Widget.bind(self.canvas, "<Double-Button-1>", self.dblClick)
		Tkinter.Widget.bind(self.canvas, "<Shift-Button-1>", self.extendSelection)
		Tkinter.Widget.bind(self.canvas, "<ButtonRelease-1>", self.mouseUp)
		Tkinter.Widget.bind(self.canvas, "<B1-Motion>", self.mouseMove)


	#
	# --- Utility Buttons ---
	#
	def ac_propertiesCB(self, event):
		if self.action == self.MULTI_MOVE:
			self.action = self.MULTI_SELECT # turn off move if using menu
		canvas = event.widget
		item = canvas.find_closest(event.x, event.y)
		button = self.item_to_button(item)
		self.transition_activate(button.keytitle)

	def ac_deleteCB(self, event):
		'Remove an action and its button'
		if self.action == self.MULTI_MOVE:
			self.action = self.MULTI_SELECT # turn off move if using menu
		canvas = event.widget
		item = canvas.find_closest(event.x, event.y)
		keytitle = canvas.gettags(item)[0]
		(name, index) = self.keyframes.keytitleSplit(keytitle)
		self.keyframes.remove(None, index)

	def append_keyframe(self):
		'''Add selected scene(s) as keyframe(s) to the time line. This puts it
		at the end of the animation.'''
		self.drop_pauseState()
		for button in self.scGUI.buttons_sorted():
			if button.select():
				self.keyframes.append(button.name)
		for button in self.cmdGUI.buttons_sorted():
			if button.select():
				self.keyframes.append(button.name)

	def button_create(self, canvas, kf):
		'"kf" is either a keyframe or an action'
		self.drop_pauseState()
		if isinstance(kf, Animate.Keyframes.Keyframe):
			button = KeyframeButton(canvas, kf, ['keyframe'])
			# register a trigger in any buttons's transition
			if not kf.trans.triggerset.hasHandlers('transition_frame'):
				kf.trans.triggerset.addHandler('transition_frame', self.triggerIn, kf)
		elif isinstance(kf, Animate.Action.Action):
			button = ActionButton(canvas, kf, ['action'])
			# register a trigger in any buttons's transition
			if not kf.triggerset.hasHandlers('transition_frame'):
				kf.triggerset.addHandler('transition_frame', self.triggerIn, kf)
		self.buttonDict[button.keytitle] = button
#		self.canvas.move(button.keytitle, self.tl_start + button.keyframe.end_frame, 0)

	def buttons_clearSelections(self):
		# De-select all keyframe buttons
		self.select_all_off()
#		for button in self.buttonDict.values():
#			button.select(False)
			# button.selectFrameLabels(None)

	def buttons_sorted(self):
		'Return buttons in their current order'
		def by_name(button):
			return button.name
		return sorted(self.buttonDict.values(), key=by_name)

	def create_utilities(self, parent):
		'''put these in 4 groups: add scene/action, play controls, 
		viewing controls, record functions.'''
		self.utilities = {}
		# utility_frame holds the component frames
		self.utility_frame = Tkinter.Frame(parent)
		self.utility_frame.grid(row=0, column=0, sticky=Tkinter.EW)
		for i in range(4):
			self.utility_frame.grid_columnconfigure(i, weight=1)

		# Create an 'Add Keyframe' button
		col = 0
		self.add_frame = Tkinter.Frame(self.utility_frame, bd=1,
			 relief=Tkinter.RAISED)
		self.add_frame.grid(row=0, column=col, sticky=Tkinter.W)
		icon = Icons.LoadImage('knob-add.png')
		if icon:
			help = 'Add selected to the timeline'
			icon = PhotoImage(icon)
			button = Tkinter.Button(self.add_frame,
				image=icon,
				relief=Tkinter.FLAT,
				command=self.append_keyframe)
			button.grid(row=0, column=col)
			button._icons = (icon,)
			self.utilities['Add Timeline'] = button
			self.balloonhelp.bind(button, help)
		# Create an 'Remove Keyframe' button
		col += 1
		icon = Icons.LoadImage('knob-remove-red.png')
		if icon:
			help = 'Remove selected from the timeline'
			icon = PhotoImage(icon)
			button = Tkinter.Button(self.add_frame,
				image=icon,
				relief=Tkinter.FLAT,
				command=self.delete_selected)
			button.grid(row=0, column=col)
			button._icons = (icon,)
			self.utilities['Remove Timeline'] = button
			self.balloonhelp.bind(button, help)

		# Populate the parent with movie controls for each play back command
		col = 0
		self.play_controls = Tkinter.Frame(self.utility_frame, bd=1,
			relief=Tkinter.RAISED)
		self.play_controls.grid(row=0, column=1)
		for cmd in self.movie_commands:
			if cmd not in ['stop', 'record']:
				col += 1
				self.create_movie_button(self.play_controls, command=cmd, col=col)

		# zoom in/out controls
		self.zoom_frame = Tkinter.Frame(self.utility_frame, bd=1,
			relief=Tkinter.RAISED)
		self.zoom_frame.grid(row=0, column=2)
		icon = Icons.LoadImage('zoom-in.png')
		if icon:
			help = 'Zoom in'
			icon = PhotoImage(icon)
			button = Tkinter.Button(self.zoom_frame,
				image=icon,
				relief=Tkinter.FLAT,
				command=self.zoom_in)
			button.grid(row=0, column=0)
			button._icons = (icon,)
			self.utilities['Zoom in'] = button
			self.balloonhelp.bind(button, help)
			col += 1
		icon = Icons.LoadImage('zoom-out.png')
		if icon:
			help = 'Zoom out'
			icon = PhotoImage(icon)
			button = Tkinter.Button(self.zoom_frame,
				image=icon,
				relief=Tkinter.FLAT,
				command=self.zoom_out)
			button.grid(row=0, column=1)
			button._icons = (icon,)
			self.utilities['Zoom out'] = button
			self.balloonhelp.bind(button, help)

		self.output_frame = Tkinter.Frame(self.utility_frame, bd=1,
			relief=Tkinter.RAISED)
		self.output_frame.grid(row=0, column=3, sticky=Tkinter.E)
		# Add a button to generate a story board
		icon = Icons.LoadImage('story-board.png')
		col = 0
		if icon:
			help = 'Generate storyboard'
			icon = PhotoImage(icon)
			button = Tkinter.Button(self.output_frame,
				image=icon, relief=Tkinter.FLAT,
				command=self.storyboard)
			button.grid(row=0, column=col)
			button._icons = (icon,)
			self.utilities['Storyboard'] = button
			self.balloonhelp.bind(button, help)
			col += 1
		# and finally, the record button
		self.create_movie_button(self.output_frame, command='record', col=col)


	def create_movie_button(self, parent, command='', col=0):
		'Create a movie control button'
		# Create the command callback, note that it arises from the GUI
		cb = (lambda:self.movie(command, 'GUI'))
		# Icon image files have the command name in their file name.
		# Try to load an 'icon_on' file
		iconfile = 'anim-%s-on.png' % command
		icon_on = Icons.LoadImage(iconfile)
		# Try to load an 'icon_off' file
		iconfile = 'anim-%s-off.png' % command
		icon_off = Icons.LoadImage(iconfile)
		# Try to load an icon file
		iconfile = 'anim-%s.png' % command
		icon = Icons.LoadImage(iconfile)
		# Create the command icon button or check button
		if command in ['loop', 'record']:
			# Create a check button with an instance variable
			button = Tkinter.Checkbutton(parent,
				indicatoron=False,
				relief=Tkinter.FLAT, offrelief=Tkinter.FLAT,
				onvalue=True, offvalue=False,
				variable=self.movie_status[command],
				command=cb)
		elif command in ['play', 'plusOne', 'minusOne']:
			# a regular button here
			button = Tkinter.Button(parent, command=cb,
				relief=Tkinter.FLAT)
			self.command_button[command] = button
		else:
			button = Tkinter.Button(parent,
				relief=Tkinter.FLAT,
				command=cb)
		if icon_on and icon_off:
			icon_on = PhotoImage(icon_on)
			icon_off = PhotoImage(icon_off)
			button.config(image=icon_off)
			button.config(selectimage=icon_on)
			button._icons = (icon_on, icon_off)
		elif icon:
			icon = PhotoImage(icon)
			button.config(image=icon)
			button._icons = (icon,)
		else:
			error = 'Cannot locate animation icons'
			raise chimera.error(error)
		background = button.config('background')[-1]
		button.config(activebackground=background)
		button._cb = cb
		button.grid(row=0, column=col)
		self.utilities[command] = button
		self.balloonhelp.bind(self.utilities[command],
			self.keyframes.movie_command_tips[command])


	def canvas_expand(self, new_width):
		'expand the existing canvas by amount frames'
		self.canvas.config(width=new_width)
		self.time_line()

	def canvas_width(self):
		cnf = self.canvas.configure()
		return int(cnf['width'][4])

	@property
	def cmdGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.cmdGUI

	def cntrlMouseDown(self, event):
		# this is multi-select. use the lowest event.x for lastx.
		# the left most widget is the one which will warp to the cursor.
#		if event.x < self.lastx:

		self.lastx = event.x
		self.lasty = event.y
		tags = self.canvas.gettags(Tkinter.CURRENT)
		if not tags:
			return
		button = self.item_to_button(Tkinter.CURRENT)
		self.action = self.MULTI_SELECT
		self.toggle_button_selected(button)

	def dblClick(self, event):
		'display this keyframe in Chimera'
		tags = self.canvas.gettags(Tkinter.CURRENT)
		if len(tags) == 0:
			return
		button = self.xpos_to_button(event.x, event.y)
		if not button:
			return

		if isinstance(button.keyframe, Animate.Action.Action):
			chimera.replyobj.warning("Display Action not currently available")
			return
		# is the movie currently playing? if so, pause, reset the display and continue play
		kf = self.keyframes.display
		isPlaying = (self.movie_status['play'] == MOVIE_PLAY)
		if self.movie_status['play'] != MOVIE_STOP:
			self.keyframes.endKeyframePlay(kf)
		button.keyframe.scene.display()
		self.frame_line('set', button.keyframe.index + 1)
		self.keyframes.display = button.keyframe
		self.keyframes.display.frameCount = 0
		self.movie_status['play'] = MOVIE_STOP
		self.setPlayIcon()
		if isPlaying: # continue playing on selected keyframe
			self.keyframes.switchKeyframePlay(kf)

	def delete_selected(self):
		for button in self.buttonDict.values():
			if button.select():
				self.keyframes.remove(None, button.keyframe.kf_id)
		self.time_line()

	def dialog_create(self, parent):
		'Add utility dialogs (activated by utility buttons)'
		self.transitionDialog = TransitionDialog(self, parent)
		self.storyboardDialog = SaveStoryboardDialog()

	def dialog_update(self, keytitle=None):
		'Update utility dialogs'
		self.transitionDialog.update(keytitle)

	def dnd_accept(self, Source, event):
		#Tkdnd is asking us if we want to tell it about a TargetObject.
		#print "LightboxKeyframes::dnd_accept"
		return self.dnd_widget

	def dnd_enter(self, Source, event):
		#This is called when the mouse pointer goes from outside the
		#Target Widget to inside the Target Widget.
		#print "LightboxKeyframes::dnd_enter"
		if hasattr(Source, 'updateXY'):
			self.savedCursor = event.widget["cursor"] or ""
			event.widget.config(cursor="dotbox")
			Source.updateXY(event.x_root, event.y_root)

	def dnd_leave(self, Source, event):
		#This is called when the mouse pointer goes from inside
		#to outside the Target Widget.
		#print "LightboxKeyframes::dnd_leave"
		if hasattr(Source, 'updateXY'):
			event.widget.config(cursor=self.savedCursor)
		return

	def dnd_motion(self, Source, event):
		#This is called when the mouse pointer moves within the TargetWidget.
		#p = self.dnd_widget.grid_location(event.x, event.y)
		#print "LightboxKeyframes::dnd_motion; grid position = %s" % repr(p)
		if hasattr(Source, 'updateXY'):
			Source.updateXY(event.x_root, event.y_root)
			canvas_root_x = self.canvas.winfo_rootx()
			x = event.x_root - canvas_root_x
			self.show_dnd_frame(x)

	def dnd_commit(self, Source, event):
		#This is called if the DraggedObject is being dropped on us
		#print "LightboxKeyframes::dnd_commit; Object received= %s" % repr(Source)
#		p = self.dnd_widget.grid_location(event.x, event.y)
		#print "LightboxKeyframes::dnd_commit; grid position = %s" % repr(p)
		if hasattr(Source, 'updateXY'):
			canvas_root_x = self.canvas.winfo_rootx()
			x = event.x_root - canvas_root_x
			end_frame = (x - self.tl_start) / self.PixelsPerFrame
			self.drop_pauseState()
			self.keyframes.insert(Source.scene.name, 1, end_frame)
			if hasattr(self, 'frame_cntr'):
				self.canvas.delete(self.frame_cntr)

	def drop_pauseState(self):
		self.keyframes.drop_pauseState()
		self.movie_status['play'] = MOVIE_STOP
		self.setPlayIcon()
		self.frame_line('unset')

	def extendSelection(self, event):
		'User clicked the mouse with shift key down. Extend the selection.'
		canvas = event.widget
		self.lastx = event.x
		self.lasty = event.y
		self.select_all_off()
		(fx, fy) = self.select_from_xy
		(tx, ty) = (event.x, event.y)
		if fx == 0 and fy == 0:
			fx = tx
			fy = ty
		self.action = self.MULTI_SELECT
		items = canvas.find_overlapping(fx, fy, tx, ty)
		buttons = self.items_to_buttons(items)
		if buttons is None:
			return
		for button in buttons:
			if button.select():
				continue
			button.select(True)

	def frame_line(self, cmd, index=None):
		'''set, move or unset a frameline showing the currently playing frame.

		'set' requires an index which is the frame about to play. calculate the
		line location.
		'move' moves it 1 frame equivalent to the right.
		'unset' makes it disappear.
		'index' is the keyframe index if the command is 'set' and 
		the number of frames to move if the command is 'move'.'''
		if cmd == 'set':
			if index == None:
				return error
			kf = None
			start_at = 0
			for i in range(len(self.keyframes)):
				if i == index:
					break
				kf = self.keyframes.entries[i]
				start_at += kf.frames
			coords = self.canvas.coords(self._frame_line)
			self.canvas.move(self._frame_line, -coords[0], 0)
			self.canvas.move(self._frame_line, self.tl_start + (self.PixelsPerFrame * start_at), 0)
			self.canvas.itemconfig(self._frame_line, state=Tkinter.NORMAL)
		elif cmd == 'move':
			'index is the value to increment/decrement'
			self.canvas.move(self._frame_line, index * self.PixelsPerFrame, 0)
		elif cmd == 'unset':
			self.canvas.itemconfig(self._frame_line, state=Tkinter.HIDDEN)
		else:
			return error

	def item_to_button(self, item):
		'lookup a button by the Canvas item. Presumes keytitle is the first tag'
		tags = self.canvas.gettags(item)
		if len(tags):
			keytitle = self.tags_to_keytitle(tags)
			if not self.buttonDict.has_key(keytitle):
				return None
			button = self.buttonDict.get(keytitle)
			return button

	def items_to_buttons(self, items):
		'return a sorted list of buttons mapped to these canvas items.'
		'ensure duplicates are avoided. Sort is by index in the timeline.'
		btn_dict = {}
		for item in items:
			button = self.item_to_button(item)
			if button:
				btn_dict[button.index] = button
		blist = btn_dict.values()
		def by_idx(btn):
			return btn.index
		return sorted(blist, key=by_idx)

	def items_to_keyframes(self, items):
		'return an ordered set of keyframes behind these canvas items'
		keyframes = []
		for button in self.items_to_buttons(items):
			keyframes.append(button.keyframe)
		return keyframes

	def keyframe_clear(self):
		'Confirm removal of all keyframes'
		from chimera.baseDialog import AskYesNoDialog
		text = ("Please confirm clearing the timeline.\n"
			"This will not remove related scenes.")
		d = AskYesNoDialog(text=text, title="Clear Timeline")
		if d.run(self.group_interior) == "yes":
			self.keyframes.clear()

	def kf_deleteCB(self, event):
		'Remove a keyframe and its button'
		if self.action == self.MULTI_MOVE:
			self.action = self.MULTI_SELECT # turn off move if using menu
		self.drop_pauseState()
		canvas = event.widget
		item = canvas.find_closest(event.x, event.y)
		keytitle = canvas.gettags(item)[0]
		(name, kf_id) = self.keyframes.keytitleSplit(keytitle)
		self.keyframes.remove(None, kf_id)
		# if others are selected, delete them too
#		selitems = self.canvas.find_withtag('selected')
#		selected_kfs = self.items_to_keyframes(selitems)
#		for kf in selected_kfs:
#			self.keyframes.remove(None, kf.kf_id)

	def kf_transitionCB(self, event):
		if self.action == self.MULTI_MOVE:
			self.action = self.MULTI_SELECT # turn off move if using menu
		canvas = event.widget
		item = canvas.find_closest(event.x, event.y)
		button = self.item_to_button(item)
		self.transition_activate(button.keytitle)

	@property
	def left_selected_kfb(self):
		'return the left most selected keyframe button, if it exists.'
		self.setSelectedEnds()
		return self._left_selected_kfb

	def lightbox_create(self, parent):
		'''Add the Canvas to self.lightbox for drawing.'''
		Lightbox.lightbox_create(self, parent)
		self.canvas = Tkinter.Canvas(self.lightbox.interior(), width=1000)
		self.canvas.pack()

	def lightbox_image_update(self):
		for keytitle, button in self.buttonDict.items():
			button.sceneImageUpdate()

	def lightbox_update(self):
		'Recreate the button lightbox'
		# TODO: Instead of clearing everything and regenerating it again,
		# iterate over the the buttons to validate they refer to existing
		# scenes, keep those that do and remove those that do not.  Then
		# rearrange the layout.
		do_reset = False
		if hasattr(self.keyframes, 'do_reset'):
			do_reset = self.keyframes.do_reset
		for kf in self.keyframes.entries:
			if not kf.keytitle in self.buttonDict:
				self.button_create(self.canvas, kf)
		if do_reset:
			# animation window now exists
			del self.keyframes.do_reset
		#
		# TODO: Should be able to remove this insurance policy, everything
		# SHOULD be taken care of in buttons_integrity().
		for button in self.buttonDict.values():
			if not button.keytitle in self.keyframes.keytitles():
				self.button_remove(button.keytitle)
		#print
		#print 'LightboxKeyframes: after button_create'
		#self.printButtonDict()
		#
		self.lightbox_rearrange()

	# Overload this method to provide a linear timeline, instead of a grid.
	def lightbox_rearrange(self, width=None):
		'Rearrange the button lightbox'
		for kf in self.keyframes.entries:
			self.move_button(kf)

	def lightbox_scroll(self, offset=0):
		'Reposition the view of the button lightbox'
		# Assign the buttons to grid positions
		return
		N = len(self.keyframes)
		if not N:
			return
		visibleA, visibleB = self.lightbox.xview()
		for i, keytitle in enumerate(self.buttons_sorted()):
			button = self.buttonDict.get(keytitle)
			if button.select():
				offset = float(i) / N
				break
		if not (visibleA < offset < visibleB):
			self.lightbox.xview('moveto', offset)
		self.lightbox.reposition()

	def mark_selection(self, xpos, ypos):
		'Mouse was raised on multi-select. Select the buttons enclosed.'
		canvas = self.canvas
		bbox = canvas.bbox(self.select_box)
		canvas.delete(self.select_box)
		self.select_box = None
		# find items in the selection area
		items = canvas.find_overlapping(bbox[0], bbox[1], bbox[2], bbox[3])
		at_frame = self.xpos_to_frame(xpos)
		buttons = self.items_to_buttons(items)
		if not buttons:
			return
		for button in buttons:
			button.select(True)

	def menuDown(self, event):
	# MB3 pressed
		canvas = event.widget
		tags = canvas.gettags(Tkinter.CURRENT)
		if 'keyframe' in tags:
			self.popupMenu(event, self.tags_to_keytitle(tags), self.keyframePopup)
		if 'action' in tags:
			self.popupMenu(event, self.tags_to_keytitle(tags), self.actionPopup)

	def mouseDown(self, event):
	# remember where the mouse went down
		if self.movie_status['play'] == MOVIE_PLAY:
			return # no mouse actions during play
		canvas = event.widget
		self.lastx = event.x
		self.lasty = event.y
		self.from_xy = (event.x, event.y)

		if DEBUG:
			tags = canvas.gettags(Tkinter.CURRENT)
			if tags:
				print "mouse down in %s at %d" % (self.tags_to_keytitle(tags), event.x)

		button = self.xpos_to_button(event.x, event.y)
		if button == None: # not over any objects; clear
			self.select_all_off()
			self.action = self.NO_ACTION
			return
		if self.action == self.MULTI_SELECT: # may move now
#			self.action = self.MULTI_MOVE
			return

		# clear everything toggle CURRENT selection state
		if button:
			selstate = button.select()
		self.select_all_off()
		if button:
			button.select(not selstate)
			if button.select():
				self.select_from_xy = (event.x, event.y) # in case extended selection made
				self.transitionDialog.update(button.keytitle)
			else:
				self.select_from_xy = (0, 0) # in case extended selection made

	def mouseEnter(self, event):
		# the Tkinter.CURRENT tag is applied to the object the cursor is over.
		# this happens automatically.
#		self.canvas.itemconfig(Tkinter.CURRENT, fill="red")
		pass
	def mouseLeave(self, event):
		# the Tkinter.CURRENT tag is applied to the object the cursor is over.
		# this happens automatically.
#		self.canvas.itemconfig(Tkinter.CURRENT, fill="blue")
		pass


	def mouseMove(self, event):
	# whatever the mouse is over gets tagged as Tkinter.CURRENT for free by tk.
		if self.movie_status['play'] == MOVIE_PLAY:
			return # no mouse actions during play
		canvas = event.widget
		if self.action == self.MULTI_SELECT: # may move now
			self.action = self.MULTI_MOVE


		# are we past the edge? If so and not at the boundary, scroll it.
		# looking for the clipper window's edge
		visibleL, visibleR = self.lightbox.xview()
		canvas_w = float(self.canvas_width())
		edge_l = int(visibleL * canvas_w)
		edge_r = int(visibleR * canvas_w)
		if event.x > edge_r and visibleR < 1.0:
			offset = 1
			self.lightbox.xview('scroll', offset, "units")
			event.x = event.x + offset
		if event.x < edge_l and visibleL > 0.0:
			offset = -1
			self.lightbox.xview('scroll', offset, "units")
			event.x = event.x + offset

		button = self.item_to_button(Tkinter.CURRENT)
		if not button: # or (button is not None and button.keyframe.index == 0):
			# drawing a selection box
			self.action = self.MULTI_SELECT
			if self.select_box:
				canvas.delete(self.select_box)
			self.select_box = canvas.create_rectangle(self.from_xy,
				event.x, event.y, outline='black', width=3, outlinestipple="gray12")
		else:
			self.drop_pauseState()
			BIT_SHIFT	 = 0x001
			select_tag = 'selected'
			# selected item? move it.
			self.action = self.MOVE
			if event.state & BIT_SHIFT and self.action != self.MULTI_MOVE: # ripple move
				select_tag = 'ripple_move'
				for butn in self.buttonDict.values():
					if butn.index >= button.index:
						butn.ripple_move(True)
				self.action = self.RIPPLE_MOVE

			# check if going too far left
			this_x = event.x
			self.setSelectedEnds()
			l_button = self._left_selected_kfb
			r_button = self._right_selected_kfb
			if l_button:
				l_coords = self.canvas.coords(l_button.tl_ptr)
				if l_coords[0] < self.tl_start + (1 * self.PixelsPerFrame):
					# constrain this to the first frame
					self.insert_frame = 1
					return

			if r_button:
				r_coords = self.canvas.coords(r_button.tl_ptr)
				if r_coords[0] > canvas_w:
					self.canvas_expand(canvas_w + 50)
					self.time_line()

			self.canvas.move(select_tag, this_x - self.lastx, 0)
			self.insert_frame = self.show_lead_frame()
			self.time_line()
			self.lastx = this_x
			self.lasty = event.y

	def move_button(self, kf):
		self.drop_pauseState()
		button = self.buttonDict[kf.keytitle]
		coords = self.canvas.coords(button.tl_ptr)
		keytitle = kf.keytitle
		self.canvas.move(keytitle, -coords[0], 0)
		self.canvas.move(keytitle, (self.PixelsPerFrame * kf.end_frame) + self.tl_start, 0)
		button.show_intro_box()


	def mouseUp(self, event):
		if hasattr(self, 'frame_cntr'):
			self.canvas.delete(self.frame_cntr)
		if self.action == self.RIPPLE_MOVE:
			select_tag = 'ripple_move'
		else:
			select_tag = 'selected'
		selitems = self.canvas.find_withtag(select_tag)
		if self.select_box: # finished drawing a selection box
			self.mark_selection(event.x, event.y)

		elif self.action == self.MULTI_MOVE or self.action == self.MOVE or \
			self.action == self.RIPPLE_MOVE:
			# move completed
			if selitems:
				sel_keyframes = self.items_to_keyframes(selitems)
				frame_delta = self.insert_frame - self.left_selected_kfb.keyframe.end_frame
				self.keyframes.move_selections(sel_keyframes, frame_delta)
				self.time_line()

			if self.action == self.RIPPLE_MOVE:
				self.ripple_all_off()
			else:
				self.select_all_off()
			self.action = self.NO_ACTION

	def movie(self, command, source='GUI'):
		'''Implements animation commands
		- movie(<command>, <source>)
		- commands include:
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
		- source is where the command originates, which determines whether or
			not to activate a command trigger (to avoid recursive triggers)
			- 'MIDAS' is a command source
			- 'GUI' is an animation module GUI source
		'''
		commands = self.movie_commands + ['status']
		if command not in commands:
			msg = 'Unknown animation command'
			chimera.replyobj.warning(msg)
		if command in ['first', 'last', 'previous', 'next', 'status']:
			if command != 'status':
				self.drop_pauseState()
				if command in ['previous', 'next']:
					self.movie_status['play'] = MOVIE_PLAY
					self.playType = MOVIE_NEXT_PREV
					if self.keyframes.display:
						add = 0
						if command == 'next':
							add = 1
						self.frame_line('set', self.keyframes.display.index + add)
					self.setPlayIcon()
				if command == 'last':
					self.frame_line('set', len(self.keyframes))
					self.playType = None
				if command == 'first':
					self.frame_line('set', 0)
					self.playType = None

			if source == 'MIDAS':
				# Are there any GUI states to change?
				pass
			else:
				self.keyframes.movie(command, source)
				if self.movie_status['play'] == MOVIE_PLAY:
					self.movie_status['play'] = MOVIE_STOP
				self.setPlayIcon()
		if command == 'stop':
			self.movie_stop(source)
		if command == 'play': # play/pause/resume button
			'''Three way state command: play, pause, stop.'''
			if not len(self.keyframes):
				self.movie_status['play'] = MOVIE_STOP
				self.setPlayIcon()
				chimera.replyobj.warning('Nothing to animate.')
				return
			play_state = self.movie_status['play']
			if play_state == MOVIE_STOP:
				if self.playType != MOVIE_NEXT_PREV:
					self.playType = MOVIE_PLAY
				self.movie_play(source)
			if play_state == MOVIE_PLAY:
				self.movie_pause(source)
			if play_state == MOVIE_PAUSE and not self.keyframes.pauseSaved:
				self.movie_status['play'] = MOVIE_STOP
				self.movie_stop(source)
			if play_state == MOVIE_PAUSE and self.keyframes.pauseSaved:
				self.movie_resume(source) # sets MOVIE_PLAY status
				if self.playType:
					# check here in case a resume got paused
					if self.movie_status['play'] == MOVIE_PLAY:
						self.movie_play(source)
				else:
					self.movie_status['play'] = MOVIE_STOP
					self.setPlayIcon()
		if command == 'loop':
			if source == 'MIDAS':
				# Update the GUI
				value = self.keyframes.movie_status[command]
				self.movie_status[command].set(value)
			else:
				self.keyframes.movie(command, source)
		if command == 'record':
			if not len(self.keyframes):
				self.movie_status[command].set(False)
				chimera.replyobj.warning('Nothing to animate.')
				return
			if source == 'MIDAS':
				# Update the GUI
				value = self.keyframes.movie_status[command]
				self.movie_status[command].set(value)
			else:
				# pause if playing and about to record
				if self.movie_status['record'].get() and \
					self.movie_status['play'] == MOVIE_PLAY:
						self.movie_pause()
				self.keyframes.movie(command, source)
		if command in ['minusOne', 'plusOne']:
			self.movie_status['play'] = MOVIE_PAUSE
			self.setPlayIcon()
			self.keyframes.movie(command, source)

	def movie_pause(self, source='GUI'):
		self.movie_status['play'] = MOVIE_PAUSE
		self.setPlayIcon()
		if source == 'MIDAS':
			# Update GUI button states from keyframes movie status
			for button in ['play']:
				value = self.keyframes.movie_status[button]
				self.movie_status[button].set(value)
		else:
			self.keyframes.movie_pause(source)

	def movie_play(self, source='GUI'):
		self.movie_status['play'] = MOVIE_PLAY
		self.setPlayIcon()
		if self.keyframes.movie_validate():
			# Update button states
			self.movie_status['play'] = MOVIE_PLAY
			if source == 'GUI':
				# Initiate the animation
				self.keyframes.movie('play', source)

	def movie_stop(self, source='GUI'):
		'Set GUI button states and keyframe movie states for stop'
		if self.movie_status['play'] == MOVIE_STOP:
			return
		# Release the check button toggle state
		self.movie_status['play'] = MOVIE_STOP
		self.setPlayIcon()
		if source == 'GUI':
			self.keyframes.movie('stop', source)
		self.frame_line('unset')
		self.keyframes.movie_first()

	def movie_resume(self, source='GUI'):
		'''return to the state and view when play was paused and continue.'''
		self.movie_status['play'] = MOVIE_PLAY
		self.setPlayIcon()
		self.keyframes.movie_resume()

#	def notebook_arrange_page(self):
#		'Create a notebook page for moving keyframes'
#		page = self.dialog._pages['Arrange']
#		#
#		# Display a list of keyframes
#		listbox = Pmw.ScrolledListBox(page,
#			items=self.keyframes.disptitles(),
#			labelpos='nw',
#			label_text='Timeline:',
#			listbox_selectmode=Tkinter.EXTENDED,
#			listbox_height=6,
#			)
#		listbox.pack(side=Tkinter.LEFT,
#			fill=Tkinter.BOTH, expand=1,
#			padx=10, pady=5)
#		self.arrange_listbox = listbox
#		msg = 'Arrange timeline\n'
#		msg += ' - click on items to select\n'
#		msg += ' - shift-click for range selection\n'
#		msg += ' - ctrl-click for multiple, discrete selections'
#		self.balloonhelp.bind(listbox, msg)
#		#
#		# Add action buttons
#		buttonbox = Pmw.ButtonBox(page,
#			labelpos='nw',
#			label_text='Arrange timeline:',
#			frame_borderwidth=2,
#			frame_relief='groove',
#			orient='vertical')
#		buttonbox.pack(side=Tkinter.RIGHT,
#			fill=Tkinter.X, expand=1,
#			padx=10, pady=5)
#		# Add some action buttons to the ButtonBox.
#		actions = ['Move Up', 'Move Down', 'Remove', 'Clear All']
#		for action in actions:
#			# Use x=button to set lambda default (can't rely on runtime lookup)
#			cb = lambda x = action: self.notebook_arrange_cb(x)
#			buttonbox.add(action, command=cb)
#		buttonbox.alignbuttons()	# set buttons same width
#		self.arrange_buttonbox = buttonbox
#
#	def notebook_arrange_activate(self):
#		'Update and activate the dialog to manage keyframes'
#		self.notebook_arrange_update()
#		self.dialog_show('Arrange')
#
#	def notebook_arrange_update(self, selectedIndices=[]):
#		'Update the dialog when keyframes are altered'
#		keytitles = self.keyframes.keytitles()
#		keytitlesSelected = [keytitles[i] for i in selectedIndices]
#		self.arrange_listbox.setlist(keytitles)
#		self.arrange_listbox.setvalue(keytitlesSelected)
#
#	def notebook_arrange_cb(self, action=None):
#		'Callback for the dialog to arrange keyframes'
#		# Define lists for trackTitles and selectTitles
#		trackTitles = []
#		selectTitles = list(self.arrange_listbox.getvalue())
#		if action == 'Move Down':
#			# selectTitles is ordered from lowest to highest index, so
#			# reverse it to move the highest item first.
#			selectTitles.reverse()
#		# Unpack index and name from strings in selectTitles, and
#		# populate trackTitles before moving anything, in case nothing moves.
#		for i, keytitle in enumerate(selectTitles):
#			name, index = self.button_keytitleSplit(keytitle)
#			selectTitles[i] = (name, index)
#			trackTitles.append(index)
#		if action == 'Move Up':
#			# Titles is ordered from lowest to highest index
#			for i, item in enumerate(selectTitles):
#				name, index = item
#				if index >= 1:
#					# update is triggered by keyframes.move
#					self.keyframes.move(indexFrom=index, indexTo=index - 1)
#					trackTitles[i] = index - 1
#				else:
#					# Stop when the lowest item in the list cannot be moved
#					break
#			self.notebook_arrange_update(trackTitles)
#		elif action == 'Move Down':
#			# Try to move selected Titles down
#			for i, item in enumerate(selectTitles):
#				name, index = item
#				if index < len(self.keyframes) - 1:
#					# update is triggered by keyframes.move
#					self.keyframes.move(indexFrom=index, indexTo=index + 1)
#					trackTitles[i] = index + 1
#				else:
#					# Stop when the highest item in the list cannot be moved
#					break
#			self.notebook_arrange_update(trackTitles)
#		elif action == 'Clear All':
#			self.keyframe_clear()
#			#self.keyframes.clear()
#		elif action == 'Remove':
#			keytitles = list(self.arrange_listbox.getvalue())
#			for i, keytitle in enumerate(keytitles):
#				name, index = self.keyframes.keytitleSplit(keytitle)
#				# index from keytitle is static, so we need to
#				# dynamically decrement index after removals
#				index -= i
#				self.keyframes.remove(name, index)
#		else:
#			# Unknown action
#			pass

	def popupMenu(self, event, button, menu_items):
		'simple popup menu for selections. items are (string, callback).'
		self.kfMenu.delete(0, "end")
		for name, cb in menu_items:
			if not name:
				self.kfMenu.add_separator()
			else:
				self.kfMenu.add_command(label=name,
						command=lambda e=event, cb=cb:
									cb(e))
		self.kfMenu.post(event.x_root, event.y_root)


	def printButtonDict(self):
		for keytitle, button in self.buttonDict.items():
			print '%s: %s' % (keytitle, button.keyframe.keytitle)

	@property
	def right_selected_kfb(self):
		'return the right most selected keyframe button, if it exists.'
		self.setSelectedEnds()
		return self._right_selected_kfb

	def ripple_all_off(self):
		for button in self.buttonDict.values():
			button.ripple_move(False)

	@property
	def scGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.scGUI

	def select_all_off(self):
		for button in self.buttonDict.values():
			button.select(False)

	def show_dnd_frame(self, x):
		return self.show_insert_frame(x)


	def show_lead_frame(self):
		'show a text box with current frame position while button moves'
		if self.left_selected_kfb == None:
			return None
		coords = self.canvas.coords(self.left_selected_kfb.tl_ptr)
		return self.show_insert_frame(coords[0])

	def show_insert_frame(self, x):
		'display the frame at canvas coord x'
		visibleL, visibleR = self.lightbox.xview()
		canvas_w = float(self.canvas_width())
		edge_l = int(visibleL * canvas_w)
		window_w = int((visibleR - visibleL) * canvas_w)
		cnf = self.lightbox.component('clipper').configure()
		window_ht = int(cnf['height'][4])
		current_frame = int(x - self.tl_start) / self.PixelsPerFrame
		if hasattr(self, 'frame_cntr'):
			self.canvas.delete(self.frame_cntr)
		self.frame_cntr = self.canvas.create_text(edge_l + (window_w / 2),
			window_ht - 20, text=str(current_frame))
		return current_frame


	def scene_append(self):
		'Append a new scene entry (from new keyframe dialog)'
		scene_name = self.scene_append_entry.getvalue()
		if scene_name not in self.scenes.names() + ['']:
			# add a new scene and keyframe
			self.scenes.append(scene_name)
			self.keyframes.append(name=scene_name)
		# No need to call self.update, it is triggered by scenes.append()

	def scene_append_validate(self, name=None):
		'Validate a new scene name entry (from new keyframe dialog)'
		if name in self.scenes.names():
			# Don't allow creation of a scene that already exists
			# Note, don't use Pmw.ERROR here because it doesn't allow
			# typing something like 'sc2' when 'sc' already exists.
			return Pmw.PARTIAL
		else:
			return Pmw.OK

	def setSelectedEnds(self):
		'''if anything is selected, set the left and right buttons.'''
		self._right_selected_kfb = None
		self._left_selected_kfb = None
		if self.action == self.RIPPLE_MOVE:
			select_tag = 'ripple_move'
		else:
			select_tag = 'selected'
		selitems = self.canvas.find_withtag(select_tag)
		if selitems:
			buttons = self.items_to_buttons(selitems)
			if len(buttons) > 0:
				self._left_selected_kfb = buttons[0]
				self._right_selected_kfb = buttons[len(buttons) - 1]

	def setPlayIcon(self):
		play_state = self.movie_status['play']
		if play_state == MOVIE_PLAY:
			play_iconfile = 'anim-pause.png'
			nxtcmd = 'Pause'
		if play_state == MOVIE_STOP:
			play_iconfile = 'anim-play.png'
			nxtcmd = 'Play'
		if play_state == MOVIE_PAUSE:
			play_iconfile = 'anim-play-pause.png'
			nxtcmd = 'Resume'
		play_icon = Icons.LoadImage(play_iconfile)
		play_icon = PhotoImage(play_icon)
		self.command_button['play'].config(image=play_icon)
		self.command_button['play']._icons = (play_icon,)

#		self.command_button['minusOne'].config(image=plus_icon)
#		self.command_button['minusOne']._icons = (plus_icon,)

		self.balloonhelp.bind(self.utilities['play'], nxtcmd)

	def storyboard(self):
		'initially a non-interactive way to generate a storyboard output file set.'
		saveDir = self.storyboardDialog.run(self.canvas)
		if not saveDir:
			return
		dirPath = saveDir[0][0]
		scene_list = []
		title = self.storyboardDialog.getTitle()
		lastScene = None
		for kf in self.keyframes.entries:
			# Don't bother with any duplicate consecutive scenes
			# since they are probably present to show a pause
			try:
				sc = kf.scene
			except AttributeError:
				# Actions
				sc = kf
			if sc is not lastScene:
				scene_list.append(kf.name)
				lastScene = sc
		import webgl
		webgl.write_scenes(scene_list, title, dirPath)

	def tags_to_keytitle(self, tags):
		'''search for the "keytitle" pattern in tags. there has to be a faster way.'''
		for tag in tags:
			if self.re.match(tag):
				return tag

	def toggle_button_selected(self, button):
		if button.select():
			button.select(False)
		else:
			button.select(True)

	def transition_activate(self, keytitle):
		self.transitionDialog.activate(keytitle)

	def time_line(self):
		# draw the timeline
		canvas = self.canvas
		canvas.delete('timeline')
		# debugging
		wd = self.canvas_width()
		n_kfs = len(self.keyframes.entries)
		last_frame = 0
		if n_kfs:
			last_frame = self.keyframes.entries[n_kfs - 1].end_frame
			if (last_frame * self.PixelsPerFrame) + self.tl_start > wd:
				wd = (last_frame * self.PixelsPerFrame) + self.tl_start + 50 # arbitrary margin
				self.canvas_expand(wd)
		cnf = self.lightbox.component('clipper').configure()
		ht = int(cnf['height'][4])
		sclen = 5
		self.tl_ht = ht - (ht / 6)
		sclen = 10
		canvas.create_line(self.tl_start, self.tl_ht, wd, self.tl_ht, fill='black',
			tags=('timeline'))
		# frame scale
		fill_color = 'black'
		for x in range(self.tl_start, int(wd), 5 * self.PixelsPerFrame):
			if x > (last_frame * self.PixelsPerFrame) + self.tl_start:
				fill_color = 'gray'
			self.canvas.create_line(x, self.tl_ht, x, self.tl_ht + sclen,
				fill=fill_color, tags='timeline')
			sclen = 10 if sclen % 10 else 5

	def triggerInit(self):
		'Initialise trigger handlers for keyframes'
		for trig in self.keyframes.triggers:
			self.keyframes.triggerset.addHandler(trig, self.triggerIn, None)
		# Add trigger handlers for scenes
		for trig in ['scene_append', ]:
			self.scenes.triggerset.addHandler(trig, self.triggerIn, 'scenes')

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'''
		A method to handle triggers for the canvas
		- calls self.update()
		- funcData is defined in self.__init__() when registering this
			handler with either scenes or keyframes triggers.
		'''
		# keyframes triggers to ignore in LightboxKeyframes
		if trigger in ['delete_actionHandler']:
			return
		if trigger in self.movie_commands:
			command = str(trigger)
			source = str(trigData[0])
			self.movie(command, source)
			if trigger == 'stop' or trigger == 'next':
				self.frame_line('set', self.keyframes.display.index + 1)

		elif trigger == 'keyframe_display':
			# Select the button for the keyframe displayed
			kf = trigData[0]
			if kf:
				self.lightbox_scroll()
				self.frame_line('set', kf.index)
		elif trigger in ['keyframe_invalid', 'keyframe_update']:
			kf = trigData[0]
			if kf:
				button = self.buttonDict[kf.keytitle]
				button.sceneImageUpdate()
				button.change_title(kf.disptitle)
				self.update(kf.keytitle)
		elif trigger == 'keyframe_remove':
			keytitle = trigData[0]
			if keytitle:
				self.button_remove(keytitle)
#				self.update(keytitle)
				self.frame_line('set', self.keyframes.display.index + 1)
		elif trigger == 'transition_frame':
			self.frame_line('move', trigData['direction'])
		elif trigger == 'keyframe_move':
			(kf,) = trigData
			self.move_button(kf)
			self.frame_line('set', self.keyframes.display.index + 1)
		elif trigger == 'change_title':
			# kf.index has already changed; button will be replaced by update
			(keytitle,) = trigData
			button = self.buttonDict.get(keytitle)
			if button:
				if button.keyframe.index == 0:
					del self.buttonDict[keytitle]
					button.destroy()
				else:
					button.change_title(button.disptitle)
				self.update(keytitle)
		elif trigger == 'keyframe_properties':
			# update balloon help and property dialog
			(kf,) = trigData
			if not self.buttonDict.has_key(kf.keytitle):
				# most likely the button has not yet been created
				return
			button = self.buttonDict[kf.keytitle]
			button.update_balloon()
			self.transitionDialog.update(kf.keytitle)
		elif trigger == 'play_ended':
			# stop play or record
			self.movie_status['play'] = MOVIE_STOP
			self.setPlayIcon()
		elif trigger == 'record_stopped':
			self.movie_status['record'].set(False)
			self.keyframes.recordDialog = None
		elif trigger == 'record_started':
			self.movie_status['play'] = MOVIE_PLAY
			self.setPlayIcon()
			self.movie_status['record'].set(True)
		elif trigger == 'set_frameline':
			(kf,) = trigData
			self.frame_line('set', kf.index)
#		else:
		elif trigger in ['keyframe_append', 'scene_append']:
			if not isinstance(trigData, Animate.Scene.Scene):
				(kf,) = trigData
				keytitle = kf.keytitle
			else:
				keytitle = None
			self.update(keytitle)

	def triggerOut(self, trigger=None, name=None, index=None):
		'''
		Activate a keyframe canvas trigger, by its name
		- inputs:
			trigger=<trigger_name>: the name of a trigger to activate
			name=<keyframe_name>: the name of a keyframe
			index=<keyframe_index>: an index into the keyframe entries
		- with no input arguments, it prints the trigger names and
			any handlers already registered for each trigger
		- with a valid trigger name, it activates that trigger
			and passes the <keyframe_name> and <keyframe_index> to
			the handler (as triggerData).
		- raises chimera.error if the <trigger_name> is invalid
		'''
		if not trigger:
			# print the list of trigger names
			trigger_names = self.triggerset.triggerNames()
			print 'Keyframe triggers: %s' % trigger_names
			for n in trigger_names:
				print 'Trigger handlers for "%s": ' % n
				print self.triggerset.triggerHandlers(n)
		else:
			if trigger not in self.keyframes.triggers:
				error = 'No trigger named "%s"' % trigger
				raise chimera.error(error)
			self.keyframes.triggerset.activateTrigger(trigger, (name, index))

	def update(self, keytitle=None):
		self.lightbox_update()
		self.dialog_update(keytitle)
		self.time_line()

	def xpos_to_button(self, xpos, ypos):
		'''use the x-axis position to determine the nearest AnimationButton based
		on its end_frame.'''
		at_frame = self.xpos_to_frame(xpos)
		at_items = self.canvas.find_overlapping(xpos, ypos, xpos + 1, ypos + 1)
		buttons = self.items_to_buttons(at_items)
		closest = 1000 # some very large amount
		the_button = None
		for button in buttons:
			distance = at_frame - button.keyframe.end_frame
			if distance < 0:
				continue
			if distance < closest:
				closest = distance
				the_button = button
		if not the_button:
			return None
		return the_button

	def xpos_to_frame(self, xpos):
		'''use the x-axis postion to determine what frame of the timeline is 
		closest.'''
		return (xpos - self.tl_start) / self.PixelsPerFrame

	def zoom_in(self):
		self.PixelsPerFrame += 1
		self.canvas.delete('timeline')
		self.time_line()
		if self.keyframes.display:
			self.frame_line('set', self.keyframes.display.index + 1)
		self.lightbox_update()

	def zoom_out(self):
		if self.PixelsPerFrame > 1:
			self.PixelsPerFrame -= 1
			self.canvas.delete('timeline')
			self.time_line()
			if self.keyframes.display:
				self.frame_line('set', self.keyframes.display.index + 1)
			self.lightbox_update()

from chimera.baseDialog import ModelessDialog
class TransitionDialog(ModelessDialog):

	buttons = ("Okay", "Apply", "Cancel")
	title = "Keyframe/Action Properties"
	help = 'ContributedSoftware/animation/animation.html#kf-context'

	def __init__(self, timeline, *args, **kw):
		self.timeline = timeline
		self.balloonhelp = timeline.balloonhelp

		self.paramDict = {}
		self.paramOrder = []
		self.widgets = {} # widgets which will have values, keyed on param name

		ModelessDialog.__init__(self, *args, **kw)
		self.Close()

	def fillInUI(self, parent):
		'A keyframe transition GUI'
		#
		# A keyframe selection widget
		optionmenu = Pmw.OptionMenu(parent,
			label_text="Keyframes/Actions:", labelpos='nw',
			command=self.update_by_disptitle)
		optionmenu.pack(side=Tkinter.TOP, anchor=Tkinter.N,
			fill=Tkinter.X, expand=0,
			padx=5, pady=5)
		disptitles = self.timeline.keyframes.disptitles()
		if disptitles:
			optionmenu.setitems(disptitles)
			optionmenu.setvalue(disptitles[0])
		self.optionmenu = optionmenu
		#
		# Add a notebook to the main dialog
		self.notebook = Pmw.NoteBook(parent,
			hull_width=300)
		self.notebook.pack(
			side=Tkinter.BOTTOM, #anchor=Tkinter.N,
			fill=Tkinter.BOTH, expand=1,
			padx=5, pady=5)
		# Add pages to the notebook (to be populated later)
		self._addAttributesPage(self.notebook)
		self._initParametersPage(self.notebook)
		# Add some hooks for tracking keyframe data
		self.keyframeIndex = None

	def _initParametersPage(self, notebook):
		if "Parameters" in notebook.pagenames():
			notebook.delete("Parameters")
		page = self.notebook.add("Parameters") # just the blank page
		frame = Tkinter.Frame(page)
		label = Tkinter.Label(frame, text="None", pady=10)
		label.pack(side=Tkinter.LEFT, fill=Tkinter.X, expand=1, padx=2, pady=2)
		frame.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=0, padx=4, pady=4)

	def _addParametersPage(self, notebook):
		# Add parameters page to notebook
		# save the widget with the get() function used to retrieve the value
		# self.update() will insert values for the current Action of this type
		notebook.delete("Parameters")
		page = notebook.add("Parameters")
		page.columnconfigure(1, weight=1)
		row = 0
		for pname in self.paramOrder:
			if not hasattr(self.paramDict[pname], 'gui'):
				continue

			gui = self.paramDict[pname].gui
			label = Tkinter.Label(page, text=gui['label'])
			label.grid(row=row, column=0, sticky="e")

			# create the editing widget according to its type
			widget = gui['widget']
			if widget == Tkinter.OptionMenu:
				val = Tkinter.StringVar(page)
				w = Tkinter.OptionMenu(page, val,
						*self.paramDict[pname].choices)
				w.grid(row=row, column=1, sticky="ew")

			elif widget == Tkinter.Entry:
				vcmd = (page.register(self._validateText), pname, '%P')
				val = Tkinter.StringVar()
				w = Tkinter.Entry(page,
					bg='gray',
					textvariable=val,
					validate='focusout',
					validatecommand=vcmd)
				w.grid(row=row, column=1, sticky="ew")
			row += 1

			self.widgets[pname] = val
			val.set(self.paramDict[pname].value)


	def _addAttributesPage(self, notebook):
		# Add attributes page to notebook
		page = notebook.add("Duration")
		#
		# Add all the keyframe transition elements
		#
		# TODO: Add per-model selection and fade-in/fade-out transition
		#
		# -----
		#
		# Number of frames in a transition
		#
		frame = Tkinter.Frame(page)
		label = Tkinter.Label(frame,
			text='Duration in frames:',
			pady=10)
		label.pack(side=Tkinter.LEFT,
			fill=Tkinter.X, expand=1,
			padx=2, pady=2)
		entry = Tkinter.Entry(frame,
			bg='gray',
			validate='focus',
			validatecommand=self._validateNframes)
		entry.pack(side=Tkinter.RIGHT,
			fill=Tkinter.X, expand=1,
			padx=2, pady=2)
		frame.pack(side=Tkinter.TOP,
			fill=Tkinter.BOTH, expand=0,
			padx=4, pady=4)
		help = 'Number of frames in transition (Nframes > 0).'
		self.balloonhelp.bind(entry, help)
		self.nframesEntry = entry
		#
		# Frame count for discrete transitions
		#
		frame = Tkinter.Frame(page)
		label = Tkinter.Label(frame,
			text='Nth frame for\ndiscrete transitions:',
			pady=10)
		label.pack(side=Tkinter.LEFT,
			fill=Tkinter.X, expand=1,
			padx=2, pady=2)
		entry = Tkinter.Entry(frame,
			bg='gray',
			validate='focus',
			validatecommand=self._validateDiscreteFrame)
		entry.pack(side=Tkinter.RIGHT,
			fill=Tkinter.X, expand=1,
			padx=2, pady=2)
		frame.pack(side=Tkinter.TOP,
			fill=Tkinter.BOTH, expand=0,
			padx=4, pady=4)
		help = 'Nth frame for discrete transitions.\n'
		help += '0 < Nth frame <= Nframes'
		self.balloonhelp.bind(entry, help)
		self.discreteFrameEntry = entry

	def _validateNframes(self):
		entry = self.nframesEntry
		try:
			nframes = int(entry.get())
			if nframes > 0:
				entry.config(bg='gray')
				return True
			else:
				# PROBLEM HERE
				entry.config(bg='red')
				return False
		except Exception, e:
			entry.config(bg='red')
			return False

	def _validateDiscreteFrame(self):
		entry = self.discreteFrameEntry
		try:
			nframes = int(self.nframesEntry.get())
			discreteFrame = int(entry.get())
			if 0 < discreteFrame <= int(nframes):
				entry.config(bg='gray')
				return True
			else:
				entry.config(bg='red')
				return False
		except Exception, e:
			entry.config(bg='red')
			return False

	def _validateText(self, pname, newval):
		param = self.paramDict[pname]
		val = param.validate(newval)
		if val is not False:
			return True
		# error dialog
		msg = 'Invalid value for %s' % (pname)
		chimera.replyobj.error(msg)
		return False


	def _addCommandsPage(self, notebook):
		#Add command editor
		page = notebook.add("Commands")
		editor = MidasEditor(page, group=False)
		help = 'Commands to execute after transition completes.\n'
		help += 'Some changes may not persist beyond the current keyframe.  For\n'
		help += 'example, adding new models may fail to persist beyond the current\n'
		help += 'keyframe, unless they were saved in subsequent keyframe states.\n'
		self.balloonhelp.bind(page, help)
		help = 'Single-click to enter command. '
		help += 'Double-click for help.'
		self.balloonhelp.bind(editor.midasCompleteListBox, help)
		self.commandEditor = editor

	def activate(self, keytitle):
		'Update and activate the keyframe transition dialog'
		self.update(keytitle)
		self.enter()

	def Apply(self):
		'Callback for the dialog to set keyframe transitions'
		try:
#			if not self.keyframeIndex: # kf0 has no transitions
#				return
			selected = self.optionmenu.getvalue()
			kf = self.timeline.keyframes.getKeyframe_by_disptitle(selected)
			Nframes = int(self.nframesEntry.get())
			if Nframes <= 0: # not allowed
				Nframes = 1
				self.nframesEntry.insert(0, 1)
			if isinstance(kf, Animate.Keyframe.Keyframe):
				# Set discrete transition
				discreteFrame = int(self.discreteFrameEntry.get())
				kf.trans.discreteFrame = discreteFrame
			elif isinstance(kf, Animate.Action.Action):
				'Callback for the dialog to set action properties'
				for pname in self.paramDict.keys():
					if not hasattr(self.paramDict[pname], 'gui'):
						continue
					val = self.widgets[pname].get()
					self.paramDict[pname].value = self.paramDict[pname].convert_to_type(val)
			# now that parameters are adjusted; apply changes
			self.timeline.keyframes.move_keyframes(kf.index, Nframes)

			# don't call this directly
			self.timeline.triggerIn('keyframe_properties', None, (kf,))
			self.timeline.update(kf.keytitle)
			# Don't close the dialog, so other transitions can be modified.
		except Exception, e:
			import traceback, sys
			traceback.print_exc(file=sys.stdout)
			msg = 'Failed to save transition parameters'
			chimera.replyobj.error(msg)

	def Okay(self):
		self.Apply()
		self.Close()

	# set up triggers to catch 'kfbutton_select' and call update()

	def update(self, keytitle=None):
		'''Update the dialog to set keyframe transition properties.
		Property dialog drop downs are indexed by the keyframe's disptitle.'''
		optionmenu = self.optionmenu
		curselection = self.notebook.getcurselection()
		# Clear all the transition fields
		self.nframesEntry.delete(0, Tkinter.END)
		self.nframesEntry.insert(0, '')
		self.discreteFrameEntry.delete(0, Tkinter.END)
		self.discreteFrameEntry.insert(0, '')
		# If no keytitle argument, try to get it from the dialog
		if keytitle is None:
			disptitle = optionmenu.getvalue()
		else:
			disptitle = self.timeline.keyframes.getName_by_keytitle(keytitle)
		titles = self.timeline.keyframes.disptitles()
		if not titles:
			optionmenu.setitems([])
			return
		optionmenu.setitems(titles)
		if disptitle in titles:
			index = titles.index(disptitle)
		elif len(titles) > 1:
			index = 1
		else:
			index = 0
		# Update the combobox of keyframe titles
		try:
			# Get a keyframe and populate transition fields
			kf = self.timeline.keyframes.getKeyframe_by_keytitle(keytitle)
			self.keyframeIndex = kf.index
			optionmenu.setvalue(kf.disptitle)
			self.nframesEntry.insert(0, kf.frames)
			if isinstance(kf, Animate.Keyframe.Keyframe):
				self.discreteFrameEntry.insert(0, kf.trans.discreteFrame)
				self._initParametersPage(self.notebook)
			elif isinstance(kf, Animate.Action.Action):
				self.paramDict = kf.cmd.paramDict # for building widgets, not for values
				self.paramOrder = kf.cmd.paramOrder
				self._addParametersPage(self.notebook)

		except:
			self.keyframeIndex = None
		self.notebook.selectpage(curselection)

	def update_by_disptitle(self, disptitle):
		kf = self.timeline.keyframes.getKeyframe_by_disptitle(disptitle)
		self.update(kf.keytitle)


from OpenSave import SaveModal
class SaveStoryboardDialog(SaveModal):
	title = "Save Storyboard to Folder"

	def __init__(self, *args, **kw):
		SaveModal.__init__(self, clientPos='s', clientSticky="nsew",
					dirsOnly=True, *args, **kw)

	def fillInUI(self, parent):
		SaveModal.fillInUI(self, parent)
		from chimera.tkoptions import StringOption
		self.clientArea.columnconfigure(1, weight=1)
		self.titleOption = StringOption(self.clientArea,
						0, "Storyboard Title",
						"Animation Storyboard", None)

	def getTitle(self):
		return self.titleOption.get()
