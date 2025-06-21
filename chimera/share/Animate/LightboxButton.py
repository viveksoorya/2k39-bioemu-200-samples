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

import Animate
import Keyframes
import Scenes
import Transitions
import Icons

DEBUG = 0


# TODO: Inherit from Tkinter.Frame instead of object.
class Button(object):
	'A base class for scene and keyframe buttons'

	@property
	def keyframes(self):
		return Keyframes.keyframes

	@property
	def kfGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.kfGUI

	@property
	def scenes(self):
		return Scenes.scenes

	@property
	def transitions(self):
		return Transitions.transitions

	@property
	def scene(self):
		return getattr(self, '_scene', None)
	@scene.setter
	def scene(self, sc):
		'''shoe horning Cmds into the same rubric as scenes to support
		this inheritance scheme. Not an optimal design.'''
		assert isinstance(sc, Animate.Scene.Scene) \
			or isinstance(sc, Animate.Cmd.Cmd)
		self._scene = sc
	@scene.deleter
	def scene(self):
		if self.scene:
			del self._scene

	# A class variable to map a Chimera frame into GUI pixels.  This might
	# be used to zoom in or out on an animation timeline.  It's used in the
	# KeyframeButton class.

		# Set active/inactive background colors for frame widgets.
	frameRGBOff = "#%02x%02x%02x" % (125, 125, 125)
	frameRGBOn = "#%02x%02x%02x" % (200, 200, 200)

	def __init__(self, parent):
		'''Create a lightbox button.'''
		self.parent = parent
		# Create a frame for the label and button
		self.frame = Tkinter.Frame(parent,
			relief='flat',
			borderwidth=0,
			padx=0, pady=0)
		# Get the frame background color (used in the select property).
		self.background = self.frame.cget('background')
		# Not using pack here, using grid in the parent: Lightbox.update().
		#
		# Create a scene frame within the main frame
		# Each button has 5 columns and 4 rows; not all cols or rows are
		# used by descendants.

		# self.frame.grid_columnconfigure(0, weight=1)
#		self.sceneFrame = Tkinter.Frame(self.frame,
#			relief='flat',
#			borderwidth=1,
#			padx=0, pady=0)
#		self.sceneFrame.grid(row=0, column=0, sticky=Tkinter.NE)
		#

		# Fill in the scene frame
		self.sceneText = Tkinter.StringVar()
		self.sceneText.set(self.dispname)
		self.sceneLabel = Tkinter.Label(self.frame,
			textvariable=self.sceneText,
			anchor=Tkinter.CENTER,
			height=1,
			borderwidth=1,
			padx=1, pady=1)
		self.sceneLabel.grid(row=0, column=1, columnspan=3, sticky=Tkinter.EW)
		# Create sceneImage
		photo = PhotoImage(self.scene.img)
		self.photo = photo
		sceneImage = Tkinter.Label(self.frame,
			#image=self.photo,
			image=photo,
			anchor=Tkinter.NW,
			borderwidth=1,
			padx=1, pady=1)
		sceneImage.grid(row=1, column=1, columnspan=3, sticky=Tkinter.EW)
		sceneImage.bind('<Button-1>', self._b1PressCallback)
		sceneImage.bind('<ButtonRelease-1>', self._b1ReleaseCallback)
		self._b1Event = None
		self._b1Motion = None
		sceneImage.bind('<Control-Button-1>', self.toggle_select_cb)
		sceneImage.bind('<Shift-Button-1>', self.extend_select_cb)
		if chimera.tkgui.windowSystem == 'aqua':
			# Button 2 and 3 reversed due to Aqua Tk bug (8.5.2).
			sceneImage.bind('<Command-Button-1>', self.menuShow)
			sceneImage.bind('<Button-2>', self.menuShow)
		else:
			sceneImage.bind('<Button-3>', self.menuShow)
		self.sceneImage = sceneImage

		# self.frame.grid_rowconfigure(0, weight=1) # top row can resize
		self.frame.grid_columnconfigure(1, weight=0)
		self.frame.grid_columnconfigure(2, weight=0)
		self.frame.grid_columnconfigure(3, weight=0)
		self.frame.grid_columnconfigure(0, weight=2)
		self.frame.grid_columnconfigure(4, weight=2)

		# Add a popup context menu to the sceneImage, do not
		# associate it with the sceneImage to avoid problems
		# when the sceneImage is destroyed. Instead, get it
		# from the buttonDict via button.keytitle.
		self.menu = self.buttonMenu()

	def _b1PressCallback(self, event):
		self._b1Event = event
		self._b1Motion = self.sceneImage.bind('<B1-Motion>',
						self._b1MotionCallback)

	def _b1MotionCallback(self, event):
		self.sceneImage.unbind('<B1-Motion>', self._b1Motion)
		self._b1Motion = None
		self.dndStart(self._b1Event)
		self._b1Event = None

	def _b1ReleaseCallback(self, event):
		if self._b1Motion:
			# User did not drag button, so press it
			self.sceneImage.unbind('<B1-Motion>', self._b1Motion)
			self._b1Motion = None
			self._b1Event = None
			self.sceneImageCallback(event)

	def sceneImageCallback(self, event):
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyobj.warning(msg)
		return None
		# See LightboxScenes and LightboxKeyframes for examples
		# Should return a lambda function callback

	def sceneImageUpdate(self):
		'Update the display of the scene image'
		size = self.scene.imgSize
		before = str(self.scene.img)
		self.img = self.scene.img.resize(size)
		after = str(self.scene.img)

		self.photo = PhotoImage(self.scene.img)
		self.sceneImage.configure(image=self.photo)
		self.trans = 'reset'

	def buttonMenu(self):
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyobj.warning(msg)
		return None
		# See LightboxScenes and LightboxKeyframes for examples
		# Should return a Tkinter.Menu instance

	@property
	def dispname(self):
		return self._scene.dispname

	def destroy(self):
		'Remove a GUI-frame-button'
		del self.sceneText
		del self.photo
		del self.menu
		self.frame.destroy()

	def menuHide(self, event):
		# e.widget should be the menu created in self.buttonMenu()
		#assert e.widget is self.menu
		self.select(False)
		self.menu.unpost()

	def dndStart(self, Event):
		'This is invoked by InitiationObject to start the drag and drop process'
		# Create an object to be dragged
		dnd = SceneDND(self.scene, Event)
		#dnd.dragFrame.place(anchor=Tkinter.NW,
		#	x=Event.x_root,
		#	y=Event.y_root)
		# Initiate the drag-n-drop
		dnd.dndStart(Event)

	def menuShow(self, event):
		if event.widget is self.sceneImage:
			try:
