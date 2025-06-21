#!/usr/bin/env python

# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: Sash.py 34686 2011-10-14 22:13:21Z conrad $


import Tkinter
Tk = Tkinter
from Tkinter import _cnfmerge
from SimpleDialog import SimpleDialog
import sys

IPS = 4		# Inter-pane spacing.  Must be a multiple
		# of 2 because when we add panes, we will
		# pad them with IPS/2 pixels to make sure
		# that we get exactly the right initial
		# window size

class CollapsiblePane(Tk.Frame):
	"""
	CollapsiblePane is a frame that has a Checkbutton at the
	top which controls whether the rest of the frame is displayed.
	CollapsiblePane instances should be children of Sash (below).
	"""
	def __init__(self, master=None, title='Untitled',
			titleFont=None, collapsed=0, **kw):
		Tk.Frame.__init__(self, master, kw)
		self.controlFrame = Tk.Frame(self)
		self.controlFrame.pack(side=Tk.TOP, fill=Tk.X)
		self.button = Tk.Label(self.controlFrame)
		from chimera import chimage
		self.rArrow = chimage.get("rightarrow.png", self.button)
		self.dArrow = chimage.get("downarrow.png", self.button)
		self.button.pack(side=Tk.LEFT, ipadx=2, ipady=0)
		self.button.bind("<Button-1>", self._buttonClick)
		self.label = Tk.Label(self.controlFrame, text=title)
		if titleFont:
			label.configure(font=titleFont)
		self.label.pack(side=Tk.LEFT)
		self.label.bind("<Button-1>", self._buttonClick)
		self.frame = Tk.Frame(self, bd=2, relief=Tk.SUNKEN)
		if collapsed:
			self.hide()
		else:
			self.show()
		self.paneMinHeight = self.controlFrame.winfo_reqheight() + \
					int(str(self.controlFrame['bd'])) * 2
		self.paneMinWidth = self.controlFrame.winfo_reqwidth()

	def _buttonClick(self, event=None):
		self.buttonCommand()

	def hide(self):
		self.paneCollapsed = Tk.TRUE
		self.button.configure(image=self.rArrow)
		self.buttonCommand = self.show
#					command=self.show)
		if not hasattr(self, 'paneHeight'):
			# Must be during setup (before being shown on screen)
			if self.paneCollapsed:
				self.frame.forget()
			return
		self.savePaneHeight = self.paneHeight
		self.paneHeight = self.winfo_height() - \
					self.frame.winfo_height()
		self.frame.forget()
		top = self.winfo_toplevel()
		ht = top.winfo_height() - self.savePaneHeight + \
			self.paneHeight
		wd = top.winfo_width()
		top.geometry('%dx%d' % (wd, ht))

	def show(self):
		self.paneCollapsed = Tk.FALSE
		self.button.configure(image=self.dArrow)
		self.buttonCommand = self.hide
#					command=self.hide)
		if not hasattr(self, 'paneHeight'):
			# Must be during setup (before being shown on screen)
			if not self.paneCollapsed:
				self.frame.pack(side=Tk.TOP, fill=Tk.BOTH,
						expand=Tk.TRUE)
			return
		if not hasattr(self, 'savePaneHeight'):
			# Must be because we started hidden
			self.savePaneHeight = self.paneHeight + \
						self.frame.winfo_reqheight()
		self.frame.pack(side=Tk.TOP, fill=Tk.BOTH, expand=Tk.TRUE,
				after=self.controlFrame)
		top = self.winfo_toplevel()
		ht = top.winfo_height() - self.paneHeight + \
			self.savePaneHeight
		self.paneHeight = self.savePaneHeight
		wd = top.winfo_width()
		top.geometry('%dx%d' % (wd, ht))

def _isCollapsed(pane):
	if not _isVisible(pane):
		return True
	if not hasattr(pane, 'paneCollapsed'):
		return False
	return pane.paneCollapsed

def _isVisible(pane):
	if not hasattr(pane, 'paneVisible'):
		return True
	return pane.paneVisible

