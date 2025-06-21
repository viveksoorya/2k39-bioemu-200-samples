from MovieRecorder import MovieError, DEFAULT_OUTFILE
from MovieRecorder import RESET_CLEAR, RESET_KEEP, RESET_NONE
from Commands import CommandError

ignore_movie_commands = False

def movie_command(cmdname, args):

    if ignore_movie_commands:
        a0 = (args.split() + [''])[0]
        if not 'ignore'.startswith(a0):
            from chimera import replyobj
            replyobj.status('Ignoring command: %s %s' % (cmdname, args))
            return

    from Commands import perform_operation, string_arg, int_arg, ints_arg
    from Commands import bool_arg, float_arg, enum_arg
    reset_modes = (RESET_CLEAR, RESET_KEEP, RESET_NONE)
    ops = {
        'record': (record_op,
                   (),
                   (),
                   (('directory', string_arg),
                    ('pattern', string_arg),
                    ('format', string_arg),
                    ('fformat', string_arg),    # Obsolete
                    ('size', ints_arg),
                    ('supersample', int_arg),
                    ('raytrace', bool_arg),
                    ('limit', int_arg),)),

        'encode': (encode_multiple_op,
                   (),
                   (('output', string_arg, 'multiple'),),
                   (('format', string_arg),
                    ('quality', string_arg),
                    ('qscale', int_arg),
                    ('bitrate', float_arg),
                    ('framerate', float_arg),
                    ('resetMode', enum_arg, {'values': reset_modes}),
                    ('roundTrip', bool_arg),
                    ('wait', bool_arg),
                    ('mformat', string_arg),    # Obsolete
                    ('buffersize', float_arg),  # Obsolete
                    )),
        'crossfade': (crossfade_op, (), (('frames', int_arg),), ()),
        'duplicate': (duplicate_op, (), (('frames', int_arg),), ()),
        'stop': (stop_op, (), (), ()),
        'abort': (abort_op, (), (), ()),
        'reset': (reset_op,
                  (),
                  (('resetMode', enum_arg, {'values': reset_modes}),),
                  ()),
        'status': (status_op, (), (), ()),
        'formats': (formats_op, (), (), ()),
        'ignore': (ignore_op, (), (('ignore', bool_arg),), ()),
        }

    perform_operation(cmdname, args, ops)

def record_op(directory = None, pattern = None, format = None, fformat = None,
              size = None, supersample = 1, raytrace = False, limit = 15000):

    if format is None and fformat:
        format = fformat        # Historical option name.
    
    import RecorderGUI as RG
    if format is None:
        if raytrace:
            format = RG.defaultRaytraceImageFormat
        else:
            format = RG.defaultImageFormat
    else:
        fmts = RG.raytraceImageFormats if raytrace else RG.imageFormats
        format = format.upper()
        if not format in fmts:
            raise CommandError('Unsupported image file format %s, use %s'
                             % (format, ', '.join(fmts)))

    from os.path import isdir
    from OpenSave import tildeExpand
    if directory and not isdir(tildeExpand(directory)):
        raise CommandError('Directory %s does not exist' % (directory,))
    if pattern and pattern.count('*') != 1:
        raise CommandError('Pattern must contain exactly one "*"')

    if not size is None and len(size) != 2:
        raise CommandError('Size must be two comma-separated integers')

    if not supersample is None and supersample < 0:
        raise CommandError('Supersample must be a positive integer')

    try:
        getDirector().startRecording(format, directory, pattern,
                                     size, supersample, raytrace, limit)
    except MovieError, what:
        raise CommandError(what)

def encode_multiple_op(**kw):

    if 'output' in kw:
        kw1 = kw.copy()
        outputs = kw1.pop('output')
        r = kw1.pop('resetMode') if 'resetMode' in kw1 else RESET_CLEAR
        w = kw1.pop('wait') if 'wait' in kw1 else False
        for o in outputs[:-1]:
            encode_op(output = o, resetMode = RESET_NONE, wait = True, **kw1)
        encode_op(output = outputs[-1], resetMode = r, wait = w, **kw1)
    else:
        encode_op(**kw)
    
