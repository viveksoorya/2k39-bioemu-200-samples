# Copyright (c) 2000 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: replyobj.py 42342 2021-11-10 01:54:13Z pett $

"""
Reply Object -- manage diagnostic and normal output

Code sends output to sys.stdout and sys.stderr, or uses one of diagnostic
output functions: message, command, status, info, warning, error, or
reportException.  Since where that output should go varies on how chimera
is used, a "stack" is maintained of objects that implement the diagnostic
output functions.
"""
__all__ = [
	'message', 'command', 'status', 'info', 'warning', 'error', 'clear',
	'reportException', 'handlePdbErrs',
	'Reply', 'pushReply', 'popReply', 'currentReply',
	'origStdout', 'origStderr'
]

import sys
import Tkinter
import tkMessageBox
import statusline
Tk = Tkinter

import chimera
from chimera import baseDialog

# tag names -- normal is not really used as a tag
NORMAL = "Normal"
COMMAND = "Command"
STATUS = "Status"
WARNING = "Warning"
WARN = WARNING
ERROR = "Error"
SHOW_STATUS_LINE = "Show status line"
STATUS_CLEARING = "Clear status line after"
BALLOON_HELP = "Show balloon help"

DisplayReplyLog = "reply log only"
DisplayDialog = "dialog"

REPLY_PREFERENCES = "Messages"

# cache original values of stdout and stderr for the case chimera
# where chimera was started within another application (e.g., Sparky)
origStdout = sys.stdout
origStderr = sys.stderr

_ENCODE_ERRORS = 'backslashreplace'

def _encode(s, encoding):
	if encoding is None:
		if isinstance(s, unicode):
			s = s.encode('utf-8', _ENCODE_ERRORS)
	elif isinstance(s, unicode):
		s = s.encode(encoding, _ENCODE_ERRORS)
	elif encoding.lower() != 'utf-8':
		s = s.decode('utf-8').encode(encoding, _ENCODE_ERRORS)
	return s

replyDialog = None

lastTracebackMsg  = ''
uncaughtExc       = False
helpInfo          = None

class MicrosoftSEDialog(baseDialog.ModalDialog):

	buttons = ("Report Bug", baseDialog.Cancel)
	default = baseDialog.Cancel
	help = "http://www.cgl.ucsf.edu/chimera/graphics/graphicsbugs.html"
	title = 'Chimera Error'

	def fillInUI(self, master):
		b, i = baseDialog._bitmap_image(master, "error")
		self.icon = Tk.Label(master, bitmap=b, image=i)
		self.icon.pack(side=Tk.LEFT, padx=4, pady=4)
		self.message = Tk.Label(master, text=
			'\n'
			'error: Microsoft SE exception C0000005\n'
			'\n'
			'This error frequently means that your graphics/video'
			' driver is out-of-date.'
			'  Please verify that you are using the latest driver.'
			'  If you have updated your driver'
			' and are still seeing this bug,'
			' please report it.'
			'\n',
			wraplength=400, justify=Tk.LEFT)
		self.message.pack(fill=Tk.BOTH, expand=Tk.TRUE, padx=4, pady=4)
		self.message.bind("<Configure>", self.msgConfig)
		self.reconfig = True

	def msgConfig(self, event):
		if not self.reconfig:
			# only reconfigure once to avoid configure loops
			return
		self.message.config(wraplength=event.width)
		self.reconfig = False

	def ReportBug(self):
		baseDialog.ModalDialog.Cancel(self, value='yes')

