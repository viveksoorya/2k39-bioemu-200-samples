# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

# -----------------------------------------------------------------------------
# Show Python integrated development environment (IDLE) window.
#
# Copied this stuff from IDLE PyShell main() leaving out commandline
# argument parsing.
#
# I also commented out two lines in IDLE 0.5 PyShell.py that set
# Tkinter._default_root to None since this causes creation of some
# Chimera top level windows to fail.
#
# I also commented out a line from IDLE 0.5 FileList.py that calls
# Tkinter quit() when last IDLE window is closed.
#
# Sent email to idle-dev@python.org suggesting fixes for these problems.
#
# ----------------------------------------------------------------------------
# UPDATE 1/05
#
# In the process of updating to Python 2.4, we are now
# using the version of Idle that comes bundled with Python, as opposed to
# keeping our own copy of Idle in chimera/share/Idle/idle8
#
# The first comment from above is no longer valid. We now save a reference
# to Tkinter._default_root, call PyShell.begin (which sets _default_root to
# None), then restore the ref.
#
# The second comment is also not exactly true, because we don't have easy
# access to that FileList.py file any more; it is in the python/lib
# directory, not in share/Idle/idle8.  So I've subclassed the PyShellFileList
# class below as noQuitPyShellFileList, overrode the offending function, and
# commented out the appropriate code.
#
# In addition, the move to the native Idle required several more changes
# in the code:
#
# (1) Instead of using a plain-old-Toplevel window to house the new
#     interpreter window, the new Idle uses a 'ListedToplevel' window, which
#     attempts to call self.quit() when it exits, which would quit Chimera.
#     I've subclassed this class, as a 'noQuitListedToplevel' with that code
#     commented out (this was a similar problem as occurred in FileList.py,
#     described) above
#
# (2) I also needed to add a couple of global variables to PyShell
#     ('use_subprocess') and also define sys.ps1, which are normally defined
#     at the top level in the PyShell module
#

import os
import Tkinter

## need to figure out how to do configuration
## with new scheme...
#IdleConf.load(os.path.join(os.path.dirname(__file__), 'idle8'))

# defer importing Pyshell until IdleConf is loaded

from idlelib import PyShell, WindowList

## keep a reference to the ListedToplevel class
origListedToplevel = WindowList.ListedToplevel

## define a subclass of the 'orig' ListedToplevel class
class noQuitListedToplevel(origListedToplevel):
	def __init__(self, *args, **kw):
		## call the __init__ on the 'orig' class, not
		## WindowList.Toplevel (which will have been assigned
		## the 'noQuit...' class by the time this
		## code is called. What ?!?
		origListedToplevel.__init__(self, *args, **kw)
		self.loopDepth = 0
		from chimera.baseDialog import triggers, TOOL_DISPLAY_CHANGE
		triggers.activateTrigger(TOOL_DISPLAY_CHANGE, (self, True))

	raTitle = "IDLE"
	enter = origListedToplevel.wakeup
	def destroy(self):
		origListedToplevel.destroy(self)
		from chimera.baseDialog import triggers, TOOL_DISPLAY_CHANGE
		triggers.activateTrigger(TOOL_DISPLAY_CHANGE, (self, False))

	def mainloop(self):
		self.loopDepth += 1
		origListedToplevel.mainloop(self)

	def quit(self):
		if self.loopDepth > 0:
			origListedToplevel.quit(self)
			self.loopDepth -= 1

## make sure that WindowList will use the ListedToplevel that won't
## quit out of Chimera!
WindowList.ListedToplevel = noQuitListedToplevel

## need to define this so Idle will run. *Don't* execute Idle
## commands in a Python subprocess.
PyShell.use_subprocess = False