def encode_op(output=None, format=None,
              quality=None, qscale=None, bitrate=None,
              framerate=25, roundTrip=False,
              resetMode=RESET_CLEAR, wait=False,
              mformat=None, buffersize=None):

    import RecorderGUI as RG

    kw = {}
    if format is None:
        if mformat:
            format = mformat
        elif output:
            format = format_from_file_suffix(output)
    if format is None:
        f = RG.default_format
    elif format.lower() in RG.command_formats:
        f = RG.command_formats[format.lower()]
    else:
        raise CommandError('Unrecognized movie format %s' % format)
    if bitrate is None and qscale is None and quality is None:
        quality = RG.default_quality
    if quality:
        fmt_name = f[RG.format_name_field]
        import MoviePreferences
        qopt = MoviePreferences.MOVIE_FORMATS[fmt_name]['ffmpeg_quality']
        if qopt:
            kw['QUALITY'] = (qopt['option_name'], qopt[quality])
    elif qscale:
        kw['QUALITY'] = ('-qscale:v', qscale)
    elif bitrate:
        kw['BIT_RATE'] = bitrate

    if output is None:
        import os.path
        ext = f[RG.file_suffix_field]
        output = '%s.%s' % (os.path.splitext(DEFAULT_OUTFILE)[0], ext)

    kw['OUT_FILE'] = output
    kw['FORMAT'] = f[RG.file_format_field]
    kw['VIDEO_CODEC'] = f[RG.video_codec_field]
    kw['PIXEL_FORMAT'] = "yuv420p"
    kw['SIZE_RESTRICTION'] = f[RG.size_restriction_field]
    kw['FPS'] = framerate
    kw['PLAY_FORWARD_AND_BACKWARD'] = roundTrip
    kw['WAIT_FOR_ENCODING'] = wait

    # Only check the MPEG license acceptance when the movie encoding
    # format is one covered by the license.
    from MovieRecorder.license import acceptLicense
    if kw['FORMAT'] in ('mpeg2video', 'mp4') and not acceptLicense():
        from chimera import replyobj
        replyobj.warning('No acceptance of MPEG license agreement')
        return

    director = getDirector()
    r = director.recorder
    if r and r.isRecording():
        director.stopRecording()

    from MovieRecorder import cmdLineUI
    try:
        director.setResetMode(resetMode)
        director.startEncoding(cmdLineUI._notifyThreadStatus, **kw)
    except MovieError, what:
        raise CommandError(what)

def crossfade_op(frames=25):

    try:
        getDirector().postprocess('crossfade', frames)
    except MovieError, what:
        raise CommandError(what)

def duplicate_op(frames=25):

    try:
        getDirector().postprocess('duplicate', frames)
    except MovieError, what:
        raise CommandError(what)

def stop_op():

    try:
        getDirector().stopRecording()
    except MovieError, what:
        raise CommandError(what)

def abort_op():

    try:
        getDirector().stopEncoding()
    except MovieError, what:
        raise CommandError(what)

def reset_op(resetMode = RESET_CLEAR):

    clr = (resetMode == RESET_CLEAR)
    try:
        getDirector().resetRecorder(clearFrames=clr)
    except MovieError, what:
        raise CommandError(what)

def ignore_op(ignore = True):

    global ignore_movie_commands
    ignore_movie_commands = ignore

def status_op():

    try:
        getDirector().dumpStatusInfo()
    except MovieError, what:
        raise CommandError(what)

def formats_op():

    import RecorderGUI as RG
    flist = '\n'.join('\t%s\t=\t %s (.%s)' % (f[RG.format_name_field],
                                              f[RG.format_description_field],
                                              f[RG.file_suffix_field])
                      for f in RG.formats)
    fnames = ' '.join(f[RG.format_name_field] for f in RG.formats)
    from chimera import replyobj
    replyobj.info('Movie encoding formats:\n%s\n' % flist)
    replyobj.status('Movie formats: %s' % fnames)

def format_from_file_suffix(path):

    import RecorderGUI as RG
    for f in RG.formats:
        suffix = '.' + f[RG.file_suffix_field]
        if path.endswith(suffix):
            return f[RG.format_name_field]
    return None

def getDirector():

    import MovieRecorder
    return MovieRecorder.getDirector(setCmdLineUI = True)

def command_keywords():

    rec_args = ('directory', 'pattern', 'format', 'fformat', 'size',
                'supersample', 'raytrace', 'limit')
    enc_args = ('output', 'format', 'quality', 'bitrate', 'framerate',
                'resetMode', 'roundTrip', 'wait',
                'mformat', 'buffersize')
    cr_args = ('frames',)
    return rec_args + enc_args + cr_args

