# -----------------------------------------------------------------------------
# Dialog for manipulating multiscale models.
#

import chimera
from chimera.baseDialog import ModelessDialog

# -----------------------------------------------------------------------------
#
class MultiScale_Manager:

  def __init__(self):

    #
    # Default surfacing parameters
    #
    self.default_surface_resolution = 8                 # Angstroms
    self.default_density_threshold = .02
    self.default_density_threshold_ca_only = .002
    self.default_smoothing_factor = .3
    self.default_smoothing_iterations = 2

    self.models = []               # Model_Piece root objects

    self.surfacer = Chain_Surfacer()

    t = chimera.triggers
    t.addHandler('Atom', self.atom_deleted_cb, None)

    import SimpleSession
    t.addHandler(SimpleSession.SAVE_SESSION, self.save_session_cb, None)
    
  # ---------------------------------------------------------------------------
  #
  def atom_deleted_cb(self, trigger, cdata, tdata):

    if len(tdata.deleted) == 0 or len(self.models) == 0:
      return

    # Figure out which chain pieces have cached atom data change.
    cpx = []
    cdx = set()
    for cp in find_pieces(self.models, Chain_Piece):
      lc = cp.lan_chain
      mcd = lc.molecule_chain_data(load = False)  # clone molecule chain data
      if mcd is None:
        mcd = lc.lan_molecule.chain_data()  # source molecule
      if mcd:
        if (mcd, lc.chain_id) in cdx:
          cpx.append(cp)
        elif mcd.update_cached_chain_data(lc.chain_id):
          cpx.append(cp)
          cdx.add((mcd, lc.chain_id))

    # Update chain piece surfaces without using cached surface geometry.
    for cp in cpx:
      cp.resurface(use_cache = False)
    
  # ---------------------------------------------------------------------------
  #
  def save_session_cb(self, trigger, x, file):

    import session
    session.save_multiscale_state(self, multiscale_model_dialog(), file)
  
  # ---------------------------------------------------------------------------
  #
  def add_models(self, mlist, show = True, surf_params = None):

    self.models.extend(mlist)

    for m in mlist:
      m.add_model_closed_callback(self.delete_model)

    source_molecules = {}
    for cp in find_pieces(mlist, Chain_Piece):
      source_molecules[cp.lan_chain.lan_molecule.source_molecule] = 1
    for mol in source_molecules.keys():
      chimera.addModelClosedCallback(mol, self.closed_source_molecule_cb)
      
    if show:
      self.show_surfaces(mlist, surf_params)

  # ---------------------------------------------------------------------------
  #
  def show_surfaces(self, plist, surf_params = None):

    if surf_params is None:
      surf_params = self.default_surface_parameters()

    cplist = find_pieces(plist, Chain_Piece)
    for cp in cplist:
      cp.show_style('surface', surf_params)

  # ---------------------------------------------------------------------------
  #
  def default_surface_parameters(self):

    return (self.default_surface_resolution,
            self.default_density_threshold,
            self.default_density_threshold_ca_only,
            self.default_smoothing_factor,
            self.default_smoothing_iterations)

  # ---------------------------------------------------------------------------
  #
  def chain_pieces(self):

    return find_pieces(self.models, Chain_Piece)

  # ---------------------------------------------------------------------------
  # Only selects surface pieces associated with chains.
  #
  def select_chains(self, chain_pieces, extend_selection = False):
    
    spieces = []
    for c in chain_pieces:
      sg = c.surface_piece
      if sg:
        spieces.append(sg)

    from chimera import selection
    if extend_selection:
      selection.addCurrent(spieces)
    else:
      selection.setCurrent(spieces)

  # ---------------------------------------------------------------------------
  #
  def selected_chains(self, selected_surfaces_only = False):

    from Surface import selected_surface_pieces
    surface_pieces = selected_surface_pieces()

    if selected_surfaces_only:
      rlist = []
    else:
      from chimera import selection
      rlist = selection.currentResidues()

    chains = containing_chain_pieces(surface_pieces, rlist)
    return chains

  # ---------------------------------------------------------------------------
  #
  def select_sequence_copies(self):

    seqs = {}
    for cp in self.selected_chains():
      seqs[cp.lan_chain.sequence()] = 1

    cplist = []
    for cp in self.chain_pieces():
      seq = cp.lan_chain.sequence()
      if seq in seqs:
        cplist.append(cp)

    self.select_chains(cplist, extend_selection = True)

  # ---------------------------------------------------------------------------
  #
  def make_multimers(self, pdb_models, get_transform_matrices,
                     show = True, surf_params = None):

    mtable = modeled_molecules(self.models)

    mmlist = []
    for mol in pdb_models:
      if isinstance(mol, chimera.Molecule) and not mtable.has_key(mol):
        matrices = get_transform_matrices(mol)
        m = self.molecule_multimer(mol, matrices, show, surf_params)
        mmlist.append(m)

    return mmlist

  # ---------------------------------------------------------------------------
  # The matrix_tree argument can be a list or nested lists.
  # For nested lists an equivalent group hierarchy is created.
  #
  def molecule_multimer(self, molecule, matrix_tree,
                        show = True, surf_params = None):

    if surf_params is None:
      surf_params = self.default_surface_parameters()

    n = tree_size(matrix_tree, is_matrix)
    if n == 0:
      from Matrix import identity_matrix
      matrix_tree = [identity_matrix()]
      n = 1
    xform_tree = numbered_xforms(matrix_tree)
    m = self.make_multimer(molecule, xform_tree)
    self.add_models([m], show, surf_params)
    if show:
      for cp in find_pieces([m], Chain_Piece):
        if cp.lan_chain.is_loaded():
          if n > 1:
            cp.show_surface(False)    # Show original molecule
          else:
            cp.show_only_style('surface', surf_params)
    return m
  
  # ---------------------------------------------------------------------------
  #
  def make_multimer(self, molecule, xform_tree):

    return molecule_multimer(molecule, self.surfacer, xform_tree)

  # ---------------------------------------------------------------------------
  #
  def selected_multiscale_models(self):

    mtable = {}
    for cp in self.selected_chains():
      mtable[cp.root()] = 1

    return mtable.keys()

  # ---------------------------------------------------------------------------
  #
  def closed_source_molecule_cb(self, molecule):

    cplist = filter(lambda cp: cp.lan_chain.lan_molecule.source_molecule == molecule,
                    self.chain_pieces())
    self.delete_childless_pieces(cplist)
      
  # ---------------------------------------------------------------------------
  # Deletes childless pieces and all parents which become childless as a
  # result.
  #
  def delete_childless_pieces(self, plist):

    parents = {}
    for p in plist:
      if len(p.children) == 0:
        parent = p.parent
        if parent:
          parent.children.remove(p)
          parents[parent] = 1
        p.delete()

    if parents:
      self.delete_childless_pieces(parents.keys())
  
  # ---------------------------------------------------------------------------
  #
  def delete_models(self, mlist):

    # Keep the same list object since the dialog references it.
    keep = subtract_lists(self.models, mlist)
    del self.models[:]
    self.models.extend(keep)

    for m in mlist:
      m.remove_model_closed_callback(self.delete_model)
      m.delete()
  
  # ---------------------------------------------------------------------------
  #
  def delete_model(self, m):

    self.delete_models([m])

