from Tkinter import Frame
class PlaybackFrame(Frame):

	TriggerName = "new frame"
	Forward = "forward"
	Backward = "reverse"

	def __init__(self, parent, minFrame, maxFrame, callback, *args, **kw):
		self.minFrame = minFrame
		self.maxFrame = maxFrame
		self.lastFrame = minFrame
		self.callback = callback
		self.playbackHandler = None
		self.direction = self.Forward
		self.playbackDelay = 0.0
		self.countDown = -1
		Frame.__init__(self, parent, *args, **kw)
		self._makeUI()

	def _makeUI(self):
		from Tkinter import IntVar, Frame
		from Pmw import EntryField
		# current frame
		self.currentFrame = IntVar(self)
		self.currentFrame.set(self.minFrame)
		frameWidth = len(str(self.maxFrame))
		validateDict = {
			"validator": "numeric",
			"min": self.minFrame,
			"max": self.maxFrame,
		}
		self.frameEntry = EntryField(self,
					validate=validateDict,
					entry_justify="right",
					labelpos="w",
					label_text="Frame",
					command=self._frameCB,
					entry_textvariable=self.currentFrame,
					entry_width=frameWidth)
		self.frameEntry.pack(side="left")
		# playback buttons
		from Tkinter import Button, Checkbutton
		getIconButton(self, Button, "image_reverse.png", relief="flat",
				balloon="Play backwards",
				command=self.playReverse).pack(side="left")
		getIconButton(self, Button, "image_previous.png", relief="flat",
				balloon="Previous frame",
				command=self.prevFrame).pack(side="left")
		getIconButton(self, Button, "image_pause.png", relief="flat",
				balloon="Pause",
				command=self.pause).pack(side="left")
		getIconButton(self, Button, "image_next.png", relief="flat",
				balloon="Next frame",
				command=self.nextFrame).pack(side="left")
		getIconButton(self, Button, "image_play.png", relief="flat",
				balloon="Play",
				command=self.playForward).pack(side="left")
		self.loopVar = IntVar(self)
		self.loopVar.set(True)
		getIconButton(self, Checkbutton, "image_loop.png",
				balloon="Continuous loop",
				indicatoron=False,
				variable=self.loopVar).pack(side="left")
		# step size
		self.step = IntVar(self)
		self.step.set(1)
		self.stepEntry = EntryField(self,
					validate=validateDict,
					entry_justify="right",
					labelpos="w",
					label_text="    Step size:",
					command=self._stepCB,
					entry_textvariable=self.step,
					entry_width=frameWidth)
		self.stepEntry.pack(side="left")
		# playback speed
		from Tkinter import Frame, Label, Scale
		Label(self, text=" Playback speed:").pack(side="left")
		f = Frame(self, bd=1, bg="black")
		f.pack(side="left", fill="x")
		Label(f, text="slower").pack(side="left", fill="y")
		Label(f, text="faster").pack(side="right", fill="y")
		scale = Scale(f, from_=1.0, to_=0.0, resolution=0.01,
				showvalue=False, orient="horizontal",
				command=self._speedCB)
		scale.set(self.playbackDelay)
		scale.pack(side="left", fill="x")

	def _frameCB(self):
		#print "PlaybackFrame._frameCB"
		frame = self.currentFrame.get()
		try:
			self.setFrame(frame, force=True)
		except ValueError, e:
			from chimera import replyobj
			replyobj.error(str(e))

	def _stepCB(self):
		#print "PlaybackFrame._stepCB"
		pass

	def _speedCB(self, sp):
		#print "PlaybackFrame._speedCB"
		self.playbackDelay = float(sp)

	def prevFrame(self):
		#print "PlaybackFrame.prevFrame"
		frame = self.currentFrame.get() - self.step.get()
		if frame < self.minFrame:
			if not self.loopVar.get():
				self.pause()
				return
			frame = self.maxFrame
		self.setFrame(frame)

	def nextFrame(self):
		#print "PlaybackFrame.nextFrame"
		frame = self.currentFrame.get() + self.step.get()
		if frame > self.maxFrame:
			if not self.loopVar.get():
				self.pause()
				return
			frame = self.minFrame
		self.setFrame(frame)

	def pause(self):
		#print "PlaybackFrame.pause"
		self._stopPlayback()

	def playReverse(self):
		#print "PlaybackFrame.playReverse"
		self._startPlayback(self.Backward)

	def playForward(self):
		#print "PlaybackFrame.playForward"
		self.direction = 1
		self._startPlayback(self.Forward)

	def getFrame(self):
		# MovieDialog uses 1-based indexing, we use 0-based
		return self.currentFrame.get()

	def setFrame(self, frame, force=False):
		if frame < self.minFrame or frame > self.maxFrame:
			raise ValueError("frame out of range")
		if frame == self.currentFrame.get():
			if not force:
				return
		else:
			self.currentFrame.set(frame)
		if self.callback:
			self.callback(frame)
		self.lastFrame = frame

	def getStepSize(self):
		# MovieDialog uses 1-based indexing, we use 0-based
		return self.step.get()

	def setStepSize(self, size):
		# MovieDialog uses 1-based indexing, we use 0-based
		self.step.set(size)

	def cleanup(self):
		self._stopPlayback()

	#
	# Playback methods
	#
	def _startPlayback(self, direction):
		if (self.playbackHandler is not None
				and self.direction == direction):
			return
		self._setupPlayback(direction)
		if self.playbackHandler is not None:
			return
		import chimera
		self.playbackHandler = chimera.triggers.addHandler(
						self.TriggerName,
						self._updatePlayback, None)

	def _stopPlayback(self):
		if self.playbackHandler is None:
			return
		import chimera
		chimera.triggers.deleteHandler(self.TriggerName,
						self.playbackHandler)
		self.playbackHandler = None

	def _updatePlayback(self, trigger, myData, triggerData):
		if not self.playbackHandler:
			return
		if self.countDown > 0:
			self.countDown -= 1
			return
		if self.direction == self.Forward:
			self.nextFrame()
		else:
			self.prevFrame()
		self._setupPlayback(None)

	def _setupPlayback(self, direction):
		if direction is not None:
			self.direction = direction
		if not self.playbackDelay:
			self.countDown = -1
		else:
			from chimera.update import UPDATE_INTERVAL
			# Make max delay N seconds per frame
			maxDelay = 3 * (1000.0 / UPDATE_INTERVAL)
			sc = self.playbackDelay * self.playbackDelay
			self.countDown = int(sc * maxDelay)

def getIconButton(parent, buttonClass, filename, balloon=None, **kw):
	import os.path
	iconPath = os.path.join(os.path.dirname(__file__), "Icons", filename)
	from PIL import Image, ImageTk
	imtk = ImageTk.PhotoImage(Image.open(iconPath), master=parent)
	b = buttonClass(parent, image=imtk, **kw)
	b._image = imtk
	if balloon:
		from chimera import help
		help.register(b, balloon=balloon)
	return b
