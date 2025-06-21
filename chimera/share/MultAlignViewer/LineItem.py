# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: LoadHeaderDialog.py 29125 2009-10-22 23:49:08Z pett $

from math import cos, sin, tan, radians
cos18 = cos(radians(18.0))
sin54 = sin(radians(54.0))
tan18 = tan(radians(18.0))
tan36 = tan(radians(36.0))
sin36 = sin(radians(36.0))

class LineItem:
	def __init__(self, itemType, canvas, *args, **kw):
		self.canvas = canvas
		try:
			self.canvasItems = [
				getattr(canvas, "create_" + itemType)(*args, **kw)]
		except AttributeError:
			self.draw(itemType, *args, **kw)

	def configure(self, **kw):
		for item in self.canvasItems:
			self.canvas.itemconfigure(item, **kw)

	def coords(self, *args):
		if args:
			for item in self.canvasItems:
				self.canvas.coords(item, *args)
			return
			
		coords = [None] * 4
		for item in self.canvasItems:
			x1, y1, x2, y2 = self.canvas.coords(item)
			minX = min(x1, x2)
			if coords[0] == None:
				coords[0] = minX
			else:
				coords[0] = min(minX, coords[0])
			minY = min(y1, y2)
			if coords[1] == None:
				coords[1] = minY
			else:
				coords[1] = min(minY, coords[1])
			maxX = max(x1, x2)
			if coords[2] == None:
				coords[2] = maxX
			else:
				coords[2] = max(maxX, coords[2])
			maxY = max(y1, y2)
			if coords[3] == None:
				coords[3] = maxY
			else:
				coords[3] = max(maxY, coords[3])
		return coords

	def delete(self):
		for item in self.canvasItems:
			self.canvas.delete(item)
		self.canvasItems = []

	def move(self, *args):
		for item in self.canvasItems:
			self.canvas.move(item, *args)

	def tagBind(self, *args):
		for item in self.canvasItems:
			self.canvas.tag_bind(item, *args)

	def draw(self, symbol, *args, **kw):
		method = eval("self.draw%s" % (symbol[0].upper() + symbol[1:]))
		self.canvasItems = method(*args, **kw)

	supportedSymbols = []

	supportedSymbols.append("star")
	def drawStar(self, left, right, top, bottom, color):
		armLength = (0.9 * (right-left)/2.0) / cos18
		indentLength = armLength / (sin36 * (1.0/tan18 + 1.0/tan36))
		starHeight = armLength * (1 + sin54)
		starCenterX = (left+right)/2.0
		starCenterY = (bottom+top)/2.0 + armLength * (1.0 - sin54)/2.0
		polygonVals = []
		for angle in range(0, 360, 72):
			x = starCenterX + sin(radians(angle)) * armLength
			y = starCenterY - cos(radians(angle)) * armLength
			polygonVals.append(x)
			polygonVals.append(y)
			x = starCenterX + sin(radians(angle+36)) * indentLength
			y = starCenterY - cos(radians(angle+36)) * indentLength
			polygonVals.append(x)
			polygonVals.append(y)
		return [self.canvas.create_polygon(*polygonVals, fill=color,
				smooth=0, outline="black")]

	supportedSymbols.append("circle")
	def drawCircle(self, left, right, top, bottom, color):
		width = right - left
		diameter = 0.65 * width
		xmargin = 0.175 * width
		ymargin = ((bottom - top) - diameter) / 2.0
		return [self.canvas.create_oval(left+xmargin, top+ymargin,
			right-xmargin, bottom-ymargin, fill=color, outline="black")]

	supportedSymbols.append("square")
	def drawSquare(self, left, right, top, bottom, color):
		width = right - left
		xmargin = 0.2 * width
		ymargin = ((bottom - top) - 0.6 * width) / 2.0
		return [self.canvas.create_rectangle(left+xmargin, top+ymargin,
			right-xmargin, bottom-ymargin, fill=color, outline="black")]

	supportedSymbols.append("diamond")
	def drawDiamond(self, left, right, top, bottom, color):
		width = right - left
		xmargin = 0.15 * width
		midx = (left + right) / 2.0
		height = bottom - top
		ymargin = 0.1 * height
		midy = (top + bottom) / 2.0
		return[self.canvas.create_polygon(left+xmargin, midy, midx, top+ymargin,
				right-xmargin, midy, midx, bottom-ymargin,
				fill=color, outline="black")]

		return [self.canvas.create_rectangle(left+xmargin, top+ymargin,
			right-xmargin, bottom-ymargin, fill=color, outline="black")]
