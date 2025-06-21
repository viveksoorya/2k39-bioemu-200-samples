# The update interval is how often we ask the viewer to poll for changes
# (to models, potentially other stuff) that could cause a redisplay.  If
# such a condition exists, a redisplay is requested, and the next time
# the event loop is idle, the redisplay happens.  Ideally, this number
# would be related to the screen refresh frequency.
#
# Note: in practice, we will never achieve the given update rate as the
# time to update the state via the trigger mechanism is not accounted for.
# See chimera gnats bug XXX for more details.

from __future__ import with_statement
from contextlib import contextmanager
import chimera

MAX_FRAME_RATE = 60		# frames per second
UPDATE_INTERVAL	= 16		# Milliseconds between graphics updates.
MIN_EVENT_TIME = 1		# Minumum input event processing time per
				#  update interval in milliseconds.

_frameNumber = 0
_inFrameUpdate = False
_frameUpdateStarted = False
_needRedisplay = {}
_blockFUStack = []
inTriggerProcessing = 0

def setMaximumFrameRate(fps):

	msec = max(1, int(1000.0/fps))
	global MAX_FRAME_RATE, UPDATE_INTERVAL, MIN_EVENT_TIME
	MAX_FRAME_RATE = fps
	UPDATE_INTERVAL = msec
	MIN_EVENT_TIME = int(msec/10)
	if not chimera.nogui:
		from chimera.tkgui import windowSystem
		if windowSystem == 'aqua':
			# User interface fails to respond with high GPU use
			# without this.
			MIN_EVENT_TIME = int(msec/5)

setMaximumFrameRate(MAX_FRAME_RATE)

def startFrameUpdate(app):
	global _frameUpdateStarted
	if _frameUpdateStarted:
		return
	_frameUpdateStarted = True
	app.after(UPDATE_INTERVAL, lambda a=app: _frameUpdateLoop(app=a))

@contextmanager
def blockFrameUpdates(forChanges=False):
	global _inFrameUpdate, inTriggerProcessing
	_blockFUStack.append(_inFrameUpdate)
	_inFrameUpdate = True
	if forChanges:
		inTriggerProcessing += 1
	yield
	_inFrameUpdate = _blockFUStack.pop()
	if forChanges:
		inTriggerProcessing -= 1

def _frameUpdateLoop(app):
	"""Do a frame update and schedule a timer for the next frame update."""
	global _inFrameUpdate
	if _inFrameUpdate:
		# Frame update has been blocked with blockFrameUpdates().
		app.after(UPDATE_INTERVAL,
			  lambda a=app: _frameUpdateLoop(app=a))
		return
	import time
	t0 = time.time()
	_frameUpdate(app)
	t1 = time.time()
	frame_time = (t1 - t0) * 1000	# milliseconds
	min_delay = MIN_EVENT_TIME * max(1,int(frame_time/UPDATE_INTERVAL))
	delay = max(min_delay, int(UPDATE_INTERVAL - frame_time))
	app.after(delay, lambda a=app: _frameUpdateLoop(app=a))

def _frameUpdate(app):
	global _inFrameUpdate
	_inFrameUpdate = True
	global _frameNumber
	chimera.triggers.activateTrigger('new frame', _frameNumber)
	chimera.viewer.checkInitialView()
	checkForChanges()
	while _needRedisplay:
		v, dummy = _needRedisplay.popitem()
		v.displayCB(None)
	chimera.triggers.activateTrigger('post-frame', _frameNumber)
	# on Aqua, pressing a button seems to not immediately call the button
	# callback, but instead do it via an idle callback.  Consequently,
	# trying to pause trajectory playback when the redraw takes more than
	# a thirtieth of a second shows the button depressing without the
	# trajectory ever stopping.  The below event processing fixes that.
	import _tkinter as tk
	while tk.dooneevent(tk.IDLE_EVENTS|tk.DONT_WAIT):
		continue
	_frameNumber += 1
	_inFrameUpdate = False