# -----------------------------------------------------------------------------
#
class MultiScale_Model_Dialog(ModelessDialog):

  title = 'Multiscale Models'
  name = 'multiscale models'
  buttons = ('Close',)
  help = 'ContributedSoftware/multiscale/framemulti.html'
  
  def fillInUI(self, parent):

    # For backward compatibility with PDB and VIPERdb image scripts.
    self.models = multiscale_manager().models

    self.default_selection_range = 5
    
    self.selection_trigger = None

    self.toplevel_widget = parent.winfo_toplevel()
    self.toplevel_widget.withdraw()
    
    row = 0

    import Tkinter
    from CGLtk import Hybrid

    scl = Tkinter.Label(parent, text = 'Select chains')
    scl.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    sc = Hybrid.Button_Row(parent, ' ',
                           (('All', self.select_all_chains_cb),
                            ('With loaded atoms', self.select_loaded_chains_cb),
                            ('Clear', self.clear_selection_cb),
                            ))
    sc.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    sec = Hybrid.Button_Row(parent, ' Extend ',
                           (('Up', self.promote_selection_cb),
                            ('Copies', self.select_copies_cb),
                            ('Atoms', self.select_atoms_cb),
                            ('Loaded atoms', lambda: self.select_atoms_cb(True)),
                            ))
    sec.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    nrf = Tkinter.Frame(parent, padx = 10)
    nrf.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    nb = Tkinter.Button(nrf, text = 'Near', command = self.select_near_cb)
    nb.grid(row = 0, column = 0, sticky = 'w')

    nb = Tkinter.Button(nrf, text = 'Contacts'
                        , command = self.select_contacts_cb)
    nb.grid(row = 0, column = 1, sticky = 'w')

    nr = Hybrid.Entry(nrf, ' Range ', 3, str(self.default_selection_range))
    nr.frame.grid(row = 0, column = 2, sticky = 'w')
    self.selection_range = nr.variable
    
    nla = Hybrid.Checkbutton(nrf, 'Load atoms', 0)
    nla.button.grid(row = 0, column = 3, sticky = 'w', padx = 5)
    self.load_nearby_atoms = nla.variable
    
    div = Tkinter.Frame(parent, relief = Tkinter.GROOVE,
                        borderwidth=1, height=2)
    div.grid(row = row, column = 0, sticky = 'ew', pady = 10)
    row = row + 1
    
    al = Tkinter.Label(parent, text = 'Act on selected chains')
    al.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    af = Tkinter.Frame(parent, padx = 10)
    af.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    arow = 0
    
    sc = Hybrid.Button_Row(af, 'Selected chains ',
                           (('Show', self.show_selected_surfaces_cb),
                            ('Hide', self.hide_selected_surfaces_cb),
                            ('Hide all styles', self.hide_selected_cb),
                            ))
    sc.frame.grid(row = arow, column = 0, sticky = 'w')
    arow = arow + 1

    oc = Hybrid.Button_Row(af, 'Other chains ',
                           (('Show', self.show_other_surfaces_cb),
                            ('Hide', self.hide_other_surfaces_cb),
                            ('Hide all styles', self.hide_others_cb),
                            ))
    oc.frame.grid(row = arow, column = 0, sticky = 'w')
    arow = arow + 1

    sf = Tkinter.Frame(af)
    sf.grid(row = arow, column = 0, sticky = 'w')
    arow = arow + 1

    sl = Tkinter.Label(sf, text = 'Style ')
    sl.grid(row = 0, column = 0, sticky = 'w')

    som = Hybrid.Menu(sf, 'Show...',
                      (('Surface', self.show_only_surface_cb),
                       ('Ribbon', self.show_only_ribbon_cb),
                       ('Wire', self.show_only_wire_cb),
                       ('Stick', self.show_only_stick_cb),
                       ('Ball & Stick', self.show_only_ball_and_stick_cb),
                       ('Sphere', self.show_only_sphere_cb),))
    som.button['relief'] = 'raised'
    som.button.grid(row = 0, column = 1, sticky = 'w')
    
    sm = Hybrid.Menu(sf, 'Show also...',
                     (('Surface', self.show_surface_cb),
                       ('Ribbon', self.show_ribbon_cb),
                       ('Wire', self.show_wire_cb),
                       ('Stick', self.show_stick_cb),
                       ('Ball & Stick', self.show_ball_and_stick_cb),
                       ('Sphere', self.show_sphere_cb),))
    sm.button['relief'] = 'raised'
    sm.button.grid(row = 0, column = 2, sticky = 'w')

    hm = Hybrid.Menu(sf, 'Hide...',
                     (('Surface', self.hide_surface_cb),
                      ('Ribbon', self.hide_ribbon_cb),
                      ('Atoms and Bonds', self.hide_atoms_cb),))
    hm.button['relief'] = 'raised'
    hm.button.grid(row = 0, column = 3, sticky = 'w')

    cf = Tkinter.Frame(af)
    cf.grid(row = arow, column = 0, sticky = 'w')
    arow = arow + 1

    ch = Tkinter.Label(cf, text = 'Color ')
    ch.grid(row = 0, column = 0)
      
    from CGLtk.color import ColorWell
    cc = ColorWell.ColorWell(cf, callback = self.change_color_cb)
    cc.grid(row = 0, column = 1)
    white_rgb = (1,1,1)
    cc.showColor(white_rgb, doCallback = False)
    self.color = cc
    
    tr = Hybrid.Entry(cf, ' Transparency ', 3, '0')
    tr.frame.grid(row = 0, column = 2, sticky = 'w')
    self.transparency = tr.variable
    tr.entry.bind('<KeyPress-Return>', self.transparency_cb)

    cof = Tkinter.Frame(af)
    cof.grid(row = arow, column = 0, sticky = 'w')
    arow = arow + 1

    cl = Tkinter.Label(cof, text = 'Color ')
    cl.grid(row = 0, column = 0, sticky = 'w')

    carb = Hybrid.Button_Row(cof, '',
                             (('Atoms', self.color_atoms_cb),
                              ('Ribbons', self.color_ribbons_cb),
                              ))
    carb.frame.grid(row = 0, column = 1, sticky = 'w')

    msl = Tkinter.Label(cof, text = ' to match surfaces')
    msl.grid(row = 0, column = 2, sticky = 'w')

    rsf = Tkinter.Frame(af)
    rsf.grid(row = arow, column = 0, sticky = 'w')
    arow = arow + 1
    
    rb = Hybrid.Button_Row(rsf, '', (('Resurface', self.resurface_cb),))
    rb.frame.grid(row = 0, column = 0, sticky = 'w')
    
    mm = multiscale_manager()
    sr = Hybrid.Entry(rsf, ' Resolution ', 3,
                      str(mm.default_surface_resolution))
    sr.frame.grid(row = 0, column = 1, sticky = 'w')
    self.surface_resolution = sr.variable
    sr.entry.bind('<KeyPress-Return>', self.resurface_cb)
    
    so = Hybrid.Checkbutton(rsf, 'Surface parameters', 0)
    so.button.grid(row = 0, column = 2, sticky = 'w', padx = 10)
    so.callback(self.allow_toplevel_resize_cb)
    
    sof = Tkinter.Frame(af)
    so.popup_frame(sof, row = arow, column = 0, sticky = 'nw')
    arow = arow + 1

    self.make_surface_options_gui(sof)

    dc = Tkinter.Button(af, text = 'Delete chains',
                        command = self.delete_chains_cb)
    dc.grid(row = arow, column = 0, sticky = 'w')
    arow = arow + 1

    
    div = Tkinter.Frame(parent, relief = Tkinter.GROOVE,
                        borderwidth=1, height=2)
    div.grid(row = row, column = 0, sticky = 'ew', pady = 10)
    row = row + 1

    mh = Tkinter.Label(parent, text = 'Models from molecules and matrices')
    mh.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    self.multimer_biounit = 'Biological unit'
    self.multimer_unitcell = 'Crystal unit cell'
    self.multimer_unitcell_packed = 'Crystal unit cell packed'
    self.multimer_3x3x3cells = '3x3x3 crystal unit cells'
    self.multimer_3x3x3cells_packed = '3x3x3 crystal unit cells packed'
    self.multimer_crystal = 'Crystal symmetry in unit cell'
    self.multimer_noncrystal = 'Non-crystal symmetry in unit cell'
    self.multimer_icosahedral_222 = 'Icosahedral symmetry, xyz 2-fold axes (VIPER)'
    self.multimer_icosahedral_222r = 'Icosahedral symmetry, xyz 2-fold axes, alt'
    self.multimer_none = 'None'
    mt = Hybrid.Option_Menu(parent, ' Multimer: ',
                            self.multimer_biounit,
                            self.multimer_unitcell,
                            self.multimer_unitcell_packed,
                            self.multimer_3x3x3cells,
                            self.multimer_3x3x3cells_packed,
                            self.multimer_crystal,
                            self.multimer_noncrystal,
                            self.multimer_icosahedral_222,
                            self.multimer_icosahedral_222r,
                            self.multimer_none,)

    mt.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.multimer_type = mt.variable

    mm = Hybrid.Button_Row(parent, ' ',
                           (('Make models', self.make_multimers_cb),
                            ('Delete selected models',
                             self.delete_selected_multimers_cb),
                            ))
    mm.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    
    #
    # Specify a label width so dialog is not resized for long messages.
    #
    msg = Tkinter.Label(parent, width = 40, anchor = 'w', justify = 'left')
    msg.grid(row = row, column = 0, sticky = 'ew')
    row = row + 1
    self.message_label = msg

  # ---------------------------------------------------------------------------
  #
  def make_surface_options_gui(self, frame):

    from CGLtk import Hybrid
    import Tkinter
    
    row = 0

    df = Tkinter.Frame(frame)
    df.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    
    mm = multiscale_manager()
    dt = Hybrid.Entry(df, '  Threshold atom density ', 4,
                      str(mm.default_density_threshold))
    dt.frame.grid(row = 0, column = 0, sticky = 'w')
    self.density_threshold = dt.variable
    dt.entry.bind('<KeyPress-Return>', self.resurface_cb)
    
    dtca = Hybrid.Entry(df, ' CA only ', 5,
                      str(mm.default_density_threshold_ca_only))
    dtca.frame.grid(row = 0, column = 1, sticky = 'w')
    self.density_threshold_ca_only = dtca.variable
    dtca.entry.bind('<KeyPress-Return>', self.resurface_cb)

    sf = Hybrid.Entry(frame, '  Smoothing factor ', 4,
                      str(mm.default_smoothing_factor))
    sf.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.smoothing_factor = sf.variable
    sf.entry.bind('<KeyPress-Return>', self.resurface_cb)

    si = Hybrid.Entry(frame, '  Smoothing iterations ', 4,
                      str(mm.default_smoothing_iterations))
    si.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.smoothing_iterations = si.variable
    si.entry.bind('<KeyPress-Return>', self.resurface_cb)

  # ---------------------------------------------------------------------------
  # After user resizes dialog by hand it will not resize automatically when
  # panels are added or deleted.  This allows the automatic resize to happen.
  #
  def allow_toplevel_resize_cb(self):

    self.toplevel_widget.geometry('')
      
  # ---------------------------------------------------------------------------
  #
  def map(self):

    if self.selection_trigger == None:
      ct = chimera.triggers
      self.selection_trigger = \
        ct.addHandler('selection changed', self.selection_cb, None)

  # ---------------------------------------------------------------------------
  #
  def unmap(self):

    if self.selection_trigger:
      ct = chimera.triggers
      ct.deleteHandler('selection changed', self.selection_trigger)
      self.selection_trigger = None
    
  # ---------------------------------------------------------------------------
  #
  def message(self, text, append = False):

    if append:
      self.message_label['text'] = self.message_label['text'] + text
    else:
      self.message_label['text'] = text
    self.message_label.update_idletasks()
  
  # ---------------------------------------------------------------------------
  #
  def make_multimers_cb(self, molecules = None):

    if molecules is None:
      molecules = selected_molecules()

    return self.make_multimers(molecules)
    
  # ---------------------------------------------------------------------------
  # Make multimers from molecule models.
  #
  def make_multimers(self, pdb_models):

    mtype = self.multimer_type.get()
    import Molecule
    if mtype == self.multimer_biounit:
      g = Molecule.biological_unit_matrices
    elif mtype == self.multimer_unitcell:
      g = lambda m: Molecule.unit_cell_matrices(m, group=True)
    elif mtype == self.multimer_unitcell_packed:
      def packed_unit_cell_matrices(m):
        import Molecule
        c = Molecule.molecule_center(m)
        o = (0,0,0)     # unit cell origin for packing molecules
        tflist = Molecule.unit_cell_matrices(m, pack = (c,o), group = True)
        return tflist
      g = packed_unit_cell_matrices
    elif mtype == self.multimer_3x3x3cells:
      g = lambda m: Molecule.unit_cell_matrices(m, group=True, cells = (3,3,3))
    elif mtype == self.multimer_3x3x3cells_packed:
      def packed_3x3x3_unit_cell_matrices(m):
        c = Molecule.molecule_center(m)
        o = (0,0,0)     # unit cell origin for packing molecules
        tflist = Molecule.unit_cell_matrices(m, pack = (c,o), group = True,
                                             cells = (3,3,3))
        return tflist
      g = packed_3x3x3_unit_cell_matrices
    elif mtype == self.multimer_crystal:
      g = Molecule.crystal_symmetries
    elif mtype == self.multimer_noncrystal:
      g = Molecule.noncrystal_symmetries
    elif mtype == self.multimer_icosahedral_222:
      from Icosahedron import icosahedral_symmetry_matrices
      g = lambda m: icosahedral_symmetry_matrices('222')
    elif mtype == self.multimer_icosahedral_222r:
      from Icosahedron import icosahedral_symmetry_matrices
      g = lambda m: icosahedral_symmetry_matrices('222r')
    elif mtype == self.multimer_none:
      g = lambda m: []
    get_transform_matrices = g

    mm = multiscale_manager()
    show = True
    return mm.make_multimers(pdb_models, get_transform_matrices,
                             show, self.surface_parameters())
          
  # -------------------------------------------------------------------------
  # Update colorwell color when a single model piece is selected.
  #
  def selection_cb(self, trigger, user_data, selection):

    cplist = self.selected_chains(warn_if_none_selected = False)
    if len(cplist) == 1:
      c = cplist[0]
      self.color.showColor(c.rgba, doCallback = False)

  # ---------------------------------------------------------------------------
  #
  def resurface_cb(self, event = None):

    sp = self.surface_parameters()
    self.apply_to_chains(lambda cp: cp.resurface(sp),
                         stoppable = 'Surface calculation')
    
  # ---------------------------------------------------------------------------
  #
  def surface_parameters(self):

    mm = multiscale_manager()
    res = float_variable_value(self.surface_resolution,
                               mm.default_surface_resolution)
    dens = float_variable_value(self.density_threshold,
                                mm.default_density_threshold)
    dens_ca = float_variable_value(self.density_threshold_ca_only,
                                   mm.default_density_threshold_ca_only)
    sf = float_variable_value(self.smoothing_factor,
                              mm.default_smoothing_factor)
    si = integer_variable_value(self.smoothing_iterations,
                                mm.default_smoothing_iterations)
    return (res, dens, dens_ca, sf, si)

  # ---------------------------------------------------------------------------
  #
  def chain_pieces(self):

    return multiscale_manager().chain_pieces()

  # ---------------------------------------------------------------------------
  #
  def select_all_chains_cb(self):

    self.select_chains(self.chain_pieces())

  # ---------------------------------------------------------------------------
  #
  def clear_selection_cb(self):

    from chimera import selection
    selection.setCurrent([])

  # ---------------------------------------------------------------------------
  #
  def select_chains(self, chain_pieces, extend_selection = False):

    multiscale_manager().select_chains(chain_pieces, extend_selection)

  # ---------------------------------------------------------------------------
  #
  def select_loaded_chains_cb(self):

    cplist = filter(lambda cp: cp.lan_chain.is_loaded(), self.chain_pieces())
    self.select_chains(cplist)

  # ---------------------------------------------------------------------------
  #
  def select_atoms_cb(self, loaded_only = False):

    cplist = self.selected_chains()
    if loaded_only:
      cplist = filter(lambda cp: cp.lan_chain.is_loaded(), cplist)

    alists = self.apply_to_chains(lambda c: c.lan_chain.atoms(), cplist)
    atoms = []
    for alist in alists:
      atoms.extend(alist)

    blists = self.apply_to_chains(lambda c: c.lan_chain.bonds(), cplist)
    bonds = []
    for blist in blists:
      bonds.extend(blist)

    from chimera import selection
    selection.addCurrent(atoms + bonds)

  # ---------------------------------------------------------------------------
  #
  def promote_selection_cb(self):

    sel = self.selected_chains()
    fs = fully_selected_pieces(sel)
    cplist = find_pieces(parent_pieces(fs), Chain_Piece)
    self.select_chains(cplist, extend_selection = True)

  # ---------------------------------------------------------------------------
  #
  def select_copies_cb(self):

    ctable = {}
    for cp in self.selected_chains():
      cname = cp.lan_chain.identifier()
      ctable[cname] = 1

    cplist = []
    for cp in self.chain_pieces():
      cname = cp.lan_chain.identifier()
      if ctable.has_key(cname):
        cplist.append(cp)

    self.select_chains(cplist, extend_selection = True)

  # ---------------------------------------------------------------------------
  #
  def select_near_cb(self):

    self.select_nearby(contacts_only = False)

  # ---------------------------------------------------------------------------
  #
  def select_contacts_cb(self):

    self.select_nearby(contacts_only = True)
    
  # ---------------------------------------------------------------------------
  # Select atoms and chains near the currently selected atoms and chains.
  # Optionally restricts the current selection to only the atoms and chains
  # involved in contacts.
  #
  def select_nearby(self, contacts_only):

    d = float_variable_value(self.selection_range,
                             self.default_selection_range)
    load_atoms = self.load_nearby_atoms.get()
    displayed_only = True
    
    import nearby
    if contacts_only:
      nearby.select_contacts(d, load_atoms, displayed_only)
    else:
      nearby.select_nearby(d, load_atoms, displayed_only)
    
  # ---------------------------------------------------------------------------
  #
  def hide_others_cb(self):
    self.apply_to_chains(lambda c: c.hide(), self.other_chains())
  def hide_other_surfaces_cb(self):
    self.apply_to_chains(lambda c: c.show_surface(False), self.other_chains())
  def hide_selected_cb(self):
    self.apply_to_chains(lambda c: c.hide())
  def hide_selected_surfaces_cb(self):
    self.apply_to_chains(lambda c: c.show_surface(False))
  def show_other_surfaces_cb(self):
    sp = self.surface_parameters()
    self.apply_to_chains(lambda c: c.show_surface(True,sp), self.other_chains())
  def show_selected_surfaces_cb(self):
    sp = self.surface_parameters()
    self.apply_to_chains(lambda c: c.show_surface(True,sp))
  def show_surface_cb(self):
    sp = self.surface_parameters()
    self.apply_to_chains(lambda c: c.show_style('surface',sp))
  def show_ribbon_cb(self):
    self.apply_to_chains(lambda c: c.show_style('ribbon'),
                         stoppable = 'Chains as ribbon')
  def show_wire_cb(self):
    self.apply_to_chains(lambda c: c.show_style('wire'),
                         stoppable = 'Chains as wire')
  def show_stick_cb(self):
    self.apply_to_chains(lambda c: c.show_style('stick'),
                         stoppable = 'Chains as stick')
  def show_ball_and_stick_cb(self):
    self.apply_to_chains(lambda c: c.show_style('ball & stick'),
                         stoppable = 'Chains as ball & stick')
  def show_sphere_cb(self):
    self.apply_to_chains(lambda c: c.show_style('sphere'),
                         stoppable = 'Chains as sphere')
  def show_only_surface_cb(self):
    sp = self.surface_parameters()
    self.apply_to_chains(lambda c: c.show_only_style('surface',sp))
  def show_only_ribbon_cb(self):
    self.apply_to_chains(lambda c: c.show_only_style('ribbon'),
                         stoppable = 'Chains as ribbon')
  def show_only_wire_cb(self):
    self.apply_to_chains(lambda c: c.show_only_style('wire'),
                         stoppable = 'Chains as wire')
  def show_only_stick_cb(self):
    self.apply_to_chains(lambda c: c.show_only_style('stick'),
                         stoppable = 'Chains as stick')
  def show_only_ball_and_stick_cb(self):
    self.apply_to_chains(lambda c: c.show_only_style('ball & stick'),
                         stoppable = 'Chains as ball & stick')
  def show_only_sphere_cb(self):
    self.apply_to_chains(lambda c: c.show_only_style('sphere'),
                         stoppable = 'Chains as sphere')
  def hide_surface_cb(self):
    self.apply_to_chains(lambda c: c.show_surface(False))
  def hide_ribbon_cb(self):
    self.apply_to_chains(lambda c: c.show_ribbon(False))
  def hide_atoms_cb(self):
    self.apply_to_chains(lambda c: c.show_atoms(False))
  def change_color_cb(self, rgba):
    self.apply_to_chains(lambda c, rgba=rgba: c.set_color(rgba))

  # ---------------------------------------------------------------------------
  #
  def apply_to_chains(self, chain_function, clist = None, stoppable = False):

    if clist == None:
      clist = self.selected_chains()

    if stoppable:
        from chimera import tasks, CancelOperation
        task = tasks.Task(stoppable, modal = True)
        results = []
        for i,c in enumerate(clist):
          r = chain_function(c)
          results.append(r)
          try:
            task.updateStatus('chain %d of %d' % (i, len(clist)))
          except CancelOperation:
            break
        task.finished()
    else:
      results = [chain_function(c) for c in clist]
      
    return results

  # ---------------------------------------------------------------------------
  #
  def transparency_cb(self, event = None):

    trans = float_variable_value(self.transparency, 0)
    if trans < 0:
      trans = 0
    elif trans > 1:
      trans = 1
    opacity = 1 - trans
    chains = self.selected_chains()
    for c in chains:
      rgba = list(c.color())
      rgba[3] = opacity
      c.set_color(rgba)

    if chains:
      # update colorwell color
      self.color.showColor(chains[0].color(), doCallback = False)

  # ---------------------------------------------------------------------------
  #
  def color_atoms_cb(self):
    self.apply_to_chains(lambda c: c.set_atom_colors())
  def color_ribbons_cb(self):
    self.apply_to_chains(lambda c: c.set_ribbon_colors())
    
  # ---------------------------------------------------------------------------
  #
  def delete_selected_multimers_cb(self):

    mm = multiscale_manager()
    mlist = mm.selected_multiscale_models()
    mm.delete_models(mlist)
      
  # ---------------------------------------------------------------------------
  #
  def delete_chains_cb(self):

    cplist = self.selected_chains()
    mm = multiscale_manager()
    mm.delete_childless_pieces(cplist)
    #
    # If a top level model is deleted the SurfaceModel will be closed
    # invoking a callback that removes the multiscale model from the
    # dialog's list.
    #

  # ---------------------------------------------------------------------------
  #
  def selected_chains(self, selected_surfaces_only = False,
                      warn_if_none_selected = True):

    mm = multiscale_manager()
    chains = mm.selected_chains(selected_surfaces_only)

    if warn_if_none_selected:
      if len(chains) == 0:
        self.message('No effect -- nothing selected')
      else:
        self.message('')
    return chains

  # ---------------------------------------------------------------------------
  # Other chains are unselected chains in models that have a selected chain.
  #
  def other_chains(self):

    schains = self.selected_chains()
    
    ctable = {}
    for c in schains:
      ctable[c] = 1

    mtable = {}
    for c in schains:
      mtable[c.root()] = 1

    ochains = []
    models = mtable.keys()
    for c in find_pieces(models, Chain_Piece):
      if not ctable.has_key(c):
        ochains.append(c)

    return ochains

