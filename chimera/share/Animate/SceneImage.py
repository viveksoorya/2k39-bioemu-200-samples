# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

from PIL import Image, ImageEnhance
import Icons

ViewImageSize = (128, 128)

DEBUG = 0


## Adapted from http://code.activestate.com/recipes/362879/

def reduce_opacity(im, opacity):
	"""Returns an image with reduced opacity."""
	assert opacity >= 0 and opacity <= 1
	if im.mode != 'RGBA':
		im = im.convert('RGBA')
	else:
		im = im.copy()
	alpha = im.split()[3]
	alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
	im.putalpha(alpha)
	return im

def watermark(im, mark, position, opacity=1):
	"""Adds a watermark to an image."""
	if opacity < 1:
		mark = reduce_opacity(mark, opacity)
	if im.mode != 'RGBA':
		im = im.convert('RGBA')
	# create a transparent layer the size of the image and draw the
	# watermark in that layer.
	layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
	if position == 'tile':
		for y in range(0, im.size[1], mark.size[1]):
			for x in range(0, im.size[0], mark.size[0]):
				layer.paste(mark, (x, y))
	elif position == 'scale':
		# scale, but preserve the aspect ratio
		ratioX = float(im.size[0]) / mark.size[0]
		ratioY = float(im.size[1]) / mark.size[1]
		ratio = min(ratioX, ratioY)
		w = int(mark.size[0] * ratio)
		h = int(mark.size[1] * ratio)
		mark = mark.resize((w, h))
		layer.paste(mark, ((im.size[0] - w) / 2, (im.size[1] - h) / 2))
	else:
		layer.paste(mark, position)
	# composite the image with the layer
	return Image.composite(layer, im, layer)

## End http://code.activestate.com/recipes/362879/



class SceneImage(object):
	'''Scene viewer images and thumb-nail image'''

	#
	# -- descriptor methods --
	#

	# owner is Scene class; instance is a Scene() object
	def __get__(self, instance, owner):	 # Return attr value
		if instance:
			return instance._img
		#else, attr access on the owner (Scene class)

	def __set__(self, instance, value):	 # Return nothing (None)
		# value is 'thumbnail' or 'orphaned' and the latter is used
		# to overlay a watermark to indicate a scene has orphaned data.
		# This is related to removing models in a scene, which is coded
		# in various 'integrity' methods of Scene.py, Scenes.py, etc.
		try:
			# capture chimera viewer display
			self.viewImages(instance)
			# Use only the left-side of the viewer display
			img = instance._viewImages[0].copy()
			# Resample the image into a thumbnail image (in-place)
			img.thumbnail(instance.imgSize, Image.ANTIALIAS)
			if value == 'orphaned':
				# Overlay a watermark on the scene thumbnail
				mark = Icons.LoadImage('orphaned.png')
				img = watermark(img, mark, 'scale', opacity=0.4)
			instance._img = img
		except IOError:
			from chimera import replyobj
			msg = "cannot create thumb-nail for scene: ", instance.name
			replyobj.warning(msg)

	def __delete__(self, instance):		 # Return nothing (None)
		del instance._img
		del instance._viewImages

	def viewImages(self, instance):
		# OPTION: Use the chimera.printer module to get an image thumbnail,
		# not using this because chimera can crash when saving images.
		# Note: with supersample>0, the image is captured from off-screen
		# rendering and we don't need to worry about anything overlapping
		# or obscuring the Chimera display.
		viewImages = getattr(instance, '_viewImages', None)
		if viewImages:
			# don't replace them, most often we just want to
			# resample them to change the thumbnail image size.
			# The viewImages are saved only when a scene is
			# created.
			return
		try:
			from chimera import viewer
			#ViewImageSize = viewer.windowSize
			instance._viewImages = viewer.pilImages(*ViewImageSize, supersample=2)
		except IOError:
			from chimera import replyobj
			msg = "cannot create view image for scene: ", instance.name
			replyobj.warning(msg)




#def test():
#	im = Image.open('test.png')
#	mark = Image.open('overlay.png')
#	watermark(im, mark, 'tile', 0.5).show()
#	watermark(im, mark, 'scale', 1.0).show()
#	watermark(im, mark, (100, 100), 0.5).show()

#if __name__ == '__main__':
#	test()
