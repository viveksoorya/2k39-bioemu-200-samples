# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id$

# preferences for movie recording

import sys
defaults = {
	'encode_format': ('vp8' if sys.platform.startswith('linux') else 'h264'),
	'encode_bitrate': 2000,		# Kbits/sec
	'encode_quality': 'good',	# Variable bit rate quality
	'encode_framerate': 25,		# Frames/sec
	'record_format': 'PPM',
	'raytrace_format': 'PNG',
	}

#
# --- Preference category name and setting names ---
#

MOVIE = "Movie"

MOVIE_RECORD_FFORMAT = 'Image format'
MOVIE_RECORD_SUPERSAMPLE = 'Image supersampling'
MOVIE_ENCODE_FORMAT = 'Movie format'
MOVIE_ENCODE_TYPE = 'Playback bit rate'
MOVIE_ENCODE_QUALITY = 'Quality'
MOVIE_ENCODE_BITRATE = 'Constant bit rate (Kbits/s)'
MOVIE_ENCODE_FRAMERATE = 'Frames per second'
MOVIE_ENCODE_RESET = 'Reset mode'

#
# --- image formats ---
#

RECORD_FORMATS = ('JPEG', 'PNG', 'PPM')
RAYTRACE_FORMATS = ('PNG',)

#
# --- movie formats ---
#

from collections import OrderedDict
MOVIE_FORMATS = OrderedDict()
h264_quality = {'option_name':'-crf',
		'low':28, 'fair':25, 'medium':23, 'good':20,
		'high':18, 'higher':17, 'highest':15}
MOVIE_FORMATS['h264'] = {'label': 'H.264',
			 'suffix': 'mp4',
			 'ffmpeg_name': 'mp4',
			 'ffmpeg_codec': 'libx264',
			 'ffmpeg_quality': h264_quality,
			 'limited_framerates': False,
			 'size_restriction': (2,2),
			 }
vp8_quality = {'option_name':'-vb',
	       'low':'200k', 'fair':'500k', 'medium':'2000k',
	       'good':'4000k', 'high':'8000k', 'higher':'12000k',
	       'highest': '25000k'}
MOVIE_FORMATS['vp8'] = {'label': 'VP8/WebM',
			'suffix': 'webm',
			'ffmpeg_name': 'webm',
			'ffmpeg_codec': 'libvpx',
			'ffmpeg_quality': vp8_quality,
			'limited_framerates': False,
			'size_restriction': None,
			}
theora_quality = {'option_name':'-qscale',
		  'low':1, 'fair':3, 'medium':5, 'good':6,
		  'high':8, 'higher':9, 'highest':10}
MOVIE_FORMATS['theora'] = {'label': 'Theora',
			   'suffix': 'ogv',
			   'ffmpeg_name': 'ogg',
			   'ffmpeg_codec': 'libtheora',
			   'ffmpeg_quality': theora_quality,
			   'limited_framerates': False,
			   'size_restriction': None,
			   }
mpeg_quality = {'option_name':'-qscale',
		'low':25, 'fair':15, 'medium':10, 'good':8,
		'high':5, 'higher':3, 'highest':1}
MOVIE_FORMATS['mov'] = {'label': 'Quicktime',
			'suffix': 'mov',
			'ffmpeg_name': 'mov',
			'ffmpeg_codec': 'mpeg4',
			'ffmpeg_quality': mpeg_quality,
			'limited_framerates': False,
			'size_restriction': None,
			}
MOVIE_FORMATS['avi'] = {'label': 'AVI MSMPEG-4v2',
			'suffix': 'avi',
			'ffmpeg_name': 'avi',
			'ffmpeg_codec': 'msmpeg4v2',
			'ffmpeg_quality': mpeg_quality,
			'limited_framerates': False,
			'size_restriction': None,
			}
MOVIE_FORMATS['mp4'] = {'label': 'MPEG-4',
			'suffix': 'mp4',
			'ffmpeg_name': 'mp4',
			'ffmpeg_codec': None,
			'ffmpeg_quality': mpeg_quality,
			'limited_framerates': False,
			 'size_restriction': (2,2),
			}
MOVIE_FORMATS['mp2'] = {'label': 'MPEG-2',
			'suffix': 'mpg',
			'ffmpeg_name': 'mpeg2video',
			'ffmpeg_codec': None,
			'ffmpeg_quality': mpeg_quality,
			'limited_framerates': True,
			'size_restriction': None,
			}