# -----------------------------------------------------------------------------
#
def is_chain_piece(surface_piece):

  return hasattr(surface_piece, 'model_piece') and surface_piece.model_piece

# -----------------------------------------------------------------------------
#
def containing_chain_pieces(surface_pieces, residues = []):

    ctable = {}
    for sg in surface_pieces:
      if hasattr(sg, 'model_piece') and sg.model_piece:
        ctable[sg.model_piece] = 1

    for r in residues:
      if hasattr(r, 'model_piece') and r.model_piece:
        ctable[r.model_piece] = 1

    chains = ctable.keys()
    return chains
  
# -----------------------------------------------------------------------------
# Base class for pieces of multiscale model.
#
class Model_Piece:

  def __init__(self):

    self.parent = None          # Model_Piece object
    self.children = []          # Model_Piece objects
    self.display_styles = []    # strings
    self.surf_model = None
    self.model_closed_callbacks = []
    
  # ---------------------------------------------------------------------------
  #
  def show_style(self, style, params = None):

    pass
    
  # ---------------------------------------------------------------------------
  #
  def show_only_style(self, style, params = None):

    pass
    
  # ---------------------------------------------------------------------------
  #
  def hide(self):

    pass
    
  # ---------------------------------------------------------------------------
  #
  def root(self):

    if self.parent:
      return self.parent.root()
    return self

  # ---------------------------------------------------------------------------
  #
  def surface_model(self, create = True, model_id = None):

    if self.parent:
      return self.parent.surface_model(create, model_id)
    
    if self.surf_model == None and create:
      import _surface
      s = _surface.SurfaceModel()
      if hasattr(self, 'name'):
        s.name = self.name + ' surfaces'
      from new import instancemethod as im
      s.surfacePieceAtomsAndBonds = im(surfacePieceAtomsAndBonds, self)
      s.atomAndBondSurfacePieces = im(atomAndBondSurfacePieces, self)
      self.surf_model = s
      if model_id == None:
        id = subid = chimera.openModels.Default
      else:
        id, subid = model_id
      chimera.openModels.add([s], baseId = id, subid = subid)
      xf = self.surface_model_initial_xform()
      if xf:
        s.openState.xform = xf
      chimera.addModelClosedCallback(s, self.surface_model_closed_cb)
      self.surface_model_created()

    return self.surf_model
        
  # ---------------------------------------------------------------------------
  # Model pieces should override this routine if they want to suggest an
  # initial xform matrix for the SurfaceModel, for example, to keep an
  # already existing molecule model from being moved.
  #
  def surface_model_initial_xform(self):

    if len(self.children) == 0:
      return None
    for c in self.children:
      xf = c.surface_model_initial_xform()
      if xf:
        return xf
    return None
  
  # ---------------------------------------------------------------------------
  # Override this in derived classes.
  #
  # The purpose of this call is so Pieces can align their models to the
  # surface model.
  #
  def surface_model_created(self):

    for p in self.children:
      p.surface_model_created()

  # ---------------------------------------------------------------------------
  #
  def add_model_closed_callback(self, cb):

    self.model_closed_callbacks.append(cb)

  # ---------------------------------------------------------------------------
  #
  def remove_model_closed_callback(self, cb):

    self.model_closed_callbacks.remove(cb)
    
  # ---------------------------------------------------------------------------
  #
  def surface_model_closed(self):

    for p in self.children:
      p.surface_model_closed()

    for cb in self.model_closed_callbacks:
      cb(self)
      
  # ---------------------------------------------------------------------------
  #
  def surface_model_closed_cb(self, surf):

    self.surf_model = None
    self.surface_model_closed()

  # ---------------------------------------------------------------------------
  #
  def delete(self):

    if self.surf_model:
      chimera.openModels.close([self.surf_model])

    for c in self.children:
      c.delete()