class Sash(Tk.Frame):
	"""
	Sash is a Frame that contains several horizontally spanning Pane's
	(see above).  When any Pane changes in size, the Sash will handle
	the reconfiguration of the entire set of Panes.
	"""
	def __init__(self, master=None, orient=Tk.VERTICAL, cnf={}, **kw):
		if orient == Tk.VERTICAL:
			self.orientation = Tk.VERTICAL
		elif orient == Tk.HORIZONTAL:
			self.orientation = Tk.HORIZONTAL
		else:
			raise ValueError, 'unknown orientation'
		if self.orientation is Tk.VERTICAL:
			self._buttonDrag = self._buttonDragVertical
			cursor = 'sb_v_double_arrow'
		else:
			self._buttonDrag = self._buttonDragHorizontal
			cursor = 'sb_h_double_arrow'
		cnf = _cnfmerge((cnf, kw))
		Tk.Frame.__init__(self, master, cnf, cursor=cursor)
		self.needResize = self.master is self.winfo_toplevel()
		self.paneList = []
		self.bind('<Configure>', self._computeSize)
		self.bind('<ButtonPress-1>', self._buttonPress)
		self.bind('<ButtonRelease-1>', self._buttonRelease)

	def destroy(self):
		del self._buttonDrag
		del self.paneList
		self.reconfigure = None
		Tk.Frame.destroy(self)

	def addPane(self, pane, where=-1):
		pane.paneHeight = pane.winfo_reqheight()
		pane.paneWidth = pane.winfo_reqwidth()
		pane['cursor'] = 'arrow'
		if self.orientation is Tk.VERTICAL:
			side = Tk.TOP
			px = 0
			py = self.paneList and IPS / 2 or 0
		else:
			side = Tk.LEFT
			px = self.paneList and IPS / 2 or 0
			py = 0
		if where < 0:
			pane.pack(side=side, expand=Tk.TRUE, fill=Tk.BOTH,
					padx=px, pady=py)
			self.paneList.append(pane)
		else:
			pane.pack(side=side, expand=Tk.TRUE, fill=Tk.BOTH,
					padx=px, pady=py,
					after=self.paneList[where])
			self.paneList.insert(where, pane)

	def setVisible(self, pane, flag):
		if pane not in self.paneList:
			return
		pane.paneVisible = flag
		if pane.winfo_ismapped():
			self.reconfigure()

	def _computeSize(self, *args):
		if self.orientation is Tk.VERTICAL:
			height = IPS * len(self.paneList) - IPS
			width = 0
			self.reconfigure = self._reconfigureVertical
		else:
			height = 0
			width = IPS * len(self.paneList) - IPS
			self.reconfigure = self._reconfigureHorizontal
		for p in self.paneList:
			ht = p.winfo_reqheight()
			wd = p.winfo_reqwidth()
			if self.orientation is Tk.VERTICAL:
				height = height + ht
				if wd > width:
					width = wd
			else:
				if ht > height:
					height = ht
				width = width + wd
			p.paneHeight = ht
			p.paneWidth = wd
			if not hasattr(p, 'paneMinHeight'):
				p.paneMinHeight = 1
			if not hasattr(p, 'paneMinWidth'):
				p.paneMinWidth = 1
		for p in self.paneList:
			p.pack_forget()
		self.bind('<Configure>', self.reconfigure)
		self.reconfigure()

	def _reconfigureVertical(self, *args):
		totalHeight = 0.0
		numPanes = 0
		for p in self.paneList:
			if _isVisible(p):
				totalHeight = totalHeight + p.paneHeight
				numPanes = numPanes + 1
		if numPanes == 0:
			return
		myHeight = float(self.winfo_height())
		availableHeight = myHeight - IPS * numPanes + IPS
		ratio = availableHeight / totalHeight
		self.gapList = []
		y = 0.0
		for p in self.paneList:
			if not _isVisible(p):
				ht = 0
				p.paneHeight = p.paneHeight * ratio
			else:
				ht = p.paneHeight * ratio
				p.paneHeight = ht
			p.place(relx=0, relwidth=1, y=y, height=ht)
			y = y + ht + IPS
			self.gapList.append(y)

	def _reconfigureHorizontal(self, *args):
		totalWidth = 0.0
		numPanes = 0
		for p in self.paneList:
			if _isVisible(p):
				totalWidth = totalWidth + p.paneWidth
				numPanes = numPanes + 1
		if numPanes == 0:
			return
		myWidth = float(self.winfo_width())
		availableWidth = myWidth - IPS * numPanes + IPS
		ratio = availableWidth / totalWidth
		self.gapList = []
		x = 0.0
		for p in self.paneList:
			if not _isVisible(p):
				wd = 0
				p.paneWidth = p.paneWidth * ratio
			else:
				wd = p.paneWidth * ratio
				p.paneWidth = wd
			p.place(rely=0, relheight=1, x=x, width=wd)
			x = x + wd + IPS
			self.gapList.append(x)

	def _buttonPress(self, event):
		if self.orientation is Tk.VERTICAL:
			crd = event.y
		else:
			crd = event.x
		gapIndex = -1
		for i in range(len(self.gapList)):
			if crd < self.gapList[i]:
				gapIndex = i
				break
		if gapIndex == -1:
			raise SystemError, 'cannot identify sash gap'
		paneAbove = None
		for above in range(gapIndex, -1, -1):
			pane = self.paneList[above]
			if not _isCollapsed(pane):
				paneAbove = pane
				break
		if paneAbove is None:
			d = SimpleDialog(self.winfo_toplevel(),
				text='There is no adjustable pane above',
				buttons=['Okay'],
				title='User Error')
			d.go()
			return
		paneBelow = None
		for below in range(gapIndex + 1, len(self.paneList)):
			pane = self.paneList[below]
			if not _isCollapsed(pane):
				paneBelow = pane
				break
		if paneBelow is None:
			d = SimpleDialog(self.winfo_toplevel(),
				text='There is no adjustable pane below',
				buttons=['Okay'],
				title='User Error')
			d.go()
			return
		self.adjustAbove = paneAbove
		self.adjustBelow = paneBelow
		self.drag = crd
		self.bind('<Motion>', self._buttonDrag)

	def _buttonRelease(self, event):
		self.gapIndex = -1
		self.unbind('<Motion>')

	def _buttonDragVertical(self, event):
		delta = event.y - self.drag
		if delta < 2 and delta > -2:
			return
		aboveHt = self.adjustAbove.paneHeight + delta
		belowHt = self.adjustBelow.paneHeight - delta
		if aboveHt < self.adjustAbove.paneMinHeight \
		or belowHt < self.adjustBelow.paneMinHeight:
			return
		self.adjustAbove.paneHeight = aboveHt
		self.adjustBelow.paneHeight = belowHt
		self.reconfigure()
		self.drag = event.y

	def _buttonDragHorizontal(self, event):
		delta = event.x - self.drag
		if delta < 2 and delta > -2:
			return
		aboveWd = self.adjustAbove.paneWidth + delta
		belowWd = self.adjustBelow.paneWidth - delta
		if aboveWd < self.adjustAbove.paneMinWidth \
		or belowWd < self.adjustBelow.paneMinWidth:
			return
		self.adjustAbove.paneWidth = aboveWd
		self.adjustBelow.paneWidth = belowWd
		self.reconfigure()
		self.drag = event.x

if __name__ == '__main__':
	f = Sash()
	f.pack(expand=Tk.TRUE, fill=Tk.BOTH)

	p = CollapsiblePane(f, collapsed=1)
	f.addPane(p)
	e = Tk.Entry(p.frame, width=20)
	e.pack(side=Tk.TOP, expand=Tk.TRUE, fill=Tk.BOTH)

	b = Tk.Button(f, text='Quit', command=f.quit)
	f.addPane(b)

	e = Tk.Text(f, width=20, height=5)
	f.addPane(e, where=0)

	f.mainloop()