class ReplyDialog(baseDialog.ModelessDialog):

	buttons = ("Report Bug", "Open Reply Log", baseDialog.Close)
	default = baseDialog.Close

	def fillInUI(self, master):
		b, i = baseDialog._bitmap_image(master, 'info')
		self.icon = Tk.Label(master, bitmap=b, image=i)
		self.icon.pack(side=Tk.LEFT, padx=4, pady=4)
		self.message = Tk.Label(master, text="Reply Dialog",
				wraplength=400, justify=Tk.LEFT, anchor=Tk.W)
		self.message.pack(fill=Tk.BOTH, expand=Tk.TRUE, padx=4, pady=4)
		self.message.bind("<Configure>", self.msgConfig)
		self.reconfig = True

	def msgConfig(self, event):
		if not self.reconfig:
			# only reconfigure once to avoid configure loops
			return
		self.message.config(wraplength=event.width)
		self.reconfig = False

	def setMessage(self, msg):
		self.message.config(text='\n' + msg.strip() + '\n')
		self.reconfig = True

	def setTitle(self, title):
		self.message.winfo_toplevel().title(title)
		self.reconfig = True

	def setIcon(self, icon):
		b, i = baseDialog._bitmap_image(self.icon, icon)
		self.icon.config(bitmap=b, image=i)
		self.reconfig = True

	def OpenReplyLog(self):
		from chimera import dialogs, tkgui
		dialogs.display(tkgui._ReplyDialog.name)
		self.Close()

	def enter(self):
		if uncaughtExc:
			self.buttonWidgets['Report Bug'].pack(anchor='se',
					side='right', padx='1p', pady='4p')
		else:
			self.buttonWidgets['Report Bug'].pack_forget()
		global helpInfo
		if helpInfo:
			self.buttonWidgets['Help'].config(state="normal")
			import help
			help.register(self._toplevel, helpInfo)
		else:
			self.buttonWidgets['Help'].config(state="disabled")
		self.help = helpInfo
		helpInfo = None

		baseDialog.ModelessDialog.enter(self)

	def ReportBug(self):
		if 'Microsoft SE exception C0000005' in lastTracebackMsg:
			yes = MicrosoftSEDialog().run(self._toplevel)
			if not yes:
				return
		from tkgui import latestVersion
		try:
			production, candidate, snapshot = latestVersion(showDialog=False)
		except:
			production = False
		if production:
			from baseDialog import AskYesNoDialog
			class NewerVersion(AskYesNoDialog):
				title = "Newer Version Available"
				buttons = ("Continue Reporting Bug", "No Bug Report")

				ContinueReportingBug = AskYesNoDialog.Yes
				NoBugReport = AskYesNoDialog.No

			dlg = NewerVersion(
"""There is newer production version of Chimera than the version
you are using.  It is usually best to upgrade to the current
version rather than report bugs in old versions, since the bug
may have already been fixed in the newer version and also
because it is easier for the Chimera programming to debug
problems in the latest version than in old versions.

Nonetheless, you may continue reporting this bug, or you may
decline to continue the bug report, in which case a dialog
offering the opportunity to download the new version will appear.""")
			if dlg.run(self.uiMaster().winfo_toplevel()) == 'no':
				latestVersion(showDialog=None)
				self.Close()
				return
		import BugReport
		br_gui = BugReport.displayDialog()
		if not br_gui:
			return

		bug_report = BugReport.BugReport(info=lastTracebackMsg)
		br_gui.setBugReport(bug_report)

ModeBitmap = {
	NORMAL:		"info",
	COMMAND:	"info",
	STATUS:		"info",
	WARNING:	"warning",
	ERROR:		"error"
}

def showDialog(title="missing title", message="missing message", mode=NORMAL):
	if not message:
		return
	global replyDialog
	if replyDialog is None:
		replyDialog = ReplyDialog(initiateAutoPositioning=False)
	replyDialog.setTitle(title)
	replyDialog.setMessage(message)
	replyDialog.setIcon(ModeBitmap[mode])
	replyDialog.enter()

def _setBalloon(o):
	from tkgui import app
	if app:
		app._setBalloon(o)

def registerPreferences():
	import tkoptions
	class ReplyDisplayOption(tkoptions.EnumOption):
		"""Specialization of EnumOption Class for side"""
		values = (DisplayReplyLog, DisplayDialog)
	class StatusClearingOption(tkoptions.SymbolicEnumOption):
		values = [5, 10, 20, 30, 60, 0]
		labels = ["5 seconds", "10 seconds", "20 seconds",
			"30 seconds", "1 minute", "never"]
	ReplyPreferences = {
		SHOW_STATUS_LINE: (tkoptions.BooleanOption, Tk.YES,
				   _showStatusLine),
		STATUS_CLEARING:(StatusClearingOption, 30, None),
		COMMAND:	(ReplyDisplayOption, DisplayReplyLog, None),
		WARNING:	(ReplyDisplayOption, DisplayDialog, None),
		ERROR:		(ReplyDisplayOption, DisplayDialog, None),
		BALLOON_HELP:
			(tkoptions.BooleanOption, Tk.YES, _setBalloon),
	}
	ReplyPreferencesOrder = [
		SHOW_STATUS_LINE, STATUS_CLEARING,
		BALLOON_HELP, COMMAND, WARNING, ERROR
	]

	import preferences
	from tkgui import GENERAL
	preferences.register(REPLY_PREFERENCES, ReplyPreferences, inherit=[
		(BALLOON_HELP, GENERAL, BALLOON_HELP, None)])
	preferences.setOrder(REPLY_PREFERENCES, ReplyPreferencesOrder)

	chimera.triggers.addHandler('status line', _statusLineShownCB, None)