# -----------------------------------------------------------------------------
# Added as a method to SurfaceModel to allow Chimera Actions menu to work
# on selected multiscale surfaces.
#
def surfacePieceAtomsAndBonds(self, plist, create):

  atoms = []
  bonds = []
  for p in plist:
    cp = getattr(p, 'model_piece', None)
    if cp:
      ca = cp.lan_chain.atoms(load = create)
      if ca:
        atoms.extend(ca)
      cb = cp.lan_chain.bonds(load = create)
      if cb:
        bonds.extend(cb)
  return atoms, bonds

# -----------------------------------------------------------------------------
# Added as a method to SurfaceModel to allow Chimera Actions menu to work
# on selected multiscale surfaces.
#
def atomAndBondSurfacePieces(self, atoms, bonds):

  rset = set([a.residue for a in atoms])
  for b in bonds:
    a1, a2 = b.atoms
    rset.add(a1.residue)
    rset.add(a2.residue)
  pset = set([r.model_piece.surface_piece for r in rset
              if hasattr(r, 'model_piece')])
  if None in pset:
    pset.remove(None)
  plist = list(pset)
  return plist
  
# -----------------------------------------------------------------------------
#
def parent_pieces(plist):

  ptable = {}
  for p in plist:
    if p.parent:
      ptable[p.parent] = 1
  return ptable.keys()

