# -----------------------------------------------------------------------------
# play command implementation.
#
def play_command(cmdname, args):

    from Commands import perform_operation, string_arg
    from Commands import bool_arg, float_arg, int_arg
    from Commands import atoms_arg, multiscale_surface_pieces_arg
    from Commands import model_arg, specifier_arg

    import explode, move, wave, wiggle, zipper
    ops = {
        'move': (move.move,
                 (('g1', string_arg),
                  ('g2', string_arg)),
                 (),
                 (('also', (string_arg, string_arg), {}, 'multiple'),
                  ('relative', bool_arg),
                  ('copies', bool_arg),
                  ('frames', int_arg))),
        'radial': (explode.move_surface_groups_radially,
                (('surfaces', multiscale_surface_pieces_arg),),
                (('factor', float_arg),
                 ('frames', int_arg)),
                ()),
        'wave': (wave.wave,
                 (('model1', model_arg),
                  ('model2', model_arg),
                  ('distanceStep', float_arg)),
                 (('frames', int_arg),),
                 (('pairChains', string_arg),
                  ('groupChains', string_arg),
                  ('equivalentChains', string_arg),
                  ('motionMethod', string_arg))),
        'wiggle': (wiggle.wiggle,
                   (('atoms', atoms_arg),),
                   (('branches', string_arg),
                    ('frames', int_arg)),
                   (('angle', float_arg),
                    ('speed', float_arg))),
        'zipper': (zipper.zipper,
                   (('residueList1', specifier_arg),
                    ('residueList2', specifier_arg)),
                   (('spacing', float_arg),
                    ('step', float_arg)),
                   ()),
        }

    perform_operation(cmdname, args, ops)

# -----------------------------------------------------------------------------
#
def unplay_command(cmdname, args):

    from Commands import perform_operation
    from Commands import float_arg, int_arg, multiscale_surface_pieces_arg

    import explode
    ops = {
        'radial': (explode.unmove_surface_groups_radially,
                (('surfaces', multiscale_surface_pieces_arg),),
                (('factor', float_arg),
                 ('frames', int_arg)),
                ()),
        }

    perform_operation(cmdname, args, ops)


# -----------------------------------------------------------------------------
#
def call_for_n_frames(func, n, args = [], done_cb = None):
    
    handler_params = [func, n, args, done_cb]
    import chimera
    h = chimera.triggers.addHandler('new frame', draw_frame_n, handler_params)
    handler_params.append(h)

# -----------------------------------------------------------------------------
#
def draw_frame_n(trigger_name, call_data, trigger_data):

    func, n, args, done_cb, h = call_data
    if len(args) >= n:
        alist = args[-n]
        if isinstance(alist, tuple):
            pass
        elif isinstance(alist, list):
            alist = tuple(alist)
        else:
            alist = (alist,)
    else:
        alist = ()
    try:
        func(*alist)
    except:
        import chimera
        chimera.triggers.deleteHandler('new frame', h)
        raise
    if n == 1:
        import chimera
        chimera.triggers.deleteHandler('new frame', h)
        if done_cb:
            done_cb()
    call_data[1] = n-1
