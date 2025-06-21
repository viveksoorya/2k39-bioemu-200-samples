# -----------------------------------------------------------------------------
#  Fetch crystallographic density maps from PDBe (formerly the Upsalla Electron Density Server).
#
#  2fofc: https://www.ebi.ac.uk/pdbe/coordinates/files/1cbs.ccp4
#   fofc: https://www.ebi.ac.uk/pdbe/coordinates/files/1cbs_diff.ccp4
#
#   Info: https://www.ebi.ac.uk/pdbe/entry-files/download/1cbs_full_validation.pdf
#
def fetch_eds_map(id, type = '2fofc', ignore_cache=False):

  url_pattern = 'https://www.ebi.ac.uk/pdbe/coordinates/files/%s'

  # Fetch map.
  from chimera.replyobj import status
  status('Fetching %s from PDBe...' % (id,), blankAfter = False)
  if type == 'fofc':
    map_name = id + '_diff.ccp4'
  elif type == '2fofc':
    map_name = id + '.ccp4'
  map_url = url_pattern % map_name
  name = 'map %s' % id
  minimum_map_size = 8192       # bytes
  from chimera import fetch
  map_path, headers = fetch.fetch_file(map_url, name, minimum_map_size,
                                       'EDS', map_name, ignore_cache=ignore_cache)
    
  # Display map.
  status('Opening map %s...' % map_name, blankAfter = False)
  from VolumeViewer import open_volume_file
  models = open_volume_file(map_path, 'ccp4', map_name, 'mesh',
                            open_models = False, polar_values = (type == 'fofc'))
  status('')

  return models

# -----------------------------------------------------------------------------
# Register to fetch crystallographic maps from the Electron Density Server
# using the command line and file prefixes.
#
def register_eds_id_file_prefix():

  import chimera
  fi = chimera.fileInfo
  fi.register('EDSID', fetch_eds_map, None, ['edsID'], category = fi.VOLUME)
  ofofc = lambda id, ignore_cache=False: fetch_eds_map(id, 'fofc',
    ignore_cache=ignore_cache)
  fi.register('EDSDIFFID', ofofc, None, ['edsdiffID'], category = fi.VOLUME)

# -----------------------------------------------------------------------------
# Register to fetch crystallographic maps from the Electron Density Server
# using the Chimera Fetch dialog.
#
def register_fetch_gui():

  from chimera import fetch
  fetch.registerIdType('EDS (2fo-fc)', 4, '1a0m', 'EDSID',
                       'www.ebi.ac.uk/pdbe/eds',
                       'https://www.ebi.ac.uk/pdbe/entry-files/download/%s_full_validation.pdf')
  fetch.registerIdType('EDS (fo-fc)', 4, '1a0m', 'EDSDIFFID',
                       'www.ebi.ac.uk/pdbe/eds',
                       'https://www.ebi.ac.uk/pdbe/entry-files/download/%s_full_validation.pdf')