# -----------------------------------------------------------------------------
# A fully selected piece is one that is selected or has at least one child
# and all children are fully selected.
#
def fully_selected_pieces(plist):

  fstable = {}
  for p in plist:
    fstable[p] = 1

  roots = {}
  for p in plist:
    roots[p.root()] = 1

  for r in roots.keys():
    find_fully_selected_pieces(r, fstable)

  return fstable.keys()

# -----------------------------------------------------------------------------
#
def find_fully_selected_pieces(p, fstable):

  if fstable.has_key(p) or len(p.children) == 0:
    return

  for c in p.children:
    find_fully_selected_pieces(c, fstable)

  for c in p.children:
    if not fstable.has_key(c):
      return

  fstable[p] = 1

# -----------------------------------------------------------------------------
#
class Group_Piece(Model_Piece):

  def __init__(self, name, children):

    Model_Piece.__init__(self)

    self.name = name
    self.children = children

    for cp in children:
      cp.parent = self

# -----------------------------------------------------------------------------
#
def molecule_multimer(molecule, surfacer, xform_tree,
                      associate_molecule_with_identity_matrix = True):

  xforms = flatten_tree(xform_tree, is_xform)
  if associate_molecule_with_identity_matrix:
    associate = identity_xform_index(xforms, 0)
  else:
    associate = 0

  n = len(xforms)
  if n > associate:
    # Untransform molecule using first xform so that it has the same
    # position in the multiscale model as before the multiscale model was made.
    xf = molecule.openState.xform
    xf.multiply(xforms[associate].inverse())
    molecule.openState.xform = xf

  lan_molecules = make_lan_molecules(molecule, n, associate)
  
  mpieces = []
  for k in range(n):
    lan_molecule = lan_molecules[k]
    chains = lan_molecule.chains()
    chain_colors = color_by_sequence(chains, seed = molecule.name)
    children = chain_pieces(chains, chain_colors, xforms[k], surfacer)
    mp = Group_Piece(lan_molecule.name, children)
    mpieces.append(mp)

  if len(mpieces) > 1:
    mptree = list_to_tree(mpieces, xform_tree, is_xform)
    m = group_tree(mptree, molecule.name)
  else:
    m = mpieces[0]   # Group containing chains

  return m

# -----------------------------------------------------------------------------
#
def group_tree(list_tree, name):

  if isinstance(list_tree, (list, tuple)):
    return Group_Piece(name, [group_tree(e,name) for e in list_tree])
  else:
    return list_tree

# -----------------------------------------------------------------------------
#
def color_by_sequence(lan_chains, seed = None):

  snum = {}
  cnum = []
  for lc in lan_chains:
    s = lc.sequence()
    if not s in snum:
      snum[s] = len(snum)
    cnum.append(snum[s])

  scolors = random_colors(len(snum), seed)
  colors = [scolors[cn] for cn in cnum]
  return colors

# -----------------------------------------------------------------------------
#
def random_colors(n, seed = None):

  import random
  if seed:
    if isinstance(seed, basestring):
      # Make 64-bit machines and 32-bit produce the same 32-bit seed by casting
      # 64-bit hash values to signed 32-bit.
      seed = hash(str(seed)) % 2**32
    random.seed(seed)
    
  colors = []
  for c in range(n):
    rgba = (.5 + random.uniform(0,.5),
            .5 + random.uniform(0,.5),
            .5 + random.uniform(0,.5),
            1)
    colors.append(rgba)

  return colors

# -----------------------------------------------------------------------------
#
def molecule_copies(molecule, matrices,
                    associate_molecule_with_identity_matrix = True):

  xforms = numbered_xforms(matrices)
  n = len(matrices)
  if associate_molecule_with_identity_matrix:
    associate = identity_xform_index(xforms, 0)
  else:
    associate = 0
  lan_molecules = make_lan_molecules(molecule, n, associate)
  copies = zip(lan_molecules, xforms)
  return copies
    
# -----------------------------------------------------------------------------
#
def numbered_xforms(matrix_tree):

  from Matrix import chimera_xform
  xforms = [chimera_xform(m) for m in flatten_tree(matrix_tree, is_matrix)]
  for i,xf in enumerate(xforms):
    xf.id_number = i+1
  xform_tree = list_to_tree(xforms, matrix_tree, is_matrix)
  return xform_tree

# -----------------------------------------------------------------------------
#
def tree_size(tree, is_element):

  s = sum([1 if is_element(e) else tree_size(e,is_element) for e in tree])
  return s

# -----------------------------------------------------------------------------
#
def flatten_tree(tree, is_element):

  f = []
  for e in tree:
    if is_element(e):
      f.append(e)
    else:
      f.extend(flatten_tree(e, is_element))
  return f

# -----------------------------------------------------------------------------
#
def list_to_tree(seq, tree, is_element, start = None):

  i = 0 if start is None else start
  t = []
  for e in tree:
    if is_element(e):
      t.append(seq[i])
      i += 1
    else:
      et, i = list_to_tree(seq, e, is_element, i)
      t.append(et)
  return t if start is None else (t,i)