MOVIE_FORMATS['mpeg'] = {'label': 'MPEG-1',
			 'suffix': 'mpg',
			 'ffmpeg_name': 'mpeg1video',
			 'ffmpeg_codec': None,
			 'ffmpeg_quality': mpeg_quality,
			 'limited_framerates': True,
			 'size_restriction': None,
			 }
MOVIE_FORMATS['wmv'] = {'label': 'WMV2',
			'suffix': 'wmv',
			'ffmpeg_name': 'asf',
			'ffmpeg_codec': 'wmv2',
			'ffmpeg_quality': vp8_quality,
			'limited_framerates': False,
			'size_restriction': None,
			}
MOVIE_FORMATS['apng'] = {'label': 'APNG',
			 'suffix': 'png',
			 'ffmpeg_name': 'apng',
			 'ffmpeg_codec': 'apng',
			 'ffmpeg_quality': None,
			 'limited_framerates': False,
			 'size_restriction': None,
			 }

movie_format_synonyms = {'webm': 'vp8',
			 'ogg': 'theora',
			 'ogv': 'theora',
			 'qt': 'mov',
			 'quicktime': 'mov'
			 }


#
# --- movie preferences ---
#

def updateNotify(option):
	'Notify interested tools that movie pref was modified'
	from chimera import triggers, MOVIE_PREF_UPDATE
	triggers.activateTrigger(MOVIE_PREF_UPDATE, option)

from chimera import tkoptions
class MovieRecordFFormatOption(tkoptions.SymbolicEnumOption):
	values = list(RECORD_FORMATS)
	labels = ['%s [.%s]' % (f, f.lower()) for f in RECORD_FORMATS]
	default = defaults['record_format']
	balloon = \
'''The format of saved image files.  Raytraced images are always
saved in PNG format regardless of this setting.'''

class MovieRecordSupersampleOption(tkoptions.SymbolicEnumOption):
	limit = 5
	values = list(range(limit))
	labels = (['none'] + ['on-screen'] +
		  ['%dx%d' % (y, y) for y in range(2, limit)])
	default = 0
	balloon = \
'''Supersampling refers to generating an initial image larger
than the window and sampling it down to the final size. Higher levels of
supersampling increase smoothness but also calculation time. 3x3 is
recommended when supersampling is done.  Rendering is normally off-screen,
but on-screen rendering (without supersampling) can be specified.'''

class MovieFormatOption(tkoptions.SymbolicEnumOption):
	values = list(MOVIE_FORMATS.keys())
	labels = ['%s [.%s]' % (x['label'], x['suffix'])
		  for x in MOVIE_FORMATS.values()]
	default = defaults['encode_format']
	balloon = ''

class MovieBitrateType(tkoptions.SymbolicEnumOption):
	values = list(range(2))
	labels = ['variable'] + ['constant']
	default = 0
	balloon = \
'''The playback bit rate relates to movie quality and file size. A higher bit
rate (at a given window size and frame rate) gives better movie quality
but also a larger file size.'''

class MovieQualityOption(tkoptions.SymbolicEnumOption):
	values = ['highest', 'higher', 'high', 'good', 'medium',
		  'fair', 'low']
	labels = values
	default = defaults['encode_quality']
	balloon = \
'''Higher encoding quality improves images but makes file size larger.'''

class MovieBitrateOption(tkoptions.IntOption):
	default = defaults['encode_bitrate'] # 2000
	balloon = \
'''Generally, 200 Kbits/s is low quality, 1000 medium, and 6000 high.'''

class MovieFramerateOption(tkoptions.IntOption):
	default = defaults['encode_framerate'] # 25
	balloon = '''Frames per second during playback.'''

class MovieResetOption(tkoptions.SymbolicEnumOption):
	CLEAR = 'clear'
	KEEP = 'keep'
	NONE = 'none'
	values = [CLEAR, KEEP, NONE]
	labels = ['reset and clear', 'reset and keep', 'none']
	default = CLEAR
	balloon = \
'''After movie encoding, reset frame counter to 0 and clear
(delete) images, or reset and keep images, or none (neither reset nor
remove images).'''

