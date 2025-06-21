# -----------------------------------------------------------------------------
#
def open_viper_model(path, model_name = None):

  from os.path import isfile
  if not isfile(path) and len(path) == 4:
    mlist = open_viper_id(path)
    return []

  import chimera
  mlist = chimera.openModels.open(path, type = 'PDB',
      temporary=bool(model_name))
  if model_name:
    for m in mlist:
      m.name = model_name
  import MultiScale
  d = MultiScale.show_multiscale_model_dialog()
  sym = d.multimer_none if is_viper_oligomer(mlist) else d.multimer_icosahedral_222
  d.multimer_type.set(sym)
  d.make_multimers(mlist)
  if mlist:
    chimera._openedInfo = "Opened %s\n" % mlist[0].name
  if len(chimera.openModels.list()) == 2*len(mlist):
    chimera.viewer.viewAll()    # Make sure full capsid is in view.
  return []

# -----------------------------------------------------------------------------
#
def is_viper_oligomer(mlist):

  for m in mlist:
    if hasattr(m, 'pdbHeaders') and 'REMARK' in m.pdbHeaders:
      for line in m.pdbHeaders['REMARK']:
        if 'oligomer generation' in line.lower():
          return True
  return False
  
# -----------------------------------------------------------------------------
# Example URL: http://viperdb.scripps.edu/cgi-bin/stream_vdb.cgi?VDB=1a6c
#
def open_viper_id(id, ignore_cache=False):

  site = 'viperdb.scripps.edu'
  url_pattern = 'http://%s/cgi-bin/stream_vdb.cgi?VDB=%s'
  
  url = url_pattern % (site, id)
  name = 'VIPERdb %s' % id
  minimum_file_size = 2048       # bytes
  from chimera import fetch
  path, headers = fetch.fetch_file(url, name, minimum_file_size,
                                   save_dir = 'VIPERdb',
                                   save_name = id + '.vdb',
                                   uncompress = 'always',
                                   ignore_cache = ignore_cache)

  mlist = open_viper_model(path, model_name = id)
  return mlist

# -----------------------------------------------------------------------------
# Register to open VIPERdb virus capsid models.
#
import chimera
fi = chimera.fileInfo
fi.register('VIPERdb', open_viper_model, ['.vdb'], ['viper'],
            category = fi.STRUCTURE)
fi.register('VIPERID', open_viper_id, None, ['viperID'],
            category = fi.STRUCTURE)

# -----------------------------------------------------------------------------
# Register to fetch models from VIPERdb web site.
#
from chimera import fetch
fetch.registerIdType('VIPERdb', 4, '1ej6', 'VIPERID', 'viperdb.scripps.edu',
                     'http://viperdb.scripps.edu/info_page.php?VDB=%s')