# -----------------------------------------------------------------------------
#
def is_matrix(m):

  try:
    return isinstance(m[0][0], (float,int))
  except:
    return False

# -----------------------------------------------------------------------------
#
def is_xform(xf):

  from chimera import Xform
  return isinstance(xf, Xform)

# -----------------------------------------------------------------------------
#
def identity_xform_index(xforms, default_index = None,
                         angle_tolerance = 0.001,
                         translation_tolerance = 0.001):

  for i, xf in enumerate(xforms):
    if (xf.getTranslation().length < translation_tolerance and
        abs(xf.getRotation()[1] ) < angle_tolerance):
      return i
  return default_index

# -----------------------------------------------------------------------------
# The associate argument gives the index of the LAN_Molecule in the returned
# list which has the given molecule associated with it.
#
def make_lan_molecules(molecule, n, associate = 0):

  lan_molecules = []

  for k in range(n):
    lm = LAN_Molecule(molecule)
    lan_molecules.append(lm)
    
  if n > associate:
    lm = lan_molecules[associate]
    lm.associate_molecule(molecule)

  return lan_molecules

# -----------------------------------------------------------------------------
#
def make_chain_groups(name_prefix, chain_names, mcopies,
                      color = None, chain_colors = []):

    if color:
        chain_colors = [color] * len(chain_names)

    if not chain_colors:
        import random
        random_color = (.5 + random.uniform(0,.5),
                        .5 + random.uniform(0,.5),
                        .5 + random.uniform(0,.5),
                        1)
        chain_colors = [random_color] * len(chain_names)
        
    groups = []
    for k in range(len(mcopies)):
        name = name_prefix + ' ' + str(k+1)
        if isinstance(mcopies[k][0], LAN_Molecule):
          copies = [mcopies[k]]
        else:
          copies = mcopies[k]
        g = make_chain_group(name, chain_names, copies, chain_colors)
        groups.append(g)

    return groups

# -----------------------------------------------------------------------------
#
def make_chain_group(name, chain_names, mcopies, chain_colors):

  mm = multiscale_manager()
  surfacer = mm.surfacer

  cplist = []
  for lan_molecule, xform in mcopies:
    ct = lan_molecule.chain_table()
    lan_chains = map(lambda cid, ct=ct: ct[cid], chain_names)
    cplist.extend(chain_pieces(lan_chains, chain_colors, xform, surfacer))

  gp = Group_Piece(name, cplist)

  return gp

# -----------------------------------------------------------------------------
#
def make_group(name, plist):

  return Group_Piece(name, plist)

# -----------------------------------------------------------------------------
#
def chain_pieces(lan_chains, chain_colors, xform, surfacer):

  cplist = []
  for c in range(len(lan_chains)):
    cp = Chain_Piece(lan_chains[c], xform, surfacer)
    cp.set_color(chain_colors[c % len(chain_colors)])
    cplist.append(cp)

  return cplist
      
# -----------------------------------------------------------------------------
#
class Chain_Piece(Model_Piece):

  def __init__(self, lan_chain, xform, surfacer):

    Model_Piece.__init__(self)

    self.lan_chain = lan_chain
    self.xform = xform
    self.surfacer = surfacer

    self.display_styles = ['surface', 'ribbon',
                           'wire', 'stick', 'ball & stick', 'sphere']
    self.atom_and_bond_modes = {
      'wire': (chimera.Atom.Dot, chimera.Bond.Wire),
      'stick': (chimera.Atom.EndCap, chimera.Bond.Stick),
      'ball & stick': (chimera.Atom.Ball, chimera.Bond.Stick),
      'sphere': (chimera.Atom.Sphere, chimera.Bond.Wire),
      'atoms': (None, None)
      }
    self.surface_piece = None
    self.rgba = (1,1,1,1)

    lm = lan_chain.lan_molecule
    lm.add_molecule_loaded_callback(self.molecule_loaded_cb)
    
    if hasattr(lm, 'chain_piece_reference_count'):
      lm.chain_piece_reference_count += 1
    else:
      lm.chain_piece_reference_count = 1
      
    if self.molecule(load = False):
      self.molecule_loaded_cb()     # Initialize xform, turn off atom display
    
  # ---------------------------------------------------------------------------
  #
  def show_style(self, style, params = None):

    if style == 'surface':
      self.show_surface(True, params)
    elif style == 'ribbon':
      self.show_ribbon(True)
    elif style in self.atom_and_bond_modes:
      atom_mode, bond_mode = self.atom_and_bond_modes[style]
      self.show_atoms(True, atom_mode, bond_mode)
    
  # ---------------------------------------------------------------------------
  #
  def show_only_style(self, style, params = None):

    self.show_style(style, params)

    if style == 'surface':
      self.show_ribbon(False)
      self.show_atoms(False)
    elif style == 'ribbon':
      self.show_surface(False)
      self.show_atoms(False)
    elif style in self.atom_and_bond_modes:
      self.show_surface(False)
      self.show_ribbon(False)
    
  # ---------------------------------------------------------------------------
  #
  def hide(self):

    self.show_surface(False)
    self.show_ribbon(False)
    self.show_atoms(False)
    
  # ---------------------------------------------------------------------------
  #
  def show_surface(self, show, surf_params = None):

    sg = self.surface_piece
    if sg:
      sg.display = show      
    elif show:
      self.resurface(surf_params)
      self.surface_piece.display = True
    
  # ---------------------------------------------------------------------------
  #
  def surface_shown(self):

    sm = self.surface_model(create = False)
    sg = self.surface_piece
    return sm and sg and sg.display
    
  # ---------------------------------------------------------------------------
  #
  def resurface(self, surf_params = None, use_cache = True):

    if surf_params is None:
      p = self.surface_piece
      if p is None:
        return
      params = p.surfacing_parameters
    else:
      res, dens, dens_ca, sf, si = surf_params
      lc = self.lan_chain
      if dens_ca != None and lc.has_only_ca_atoms():
        params = (res, dens_ca, sf, si)
      else:
        params = (res, dens, sf, si)

    s = self.surfacer
    lc = self.lan_chain
    varray, tarray, narray = s.surface_geometry(lc, *params,
                                                **{'use_cache':use_cache})

    p = self.surface_piece
    if p:
      p.geometry = varray, tarray
    else:
      sm = self.surface_model()
      p = sm.addPiece(varray, tarray, self.rgba)
      p.oslName = self.osl_name()
      p.model_piece = self
      p.display = False
      self.surface_piece = p
    import Matrix
    p.placement = Matrix.xform_matrix(self.xform)
    p.normals = narray
    p.surfacing_parameters = params

  # ---------------------------------------------------------------------------
  #
  def osl_name(self):

    if hasattr(self.xform, 'id_number'):
      id_number = '%d' % self.xform.id_number
    else:
      id_number = '?'
    return '%s.%s' % (id_number, self.lan_chain.chain_id)
    
  # ---------------------------------------------------------------------------
  #
  def remove_surface(self):

    p = self.surface_piece
    if p:
      sm = self.surface_model()
      sm.removePiece(p)
      p.model_piece = None
      self.surface_piece = None
    
  # ---------------------------------------------------------------------------
  #
  def show_ribbon(self, show):

    round = chimera.Residue.Ribbon_Round
    rlist = self.lan_chain.residues(load = show)
    if rlist != None:
      for r in rlist:
        if show:
          r.ribbonDrawMode = round
        r.ribbonDisplay = show

  # ---------------------------------------------------------------------------
  #
  def show_atoms(self, show, atom_mode = None, bond_mode = None):
      
    if atom_mode != None:
      alist = self.lan_chain.atoms(load = show)
      if alist != None:
        for a in alist:
          a.drawMode = atom_mode

    if bond_mode != None:
      blist = self.lan_chain.bonds(load = show)
      if blist != None:
        for b in blist:
          b.drawMode = bond_mode
        
    alist = self.lan_chain.atoms(load = show)
    if alist != None:
      for a in alist:
        a.display = show

  # ---------------------------------------------------------------------------
  #
  def color(self):

    return self.rgba

  # ---------------------------------------------------------------------------
  #
  def set_color(self, rgba = None):

    if rgba == None:
      rgba = self.rgba
    else:
      self.rgba = rgba

    p = self.surface_piece
    if p:
      p.color = tuple(rgba)
    
  # ---------------------------------------------------------------------------
  #
  def set_ribbon_colors(self):

    rlist = self.lan_chain.residues(load = False)
    if rlist != None:
      color = chimera_color(self.rgba)
      for r in rlist:
        r.ribbonColor = color
    
  # ---------------------------------------------------------------------------
  #
  def set_atom_colors(self):

    alist = self.lan_chain.atoms(load = False)
    if alist != None:
      color = chimera_color(self.rgba)
      for a in alist:
        a.color = color
    
  # ---------------------------------------------------------------------------
  #
  def molecule(self, load = True):

    return self.lan_chain.lan_molecule.molecule(load)
    
  # ---------------------------------------------------------------------------
  #
  def molecule_loaded_cb(self):

    if self.is_first_chain_of_molecule():
      self.set_molecule_xform()

    self.position_chain_atoms()
    
    for r in self.lan_chain.residues():
      r.model_piece = self
    
  # ---------------------------------------------------------------------------
  # Transform is in local coordinates.
  #
  def move_piece(self, xform):

    sm = self.surface_model(create = False)
    if sm == None:
      return

    import chimera
    xf = chimera.Xform()
    xf.multiply(xform)
    xf.multiply(self.xform)
    self.set_xform(xf)
    
  # ---------------------------------------------------------------------------
  #
  def set_xform(self, xform):

    if hasattr(self.xform, 'id_number'):
      xform.id_number = self.xform.id_number
      
    self.xform = xform

    self.position_chain_atoms()         # Move atoms

    self.resurface(use_cache = False)   # Move surface.
    
  # ---------------------------------------------------------------------------
  # Set molecule transform to match surface model transform.
  #
  def set_molecule_xform(self):

    m = self.molecule(load = False)
    if m == None:
      return

    sm = self.surface_model(create = False)
    if sm == None:
      return
    
    m.openState.xform = sm.openState.xform

  # ---------------------------------------------------------------------------
  # Position atoms by applying transform to original chain atom positions.
  #
  def position_chain_atoms(self):

    lc = self.lan_chain
    atoms = lc.atoms(load = False)
    if atoms:
      # TODO: Number of atom coordinates can be wrong if atoms have been
      #  deleted from molecule after coordinates were cached.
      position_atoms(atoms, lc.source_atom_xyz(), self.xform)
    
  # ---------------------------------------------------------------------------
  # Request that SurfaceModel initial xform matches already opened molecule.
  #
  def surface_model_initial_xform(self):

    lc = self.lan_chain
    if lc.is_loaded():
      xf = lc.lan_molecule.molecule().openState.xform
      return xf
    return None
  
  # ---------------------------------------------------------------------------
  # This is used to avoid updating the molecule xform for every chain.
  #
  def is_first_chain_of_molecule(self):

    c = self.lan_chain
    return (c == c.lan_molecule.chains()[0])
        
  # ---------------------------------------------------------------------------
  #
  def surface_model_created(self):

    if self.is_first_chain_of_molecule():
      self.set_molecule_xform()
        
  # ---------------------------------------------------------------------------
  #
  def surface_model_closed(self):

    self.surface_piece = None
    self.surfacer.clear_cache(self.lan_chain)

  # ---------------------------------------------------------------------------
  #
  def delete(self):

    self.remove_surface()

    lc = self.lan_chain

    if lc.is_loaded():
      for r in lc.residues():
        if hasattr(r, 'model_piece'):
          delattr(r, 'model_piece')
      
    lm = lc.lan_molecule
    lm.chain_piece_reference_count -= 1
    if lm.chain_piece_reference_count == 0:
      lm.unload()

    lm.remove_molecule_loaded_callback(self.molecule_loaded_cb)

    self.lan_chain = None
    
