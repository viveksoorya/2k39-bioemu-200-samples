# Copyright (c) 2000 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: toolbar.py 41909 2018-10-01 21:24:48Z pett $

"""
	Toolbar interface
"""

__all__ = ("Toolbar", "YES", "NO", "AUTO")

import Tkinter as Tk
import chimage

# visibility arguments
YES = "yes"
NO = "no"
AUTO = "auto"

TOOLBAR_RA = "Rapid Access"

def _guard(func):
	"""Protect against faulty callback functions."""
	try:
		func()
	except (SystemExit, KeyboardInterrupt):
		raise
	except Exception:
		import replyobj
		replyobj.reportException('Error in toolbar callback')

def _size(w, attr):
	"""Get widget attribute as integer size"""
	return int(str(w[attr]))

class Toolbar(Tk.Frame, object):
	"""A Toolbar widget.

	Toolbar(master, side=Tk.LEFT) => widget

	A Toolbar is a frame that contains a scrollable list of tool
	buttons and one work widget that is always visible.  The work
	widget is created by the caller as a child of the toolbar, and
	then the 'work' property must be set to that widget.  The
	optional side argument may be one of LEFT, RIGHT, TOP, or BOTTOM.

	Example:
		from toolbar import Toolbar
		tb = Toolbar(application)
		tb.pack()
		graphics = Canvas(tb)
		tb.work = graphics
	"""
	# implementation:
	#    work widget is at grid (2, 2)
	#    the scrollbar and toolbox locations are kept in _geom
	#    (boxrow, boxcol, scrollrow, scrollcol, sticky)

	def __init__(self, master, side=Tk.LEFT):
		Tk.Frame.__init__(self, master)
		self.grid_columnconfigure(2, weight=1)
		self.grid_rowconfigure(2, weight=1)
		self._visible = AUTO
		self._side = side
		self._work = None
		self._buttons = []
		self._toolbox = Tk.Canvas(self, relief=Tk.SUNKEN,
						borderwidth=2,
						highlightthickness=0)
		self._scrollbar = Tk.Scrollbar(self)
		self._updateSideParameters(side)
		self._gridHistory = set()

	def getWork(self):
		return self._work

	def setWork(self, w):
		"""Set work widget.

		toolbar.setWork(widget) => None

		See Toolbar class description for more details.
		"""
		if self._work == w:
			return
		reset = (self._work is None or w is None)
		if not reset and self._work != w:
			self._work.grid_remove()
		self._work = w
		if self._work:
			if self._work in self._gridHistory:
				kw = {}
			else:
				self._gridHistory.add(self._work)
				kw = { 'sticky': 'news' }
			self._work.grid(row=2, column=2, **kw)
		if reset:
			self._updateSideParameters(self._side)
			visible = self._visible
			self._visible = None
			self.setVisible(visible)
	work = property(getWork, setWork)

	def _autoscroll_set(self, first, last):
		if not self._toolbox.winfo_ismapped():
			return
		if float(first) <= 0 and float(last) >= 1:
			self._scrollbar.grid_forget()
		elif not self._scrollbar.winfo_ismapped():
			brow, bcol, srow, scol, sticky = self._geom
			self._scrollbar.grid(row=srow, column=scol, sticky=sticky)
			# need to update_idletasks so scrollbar behaves
			self._scrollbar.update_idletasks()
		self._scrollbar.set(first, last)

	def _updateSideParameters(self, side):
		# only call this
		if self._work == None or side == Tk.TOP:
			orient = Tk.HORIZONTAL
			self._geom = (1, 2, 0, 2, Tk.EW)
		elif side == Tk.BOTTOM:
			# Tk.BOTTOM
			orient = Tk.HORIZONTAL
			self._geom = (3, 2, 4, 2, Tk.EW)
		elif side == Tk.LEFT:
			orient = Tk.VERTICAL
			self._geom = (2, 1, 2, 0, Tk.NS)
		elif side == Tk.RIGHT:
			orient = Tk.VERTICAL
			self._geom = (2, 3, 2, 4, Tk.NS)
		elif side == TOOLBAR_RA:
			from tkgui import app
			if app:
				app.rapidAccess.showToolArea(True)
			self._geom = None
			self.setVisible(NO)
			return
		else:
			raise AssertionError("Bad toolbar placement: %s" % side)
		from tkgui import app
		if app:
			app.rapidAccess.showToolArea(False)
		if orient == Tk.VERTICAL:
			self._toolbox.config(
				xscrollcommand="{}",
				yscrollcommand=self._autoscroll_set)
			self._scrollbar.config(orient=orient,
				command=self._toolbox.yview)
		else:
			self._toolbox.config(
				xscrollcommand=self._autoscroll_set,
				yscrollcommand="{}")
			self._scrollbar.config(orient=orient,
				command=self._toolbox.xview)
		self.setVisible(AUTO)

	def getSide(self):
		return self._side

	def setSide(self, side):
		"""Set which side of the frame to place the toolbar.

		toolbar.setSide(side) => None

		side can be one of Tk constants LEFT, RIGHT TOP or BOTTOM,
			or module constant TOOLBAR_RA.
		"""
		if self._side == side:
			return
		from tkgui import app
		if app:
			app.allowResize = False
		self._side = side
		self._updateSideParameters(side)
		self._redisplayButtons()
		if self._visible == YES \
		or (self._visible == AUTO and self.count() > 0):
			brow, bcol, srow, scol, sticky = self._geom
			self._scrollbar.grid(row=srow, column=scol, sticky=sticky)
			self._toolbox.grid(row=brow, column=bcol, sticky=sticky)
			if self._work:
				self._work.grid(row=2, column=2)
		if app:
			app.after(500,
				lambda app=app, *args: setattr(app, 'allowResize', True))

	side = property(getSide, setSide)

	def setVisible(self, visibility):
		"""Turn on and off the toolbar.

		toolbar.setVisible(visibility) => None
		"""
		if self._visible == visibility:
			return
		from tkgui import app
		if app:
			app.allowResize = False
		self._visible = visibility
		if visibility == AUTO:
			if self.count() > 0:
				visibility = YES
			else:
				visibility = NO
		if visibility == NO:
			self._scrollbar.grid_forget()
			self._toolbox.grid_forget()
		elif visibility == YES:
			brow, bcol, srow, scol, sticky = self._geom
			self._scrollbar.grid(row=srow, column=scol, sticky=sticky)
			self._toolbox.grid(row=brow, column=bcol, sticky=sticky)
			if self._work:
				self._work.grid(row=2, column=2)
		else:
			if app:
				app.allowResize = True
			raise TypeError, "visibility must be 'yes', 'no', or 'auto'"
		if app:
			app.after(500,
				lambda app=app, *args: setattr(app, 'allowResize', True))

	def add(self, image, callback, balloon, helpURL=None):
		"""Add button to toolbar.

		toolbar.add(image, callback, balloon, helpURL) => None

		Create a button for a tool with the given image, callback
		function, balloon help string, and URL for context sensitive
		help.  The image may be a filename or an Image instance.
		The callback function should take no arguments.  Balloon help
		should be a short string.
		"""

		buttonKw = {
			'highlightthickness': 0, 'padx': 0, 'pady': 0,
			'command': lambda func=callback: _guard(func)
		}
		button = Tk.Button(self._toolbox, **buttonKw)
		import help
		help.register(button, helpURL, balloon)

		imtk = chimage.get(image, button, allowRelativePath=True)
		button.config(image=imtk)
		# need to keep reference to Tk image or else it is destroyed
		# and the button stops working
		button._image = imtk
		self._buttons.append(button)
		self._redisplayButtons()
		if self._visible == AUTO and self.count() == 1:
			self._visible = NO
			self.setVisible(AUTO)
		from tkgui import app
		app.rapidAccess.addTool(button, image, buttonKw, balloon, helpURL)
		return button

	def remove(self, button):
		"""Remove button from toolbar.

		toolbar.remove(button) => None

		Remove a button created by "add"."""

		self._buttons.remove(button)
		from tkgui import app
		app.rapidAccess.removeTool(button)
		button.destroy()
		if self._visible == AUTO and self.count() == 0:
			self._visible = YES
			self.setVisible(AUTO)

	_SideMap = {
		Tk.LEFT:	( True , Tk.TOP , Tk.W ),
		Tk.RIGHT:	( True , Tk.TOP , Tk.E ),
		Tk.TOP:		( False, Tk.LEFT, Tk.N ),
		Tk.BOTTOM:	( False, Tk.LEFT, Tk.S ),
	}
	def _redisplayButtons(self):
		if self._side == TOOLBAR_RA:
			return
		vertical, side, anchor = self._SideMap[self._side]
		self._toolbox.delete("buttons")
		bd = _size(self._toolbox, "borderwidth")
		x = bd
		y = bd
		maxSize = 0
		buttonSize = {}
		import tkgui
		for button in self._buttons:
			bd = _size(button, "borderwidth")
			bw = button._image.width() + bd * 2
			bh = button._image.height() + bd * 2
			buttonSize[button] = (bw, bh)
			if vertical:
				if bw > maxSize:
					maxSize = bw
			else:
				if bh > maxSize:
					maxSize = bh
		for button in self._buttons:
			bw, bh = buttonSize[button]
			if self._side == Tk.LEFT or self._side == Tk.RIGHT:
				x = bd + (maxSize - bw) / 2
			else:
				y = bd + (maxSize - bh) / 2
			self._toolbox.create_window((x, y), window=button,
							anchor="nw",
							tags="buttons")
			if vertical:
				y += bh + 1
			else:
				x += bw + 1
		if vertical:
			self._toolbox.config(width=maxSize,
					scrollregion=(bd, bd, maxSize, y))
		else:
			self._toolbox.config(height=maxSize,
					scrollregion=(bd, bd, x, maxSize))

	def clear(self):
		"""Remove all buttons from toolbar"""
		self._toolbox['state'] = 'normal'
		self._toolbox.delete('1.0', Tk.END)
		self._toolbox['state'] = 'disabled'

	def count(self):
		return len(self._buttons)

if __name__ == "__main__":
	def pressed(what):
		print what
	app = Tk.Frame(Tk.Tk())
	app.pack(expand=Tk.YES, fill=Tk.BOTH)
	tb = Toolbar(app, side=Tk.LEFT)
	tb.pack(expand=Tk.YES, fill=Tk.BOTH)
	work = Tk.Canvas(tb, background="#600")
	tb.work = work
	work.bind('<ButtonRelease-1>', lambda e, t=tb: t.setVisible(YES))
	tb.add('images/avacado.png', lambda: setattr(tb, 'side', Tk.LEFT), 'fruit', "avacado.html")
	tb.add('images/Palette.png', lambda: setattr(tb, 'side', Tk.RIGHT), 'color palette', "palette.html")
	tb.add('images/avacado.png', lambda: setattr(tb, 'side', Tk.BOTTOM), 'fruit', "avacado.html")
	tb.add('images/Palette.png', lambda: setattr(tb, 'side', Tk.TOP), 'color palette', "palette.html")
	tb.add('images/CowboyHat3.png', lambda: tb.setVisible(NO), 'cowboy', "cowboy.html")
	app.mainloop()
