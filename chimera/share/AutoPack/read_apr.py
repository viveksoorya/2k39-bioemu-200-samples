def read_autopack_results(path):

    j = read_json(path)
    recipe_path = j['recipe']['setupfile']
    pieces = {}
    for comp_name, cres in j['compartments'].items():
        for interior_or_surface, comp_ingr in cres.items():
            for ingr_name, ingr_places in comp_ingr['ingredients'].items():
                for translation, rotation44 in ingr_places['results']:
                    t0,t1,t2 = translation
                    r00,r01,r02 = rotation44[0][:3]
                    r10,r11,r12 = rotation44[1][:3]
                    r20,r21,r22 = rotation44[2][:3]
                    tf = ((r00,r01,r02,t0),
                          (r10,r11,r12,t1),
                          (r20,r21,r22,t2))
                    ingr_id = (comp_name, interior_or_surface, ingr_name)
                    if ingr_id in pieces:
                        pieces[ingr_id].append(tf)
                    else:
                        pieces[ingr_id] = [tf]

    return recipe_path, pieces

def read_autopack_recipe(path):

    j = read_json(path)
    ingr_filenames = {}
    comp_surfaces = []
    for comp_name, comp_details in j['compartments'].items():
        if 'rep_file' in comp_details:
            comp_surfaces.append(comp_details['rep_file'])
        for interior_or_surface in ('interior', 'surface'):
            if interior_or_surface in comp_details:
                for ingr_name, ingr_info in comp_details[interior_or_surface]['ingredients'].items():
                    ingr_filename = ingr_info['include']
                    ingr_id = (comp_name, interior_or_surface, ingr_name)
                    ingr_filenames[ingr_id] = ingr_filename
    return ingr_filenames, comp_surfaces

def read_ingredient(path):

    j = read_json(path)
    return j['meshFile']
    
def read_json(path):

    f = open(path, 'r')
    import json
    j = json.load(f)
    f.close()
    return j

def create_surfaces(surface_placements):

    from ReadCollada import read_collada
    from os.path import basename
    surfs = []
    for path, placements in surface_placements:
        surf = read_collada(path)
        if placements:
            surf.name += ' %d copies' % len(placements)
        create_surface_copies(surf, placements)
        surfs.append(surf)
    return surfs

def create_surface_copies(surf, tflist, random_colors = False):

    for p in surf.surfacePieces:
        va, ta = p.geometry
        na = p.normals
        if random_colors:
            p.color = random_color(surf.name)
        color = p.color
        if len(tflist) > 0:
            # Set geometry uses unplaced vertices while get geometry gives placed vertices!
            p.geometry = va, ta
            p.normals = na
            p.placement = tflist[0]
        p.save_in_session = True
        import Matrix
        for tf in tflist[1:]:
            pc = surf.addPiece(va, ta, color)
            pc.normals = na
            pc.placement = tf
            pc.save_in_session = True