#				self.select(True)
				self.menu.tk_popup(event.x_root, event.y_root)
			except Tkinter.TclError:
				pass
			# The code below was used to explore bug #9694, without success.
			#try:
			#	self.menu.focus()
			#	self.menu.update_idletasks()
			#	self.menu.post(event.x_root - 5, event.y_root - 5)
			#	# tk_popup is no better than post.
			#	#self.menu.tk_popup(event.x_root, event.y_root)
			#except Tkinter.TclError:
			#	import pdb; pdb.set_trace()
		return "break"

	@property
	def select(self):
		'select status of button'
		return getattr(self, '_select', None)
	@select.setter
	def select(self, selected=False):
		'set select status of button'
		self._select = selected


class SceneButton(Button):
	'A class for scene buttons'

	# Read some rating star icons
	#iconOff = PhotoImage(Icons.LoadImage('stars12_off.png'))
	#iconOnY = PhotoImage(Icons.LoadImage('stars12_onYellow.png'))
	iconOff = PhotoImage(Icons.LoadImage('stars12_onYellow.png'))
	iconOn = PhotoImage(Icons.LoadImage('stars12_onRed.png'))

	def __init__(self, parent, scene):
		self.scene = scene
		Button.__init__(self, parent)
		# Add balloon help to the sceneImage
		self.balloonhelp = Pmw.Balloon()
		help = self.scene.name + ':\n'
		help += '  left-click to restore display\n'
		#help += '  middle-click to drag scene to timeline\n'
		help += '  right-click for action menu'
		if self.scene.description:
			help += '\n\n' + self.scene.description
		self.balloonhelp.bind(self.sceneImage, help)
		#self.rating = 'property setter ignores this value'
		self._select = False	# property
		self.triggerInit()

	# Implement abstract method in Button
	def sceneImageCallback(self, event):
		'''show a scene'''
		geom = self.frame.grid_bbox()
		conf = self.frame.config()
		if event.widget is self.sceneImage:
			self.kfGUI.movie_stop()
			self.scenes.show(self.scene.name)
			self.scGUI.radio_select(self.scene.name)
			self.scGUI.properties_dialog_update(self.scene)

	# Implement abstract method in LightboxButton
	def buttonMenu(self):
		'Create a callback menu for buttons'
		#popup = Tkinter.Menu(self.sceneImage, tearoff=False)
		popup = Tkinter.Menu(None, tearoff=False)
		# popupHide = lambda:popup.unpost
		# popup.add_command(label='Cancel', command=popupHide)
		cb_add_keyframe = lambda: self.keyframes.append(self.scene.name)
		popup.add_command(label='Add to timeline', command=cb_add_keyframe)
		cb_scene_properties = lambda:self.scGUI.properties_activate(self.scene)
		popup.add_command(label='Properties', command=cb_scene_properties)

		popup.add_separator()
		cb_scene_update = lambda:self.scenes.update(self.scene.name,
			self.scene.description)
		popup.add_command(label='Update', command=cb_scene_update)
		cb_scene_remove = lambda:self.scenes.remove(self.scene.name)
		popup.add_command(label='Delete', command=cb_scene_remove)
		#
		# TODO: Enable this menu item below when keyframe time line is enabled
		#
		#cb_kf_append = (lambda: self.keyframes.append(self.name))
		#popup.add_command(label='Append to Timeline', command=cb_kf_append)
		return popup

	def destroy(self):
		'Remove a GUI-frame-button'
		self.triggerRelease()
		del self.rating
		del self.scene
		self.balloonhelp.unbind(self.sceneImage)
		self.balloonhelp.update_idletasks()
		del self.balloonhelp
		Button.destroy(self)

	@property
	def rating(self):
		return getattr(self, '_rating', None)
	@rating.setter
	def rating(self, value):
		'''Add rating icons below the button.
		Sets self._rating to a list of rating labels.
		'''
		if self.rating is None:
			self.scaleFrame.grid(row=1, column=1)
			ratingButtons = []
			for i in range(self.scene.ratingMax):
				if i < self.scene.rating:
					icon = self.iconOn
				else:
					icon = self.iconOff
				button = Tkinter.Label(self.scaleFrame, image=icon)
				button.grid(row=0, column=i)
				button.rating = i + 1
				button.bind('<Button-1>', self.ratingCB)
				help = 'rating: %d' % button.rating
				self.balloonhelp.bind(button, help)
				ratingButtons.append(button)
			self._rating = ratingButtons
	@rating.deleter
	def rating(self):
		return # ratings no longer shown
		ratingButtons = self.rating
		for button in ratingButtons:
			self.balloonhelp.unbind(button)

	def ratingCB(self, event):
		button = event.widget
		self.scene.rating = button.rating
		ratingButtons = self.rating
		for i in range(self.scene.ratingMax):
			index = i + 1
			icon = self.iconOff
			if index <= self.scene.rating:
				icon = self.iconOn
			button = ratingButtons[i]
			button.configure(image=icon)

	@property
	def scGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.scGUI

	@property
	def name(self):
		return self.scene.name

	@property
	def cmdGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.cmdGUI

	def select(self, selected=None):
		'set select status of button'
		if selected is None:
			return self._select
		self._select = selected
		tk_rgb = "#%02x%02x%02x" % (125, 125, 125)
		if selected:
			self.cmdGUI.unselect_all()
			self.sceneImage.configure(background=tk_rgb)
			self.sceneLabel.configure(background=tk_rgb)
		else:
			self.sceneImage.configure(background=self.background)
			self.sceneLabel.configure(background=self.background)

	def toggle_select_cb(self, event):
		if isinstance(self, SceneButton):
			self.scGUI.toggle_select(self.scene.name)

	def extend_select_cb(self, event):
		if isinstance(self, SceneButton):
			self.scGUI.extend_select(self.scene.name)

	@property
	def name(self):
		'A standardized name for scene buttons'
		return self.scene.name

	#
	# --- Triggers ---
	#

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'''
		A method to handle triggers
		- trigger and funcData is defined in self.triggerInit()
		'''
		if DEBUG:
			print 'SceneButton.triggerIn: trigger=', trigger
			print 'SceneButton.triggerIn: funcData=', funcData
			print 'SceneButton.triggerIn: trigData=', trigData
		#if trigger in ['scene_update', 'scene_invalid']:
		#	# Update the scene
		#	sceneName = trigData
		#	if sceneName == self.scene.name:
		#		self.photo = PhotoImage(self.scene.img)
		#		self.sceneImage.configure(image=self.photo)
		#if trigger == 'scene_remove':
		#	sceneName = trigData.name
		#	if sceneName == self.scene.name:
		#		self.destroy()

	def triggerInit(self):
		'register triggers'
		self.triggerHandlers = {}
		# Skipping scenes trigger handling here, doing it all in the
		# Scenes.py controller.
		#for trig in self.scenes.triggers:
		#	trigArgs = (trig, self.triggerIn, 'scenes')
		#	h = self.scenes.triggerset.addHandler(*trigArgs)
		#	self.triggerHandlers[trig] = h

	def triggerRelease(self):
		'deregister triggers'
		for trig in self.triggerHandlers:
			h = self.triggerHandlers[trig]
			self.scenes.triggerset.deleteHandler(trig, h)
			del self.triggerHandlers[trig]

	def verify(self):
		'A method to verify the attributes of a scene button'
		# For this validation to work, the scenes class must remove
		# a scene instance from it's entries before issuing a
		# 'scene_remove' trigger.
		if self.scene in self.scenes.entries:
			# The self.name property refers to self.scene.name (scene.name)
			self.sceneText.set(self.dispname)
			return True
		else:
			return False