def checkForChanges():
	"""check and propagate chimera data changes

	This is called once per frame and whenever otherwise needed.
	"""
	from chimera import TimeIt
	with blockFrameUpdates(forChanges=True):
		tm7 = TimeIt('checkForChanges()', 0.01)
		tm0 = TimeIt("activateTrigger('check for changes')", 0.01)
		chimera.triggers.activateTrigger('check for changes', None)
		tm0.done()
		track = chimera.TrackChanges.get()
		tm1 = TimeIt('track.check()', 0.01)
		names = track.check()
		tm1.done()
		allChanges = []
		selChanges = None	# TODO: remove if selections move to C++
		for n in names:
			name = n.split('.')[-1]
			# Viewer always needed below.
			# Model is needed for sloppy extensions that
			# don't destroy() their temporary models.
			if (name not in ('Viewer', 'Model')
			and not chimera.triggers.hasHandlers(name)):
				continue
			if name == 'Selectable':
				selChanges = track.changes(n)
				continue
			allChanges.append((name, track.changes(n)))
		tm2 = TimeIt('track.clear()', 0.01)
		track.clear()
		tm2.done()
		if selChanges:
			tm3 = TimeIt("activateTrigger('Selectable')", 0.01)
			chimera.triggers.activateTrigger('Selectable',
								selChanges)
			tm3.done()

		for name, changes in allChanges:
			tm4 = TimeIt('activateTrigger(%s)' % name, 0.01)
			chimera.triggers.activateTrigger(name, changes)
			tm4.done()
		if selChanges:
			allChanges = [('Selectable', selChanges)] + allChanges
		tm5 = TimeIt("activateTrigger('monitor changes')", 0.01)
		chimera.triggers.activateTrigger('monitor changes', allChanges)
		tm5.done()

		tm6 = TimeIt('need redisplay', 0.01)
		changes = [c for n, c in allChanges if n == 'Viewer']
		if changes:
			modified = changes[0].created | changes[0].modified
			if modified:
				if chimera.nogui:
					for v in modified:
						v.postRedisplay()
				else:
					global _needRedisplay
					for v in modified:
						_needRedisplay[v] = True
		tm6.done()

		cs = ', '.join(['%s %d %d %d' % (n, len(c.created), len(c.modified), len(c.deleted)) for n,c in allChanges])
		ss = 'sel %d %d %d' % (len(selChanges.created),len(selChanges.modified),len(selChanges.deleted)) if selChanges else 'sel None'
		tm7.message += ' %s %s' % (ss, cs)
		tm7.done()

def withoutChecks(func):
	# This was designed for IDLE, so a python command could be run
	# without triggers happening during the command
	with blockFrameUpdates():
		func()

_quitRequested = False
def quitCB(*args):
	global _quitRequested
	_quitRequested = True

_waitHandler = None
def wait(waiting, app):
	global _inFrameUpdate
	if _inFrameUpdate:
		return
	if not app:
		global _frameNumber
		while waiting():
			chimera.triggers.activateTrigger('new frame',
								_frameNumber)
			checkForChanges()
			chimera.triggers.activateTrigger('post-frame',
								_frameNumber)
			_frameNumber += 1
		return
	startFrameUpdate(app)
	global _waitHandler
	if _waitHandler is None:
		from chimera import APPQUIT
		_waitHandler = chimera.triggers.addHandler(
							APPQUIT, quitCB, None)
	app.viewer.setCursor('wait')
	changesActive = True
	while waiting() and not _quitRequested:
		app.tk.dooneevent()
		# TODO: activate a 'new frame' trigger so that waiting() will
		# see a decrement in param['frames'] by Midas._wait().
		#_frameUpdate(app)
	app.viewer.setCursor(None)
	if _quitRequested:
		from chimera import ChimeraSystemExit
		raise ChimeraSystemExit, 0

#
# Process only events for a specific widget.
# This is used to detect clicks on halt buttons without handling other events.
#
def processWidgetEvents(w, maxEvents = 100):
	import _tkinter as tk
	from _chimera import restrictEventProcessing
	restrictEventProcessing(w.winfo_id())
	try:
		for i in range(maxEvents):
			if not tk.dooneevent(tk.WINDOW_EVENTS|tk.DONT_WAIT):
				break
	finally:
		restrictEventProcessing(0)