class Reply:
	"""Send normal output to a text widget.  Optionally show diagnostic
	output in a dialog, otherwise send to text widget.
	"""

	encoding = 'utf-8'
	softspace = 0
	tagInfo = {
		NORMAL: {
			"icon": None, "text": None,
			"font": "Helvetica 12", "relief":Tk.FLAT
		},
		COMMAND: {
			"icon": None, "text": None,
			"font": "Helvetica 12", "relief":Tk.RIDGE
		},
		STATUS: {
			"icon": None, "text": None,
			"color": "#3300c3",
			"font": "Helvetica 12", "relief":Tk.FLAT
		},
		WARNING: {
			"icon": None, "text": None,
			"color": "#0033d3",
			"font": "Helvetica 12 italic", "relief":Tk.FLAT
		},
		ERROR: {
			"icon": None, "text": None,
			"color": "#c12300",
			"font": "Helvetica 12 bold", "relief":Tk.FLAT
		}
	}

	def __init__(self, widget):
		# TODO: assert widget is a Text widget
		self._widget = widget
		self._widget.config(state=Tk.DISABLED)
		# TODO: text background is read-only color
		ti = Reply.tagInfo[NORMAL]
		ti["color"] = self._widget["foreground"]
		self._widget.config(font=ti["font"], foreground=ti["color"])
		keys = Reply.tagInfo.keys()
		keys.remove(NORMAL)
		for k in keys:
			ti = Reply.tagInfo[k]
			if not ti.has_key("color"):
				ti["color"] = self._widget["foreground"]
			self._widget.tag_configure(k,
				font=ti["font"], foreground=ti["color"],
				relief=ti["relief"], borderwidth=2)
		self._mode = [ NORMAL ]
		self._messages = []

	def write(self, s):
		"""Write string to reply window.

		widget.write(string) => None
		"""
		self.message(s)

	def flush(self):
		"""Flush output to reply window.

		widget.flush() => None
		"""
		self._widget.update_idletasks()

	def message(self, s):
		"""Display a message in current message mode"""
		mode = self._mode[0]
		if mode == STATUS:
			self._messages[0].append(s)
			return
		self._widget.config(state=Tk.NORMAL)
		if mode == NORMAL:
			while 1:
				i = s.find('\r')
				if i == -1:
					break
				if i + 1 < len(s) and s[i + 1] == '\n':
					self._widget.insert(Tk.END, s[:i] + '\n')
					s = s[i + 2:]
					continue
				# TODO: would like to overwrite last line
				# instead of deleting it
				self._widget.delete('end-1c linestart', Tk.END)
				self._widget.insert(Tk.END, '\n')
				s = s[i + 1:]
			if s:
				self._widget.insert(Tk.END, s)
		else:
			# The warning/error text in undisplayed reply log crashes in Tk 8.6.10
			if sys.platform == 'darwin' and not chimera.nogui:
				chimera.dialogs.display(chimera.tkgui._ReplyDialog.name)
			self._widget.insert(Tk.END, s, mode)
			self._messages[0].append(s)
		self._widget.config(state=Tk.DISABLED)
		self._widget.see(Tk.END)

	def _pushMode(self, mode):
		"""Enter a message mode (NORMAL, WARNING, ERROR, etc.)"""
		if mode != NORMAL:
			self._messages.insert(0, [])
		self._mode.insert(0, mode)
		self._setMode(mode)

	def _popMode(self, log=0, **kw):
		"""Exit a message mode"""
		if len(self._mode) == 1:
			return
		if self._mode[0] == STATUS:
			if log:
				info("".join(self._messages[0]) + '\n')
				if 'followWith' not in kw:
					kw['followWith'] = \
				"Previous message also written to reply log"
			self._showStatus(**kw)
			del self._messages[0]
		elif self._mode[0] != NORMAL:
			if sys.platform != 'darwin':
				# The three lines below crash Chimera if the log isn't displayed in Tk 8.6.10 on Mac
				self._widget.config(state=Tk.NORMAL)
				self._widget.insert(Tk.END, '\n')
				self._widget.config(state=Tk.DISABLED)
			import preferences
			p = preferences.get(REPLY_PREFERENCES, self._mode[0])
			if p == DisplayDialog:
				self._showDialog()
			del self._messages[0]
		del self._mode[0]
		self._setMode(self._mode[0])

	def _setMode(self, mode):
		self._widget.config(state=Tk.NORMAL)
		ti = Reply.tagInfo[mode]
		if ti["icon"]:
			b, i = baseDialog._bitmap_image(self._widget, ti["icon"])
			win = Label(self._widget, bitmap=b, image=i,
					foreground=ti["color"])
			self._widget.window_create(Tk.END, window=win,
					align=TOP, padx=2, pady=2)
			self._widget.tag_add(mode, 'end - 2c', 'end - 1c')
		if ti["text"]:
			self._widget.insert(Tk.END, ti["text"], mode)
		if ti["icon"] or ti["text"]:
			self._widget.insert(Tk.END, '\n')
		self._widget.config(state=Tk.DISABLED)

	def _showDialog(self):
		showDialog(title="Chimera %s" % self._mode[0],
				message="".join(self._messages[0]),
				mode=self._mode[0])

	def _showStatus(self, **kw):
		msg = "".join(self._messages[0])
		statusline.show_message(msg, **kw)

	def clear(self):
		"""Clear contents of reply window.

		widget.clear() => None
		"""
		if hasattr(self._widget, 'clear'):
			self._widget.clear()
		else:
			self._widget.config(state=Tk.NORMAL)
			self._widget.delete(1.0, Tk.END)
			self._widget.config(state=Tk.DISABLED)

	def command(self, s):
		"""Log a command string"""
		self._pushMode(COMMAND)
		self.message(s)
		self._popMode()

	def status(self, s, **kw):
		"""Log a status string"""
		self._pushMode(STATUS)
		self.message(s)
		self._popMode(**kw)

	def info(self, s):
		"""Log an informational message"""
		self._pushMode(NORMAL)
		self.message(s)
		self._popMode()

	def warning(self, s):
		"""Log a warning string"""
		self._pushMode(WARNING)
		self.message(s)
		self._popMode()

	def error(self, s):
		"""Log an error string"""
		self._pushMode(ERROR)
		self.message(s)
		self._popMode()