class SceneDND(object):
	'A scene button for Tkdnd'

	def __init__(self, scene, event):
		self.scene = scene
		# Add a 'lightbox' for scenes and keyframes
		aniGUI = chimera.dialogs.find('Animation')
		self.parent = aniGUI.parent
		#Create an object to be dragged
		self.dialog = Tkinter.Toplevel(self.parent,
			borderwidth=2,
			relief=Tkinter.RAISED)
		self.dragFrame = Tkinter.Frame(self.dialog,
			borderwidth=2,
			padx=1, pady=1)
		self.dragLabel = Tkinter.Label(self.dragFrame,
			text=self.scene.name,
			height=1,
			borderwidth=2,
			padx=1, pady=1)
		self.dragLabel.pack(expand=1, fill=Tkinter.BOTH)
		# Create sceneImage
		self.dragPhoto = PhotoImage(self.scene.img)
		self.dragImage = Tkinter.Label(self.dragFrame,
			image=self.dragPhoto,
			borderwidth=2,
			padx=1, pady=1)
		self.dragImage.pack(expand=1, fill=Tkinter.BOTH)
		self.dragFrame.pack()
		#print 'SceneDND::__init__:', self.geometry
		#print 'SceneDND::__init__:', event.x, event.y
		#print 'SceneDND::__init__:', event.x_root, event.y_root
		self.dialog.wm_overrideredirect(1)
		self.dialog.wm_transient(self.parent)
		self.updateXY(event.x_root, event.y_root)
		# Remove the window manager decorations and raise the dialog
		self.dialog.tkraise()
		#print 'SceneDND::__init__:', scene.name, dir(event)

	def destroy(self):
		del self.scene
		self.dialog.destroy()

	def dndStart(self, event):
		'This is invoked by InitiationObject to start the drag and drop process'
		# determine the current x-coord
		mycoord = self.dialog.grid_location(event.x, event.y)
		mysize = self.dialog.size()
		mybbox = self.dialog.bbox()
		framesize = self.parent.size()
		framecoord = self.parent.grid_location(event.x, event.y)
		frame = self.parent.bbox()
		#Pass the object to be dragged and the event to Tkdnd
		import Tkdnd
		Tkdnd.dnd_start(self, event)

	def dnd_end(self, Target, event):
		self.destroy()

	@property
	def geometry(self):
		import re
		self.dialog.update_idletasks()
		geometry = self.dialog.geometry()
		m = re.match("(\d+)x(\d+)([-+]\d+)([-+]\d+)", geometry)
		if not m:
			raise ValueError("failed to parse geometry string")
		return map(int, m.groups())
	@geometry.setter
	def geometry(self, value):
		assert isinstance(value, list)
		assert len(value) == 4
		#self.dialog.update_idletasks()
		#self.dialog.overrideredirect(False)
		width, height, xoffset, yoffset = value
		g = "%dx%d+%d+%d" % (width, height, xoffset, yoffset)
		self.dialog.geometry(g)

	def hide(self):
		self.dialog.withdraw()

	def show(self):
		self.dialog.deiconify()

	def updateXY(self, x, y):
		# Add offset so that window does not appear directly below
		# mouse so that Tkdnd works properly
		self.dialog.geometry("+%d+%d" % (x + 1, y + 1))

