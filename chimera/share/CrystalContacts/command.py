# -----------------------------------------------------------------------------
# Command to show crystal contacts.
#
# Syntax: crystalcontacts <molecule-id> <distance>
#                         [copies true|false]
#                         [replace true|false]
#
def crystal_contacts(cmdname, args):

    from Midas.midas_text import doExtensionFunc
    doExtensionFunc(show_contacts, args,
                    specInfo = [('moleculeSpec','molecules','models'),])

# -----------------------------------------------------------------------------
#
def show_contacts(molecules, distance, residueInfo = False,
                  buriedAreas = False, probeRadius = 1.4,
                  intraBioUnit = True,
                  copies = False, schematic = True, replace = True):

    from chimera import Molecule
    mlist = [m for m in molecules if isinstance(m, Molecule)]

    if len(mlist) == 0:
        from Midas import MidasError
	raise MidasError('No molecules specified')

    from CrystalContacts import show_crystal_contacts
    for m in mlist:
        if show_crystal_contacts(m, distance,
                                 make_copies = copies,
                                 schematic = schematic,
                                 residue_info = residueInfo,
                                 buried_areas = buriedAreas,
                                 probe_radius = probeRadius,
                                 intra_biounit = intraBioUnit,
                                 replace = replace) is None:
            from Midas import MidasError
            raise MidasError('Missing crystal symmetry for %s' % m.name)