class SplashReply:
	"""A splash window status widget.

	The splay reply window widget updates a label widget with
	status messages.  Error output goes to origStderr.
	"""

	encoding = 'utf-8'

	def __init__(self, widget):
		self._widget = widget

	def write(self, s):
		"""Write string to reply window."""
		self._widget.config(text=s)

	def flush(self):
		"""Flush output to reply window."""
		self._widget.update_idletasks()

	def clear(self):
		"""Clear contents of reply window."""
		if hasattr(self._widget, 'clear'):
			self._widget.clear()
		else:
			self._widget.config(text="")

	def message(self, s):
		"""Display a message in current message mode"""
		self._widget.config(text=s)

	def command(self, s):
		"""Log a command string"""
		s = _encode(s, origStdout.encoding)
		print >> origStdout, s

	def status(self, s, **kw):
		"""Log a status string"""
		self._widget.config(text=s)
		self.flush()
		if not chimera.debug:
			return
		try:
			origStdout.flush()
		except IOError:
			pass
		s = _encode(s, origStderr.encoding)
		print >> origStderr, s

	def info(self, s):
		"""Log an informational message"""
		s = _encode(s, origStdout.encoding)
		print >> origStdout, s

	def warning(self, s):
		"""Log a warning string"""
		try:
			origStdout.flush()
		except IOError:
			pass
		s = _encode(s, origStderr.encoding)
		print >> origStderr, s

	def error(self, s):
		"""Log an error string"""
		try:
			origStdout.flush()
		except IOError:
			pass
		s = _encode(s, origStderr.encoding)
		print >> origStderr, s

class NoGUIReply:
	"""Status for when there is no GUI.

	Error output goes to origStderr, and regular output goes to origStdout.
	"""

	encoding = origStdout.encoding

	def write(self, s):
		s = _encode(s, origStdout.encoding)
		origStdout.write(s)

	def flush(self):
		origStdout.flush()

	def clear(self):
		"""Clear output window"""
		pass

	def message(self, s):
		"""Show a message"""
		if chimera.silent:
			return
		s = _encode(s, origStdout.encoding)
		print >> origStdout, s

	def command(self, s):
		"""Log a command string"""
		if chimera.silent:
			return
		s = _encode(s, origStdout.encoding)
		print >> origStdout, s

	def status(self, s, **kw):
		"""Log a status string"""
		if chimera.nostatus:
			return
		s = _encode(s, origStdout.encoding)
		print >> origStdout, s

	def info(self, s):
		"""Log an informational message"""
		if chimera.silent:
			return
		s = _encode(s, origStdout.encoding)
		print >> origStdout, s

	def warning(self, s):
		"""Log a warning string"""
		if chimera.silent:
			return
		try:
			sys.stdout.flush()
		except IOError:
			pass
		s = _encode(s, origStderr.encoding)
		print >> origStderr, s

	def error(self, s):
		"""Log an error string"""
		try:
			sys.stdout.flush()
		except IOError:
			pass
		s = _encode(s, origStderr.encoding)
		print >> origStderr, s