class CmdButton(Button):
	'''this is a pallette icon with limited behavior. It represents a GUI
	component that copies to the timeline as an ActionButton. CmdButton
	is mostly like Button but does not have an associated scene.'''
	def __init__(self, parent, cmd):
		self.cmd = cmd
		self.img = Icons.LoadImage(cmd.img_file)
		if self.img.mode == "P":
			self.img = self.img.convert("RGBA")
#		self.scene = cmd # to keep Button._init__ happy
		Button.__init__(self, parent)
		self._select = False
		self.setImageSize()

	@property
	def scene(self):
		'to fool Button.___init__()'
		return self

	def toggle_select_cb(self, event):
		if isinstance(self, CmdButton):
			self.cmdGUI.toggle_select(self.name)

	def extend_select_cb(self, event):
		if isinstance(self, CmdButton):
			self.cmdGUI.extend_select(self.name)

	def buttonMenu(self):
		pass

	@property
	def dispname(self):
		return self.cmd.dispname

	def menuShow(self, event):
		return "break"

	@property
	def scGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.scGUI

	@property
	def cmdGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.cmdGUI

	@property
	def name(self):
		return self.cmd.name

	def destroy(self):
		'should be called from LightboxCmds, which will remove it from the list'
		self.scene.dest
		del self.scene
		del self.photo

	def select(self, selected=None):
		'set/get select status of button'
		if selected is None:
			return self._select
		self._select = selected
		tk_rgb = "#%02x%02x%02x" % (125, 125, 125)
		if selected:
			self.scGUI.unselect_all()
			self.sceneImage.configure(background=tk_rgb)
			self.sceneLabel.configure(background=tk_rgb)
		else:
			self.sceneImage.configure(background=self.background)
			self.sceneLabel.configure(background=self.background)

	def setImageSize(self):
		'''modify the size of the button image to the class image size.'''
		size = self.cmd.imgSize
		before = str(self.img)
		self.img = self.img.resize(size)
		after = str(self.img)
		self.photo = PhotoImage(self.img)
		self.sceneImage.configure(image=self.photo)

