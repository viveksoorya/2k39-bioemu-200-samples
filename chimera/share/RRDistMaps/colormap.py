# --- UCSF Chimera Copyright ---
# Copyright (c) 2014 Regents of the University of California.
# All rights reserved. This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

_DRAG_NONE = -1
_DRAG_BOTH = 0
_DRAG_LOW = 1
_DRAG_HIGH = 2
_DRAG_HIGH_LOW = [ _DRAG_HIGH, _DRAG_LOW ]

_lo_lo = np.array((1.00, 1.00, 1.00))	# low D, low SD
_hi_lo = np.array((0.50, 0.50, 0.50))	# high D, low SD
_lo_hi = np.array((1.00, 0.00, 0.00))	# low D, high SD
_hi_hi = np.array((0.00, 0.50, 1.00))	# high D, high SD
_uncolored = np.array((0.20, 0.20, 0.20))	# color not in colormap

#comboColors = ( _lo_lo, _hi_lo, _lo_hi, _hi_hi )
comboColors = ( _lo_lo, _lo_hi, _hi_lo, _hi_hi )
distColors = ( _lo_lo, _hi_lo )
sdColors = ( _lo_lo, _lo_hi )
noColor = _uncolored
diffColors = ( np.array((1.0,1.0,0.0)),
		np.array((0.0,0.0,0.0)),
		np.array((0.0,1.0,1.0)) )

class ColorMap:
	"""Color map for scalar quantities."""

	Resolution = 10

	def __init__(self, fig, ax, colors, minmax, vFormat="%.2f",
			bg=_uncolored, resolution=Resolution, cb=None,
			numColors=2):
		if len(colors) != numColors:
			raise ValueError("expected %d colors" % numColors)
		if len(minmax) != 2:
			raise ValueError("expected 2 values for minmax")
		self.fig = fig
		self.ax = ax
		self.minmax = minmax
		self.resolution = resolution
		if minmax[0] == minmax[1]:
			self._dataRange = 1.0
		else:
			self._dataRange = minmax[1] - minmax[0]
		self.vFormat = vFormat
		self.bg = bg
		self.cb = cb
		self._makeMap(colors)
		self._drawMap()
		self._dragging = _DRAG_NONE

	def _makeMap(self, colors):
		self.colors = colors
		self._map = np.empty((self.resolution + 1, 1, 3))
		scale = 1.0 / (self.resolution - 1)
		for i in range(self.resolution):
			f = i * scale
			self._map[i, 0] = f * colors[1] + (1.0 - f) * colors[0]
		self._map[self.resolution, 0] = colors[1]
		self._filteredMap = self._map.copy()

	def _drawMap(self):
		self.ax.imshow(self._map, aspect='auto', origin='lower',
					extent=(0, 1,
						0, self.resolution + 1),
					interpolation='nearest')
		self.ax.yaxis.tick_right()
		self.ax.xaxis.set_label_position("top")
		self.ax.set_ylim([0, self.resolution])
		self._drawAxes(0, self.resolution)
		# Figure out pixel with in data coordinate system
		d0, d1 = self.ax.transData.transform([(0, 0), (1, 1)])
		self.px = 1.0 / (d1[0] - d0[0])
		self.py = 1.0 / (d1[1] - d0[1])
		xy = self.px, self.py
		w, h = 1.0 - 2 * self.px, self.resolution - 2 * self.py
		from matplotlib.patches import Rectangle
		self.rectangle = self.ax.add_patch(Rectangle(xy, w, h,
							fc='none',
							ec=(0, 1, 0, 1)))

	def _drawAxes(self, bottom, top):
		self.ax.set_yticks([bottom, top])
		# bottom/top are in image/pixel coordinates
		# we want labels in data coordinates
		# Map 0..self.resolution to minmax[0]..minmax[1]
		scale = self._dataRange / self.resolution
		lo = bottom * scale + self.minmax[0]
		hi = top * scale + self.minmax[0]
		self.ax.set_yticklabels([ self.vFormat % lo,
						self.vFormat % hi ])

	def makeImage(self, ci):
		return self._filteredMap[ci, 0]

	def onPress(self, event):
		y = int(self.rectangle.get_xy()[1] + 0.1)
		h = int(self.rectangle.get_height() + 0.1)
		bottom = y
		top = y + h
		self._dragging = _findTarget(event.ydata, bottom, top,
							self.resolution)
		self._lastDrag = int(event.ydata + 0.5)

	def onMotion(self, event):
		if self._dragging == _DRAG_NONE:
			return
		# Check if there is sufficient movement
		my = int(event.ydata + 0.5)
		delta = my - self._lastDrag
		if delta == 0:
			return
		# Compute current top and height
		y = int(self.rectangle.get_xy()[1] - self.py + 0.1)
		h = int(self.rectangle.get_height() + 2 * self.py + 0.1)
		# Compute new top and height
		nb = bottom = y
		nt = top = y + h
		if self._dragging == _DRAG_BOTH:
			nb += delta
			nt += delta
		elif self._dragging == _DRAG_LOW:
			nb += delta
		else:	# _DRAG_HIGH
			nt += delta
		# Check for out of bounds
		if nb < 0 or nt > self.resolution or nb >= nt:
			return
		# Check for no change again
		if nb == bottom and nt == top:
			return
		# Update rectangle dimensions and save state
		self._drawAxes(nb, nt)
		self.rectangle.set_bounds(self.px, nb + self.py,
						1.0 - 2 * self.px,
						nt - nb - 2 * self.py)
		self.fig.draw()
		self._lastDrag = my
		self._filteredMap[:nb,0] = self.bg
		self._filteredMap[nb:nt+1,0] = self._map[nb:nt+1,0]
		self._filteredMap[nt+1:,0] = self.bg
		self.cb(nb, nt)

	def onRelease(self, event):
		self._dragging = _DRAG_NONE


