# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

from Tkinter import Text, Widget, BaseWidget

class PeerText(Text):
	def __init__(self, *args, **kw):
		self.peer = kw.pop('peer', None)

		# need to change the way BaseWidget works...
		bw__init__ = BaseWidget.__init__
		BaseWidget.__init__ = PeerBaseWidget__init__
		try:
			Text.__init__(self, *args, **kw)
		finally:
			BaseWidget.__init__ = bw__init__

def PeerBaseWidget__init__(self, master, widgetName, cnf={}, kw={}, extra=()):
	"""Construct a widget with the parent widget MASTER, a name WIDGETNAME
	and appropriate options."""
	if kw:
		cnf = _cnfmerge((cnf, kw))
	self.widgetName = widgetName
	BaseWidget._setup(self, master, cnf)
	if self._tclCommands is None:
		self._tclCommands = []
	classes = []
	for k in cnf.keys():
		if type(k) is ClassType:
			classes.append((k, cnf[k]))
			del cnf[k]
	if self.peer:
		self.tk.call((self.peer._w, "peer", "create", self._w)
				+ extra + self._options(cnf))
	else:
		self.tk.call((widgetName, self._w) + extra + self._options(cnf))
	for k, v in classes:
		k.configure(self, v)