## Provide Reply object to route errors/warning/etc. to dialogs
import sys
from chimera import replyobj, preferences
class IDLEReply:
	"""Reply object for IDLE

	If any of the GUI replies go to a dialog, keep that behavoir,
	otherwise send to IDLE's stdout and stderr.
	"""

	def __init__(self, stdout, stderr):
		self._delegate = replyobj.currentReply()
		self.encoding = self._delegate.encoding
		self.softspace = self._delegate.softspace
		self.stdout = stdout
		self.stderr = stderr

	def write(self, s):
		"""output string."""
		if isinstance(s, unicode):
			s = s.encode(self.stdout.encoding, replyobj._ENCODE_ERRORS)
		elif sys.stdout.encoding.lower() != 'utf-8':
			s.decode('utf-8').encode(sys.stdout.encoding,
							replyobj._ENCODE_ERRORS)
		self.stdout.write(s)

	def flush(self):
		self.stdout.flush()

	def clear(self):
		self.stdout.flush()

	def message(self, s):
		if isinstance(s, unicode):
			s = s.encode(self.stdout.encoding, replyobj._ENCODE_ERRORS)
		elif sys.stdout.encoding.lower() != 'utf-8':
			s.decode('utf-8').encode(sys.stdout.encoding,
							replyobj._ENCODE_ERRORS)
		print >> self.stdout, s

	def command(self, s):
		if preferences.get(replyobj.REPLY_PREFERENCES, replyobj.COMMAND) == replyobj.DisplayDialog:
			self._delegate.command(s)
			return
		if isinstance(s, unicode):
			s = s.encode(self.stdout.encoding, replyobj._ENCODE_ERRORS)
		elif sys.stdout.encoding.lower() != 'utf-8':
			s.decode('utf-8').encode(sys.stdout.encoding,
							replyobj._ENCODE_ERRORS)
		print >> self.stdout, s

	def status(self, s, **kw):
		self._delegate.status(s, **kw)

	def info(self, s):
		if isinstance(s, unicode):
			s = s.encode(self.stdout.encoding, replyobj._ENCODE_ERRORS)
		elif sys.stdout.encoding.lower() != 'utf-8':
			s.decode('utf-8').encode(sys.stdout.encoding,
							replyobj._ENCODE_ERRORS)
		print >> self.stdout, s

	def warning(self, s):
		if preferences.get(replyobj.REPLY_PREFERENCES, replyobj.WARNING) == replyobj.DisplayDialog:
			self._delegate.warning(s)
			return
		if isinstance(s, unicode):
			s = s.encode(self.stderr.encoding, replyobj._ENCODE_ERRORS)
		elif sys.stderr.encoding.lower() != 'utf-8':
			s.decode('utf-8').encode(sys.stderr.encoding,
							replyobj._ENCODE_ERRORS)
		print >> self.stderr, s

	def error(self, s):
		if preferences.get(replyobj.REPLY_PREFERENCES, replyobj.ERROR) == replyobj.DisplayDialog:
			self._delegate.error(s)
			return
		if isinstance(s, unicode):
			s = s.encode(self.stderr.encoding, replyobj._ENCODE_ERRORS)
		elif sys.stderr.encoding.lower() != 'utf-8':
			s.decode('utf-8').encode(sys.stderr.encoding,
							replyobj._ENCODE_ERRORS)
		print >> self.stderr, s

class ChimeraPyShell(PyShell.PyShell):
	# overload __init__ and __del__ to grab and restore output/error
	# redirection within the context of Chimera
	def __init__(self, *args, **kw):
		from chimera.replyobj import pushReply
		PyShell.PyShell.__init__(self, *args, **kw)
		self.__replyState = pushReply(IDLEReply(self.stdout, self.stderr))
		# prevent output window from calling update rather than update_idletask;
		# a full update causes things to hang, e.g. open any tool (Model Panel
		# for instance) and then IDLE, then click on a Rapid Access entry --
		# no drawing of the structure until you close the other tool.
		self.text.update = self.text.update_idletasks

	def begin(self):
		try:
			import sys
			sys.ps1
		except AttributeError:
			sys.ps1 = ">>> "
		## save a reference to _default_root, because
		## PyShell.begin will set this to None
		root = Tkinter._default_root
		PyShell.PyShell.begin(self)
		## restore Tkinter._default_root
		Tkinter._default_root = root
		self.interp.runsource('import chimera')
		self.write('import chimera\n')
		self.showprompt()
		return True

	def runit(self):
		from chimera import update
		update.withoutChecks(lambda s=self: PyShell.PyShell.runit(s))

	def close(self, *args, **kw):
		from chimera.replyobj import popReply
		ret = PyShell.PyShell.close(self, *args, **kw)
		popReply(self.__replyState)
		return ret


class noQuitPyShellFileList(PyShell.PyShellFileList):

	def unregister_maybe_terminate(self, edit):
		## Code copied from idlelib/FileList.py
		## Commented out code below, so Chimera won't
		## quit when Idle exits
		try:
			key = self.inversedict[edit]
		except KeyError:
			print "Don't know this EditorWindow object.  (close)"
			return
		if key:
			del self.dict[key]
		del self.inversedict[edit]
		#if not self.inversedict:
		#	self.root.quit()
		self.pyshell = None


	def open_shell(self, event=None):
		## Code copied from idlelib/PyShell.py
		## Replaced call to PyShell with ChimeraPyShell so
		## we can do more customization
		if self.pyshell:
			self.pyshell.top.wakeup()
		else:
			self.pyshell = ChimeraPyShell(self)

			if self.pyshell:
				if not self.pyshell.begin():
					return None
		return self.pyshell


# Use Chimera root window so that IDLE windows are iconified
# when Chimera is iconified.
import chimera
flist = noQuitPyShellFileList(chimera.tkgui.app)
from idlelib import macosxSupport
#macosxSupport.setupApp(chimera.tkgui.app.master, flist)
macosxSupport._initializeTkVariantTests(chimera.tkgui.app.master)

def start_shell():
	global flist
	flist.open_shell()