def registerMoviePreferences():

	moviePreferences = {
		# --- Encoding options
		MOVIE_ENCODE_FORMAT:
			(MovieFormatOption, MovieFormatOption.default, updateNotify),
		MOVIE_ENCODE_QUALITY:
			(MovieQualityOption, MovieQualityOption.default, None),
		MOVIE_ENCODE_BITRATE:
			(MovieBitrateOption, MovieBitrateOption.default, None),
		MOVIE_ENCODE_FRAMERATE:
			(MovieFramerateOption, MovieFramerateOption.default, None),
		MOVIE_ENCODE_RESET:
			(MovieResetOption, MovieResetOption.default, None),
		# --- Recording options
		MOVIE_RECORD_FFORMAT:
			(MovieRecordFFormatOption, MovieRecordFFormatOption.default, None),
		MOVIE_RECORD_SUPERSAMPLE:
			(MovieRecordSupersampleOption, MovieRecordSupersampleOption.default, None),
		}

	moviePreferencesOrder = [
		# Encoding
		MOVIE_ENCODE_FORMAT,
		MOVIE_ENCODE_QUALITY,
		MOVIE_ENCODE_BITRATE,
		MOVIE_ENCODE_FRAMERATE,
		MOVIE_ENCODE_RESET,
		# Recording
		MOVIE_RECORD_FFORMAT,
		MOVIE_RECORD_SUPERSAMPLE,
		]

	from chimera import preferences
	preferences.register(MOVIE, moviePreferences)
	preferences.setOrder(MOVIE, moviePreferencesOrder)

#
# --- movie preference functions ---
#

def display():
	'Display the movie preferences dialog.'
	# TODO: Only check the license when a preference is set for an output
	# encoding that is covered by the license.
	from chimera import dialogs
	pref = dialogs.display('preferences')
	pref.menu.invoke(index=MOVIE)

def get():
	'''Return the preference settings in a dictionary.
	prefs = {
		'movie_record': {'cmd': record_cmd, 'args':record_args},
		'movie_encode': {'cmd': encode_cmd, 'args':encode_args},
		}
	The 'args' values are a dictionary with keys that mirror the
	keyword movie command arguments.
	'''
	#
	# The purpose of this function is to provide preference values that are
	# compatible with the Midas movie command.

	#
	# Initialize all the input arguments for
	# MovieRecorder/__init__.processMovieCmd()
	record_args = dict(directory=None, pattern=None, fformat=None,
			   size=None, supersample=None, raytrace=None)
	encode_args = dict(output=None, bitrate=None, quality=None,
			   framerate=None, mformat=None,
			   resetMode=None)
	# This can be done with inspect (see get_args() below), but it's
	# not specific for record/encode arguments.
	#
	# Parse the preferences to contruct reasonable preference values; this is
	# required here because the preferences GUI doesn't have any validation or
	# callback contingencies while setting values (all values are deemed to be
	# indepedent in the preferences GUI, which is not true).
	size = None

	from chimera import preferences
	mformat = preferences.get(MOVIE, MOVIE_ENCODE_FORMAT)
	bitrate = preferences.get(MOVIE, MOVIE_ENCODE_BITRATE)

	# Construct movie recording arguments
	record_args['fformat'] = preferences.get(MOVIE, MOVIE_RECORD_FFORMAT)
	record_args['size'] = size
	record_args['supersample'] = preferences.get(MOVIE, MOVIE_RECORD_SUPERSAMPLE)

	# Construct movie encoding arguments
	ext = MOVIE_FORMATS[mformat]['suffix']
	encode_args['mformat'] = mformat
	encode_args['bitrate'] = bitrate
	encode_args['quality'] = preferences.get(MOVIE, MOVIE_ENCODE_QUALITY)
	encode_args['framerate'] = preferences.get(MOVIE, MOVIE_ENCODE_FRAMERATE)
	encode_args['resetMode'] = preferences.get(MOVIE, MOVIE_ENCODE_RESET)
	# Construct Midas commands
	record_cmd = 'movie record '
	for k, v in record_args.items():
		if v is not None:
			record_cmd += '%s %s ' % (k, str(v))
	encode_cmd = 'movie encode '
	for k, v in encode_args.items():
		if v is not None:
			encode_cmd += '%s %s ' % (k, str(v))
	# Contruct preferences data
	prefs = {
		'movie_record': {'cmd': record_cmd, 'args':record_args},
		'movie_encode': {'cmd': encode_cmd, 'args':encode_args},
		}
	return prefs

def get_args():
	import moviecmd
	args = dict((kw,None) for kw in moviecmd.command_keywords())
	prefs = get()
	args.update(prefs['movie_record']['args'])
	args.update(prefs['movie_encode']['args'])
	return args