#	def triggerInit(self):
#		'register triggers'
#		self.triggerHandlers = {}

	def sceneImageCallback(self, event):
		'''show a scene'''
		if event.widget is self.sceneImage:
			self.cmdGUI.radio_select(self.name)

class AnimationButton(Button):
	'''Parent for KeyframeButton and Action Button encapsulating common
	behavior. Children choose whether to call this parent or the super parent
	__init__.'''
	def __init__(self, canvas, tags):
		'''"kf_ac" is either a Keyframe or an Action, then defined as a property
		in the child.
		
		Buttons are given IDs to ensure change operations are
		specific to the button. The ID must not conflict with a Canvas item
		number so use a string.'''
		self._select = False
		x = 0
		y = 15 # y = 5
		self._id = "ButtonID=%d" % (self.keyframes.new_id())
		self.tags = tags + [self._id]

		self.build_button()

		self.triggerInit()
		self.balloon = Pmw.Balloon(canvas)
		self.update_balloon()

	def build_button(self):
		'''encapsulate building the canvas elements of the button separate
		from the button so they can be resized if image size changes.'''
		# if not the first time, delete the old components
		if hasattr(self, 'txt'):
			self.canvas.delete(self.txt)
			self.canvas.delete(self.img)
			self.canvas.delete(self.buttonbg)
			self.canvas.delete(self.tl_ptr)
		x = 0
		y = 15 # y = 5
		# button name
		self.txt = self.canvas.create_text(x, y, text=self.disptitle,
			anchor=Tkinter.CENTER, tags=tuple([self.keytitle, 'keytitle'] + self.tags))
		(tx1, ty1, tx2, ty2) = self.canvas.bbox(self.txt)

		# button image and a box to go around it and the name
		self.img = self.canvas.create_image(x, ty2, image=self.photo,
			anchor=Tkinter.NW, tags=tuple([self.keytitle, 'image'] + self.tags))
		(ix1, iy1, ix2, iy2) = self.canvas.bbox(self.img)
		# center text on image
		self.canvas.move(self.txt, (ix2 - ix1) / 2, 0)
#		self.canvas.move(self.txt, (ix2 - ix1) / 2 - (tx2 - tx1) / 2, 0)
		(tx1, ty1, tx2, ty2) = self.canvas.bbox(self.txt)
		x1 = tx1 if tx1 < ix1 else ix1
		x2 = tx2 if tx2 > ix2 else ix2
		self.buttonbg = self.canvas.create_rectangle(x1, ty1, x2, iy2,
			outline='', fill='',
			tags=tuple([self.keytitle, 'textrect'] + ['fillit'] + self.tags))
		self.canvas.tag_raise(self.txt)
		self.canvas.tag_raise(self.img)

		# timeline pointer line for buttons; allow for line thickness to place along img
		(ix1, iy1, ix2, iy2) = self.canvas.bbox(self.img)
		tl = self.canvas.find_withtag('timeline')
		(tl1, tly1, tlx2, tly2) = self.canvas.bbox('timeline')
		#		(w, height) = self.scene.imgSize
		height = 48 # need a better derivation
		lthk = 3
		tlptrx1 = ix1 + 1
		tlptry1 = iy2
		tlptrx2 = tlptrx1
		tlptry2 = tlptry1 + (0.5 * height)
		self.tl_ptr = self.canvas.create_line(tlptrx1, tlptry1, tlptrx2, tly2,
			width=lthk, fill="red", tags=tuple([self.keytitle, 'TLptr'] + self.tags))
		self.intro_box = None
