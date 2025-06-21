# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

from Tkinter import Label
class WrappingLabel(Label):
	"""Label that word wraps to fit available space"""

	def __init__(self, *args, **kw):
		preserveWords = kw.pop("preserveWords", False)
		try:
			if preserveWords:
				self.__words = kw.pop('text').split()
			else:
				self.__text = kw.pop('text')
		except KeyError:
			raise ValueError("%ss currently only supports 'text' keyword"
				" for specifying label text" % self.__class__.__name__)
		Label.__init__(self, *args, **kw)
		if preserveWords:
			self.bind('<Configure>', self.__wrapWords)
		else:
			self.bind('<Configure>', self.__wrap)

	def __wrap(self, event):
		self.configure(text=self.__text, wraplength=event.width)

	def __wrapWords(self, event):
		w = event.width
		words = self.__words[:]
		wrapped = words.pop(0)
		while words:
			self.configure(text=wrapped + " " + words[0])
			if self.winfo_reqwidth() > w:
				wrapped += "\n" + words.pop(0)
			else:
				wrapped += " " + words.pop(0)
		self.configure(text=wrapped)
