# -----------------------------------------------------------------------------
# Fetch density maps from the Electron Microscopy Data Bank
#
#       ftp://ftp.wwpdb.org/pub/emdb/structures/EMD-5582/map/emd_5582.map.gz
#       ftp://ftp.ebi.ac.uk/pub/databases/emdb/structures/EMD-5680/map/emd_5680.map.gz
#

# -----------------------------------------------------------------------------
#
def fetch_emdb_map(id, open_fit_pdbs = False, ignore_cache=False):
  import socket
  hname = socket.gethostname()
  if hname.endswith('.edu') or hname.endswith('.gov'):
    site = 'ftp.wwpdb.org'
    url_pattern = 'ftp://%s/pub/emdb/structures/EMD-%s/map/%s'
    xml_url_pattern = 'ftp://%s/pub/emdb/structures/EMD-%s/header/%s'
  elif hname.endswith('.cn'):
    site = 'ftp.emdb-china.org'
    url_pattern = 'ftp://%s/structures/EMD-%s/map/%s'
    xml_url_pattern = 'ftp://%s/structures/EMD-%s/header/%s'
  else:
    site = 'ftp.ebi.ac.uk'
    url_pattern = 'ftp://%s/pub/databases/emdb/structures/EMD-%s/map/%s'
    xml_url_pattern = 'ftp://%s/pub/databases/emdb/structures/EMD-%s/header/%s'

  from chimera.replyobj import status, info, warning
  status('Fetching %s from %s...' % (id,site), blankAfter = False)

  # Fetch map.
  map_name = 'emd_%s.map' % id
  map_gz_name = map_name + '.gz'
  map_url = url_pattern % (site, id, map_gz_name)
  name = 'EMDB %s' % id
  minimum_map_size = 8192       # bytes
  from chimera import fetch, NonChimeraError
  try:
    map_path, headers = fetch.fetch_file(map_url, name, minimum_map_size,
                 'EMDB', map_name, uncompress = True, ignore_cache=ignore_cache)
  except NonChimeraError, e:
    if 'Failed to change directory' in str(e):
      raise NonChimeraError('EMDB ID %s does not exist or map has not been released.' % id)
    else:
      raise
  # Display map.
  status('Opening map %s...' % map_name, blankAfter = False)
  from VolumeViewer import open_volume_file
  models = open_volume_file(map_path, 'ccp4', map_name, 'surface',
                            open_models = False)

  if open_fit_pdbs:
    # Find fit pdb ids.
    # Fetch meta data. 
    xml_name = 'emd-%s.xml' % id 
    xml_url = xml_url_pattern % (site, id, xml_name) 
    name = 'EMDB %s meta data' % id 
    minimum_xml_size = 128       # bytes 
    status('EMDB %s: looking for fits PDBs\n' % id) 
    xml_path, headers = fetch.fetch_file(xml_url, name, minimum_xml_size, 
                                         'EMDB', xml_name) 
    # Find fit pdb ids. 
    f = open(xml_path, 'r') 
    pdb_ids = fit_pdb_ids_from_xml(f) 
    f.close() 

    msg = ('EMDB %s has %d fit PDB models: %s\n'
           % (id, len(pdb_ids), ','.join(pdb_ids)))
    status(msg)
    info(msg)
    if pdb_ids:
      mlist = []
      errors = []
      from chimera import _openPDBIDModel
      for pdb_id in pdb_ids:
        status('Opening %s' % pdb_id)
        try:
          m = _openPDBIDModel(pdb_id, ignore_cache=ignore_cache)
        except Exception as e:
          errors.append(str(e))
        else:
          mlist.extend(m)
      models.extend(mlist)
      if errors:
        warning('\n'.join(errors))

  return models
  
# -----------------------------------------------------------------------------
#
def fit_pdb_ids_from_xml(xml_file):

  # ---------------------------------------------------------------------------
  # Handler for use with Simple API for XML (SAX2).
  #
  from xml.sax import ContentHandler
  class EMDB_SAX_Handler(ContentHandler):

    def __init__(self):
      self.pdbEntryId = False
      self.ids = []

    def startElement(self, name, attrs):
      if name == 'fittedPDBEntryId':
        self.pdbEntryId = True

    def characters(self, s):
      if self.pdbEntryId:
        self.ids.append(s)

    def endElement(self, name):
      if name == 'fittedPDBEntryId':
        self.pdbEntryId = False

    def pdb_ids(self):
      return (' '.join(self.ids)).split()

  from xml.sax import make_parser
  xml_parser = make_parser()

  from xml.sax.handler import feature_namespaces
  xml_parser.setFeature(feature_namespaces, 0)

  h = EMDB_SAX_Handler()
  xml_parser.setContentHandler(h)
  xml_parser.parse(xml_file)

  return h.pdb_ids()

# -----------------------------------------------------------------------------
#
def fit_pdb_ids_from_web_service(id):

  from WebServices.emdb_client import EMDB_WS
  ws = EMDB_WS()
  import socket
  try:
    results = ws.findFittedPDBidsByAccessionCode(id)
  except socket.gaierror:
    from chimera import replyobj
    replyobj.error('Could not connect to EMDB web service\nto determine fit PDB entries.')
    pdb_ids = []
  else:
    pdb_ids = [t['fittedPDBid'] for t in ws.rowValues(results)
               if t['fittedPDBid']]
  return pdb_ids

# -----------------------------------------------------------------------------
# Register to fetch EMDB maps using the command line and file prefixes.
#
def register_emdb_file_prefix():

  import chimera
  fi = chimera.fileInfo
  fi.register('EMDBID', fetch_emdb_map, None, ['emdbID'], category = fi.VOLUME)
  ffm = lambda id, ignore_cache=False: fetch_emdb_map(id, open_fit_pdbs = True,
    ignore_cache=ignore_cache)
  fi.register('EMDBFITID', ffm, None, ['emdbfitID'], category = fi.VOLUME)

# -----------------------------------------------------------------------------
# Register to fetch EMDB using the Chimera Fetch by Id dialog.
#
def register_emdb_fetch():

  from chimera.fetch import registerIdType as reg
  from emdb_search import search_emdb
  reg('EMDB', 4, '5625', 'EMDBID',
      'www.emdatabank.org',
      'https://www.ebi.ac.uk/emdb/entry/EMD-%s')
  reg('EMDB & fit PDBs', 4, '1048', 'EMDBFITID',
      'www.emdatabank.org',
      'https://www.ebi.ac.uk/emdb/entry/EMD-%s')