#		self.ht = iy2 - ty1 # overall height of this button, without the ptr line
		# move to the proper place on the timeline
		coords = self.canvas.coords(self.tl_ptr)
		self.canvas.move(self.keytitle, -coords[0], 0)
		self.canvas.move(self.keytitle,
			(self.keyframe.end_frame + self.kfGUI.tl_start) * self.kfGUI.PixelsPerFrame, 0)

		if chimera.tkgui.windowSystem == 'aqua':
			# Button 2 and 3 reversed due to Aqua Tk bug (8.5.2).
			self.canvas.tag_bind(self.img, '<Command-Button-1>', self.kfGUI.menuDown)
			self.canvas.tag_bind(self.img, '<Button-2>', self.kfGUI.menuDown)
		else:
			self.canvas.tag_bind(self.img, "<3>", self.kfGUI.menuDown)


	def change_title(self, newtitle):
		'''change the button's displayed title.'''
		self.canvas.itemconfig(self.txt, text=newtitle)
		(ix1, iy1, ix2, iy2) = self.canvas.bbox(self.img)
		(tx1, ty1, tx2, ty2) = self.canvas.bbox(self.txt)
		self.canvas.delete(self.buttonbg)
		x1 = tx1 if tx1 < ix1 else ix1
		x2 = tx2 if tx2 > ix2 else ix2
		self.buttonbg = self.canvas.create_rectangle(x1, ty1, x2, iy2,
			outline='', fill='',
			tags=tuple([self.keytitle, 'textrect'] + ['fillit'] + self.tags))
		self.canvas.tag_raise(self.txt)
		self.canvas.tag_raise(self.img)


	def destroy(self):
		self.balloon.tagunbind(self.canvas, self.img)
		del self.balloon
		self.canvas.delete(self.txt)
		self.canvas.delete(self.img)
		self.canvas.delete(self.buttonbg)
		self.canvas.delete(self.tl_ptr)
		if self.intro_box:
			self.canvas.delete(self.intro_box)
		del self.photo

	@property
	def disptitle(self):
		if self.kf_ac:
			return self.kf_ac.disptitle
		return None

	@property
	def keytitle(self):
		if self.kf_ac:
			return self.kf_ac.keytitle
		return None

	@property
	def index(self):
		return self.kf_ac.index

	@property
	def keyframe(self):
		'to be compatible for lightboxkeyframes'
		return self.kf_ac

	@property
	def cmdGUI(self):
		aniGUI = chimera.dialogs.find('Animation')
		return aniGUI.cmdGUI

	@property
	def name(self):
		if self.kf_ac:
			return self.kf_ac.name
		else:
			return None

	def ripple_move(self, state):
		'''When state is true, this button is being moved via shift-drag. It is
		not being selected.'''
		keytitle = self.keytitle
		if state:
			for item in self.canvas.find_withtag(keytitle):
				self.canvas.addtag_withtag('ripple_move', item)
		if state == False:
			for item in self.canvas.find_withtag(keytitle):
				self.canvas.dtag(item, 'ripple_move')

	def select(self, selected=None):
		'set select status of button'
		if selected is None:
			return self._select
		self._select = selected
		keytitle = self.keytitle
		if selected:
			tk_rgb = "#%02x%02x%02x" % (125, 125, 125)
			self.canvas.itemconfig(self.buttonbg, fill=tk_rgb)
			for item in self.canvas.find_withtag(keytitle):
				self.canvas.addtag_withtag('selected', item)
		else:
			self.canvas.itemconfig(self.buttonbg, fill='')
			for item in self.canvas.find_withtag(keytitle):
				self.canvas.dtag(item, 'selected')


	def sceneImageUpdate(self):
		'Update the display of the scene image'
		self.photo = PhotoImage(self.scene.img)
		self.build_button()
		self.trans = 'reset'

	def show_intro_box(self):
		'''if this button is the first keyframe and has frames > 1, show a box'''
		if self.keyframe.index != 0:
			self.canvas.delete(self.intro_box)
			return
		frames = self.keyframe.frames
		self.canvas.delete(self.intro_box)
		if frames <= 1:
			self.intro_box = None
			return

		# a box to be used in case this button is first and has frames > 1
		(bx1, by1, bx2, by2) = self.canvas.bbox(self.img)
		(tlx1, tly1, tlx2, tly2) = self.canvas.bbox(self.tl_ptr)
		wd = frames * self.kfGUI.PixelsPerFrame
		tk_rgb = "#%02x%02x%02x" % (150, 150, 150)
		self.intro_box = self.canvas.create_rectangle(bx1 - wd, by1, bx1, tly2,
			outline='', fill=tk_rgb,
			tags=tuple([self.keytitle, 'intro_box'] + ['fillit'] + self.tags))


	def triggerInit(self):
		'register triggers'
		self.triggerHandlers = {}
		self.triggerset = chimera.triggerSet.TriggerSet()
#		self.triggers = ['keyframe_move']
#		for trig in self.triggers:
#			self.triggerset.addTrigger(trig, self.triggerTracking)
#			h = self.triggerset.addHandler(trig, self.triggerIn, None)
#			self.triggerHandlers[trig] = h

#
#	def triggerTracking(self, trigger, *args):
#		if DEBUG:
#			h = self.triggerset.triggerHandlers(trigger)
#			print 'AnimationButton.triggerTracking: %s = \t %s\n' % (trigger, repr(h))

	def verify(self):
		'A method to verify the name and index attributes of a keyframe button'
		# For this validation to work, the keyframes class must remove
		# a keyframe or action instance from it's entries before issuing a
		# 'keyframe_remove' trigger.
		if self.kf_ac in self.keyframes.entries:
			return True
		else:
			return False

	def update_balloon(self):
		# abstract method
		chimera.replyobj.warning("override abstract method in child class.")

class KeyframeButton(AnimationButton):
	'A class for scene buttons'
