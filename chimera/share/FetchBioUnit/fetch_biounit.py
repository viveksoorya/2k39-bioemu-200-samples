# -----------------------------------------------------------------------------
# Fetch biological unit PDB files.  There can be any number of files for one pdb id.
#
#   ftp://ftp.wwpdb.org/pub/pdb/data/biounit/coordinates/all/391d.pdb1.gz
#   ftp://ftp.wwpdb.org/pub/pdb/data/biounit/coordinates/all/391d.pdb2.gz
#   ftp://ftp.wwpdb.org/pub/pdb/data/biounit/coordinates/all/391d.pdb3.gz
#
#   Structure info: http://www.rcsb.org/pdb/explore.do?structureId=391d
#
def read_biounit(id, ignore_cache=False):

  site = 'files.rcsb.org'
  url_pattern = 'https://%s/download/%s.gz'

  # Fetch file(s).
  models = []
  sid = id.split('.')
  if len(sid) > 1:
    # Parse specific biological assembly number from identifier, e.g. 1hho.2
    id = sid[0]
    bunums = [int(i) for i in sid[1:]]
  else:
    from itertools import count
    bunums = count(1)
  from chimera import openModels
  for i in bunums:
    suffix = '.pdb%d' % i
    mlist = fetch_biounit(site, url_pattern, id, suffix, ignore_cache=ignore_cache)
    if len(mlist) == 0:
      break
    openModels.add(mlist)
    if len(mlist) > 1:
      from ModelPanel import groupCmd
      groupCmd(mlist, name = '%s%s' % (id, suffix))
    models.extend(mlist)

  from chimera.replyobj import status
  if len(models) == 0:
    from chimera import NonChimeraError
    status('')
    raise NonChimeraError('PDB biounit file %s not available.' % id)
  status('')

  # Models already opened so must return emtpy list of models.
  # Already opened so that each assembly has its own top level id and its own color.
  return []

# -----------------------------------------------------------------------------
#
def fetch_biounit(site, url_pattern, id, suffix, ignore_cache=False):

  name = id + suffix
  from chimera.replyobj import status
  status('Fetching %s from web site %s...' % (name,site), blankAfter = False)
  minimum_file_size = 2048       # bytes
  file_url = url_pattern % (site, name.lower())
  from chimera import fetch, NonChimeraError
  try:
    file_path, headers = fetch.fetch_file(file_url, name, minimum_file_size,
                                          'PDB', name, uncompress = 'always',
                                          ignore_cache=ignore_cache)
  except NonChimeraError:
    return []

  # Display file(s).
  status('Opening PDB biounit file %s...' % name, blankAfter = False)
  from chimera import _openPDBModel
  mlist = _openPDBModel(file_path, identifyAs = name)

  return mlist

# -----------------------------------------------------------------------------
# Register to fetch biological unit files the PDB using the command line and
# file prefixes.
#
def register_pdb_biounit_id_file_prefix():

  import chimera
  fi = chimera.fileInfo
  fi.register('BIOUNITID', read_biounit, None, ['biounitID'], category = fi.STRUCTURE)
  # Deprecated type name and prefix, pdbbuid
  fi.register('PDBBUID', read_biounit, None, ['pdbbuid'], category = fi.STRUCTURE)
