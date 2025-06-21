# -----------------------------------------------------------------------------
# Fetch AutoPack recipe files, ingredient files, and ingredient meshes.
#
default_autopack_database = 'https://github.com/mesoscope/cellPACK_data/raw/master/cellPACK_database_1.1.0'

# -----------------------------------------------------------------------------
#
def fetch_autopack_by_id(results_name, database = default_autopack_database, ignore_cache = False):

    try:
        surfs = fetch_autopack(results_name, database, ignore_cache)
    except IOError as e:
        from chimera import UserError
        raise UserError('Unknown cellPACK id "%s"\n\n%s' % (results_name, str(e)))
    return surfs

# -----------------------------------------------------------------------------
#
def fetch_autopack(results_name, database = default_autopack_database, ignore_cache = False):

    path = fetch_autopack_results(results_name, database, ignore_cache)
    import read_apr
    recipe_loc, pieces = read_apr.read_autopack_results(path)
    recipe_url = recipe_loc.replace('autoPACKserver', database)
    from os.path import basename
    recipe_filename = basename(recipe_loc)
    min_size = 0
    recipe_path, headers = fetch_file(recipe_url, 'recipe for ' + results_name, min_size,
                                      'cellPACK', recipe_filename, ignore_cache=ignore_cache)

    # Combine ingredients used in multiple compartments
    ingr_filenames, comp_surfaces = read_apr.read_autopack_recipe(recipe_path)
    ingr_placements = {}
    for ingr_id, placements in pieces.items():
        ingr_filename = ingr_filenames[ingr_id]
        if ingr_filename in ingr_placements:
            ingr_placements[ingr_filename].extend(placements)
        else:
            ingr_placements[ingr_filename] = list(placements)

    # Fetch ingredient surface files.
    surf_placements = []
    for ingr_filename, placements in ingr_placements.items():
        from urlparse import urljoin
        ingr_url = urljoin(recipe_url, ingr_filename)
        ingr_path, headers = fetch_file(ingr_url, 'ingredient ' + ingr_filename, min_size,
                                        'cellPACK', ingr_filename, ignore_cache=ignore_cache)
        mesh_loc = read_apr.read_ingredient(ingr_path)
        mesh_url = mesh_loc.replace('autoPACKserver', database)
        mesh_filename = basename(mesh_loc)
        mesh_path, headers = fetch_file(mesh_url, 'mesh ' + mesh_filename, min_size,
                                        'cellPACK', mesh_filename, ignore_cache=ignore_cache)
        surf_placements.append((mesh_path, placements))

    # Fetch compartment surface files.
    comp_paths = []
    for comp_loc in comp_surfaces:
        comp_url = comp_loc.replace('autoPACKserver', database)
        comp_filename = basename(comp_loc)
        comp_path, headers = fetch_file(comp_url, 'component surface ' + comp_filename, min_size,
                                      'cellPACK', comp_filename, ignore_cache=ignore_cache)
        comp_paths.append(comp_path)

    # Open surface models
    surf_placements.extend((cmesh_path, []) for cmesh_path in comp_paths)
    surfs = read_apr.create_surfaces(surf_placements)

    return surfs

# -----------------------------------------------------------------------------
# Fetch AutoPack results files
#
def fetch_autopack_results(results_name, database = default_autopack_database, ignore_cache = False):

    # Fetch results file.
    results_url = database + '/results/%s.apr.json' % results_name

    from chimera.replyobj import status
    status('Fetching %s from web %s...' % (results_name,results_url), blankAfter = False)
    results_filename = results_name + '.apr.json'
    min_size = 0
    results_path, headers = fetch_file(results_url, 'results ' + results_name, min_size,
                                      'cellPACK', results_filename, ignore_cache=ignore_cache)
    return results_path

# -----------------------------------------------------------------------------
#
def fetch_file(*args, **kw):
    print 'Fetching ', args[0]
    from chimera import fetch
    path, headers = fetch.fetch_file(*args, **kw)
    if 'status' in headers and headers['status'].find('404') != -1:
        if path:
            import os
            os.remove(path)
        raise IOError('Web server reports file not found fetching %s' % (args[0],))
    return path, headers

# -----------------------------------------------------------------------------
# Register to fetch EMDB maps using the command line and file prefixes.
#
def register_autopack_file_prefix():

  import chimera
  fi = chimera.fileInfo
  fi.register('cellPACKId', fetch_autopack_by_id, None, ['cellpackID'], category = fi.GENERIC3D)

# -----------------------------------------------------------------------------
# Register to fetch AutoPack using the Chimera Fetch by Id dialog.
#
def register_autopack_fetch():

  info_url = '%s/results/%%s.apr.json' % (default_autopack_database,)
  from chimera.fetch import registerIdType as reg
  reg('cellPACK', 12, 'HIV-1_0.1.6', 'cellPACKId', 'http://www.cellpack.org', info_url)