#	UP = 0
#	DOWN = 1

	def __init__(self, canvas, keyframe, tags):
		'''tags is a list which is used to specify certain things about this
		button which others may want to know as well as group the buttons.'''

		''' The button consists of name
		text in front of a borderless rectangle (used for selecting). Below is
		the image. Below that is a timeline pointer. All components have a
		tag identifying them by the keytitle. The keytitle is tied to the scene's
		name.
		The button keeps track of which frame on the timeline its pointer is on.
		'''
		'''make a button out of parts, all with the same tag.
		Name is a list which must be converted to a tuple, adding more tags here.'''

		self.kf_ac = keyframe
		self.canvas = canvas
		photo = PhotoImage(self.keyframe.scene.img)
		self.photo = photo
		AnimationButton.__init__(self, canvas, tags)


#
#	def button_up(self):
#		'raise this button the timeline'
#		if self.tl_state == self.UP:
#			return
#		self.tl_state = self.UP
#		self.canvas.move(self.keytitle, 0, -self.ht)
#
#	def button_down(self):
#		'lower this button on the timeline'
#		if self.tl_state == self.DOWN:
#			return
#		self.tl_state = self.DOWN
#		self.canvas.move(self.keytitle, 0, self.ht)

	def destroy(self):
#		'Remove a GUI-frame-button'
		AnimationButton.destroy(self)
		# should this be destroyed at this time?
		self.triggerRelease()


	def dnd_accept(self, Source, event):
		#Tkdnd is asking us if we want to tell it about a TargetObject.
		#print "KeyframeButton::dnd_accept"
		return self.dnd_widget
	def dnd_enter(self, Source, event):
		#This is called when the mouse pointer goes from outside the
		#Target Widget to inside the Target Widget.
		#print "KeyframeButton::dnd_enter"
		self.savedCursor = event.widget["cursor"] or ""
		event.widget.config(cursor="dotbox")
		Source.updateXY(event.x_root, event.y_root)
	def dnd_leave(self, Source, event):
		#This is called when the mouse pointer goes from inside
		#to outside the Target Widget.
		#print "KeyframeButton::dnd_leave"
		event.widget.config(cursor=self.savedCursor)
		return
	def dnd_motion(self, Source, event):
		#This is called when the mouse pointer moves within the TargetWidget.
		#p = self.dnd_widget.grid_location(event.x, event.y)
		#print "KeyframeButton::dnd_motion; grid position = %s" % repr(p)
		Source.updateXY(event.x_root, event.y_root)
	def dnd_commit(self, Source, event):
		#This is called if the DraggedObject is being dropped on us
		#print "KeyframeButton::dnd_commit; Object received= %s" % repr(Source)
		#p = self.dnd_widget.grid_location(event.x, event.y)
		#print "KeyframeButton::dnd_commit; grid position = %s" % repr(p)
		#
		# TODO: Dubug why the insertion creates a mess in the GUI indexing.
		#
		#
		i = self.index + 1
		self.keyframes.insert(Source.scene.name, i)
		#return

#

	@property
	def keyframe(self):
		return self.kf_ac

	@property
	def scene(self):
		if self.keyframe:
			return self.keyframe.scene
		else:
			return None
#
#	def sceneImageUpdate(self):
#		'Update the display of the scene image'
#		self.photo = PhotoImage(self.keyframe.scene.img)
#		self.canvas.itemconfig(self.img, image=self.photo)
#		self.trans = 'reset'

#	# Implement abstract method in Button
#	def sceneImageCallback(self, event):
#		'''show a keyframe'''
#		if event.widget is self.sceneImage:
#			self.keyframes.show(self.keyframe.name, self.keyframe.index)