# -----------------------------------------------------------------------------
#
class Chain_Surfacer:

  def __init__(self):

    self.surface_table = {}     # caches triangulated surface geometry
    
  # ---------------------------------------------------------------------------
  #
  def surface_geometry(self, lan_chain,
                       surface_resolution, density_threshold,
                       smoothing_factor, smoothing_iterations,
                       use_cache = True):

    varray, tarray, narray = \
        self.chain_surface(lan_chain,
                           surface_resolution, density_threshold,
                           smoothing_factor, smoothing_iterations, use_cache)

    return varray, tarray, narray

  # ---------------------------------------------------------------------------
  #
  def chain_surface(self, lan_chain,
                    surface_resolution, density_threshold,
                    smoothing_factor, smoothing_iterations,
                    use_cache = True):

    surf_id = lan_chain.identifier()
    st = self.surface_table
    params = (surface_resolution, density_threshold,
              smoothing_factor, smoothing_iterations)
    if use_cache and st.has_key(surf_id) and st[surf_id][0] == params:
      return st[surf_id][1:]

    import surface
    xyz = lan_chain.source_atom_xyz()
    if surface_resolution == 0:
      # Compute solvent excluded surface.
      r = lan_chain.source_atom_radii()
      varray, tarray, narray = surface.solvent_excluded_surface(xyz, r)
    else:
      varray, tarray, narray = surface.surface_points(xyz,
                                                      surface_resolution,
                                                      density_threshold,
                                                      smoothing_factor,
                                                      smoothing_iterations)
    st[surf_id] = (params, varray, tarray, narray)

    return (varray, tarray, narray)

  # ---------------------------------------------------------------------------
  #
  def clear_cache(self, lan_chain):

    surf_id = lan_chain.identifier()
    st = self.surface_table
    if surf_id in st:
      del st[surf_id]

# -----------------------------------------------------------------------------
# Load As Needed Molecule.
#
# This class allows displaying chain surfaces without having a molecule opened.
# It can open a molecule for displaying ribbon or atom representations.
#
class LAN_Molecule:

  def __init__(self, source_molecule):

    self.source_molecule = source_molecule
    self.name = source_molecule.name

    if not hasattr(source_molecule, 'multiscale_chain_data'):
      from chaindata import Multiscale_Chain_Data
      cd = Multiscale_Chain_Data(source_molecule)
      cd.reference_count = 0
      source_molecule.multiscale_chain_data = cd
      # Cache original molecule coordinates as they will be changed if source
      # molecule is associated with Chain_Piece with non-identity transform.
      for chain_id in cd.chain_ids():
        cd.chain_atom_xyz(chain_id)
    
    self.mol = None             # Loaded molecule if available.
    self.dont_unload = False

    self.chain_list = None

    self.molecule_loaded_callbacks = []
    
  # ---------------------------------------------------------------------------
  #
  def associate_molecule(self, molecule, allow_close = False):

    if hasattr(molecule, 'multiscale_chain_data'):
      molecule.multiscale_chain_data.reference_count += 1
    else:
      # TODO: Reuse self.source_molecule.multiscale_chain_data ?
      from chaindata import Multiscale_Chain_Data
      molecule.multiscale_chain_data = cd = Multiscale_Chain_Data(molecule)
      cd.reference_count = 1
    
    self.mol = molecule

    import chimera
    chimera.addModelClosedCallback(molecule, self.molecule_closed_cb)

    self.dont_unload = not allow_close
    
  # ---------------------------------------------------------------------------
  #
  def molecule(self, load = True):

    if self.mol == None and load:
      from Molecule import copy_molecule
      m = copy_molecule(self.source_molecule)
      import chimera
      chimera.openModels.add([m], noprefs = True)
      self.associate_molecule(m, allow_close = True)
      for a in m.atoms:
        a.display = False
      for cb in self.molecule_loaded_callbacks:
        cb()

    return self.mol

  # ---------------------------------------------------------------------------
  #
  def is_loaded(self):

    return self.molecule(load = False) != None
    
  # ---------------------------------------------------------------------------
  #
  def add_molecule_loaded_callback(self, cb):

    self.molecule_loaded_callbacks.append(cb)
    
  # ---------------------------------------------------------------------------
  #
  def remove_molecule_loaded_callback(self, cb):

    self.molecule_loaded_callbacks.remove(cb)
    
  # ---------------------------------------------------------------------------
  # Delete multiscale chain data.
  # Close model unless self.dont_unload == True.
  #
  def unload(self):

    m = self.molecule(load = False)
    if m == None:
      return

    if hasattr(m, 'multiscale_chain_data'):
      cd = m.multiscale_chain_data
      cd.reference_count -= 1
      if cd.reference_count == 0:
        del m.multiscale_chain_data
      
    if self.dont_unload:
      return

    chimera.openModels.close([m])
  
  # ---------------------------------------------------------------------------
  #
  def molecule_closed_cb(self, m):

    self.mol = None

  # ---------------------------------------------------------------------------
  #
  def chains(self):

    if self.chain_list == None:
      chains = []
      for cid in self.chain_ids():
        chains.append(LAN_Chain(self, cid))
      self.chain_list = chains

    return self.chain_list

  # ---------------------------------------------------------------------------
  #
  def chain_table(self):

    chain_id_to_lan_chain = {}
    for lc in self.chains():
      chain_id_to_lan_chain[lc.chain_id] = lc
    return chain_id_to_lan_chain
    
  # ---------------------------------------------------------------------------
  #
  def chain_data(self):

    return self.source_molecule.multiscale_chain_data
    
  # ---------------------------------------------------------------------------
  #
  def chain_ids(self):

    cd = self.chain_data()
    return cd.chain_ids()
    