def _showStatusLine(option):
	statusline.show_status_line(option.get())

def _statusLineShownCB(trigName, x, shown):
	import preferences
	preferences.set(REPLY_PREFERENCES, SHOW_STATUS_LINE, shown)

_replyStack = [NoGUIReply()]

def currentReply():
	return _replyStack[-1]

def message(s):
	_replyStack[-1].message(s)

def command(s):
	_replyStack[-1].command(s)

def status(s, **kw):
	if chimera.nostatus:
		return
	_replyStack[-1].status(s, **kw)

def info(s, help=None):
	if chimera.silent:
		return
	global helpInfo
	helpInfo = help
	_replyStack[-1].info(s)

def warning(s, help=None):
	if chimera.silent:
		return
	global helpInfo
	helpInfo = help
	_replyStack[-1].warning(s)

def error(s, help=None):
	global helpInfo
	helpInfo = help
	_replyStack[-1].error(s)

def clear(s):
	_replyStack[-1].clear(s)

def pushReply(reply):
	"""add reply to reply stack"""
	if reply is None:
		reply = NoGUIReply()
	sys.stdout = reply
	if not chimera.debug:
		sys.stderr = reply
	_replyStack.append(reply)
	return reply

def popReply(stackObj):
	"""remove reply from reply stack"""
	if not _replyStack:
		raise IndexError, 'no reply object on stack'
	n = _replyStack.index(stackObj)
	del _replyStack[n]
	assert(len(_replyStack) > 0)
	sys.stdout = _replyStack[-1]
	if not chimera.debug:
		sys.stderr = _replyStack[-1]

def clearReplyStack():
	del _replyStack[1:]
	sys.stdout = _replyStack[0]
	if not chimera.debug:
		sys.stderr = _replyStack[0]

def convertToPrintable(value):
	try:
		return unicode(value)
	except UnicodeDecodeError:
		return str(value).decode('utf-8', 'replace')

def reportException(description=None, fullDescription=None):
	"""Report the current exception, prepending 'description'.

	A 'fullDescription' overrides the description and traceback
	information."""

	from chimera import NotABug, CancelOperation
	from traceback import format_exception_only, format_exception, format_tb
	ei = sys.exc_info()
	if description:
		preface = "%s:\n" % description
	else:
		preface = ""

	exception_value = ei[1]

	if isinstance(exception_value, NotABug):
		error(u"%s%s\n" % (preface, convertToPrintable(exception_value)))
	elif isinstance(exception_value, CancelOperation):
		pass	# Cancelled operations are not reported.
	else:
		global uncaughtExc
		uncaughtExc = True

		if fullDescription:
			tb_msg = fullDescription
		else:
			tb = format_exception(ei[0], ei[1], ei[2])
			tb_msg = u"".join([convertToPrintable(t) for t in tb])
		message(tb_msg)
		global lastTracebackMsg
		lastTracebackMsg = tb_msg

		err = u"".join([convertToPrintable(t) for t in format_exception_only(ei[0], ei[1])])
		loc = u''.join([convertToPrintable(t) for t in format_tb(ei[2])[-1:]])
		error(u'%s%s\n%s\n' % (preface, err, loc)
		      + u"See reply log for Python traceback.\n\n")
		uncaughtExc=False

def handlePdbErrs(identifyAs, errs):
	prep = ("The following problems occurred while reading PDB file for %s"
								% identifyAs)
	# using info instead of warning because this is too common of an error
	info("\n".join([prep, errs]))

class PdbErrsDialog(baseDialog.ModelessDialog):
	oneshot = True
	title = "Errors in PDB File"
	buttons = ('OK',)
	
	def __init__(self, prep, errs):
		self.info = (prep, errs)
		baseDialog.ModelessDialog.__init__(self)

	def fillInUI(self, parent):
		prep, errs = self.info
		import Tkinter, Pmw
		Tkinter.Label(parent, text=prep).grid(row=0)
		scrolled = Pmw.ScrolledText(parent)
		scrolled.settext(errs)
		scrolled.component('text').configure(state='disabled')
		scrolled.grid(row=1, sticky='nsew')