#
#	def show_insert_ptr(self):
#		self.canvas.itemconfig(self.insert_ptr, state=Tkinter.NORMAL)
#
#	def hide_insert_ptr(self):
#		self.canvas.itemconfig(self.insert_ptr, state=Tkinter.HIDDEN)


	@property
	def trans(self):
		'''A keyframe transition: the assigned value must be a dict
		with keys named 'frames', 'mode', and 'properties'.
		'''
		try:
			tr = getattr(self, '_trans', None)
			assert tr is self.keyframe.trans
		except:
			self.trans = 'reset'
			tr = getattr(self, '_trans', None)
		return tr

	@trans.setter
	def trans(self, value):
		# Ignore value (this is not the place to set transition parameters).
		# Only allow this property to be set once and for all.  If a keyframe
		# index changes, this property will track the keyframe/transition
		# instance anyway.
		tr = getattr(self, '_trans', None)
		if tr:
			del self.trans
		self._trans = self.keyframe.trans
		self.transHandlers('add')

	@trans.deleter
	def trans(self):
		tr = getattr(self, '_trans', None)
		if tr:
			self.transHandlers('delete')
			del self._trans

	def transHandlers(self, action):
		triggers = ['transition_started', 'transition_complete',
			'transition_discreteFrame', 'transition_frames']
		tr = self.trans
		if action == 'add':
			self._transTriggerHandlers = {}
			for trigName in triggers:
				trigArgs = (trigName, self.triggerIn, self.name)
				h = tr.triggerset.addHandler(*trigArgs)
				self._transTriggerHandlers[trigName] = h
		elif action == 'delete':
			for trigName in triggers:
				h = self._transTriggerHandlers[trigName]
				tr.triggerset.deleteHandler(trigName, h)
				del self._transTriggerHandlers[trigName]
			del self._transTriggerHandlers

	def transFrameHandler(self, action):
		if action == 'add':
			# Register the transition frame trigger
			trigName = 'transition_frame'
			trigArgs = (trigName, self.triggerIn, self.keytitle)
			h = self.trans.triggerset.addHandler(*trigArgs)
			self._transTriggerHandlers[trigName] = h
		if action == 'delete':
			# De-register from the transition frame trigger
			trigName = 'transition_frame'
			h = self._transTriggerHandlers[trigName]
			self.trans.triggerset.deleteHandler(trigName, h)
			del self._transTriggerHandlers[trigName]

	#
	# --- Triggers ---
	#

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'''
		A method to handle triggers
		- trigger and funcData is defined in self.triggerInit()
		'''
		if DEBUG:
			print 'KeyframeButton.triggerIn: trigger=', trigger
			print 'KeyframeButton.triggerIn: funcData=', funcData
			print 'KeyframeButton.triggerIn: trigData=', trigData
		if trigger == 'transition_frame':
			transDict = trigData
			frameCount = transDict['frameCount']
			# self.selectFrameLabels(frameCount)
		if trigger == 'transition_started':
			self.transFrameHandler('add')
		if trigger == 'transition_complete':
			# Clear all the time-line indicator selections
			# self.selectFrameLabels()
			self.transFrameHandler('delete')
		#
		# Let LightboxKeyframes manage the button
		# (i.e., respond to keyframes triggers).
		#
		if trigger == 'keyframe_move':
			(kf, delta) = trigData[0]
			# move the button
			self.canvas.move(self._id, delta * self.kfGUI.PixelsPerFrame, 0)
		#if trigger == 'keyframe_invalid':
		#	# Update the scene image
		#	self.sceneImageUpdate()
		#if trigger == 'keyframe_remove':
		#	self.destroy()


	def triggerRelease(self):
		'deregister keyframe triggers'
		for trig in self.triggerHandlers:
			h = self.triggerHandlers[trig]
			self.keyframes.triggerset.deleteHandler(trig, h)
			del self.triggerHandlers[trig]

	def update_balloon(self):
		self.balloon.tagunbind(self.canvas, self.img)
		msg = "%s, %d frames" % (self.disptitle, self.keyframe.frames)
		self.balloon.tagbind(self.canvas, self.img, msg)



class ActionButton(AnimationButton):
	'''A class for action buttons in the LightboxKeyframe GUI, similar to
	KeyframeButtons.'''
	def __init__(self, canvas, action, tags):
		'''tags is a list which is used to specify certain things about this
		button which others may want to know as well as group the buttons.'''

		''' The button consists of name
		text in front of a borderless rectangle (used for selecting). Below is
		the image. Below that is a timeline pointer. All components have a
		tag identifying them by the keytitle. The keytitle is tied to the scene's
		name.
		The button keeps track of which frame on the timeline its pointer is on.
		'''
		'''make a button out of parts, all with the same tag.
		Name is a list which must be converted to a tuple, adding more tags here.'''

		self.kf_ac = action
		self.cmd = action.cmd
		self.canvas = canvas
		photo = PhotoImage(self.scene.img)
		self.photo = photo
		AnimationButton.__init__(self, canvas, tags)

	def toggle_select_cb(self, event):
		pass
#		if isinstance(self, ActionButton):
#			self.cmdGUI.toggle_select(self.name)

	def extend_select_cb(self, event):
		pass
#		if isinstance(self, ActionButton):
#			self.cmdGUI.extend_select(self.name)

	def buttonMenu(self):
		pass

	@property
	def action(self):
		return self.kf_ac

	@property
	def scene(self):
		'to enable Button to find scene.img'
		return self.cmdGUI.buttonDict[self.name]

	def update_balloon(self):
		self.balloon.tagunbind(self.canvas, self.img)
		msg = "%s: %d frames; %s" % (self.name, self.keyframe.frames,
			self.cmd.balloon_msg())
		self.balloon.tagbind(self.canvas, self.img, msg)


##	#
	# --- Triggers ---
	#

#	def triggerIn(self, trigger=None, funcData=None, trigData=None):
#		'''
#		A method to handle triggers
#		- trigger and funcData is defined in self.triggerInit()
#		'''
#		if DEBUG:
#			print 'SceneButton.triggerIn: trigger=', trigger
#			print 'SceneButton.triggerIn: funcData=', funcData
#			print 'SceneButton.triggerIn: trigData=', trigData
#		if trigger == 'keyframe_move':
#			delta = trigData
#			# move the button
#			self.canvas.move(self._id, delta, 0)