class ColorMapDifference(ColorMap):
	"""Color map for difference maps."""

	def __init__(self, *args, **kw):
		ColorMap.__init__(self, *args, numColors=3, **kw)

	def _makeMap(self, colors):
		# colors is a 3-tuple of (negative, zero, positive) colors
		self.colors = colors
		self._map = np.empty((self.resolution + 1, 1, 3))
		scale = 1.0 / (self.resolution - 1)
		for i in range(self.resolution):
			f = i * scale
			v = self.minmax[0] + i * scale * self._dataRange
			if v < 0:
				f = v / self.minmax[0]
				c = f * colors[0] + (1.0 - f) * colors[1]
			else:
				f = v / self.minmax[1]
				c = f * colors[2] + (1.0 - f) * colors[1]
			self._map[i, 0] = c
		self._map[self.resolution, 0] = colors[2]
		self._filteredMap = self._map.copy()


class ColorMap2D:
	"""Color map for 2-vector quantities."""

	XResolution = 10
	YResolution = 10

	# indices for colors
	LL = 0
	LR = 1
	UL = 2
	UR = 3

	def __init__(self, fig, ax, colors, xminmax, yminmax,
				xFormat="%.1f", yFormat="%.2f",
				xResolution=XResolution,
				yResolution=YResolution,
				bg=_uncolored, cb=None):
		if len(colors) != 4:
			raise ValueError("wrong number of colors")
		if len(xminmax) != 2 or len(yminmax) != 2:
			raise ValueError("expected 2 values for minmax")
		self.fig = fig
		self.ax = ax
		self.colors = colors
		self.xminmax = xminmax
		if self.xminmax[0] == self.xminmax[1]:
			self._xRange = 1.0
		else:
			self._xRange = self.xminmax[1] - self.xminmax[0]
		self.yminmax = yminmax
		if self.yminmax[0] == self.yminmax[1]:
			self._yRange = 1.0
		else:
			self._yRange = self.yminmax[1] - self.yminmax[0]
		self.xFormat = xFormat
		self.yFormat = yFormat
		self.xResolution = xResolution
		self.yResolution = yResolution
		self.bg = bg
		self.cb = cb
		self._makeMap(colors)
		self._drawMap()
		self._hDragging = _DRAG_NONE
		self._vDragging = _DRAG_NONE

	def _makeMap(self, colors):
		self._map = np.empty((self.yResolution + 1,
					self.xResolution + 1, 3))
		colScale = 1.0 / (self.xResolution - 1)
		rowScale = 1.0 / (self.yResolution - 1)
		for row in range(self.yResolution):
			rf = row * rowScale
			rfm = 1 - rf
			for col in range(self.xResolution):
				cf = col * colScale
				cfm = 1 - cf
				ll = rfm * cfm
				lr = rfm * cf
				ul = rf * cfm
				ur = rf * cf
				self._map[row, col] = (ll * colors[self.LL]
							+ lr * colors[self.LR]
							+ ul * colors[self.UL]
							+ ur * colors[self.UR])
		# Fill in extra row and column corresponding to maximum values
		for row in range(self.yResolution):
			self._map[row, self.xResolution] = \
					self._map[row, self.xResolution - 1]
		for col in range(self.xResolution):
			self._map[self.yResolution, col] = \
					self._map[self.yResolution - 1, col]
		self._map[self.yResolution, self.xResolution] = colors[self.UR]
		self._filteredMap = self._map.copy()

	def _drawMap(self):
		self.ax.imshow(self._map, aspect='auto', origin='lower',
					extent=(0, self.xResolution + 1,
						0, self.yResolution + 1),
					interpolation='nearest')
		self.ax.yaxis.tick_right()
		self.ax.xaxis.set_label_position("top")
		self.ax.set_xlim([0, self.xResolution])
		self.ax.set_ylim([0, self.yResolution])
		self._drawAxes(0, self.xResolution, 0, self.yResolution)
		# Figure out pixel with in data coordinate system
		d0, d1 = self.ax.transData.transform([(0, 0), (1, 1)])
		self.px = 1.0 / (d1[0] - d0[0])
		self.py = 1.0 / (d1[1] - d0[1])
		from matplotlib.patches import Rectangle
		xy = self.px, self.py
		w = self.xResolution - 2 * self.px
		h = self.yResolution - 2 * self.py
		self.rectangle = self.ax.add_patch(Rectangle(xy, w, h,
							fc='none',
							ec=(0, 1, 0, 1)))

	def _drawAxes(self, left, right, bottom, top):
		self.ax.set_xticks([left, right])
		self.ax.set_yticks([bottom, top])
		# left/right/bottom/top are in image/pixel coordinates
		# we want labels in data coordinates
		# Map 0..self.xResolution to xminmax[0]..xminmax[1]
		# Map 0..self.yResolution to yminmax[0]..yminmax[1]
		scale = self._xRange / self.xResolution
		lo = left * scale + self.xminmax[0]
		hi = right * scale + self.xminmax[0]
		self.ax.set_xticklabels([ self.xFormat % lo,
						self.xFormat % hi ],
						rotation="vertical")
		scale = self._yRange / self.yResolution
		lo = bottom * scale + self.yminmax[0]
		hi = top * scale + self.yminmax[0]
		self.ax.set_yticklabels([ self.yFormat % lo,
						self.yFormat % hi ])

	def makeImage(self, yi, xi):
		return self._filteredMap[yi, xi]

	def onPress(self, event):
		xy = self.rectangle.get_xy()
		x = int(xy[0] + 0.1)
		y = int(xy[1] + 0.1)
		w = int(self.rectangle.get_width() + 0.1)
		h = int(self.rectangle.get_height() + 0.1)
		left = x
		right = x + w
		bottom = y
		top = y + h
		self._hDragging = _findTarget(event.xdata, left, right,
							self.xResolution)
		self._vDragging = _findTarget(event.ydata, bottom, top,
							self.yResolution)
		# If we are moving only one edge in one direction,
		# then we do not allow dragging in the other because
		# it gets confusing for the user
		if self._hDragging == _DRAG_BOTH:
			if self._vDragging in _DRAG_HIGH_LOW:
				self._hDragging = _DRAG_NONE
		if self._vDragging == _DRAG_BOTH:
			if self._hDragging in _DRAG_HIGH_LOW:
				self._vDragging = _DRAG_NONE
		self._lastDragX = int(event.xdata + 0.5)
		self._lastDragY = int(event.ydata + 0.5)

	def onMotion(self, event):
		if (self._hDragging == _DRAG_NONE
				and self._vDragging == _DRAG_NONE):
			return
		# Check if there is sufficient movement
		mx = int(event.xdata + 0.5)
		my = int(event.ydata + 0.5)
		deltaX = mx - self._lastDragX
		deltaY = my - self._lastDragY
		if deltaX == 0 and deltaY == 0:
			return
		# Compute current top and height
		xy = self.rectangle.get_xy()
		y = int(xy[1] - self.py + 0.1)
		h = int(self.rectangle.get_height() + 2 * self.py + 0.1)
		# Compute old and new edge coordinates
		nb = bottom = y
		nt = top = y + h
		if self._vDragging == _DRAG_BOTH:
			nb += deltaY
			nt += deltaY
		elif self._vDragging == _DRAG_LOW:
			nb += deltaY
		elif self._vDragging == _DRAG_HIGH:
			nt += deltaY
		x = int(xy[0] - self.px + 0.1)
		w = int(self.rectangle.get_width() + 2 * self.px + 0.1)
		nl = left = x
		nr = right = x + w
		if self._hDragging == _DRAG_BOTH:
			nl += deltaX
			nr += deltaX
		elif self._hDragging == _DRAG_LOW:
			nl += deltaX
		elif self._hDragging == _DRAG_HIGH:
			nr += deltaX
		# Check for out of bounds:
		if nb < 0 or nt > self.yResolution or nb >= nt:
			return
		if nl < 0 or nr > self.xResolution or nl >= nr:
			return
		# Check for no change again
		if nb == bottom and nt == top and nl == left and nr == right:
			return
		# Update rectangle dimensions and save state
		self._drawAxes(nl, nr, nb, nt)
		self.rectangle.set_bounds(nl + self.px, nb + self.py,
						nr - nl - 2 * self.px,
						nt - nb - 2 * self.py)
		self.fig.draw()
		self._lastDragX = mx
		self._lastDragY = my
		self._filteredMap[nb:nt+1,nl:nr+1] = self._map[nb:nt+1,nl:nr+1]
		self._filteredMap[:nb,:] = self.bg
		self._filteredMap[nt + 1:,:] = self.bg
		self._filteredMap[:,:nl] = self.bg
		self._filteredMap[:,nr + 1:] = self.bg
		if self.cb:
			self.cb(nl, nr, nb, nt)

	def onRelease(self, event):
		self._hDragging = _DRAG_NONE
		self._vDragging = _DRAG_NONE

def _findTarget(coord, lo, hi, total):
	"""Return -1 to move lo, 0 to move both, 1 to move hi"""
	near = total * 0.25
	if coord <= lo:
		# Less than lo, can at most drag lo
		delta = lo - coord
		if delta > near:
			return _DRAG_NONE
		return _DRAG_LOW
	elif coord >= hi:
		# Greater than hi, can at most drag hi
		delta = coord - hi
		if delta > near:
			return _DRAG_NONE
		return _DRAG_HIGH
	else:
		# Between lo and hi, choose base on nearest edge or middle
		which = _DRAG_LOW
		delta = coord - lo
		dhi = hi - coord
		if dhi < delta:
			which = _DRAG_HIGH
			delta = dhi
		dmid = abs(coord - (lo + hi) / 2.0)
		if dmid < delta:
			which = _DRAG_BOTH
		return which