# -----------------------------------------------------------------------------
#
class LAN_Chain:

  def __init__(self, lan_molecule, chain_id):

    self.lan_molecule = lan_molecule
    self.chain_id = chain_id
    
  # ---------------------------------------------------------------------------
  #
  def identifier(self):

    id = (self.lan_molecule.source_molecule, self.chain_id)
    return id
    
  # ---------------------------------------------------------------------------
  #
  def molecule_chain_data(self, load = True):
  
    m = self.lan_molecule.molecule(load)
    if m:
      return m.multiscale_chain_data
    return None
    
  # ---------------------------------------------------------------------------
  #
  def residues(self, load = True):

    mcd = self.molecule_chain_data(load)
    if mcd:
      return mcd.chain_residues(self.chain_id)
    return None
    
  # ---------------------------------------------------------------------------
  #
  def sequence(self):

    cd = self.lan_molecule.chain_data()
    seq = cd.chain_sequence(self.chain_id)
    return seq
  
  # ---------------------------------------------------------------------------
  #
  def atoms(self, load = True):

    mcd = self.molecule_chain_data(load)
    if mcd:
      return mcd.chain_atoms(self.chain_id)
    return None

  # ---------------------------------------------------------------------------
  # Bonds entirely within chain.
  #
  def bonds(self, load = True):

    mcd = self.molecule_chain_data(load)
    if mcd:
      return mcd.chain_bonds(self.chain_id)
    return None
    
  # ---------------------------------------------------------------------------
  # Source molecule cached atom coordinates.
  #
  def source_atom_xyz(self):

    cd = self.lan_molecule.chain_data()
    xyz = cd.chain_atom_xyz(self.chain_id)
    return xyz
    
  # ---------------------------------------------------------------------------
  # Source molecule cached atom radii.
  #
  def source_atom_radii(self):

    cd = self.lan_molecule.chain_data()
    r = cd.chain_atom_radii(self.chain_id)
    return r
    
  # ---------------------------------------------------------------------------
  #
  def has_only_ca_atoms(self):

    cd = self.lan_molecule.chain_data()
    ca_only = cd.chain_has_only_ca_atoms(self.chain_id)
    return ca_only

  # ---------------------------------------------------------------------------
  #
  def is_loaded(self):
    
    return self.lan_molecule.is_loaded()
    
# -----------------------------------------------------------------------------
#
def find_pieces(pieces, piece_type, already_checked = None):

  if already_checked == None:
    already_checked = {}

  ptable = {}
  for p in pieces:
    if not already_checked.has_key(p):
      if isinstance(p, piece_type):
        ptable[p] = 1
      already_checked[p] = 1
      for p2 in find_pieces(p.children, piece_type, already_checked):
        ptable[p2] = 1

  return ptable.keys()
    
# -----------------------------------------------------------------------------
#
def modeled_molecules(pieces, mtable = None):

  if mtable == None:
    mtable = {}

  for p in pieces:
    if isinstance(p, Chain_Piece):
      m = p.molecule(load = False)
      if m:
        mtable[m] = 1
    modeled_molecules(p.children, mtable)

  return mtable
    
# -----------------------------------------------------------------------------
#
def chimera_color(rgba):

  return chimera.MaterialColor(*rgba)
  
# -----------------------------------------------------------------------------
# Set position of atoms.
#
def position_atoms(atoms, xyz_array, xform):

  from chimera import Point
  for a in range(len(atoms)):
    p = xform.apply(Point(*xyz_array[a]))
    atoms[a].setCoord(p)

# -----------------------------------------------------------------------------
#
def float_variable_value(v, default = None):

  try:
    return float(v.get())
  except:
    return default
  
# -----------------------------------------------------------------------------
#
def integer_variable_value(v, default = None):

  try:
    return int(v.get())
  except:
    return default
  
# -----------------------------------------------------------------------------
#
def subtract_lists(list1, list2):

  t2 = {}
  for e2 in list2:
    t2[e2] = 1
  diff = filter(lambda e1: not t2.has_key(e1), list1)
  return diff

# -----------------------------------------------------------------------------
#
def color_surfaces_to_match_atoms():

  mm = multiscale_manager(create = False)
  if mm:
    for cp in mm.selected_chains():
      lc = cp.lan_chain
      atoms = lc.lan_molecule.chain_data().chain_atoms(lc.chain_id)
      if atoms:
        a = atoms[0]
        c = a.color
        if c:
          rgba = c.rgba()
        else:
          rgba = a.molecule.color.rgba()
        cp.set_color(rgba)
      
# -----------------------------------------------------------------------------
#
def set_selected_biomt():
    '''Set the PDB biomt matrices for the selected multiscale chains.'''
    mm = multiscale_manager(create = False)
    if mm is None:
        return
    mxf = {}
    mcopies = {}
    cplist = mm.selected_chains()
    for cp in cplist:
        lm = cp.lan_chain.lan_molecule
        sm = lm.source_molecule
        mxf.setdefault(sm, []).append(cp.xform)
        cm = lm.molecule(load = False)
        if cm:
            mcopies.setdefault(sm, []).append((cm,cp.xform))
    for sm, xflist in mxf.items():
        for cm,cxf in mcopies.get(sm, []):
            import PDBmatrices
            PDBmatrices.set_pdb_biomt_remarks(cm, relative_xforms(xflist,cxf))
      
# -----------------------------------------------------------------------------
#
def relative_xforms(xflist, relxf):
    rxflist = []
    relxfinv = relxf.inverse()
    from chimera import Xform
    for xf in xflist:
        rxf = Xform()
        rxf.premultiply(relxfinv)
        rxf.premultiply(xf)
        rxflist.append(rxf)
    return rxflist
      
# -----------------------------------------------------------------------------
#
def show_biological_unit(molecules = None, show_dialog = True):

  if molecules is None:
    molecules = selected_molecules()

  import Molecule
  bumlist = [m for m in molecules
             if len(Molecule.biological_unit_matrices(m)) > 1]
  if len(molecules) > len(bumlist):
    names = ', '.join([m.name for m in molecules if m not in bumlist])
    from chimera.replyobj import status
    status('Molecule %s has no BIOMT PDB headers' % names)

  mm = multiscale_manager()
  mmlist = mm.make_multimers(bumlist, Molecule.biological_unit_matrices)

  if show_dialog:
    show_multiscale_model_dialog()

  return mmlist

# -----------------------------------------------------------------------------
#
def selected_molecules():

  from chimera import openModels, Molecule, selection
  molecules = selection.currentMolecules()
  if len(molecules) == 0:
    molecules = openModels.list(modelTypes = [Molecule])
  return molecules
  
# -----------------------------------------------------------------------------
#
_msman = None
def multiscale_manager(create = True):

  global _msman
  if create and _msman is None:
    _msman = MultiScale_Manager()
  return _msman
  
# -----------------------------------------------------------------------------
#
def multiscale_model_dialog(create = False):

  from chimera import dialogs
  return dialogs.find(MultiScale_Model_Dialog.name, create=create)
  
# -----------------------------------------------------------------------------
#
def show_multiscale_model_dialog():

  from chimera import dialogs
  return dialogs.display(MultiScale_Model_Dialog.name)

# -----------------------------------------------------------------------------
#
from chimera import dialogs
dialogs.register(MultiScale_Model_Dialog.name, MultiScale_Model_Dialog, replace = True)
