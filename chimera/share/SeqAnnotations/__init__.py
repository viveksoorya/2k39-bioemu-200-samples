# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

def name2pdbID(name):
	startable = True
	for i in range(0, len(name)-3):
		if startable and name[i].isdigit() and name[i+1:i+4].isalnum() and (
				len(name[i:]) == 4 or not name[i+4].isalnum()
				or (name[i+4].isupper() and not name[i+3].isupper())):
			pdbID = name[i:i+4].upper()
			return pdbID, pdbID, "PDBID"
		startable = not name[i].isalnum()

	# SCOP?
	if len(name) == 7 and name[0] == 'd':
		if name[1].isdigit() and name[2:5].isalnum():
			pdbID = name[1:5].upper()
			return pdbID, name, "SCOP"
	return None, None, None

def chain2pdbID(chain):
	header = getattr(chain.molecule, 'pdbHeaders', {}).get('HEADER', None)
	if header:
		pdbID = header[0].split()[-1]
		if len(pdbID) == 4 and pdbID[0].isdigit() \
		and pdbID[1:].isalnum():
			return pdbID
	pdbID, fetchID, db = name2pdbID(chain.molecule.name)
	return pdbID

def uniprotIDs(pdbCode, chainID, align_info=None):
	if align_info == None:
		chain_info, align_info = parseUniprotAlignment(pdbCode, chainID)
	return set([ai["reference_database_accession"] for ai in align_info])

class InvalidAccessionError(ValueError):
	pass

def mapUniprotNameID(ident):
	import urllib, urllib2
	params = { 'from': 'UniProtKB_AC-ID', 'to': 'UniProtKB', 'ids': ident}
	data = urllib.urlencode(params)
	request = urllib2.Request("https://rest.uniprot.org/idmapping/run/", data)
	request.add_header("User-Agent", "Python chimera-bugs@cgl.ucsf.edu")
	from chimera import NonChimeraError
	try:
		response = urllib2.urlopen(request)
	except urllib2.HTTPError, v:
		raise NonChimeraError("Error from UniProt web server while submitting job: %s\n\n"
			"Try again later.  If you then still get the error, you could use"
			"Help->Report A Bug to report the error to the Chimera team."
			"They may be able to help you work around the problem."
			% unicode(v))
	job_page = response.read().decode('utf-8')
	import json
	try:
		job_info = json.loads(job_page)
	except json.JSONDecodeError:
		raise InvalidAccessionError("Invalid UniProt entry name / accession number: %s" % ident)
	try:
		job_id = job_info['jobId']
	except KeyError:
		raise ValueError("Unexpected response from UniProt ID-mapping server: %s" % job_info)
	# wait for mapping job to finish...
	while True:
		try:
			response = urllib2.urlopen("https://rest.uniprot.org/idmapping/status/" + job_id)
		except urllib2.HTTPError, v:
			raise NonChimeraError("Error from UniProt web server while checking job status: %s\n\n"
				"Try again later.  If you then still get the error, you could use"
				"Help->Report A Bug to report the error to the Chimera team."
				"They may be able to help you work around the problem."
				% unicode(v))
		status_page = response.read().decode('utf-8')
		try:
			info = json.loads(status_page)
		except json.JSONDecodeError:
			raise InvalidAccessionError("Invalid UniProt entry name / accession number: %s" % ident)
		if "jobStatus" in info:
			import time
			time.sleep(0.5)
		elif "failedIds" in info:
			raise InvalidAccessionError("Invalid UniProt entry name / accession number: %s" % ident)
		else:
			results = info['results'][0]
			return results["from"]

def uniprotFetch(uniprotID):
	"""can raise CancelOperation"""
	from chimera.fetch import fetch_file
	path, headers = fetch_file("https://www.uniprot.org/"
		"uniprot/%s.xml" % uniprotID, "%s UniProt info" % uniprotID)
	tree = xmlParsePath(path)
	import os
	os.unlink(path)
	try:
		uniprot = [cn for cn in tree.childNodes
			if getattr(cn, 'tagName', None) == "uniprot"][0]
	except IndexError:
		raise InvalidAccessionError(
				"Invalid UniProt accession number: %s" % uniprotID)
	entry = [cn for cn in uniprot.childNodes
		if getattr(cn, 'tagName', None) == "entry"][0]
	try:
		seqNode = [cn for cn in entry.childNodes
			if getattr(cn, 'tagName', None) == "sequence"][0]
	except (KeyError, IndexError):
		raise AssertionError("No sequence for %s in Uniprot"
			" info" % uniprotID)
	protein = [cn for cn in entry.childNodes
		if getattr(cn, 'tagName', None) == "protein"][0]
	recName = [cn for cn in protein.childNodes
		if getattr(cn, 'tagName', None)
		in ("recommendedName", "submittedName")][0]
	fullName = [cn for cn in recName.childNodes
		if getattr(cn, 'tagName', None) == "fullName"][0].firstChild.nodeValue
	features = [cn for cn in entry.childNodes
			if getattr(cn, 'tagName', None) == "feature"]
	return "".join([c for c in seqNode.firstChild.nodeValue
				if not c.isspace()]), fullName, features

def showCddFeatures(mav, seqIndex=-1, hideSS=None):
	"""returns corresponding PSSM Ids

	   can raise CancelOperation
	"""

	seq = mav.seqs[seqIndex]
	from chimera import tasks
	task = tasks.Task("Fetch CDD annotations for %s" % seq.fullName())
	from CGLutil import multipart
	import socket
	cddHost = "www.ncbi.nlm.nih.gov"
	cddPage = "/Structure/bwrpsb/bwrpsb.cgi"
	mav.status("Submitting CDD annotations job for %s" % seq.fullName())
	task.updateStatus("submitting job")
	try:
		# settings documented here:
		# www.ncbi.nlm.nih.gov/Structure/cdd/cdd_help.shtml#BatchRPSBWebAPI
		cddData = multipart.post_multipart(cddHost, cddPage, [
				("queries", None, seq.ungapped().upper()),
				("db", None, "cdd"),
				("smode", None, "live"),
				("evalue", None, "0.01"),
				("tdata", None, "feats"),
				("dmode", None, "rep"),
				("qdefl", None, "false"),
				("cddefl", None, "false")
			], ssl=True)
	except (IOError, socket.error), v:
		task.finished()
		from chimera import NonChimeraError
		raise NonChimeraError("Error posting CDD annotations"
			" from %s: %s" % (cddHost, str(v)))
	except:
		task.finished()
		raise
	cddStatus = cdsid = None
	for line in cddData.splitlines():
		fields = line.split()
		if fields[0] == "#status":
			cddStatus = int(fields[1])
		elif fields[0] == "#cdsid":
			cdsid = fields[1]
	if cddStatus is None or cdsid is None:
		task.finished()
		raise AssertionError("No status info and/or job ID in CDD response")

	mav.status("CDD annotations job submitted; awaiting results")
	waitIncr = waitAmount = 0
	import time
	while cddStatus != 0:
		for i in range(waitAmount):
			task.updateStatus("awaiting job completion")
			time.sleep(1.0)
		try:
			cddData = multipart.post_multipart(cddHost, cddPage,
				[("cdsid", None, cdsid)])
		except (IOError, socket.error), v:
			task.finished()
			from chimera import NonChimeraError
			raise NonChimeraError("Error retrieving CDD annotations"
				" from %s: %s" % (cddHost, str(v)))
		except:
			task.finished()
			raise
		for line in cddData.splitlines():
			fields = line.split()
			if fields[0] == "#status":
				cddStatus = int(fields[1])
				break
		waitIncr += 1
		waitAmount += waitIncr
	task.finished()
	mav.status("CDD job finished; processing results")

	rb = mav.regionBrowser
	msReg = None
	if hideSS == None:
		hideSS = len(mav.seqs) == 1
	if hideSS:
		mav.showSS(show=False)
	for reg in rb.regions[:]:
		if reg.name in ["structure strands", "structure helices"]:
			rb.lowerRegion(reg, rebuildTable=False)
		if reg.name and reg.name.startswith(mav.GAP_REG_NAME_START):
			msReg = reg
	featureInfo = []
	pssmIDs = set()
	for line in cddData.splitlines():
		if not line or line[0] == '#':
			continue
		fields = line.split('\t')
		if len(fields) != 7 or fields[0] == 'Query':
			continue
		query, qtype, title, coordinates, fullSize, mappedSize, pssmID = fields
		ungappedCoords = []
		for coord in coordinates.split(','):
			if '-' in coord:
				# explicit range
				fromCrd, toCrd = coord.split('-')
				fromRC, fromPos = fromCrd[0], int(fromCrd[1:])
				toRC, toPos = toCrd[0], int(toCrd[1:])
				for pos in range(fromPos, toPos+1):
					ungappedCoords.append(seq.ungapped2gapped(pos-1))
			else:
				resCode, pos = coord[0], int(coord[1:])
				ungappedCoords.append(seq.ungapped2gapped(pos-1))
		# convert to ranges
		ranges = []
		start = cur = None
		for uc in ungappedCoords:
			if start is None:
				start = cur = uc
			elif uc == cur + 1:
				cur = uc
			else:
				ranges.append((start, cur))
				start = cur = uc
		ranges.append((start, cur))
		featureInfo.append((title, ranges, pssmID))
		if pssmID != '-':
			pssmIDs.add(pssmID)
	featureInfo.sort()
	featureInfo.reverse()
	# use region colors that differ from each other and from
	# letters (black) and selection region (green)
	usedColors = [(0.0, 1.0, 0.0), (0.0, 0.0, 0.0)]
	from CGLtk.color import distinguishFrom
	for title, ranges, pssmID in featureInfo:
		rebuildTable = (title, ranges, pssmID) == featureInfo[-1]
		fill = distinguishFrom(usedColors, numCandidates=5, seed=len(seq))
		usedColors.append(fill)
		if len(pssmIDs) > 1 and pssmID != '-':
			source = "CDD (PSSM %s)" % pssmID
		else:
			source = "CDD"
		mav.newRegion(name=title, shown=False, fill=fill, blocks=[
			(seq, seq, begin, end) for begin,end in ranges], sequence=seq,
			rebuildTable=rebuildTable, after=msReg, source=source)
	rb.showSeqRegions(seq)
	rb.enter()
	mav.enter() # put the sequence on top
	if featureInfo:
		mav.status("CDD features shown")
	else:
		mav.status("No CDD features found")
	return pssmIDs

from chimera import UserError
class UniprotMappingError(UserError):
	pass
class NoUniprotEntryError(UniprotMappingError):
	pass
def parseUniprotAlignment(pdbCode, chainID, noAlignmentOkay=False):
	url = 'https://data.rcsb.org/rest/v1/core/entry/%s' % pdbCode
	from urllib2 import URLError
	entry_info = grab_url(url)
	key ="rcsb_entry_container_identifiers"
	try:
		id_info = entry_info[key]
	except KeyError:
		raise UniprotMappingError("Cannot find '%s' in entry info for %s" % (key, pdbCode))
	key = "polymer_entity_ids"
	try:
		entity_ids = id_info[key]
	except KeyError:
		raise UniprotMappingError("Cannot find '%s' in entry info for %s" % (key, pdbCode))

	for eid in entity_ids:
		url = 'https://data.rcsb.org/rest/v1/core/polymer_entity/%s/%s' % (pdbCode, eid)
		entity_info = grab_url(url)
		key = 'rcsb_polymer_entity_container_identifiers'
		try:
			id_data = entity_info[key]
		except KeyError:
			raise UniprotMappingError("Cannot find '%s' in entity info for %s" % (key, pdbCode))

		key = 'asym_ids'
		try:
			canon = id_data[key]
		except KeyError:
			raise UniprotMappingError("Cannot find '%s' in chain ID info for %s" % (key, pdbCode))
		key = 'auth_asym_ids'
		try:
			auth = id_data[key]
		except KeyError:
			raise UniprotMappingError("Cannot find '%s' in chain ID info for %s" % (key, pdbCode))
		if len(canon) != len(auth):
			raise UniprotMappingError("Number of canonical chains (%d) does not match the number"
				" of author chains (%d) for %s" % (len(canon), len(auth), pdbCode))
		for label_id, auth_id in zip(canon, auth):
			if auth_id == chainID:
				break
		else:
			continue
		break
	else:
		raise UniprotMappingError("Cannot find chain '%s' in chain-mapping info for %s"
			% (chainID, pdbCode))
	key = "rcsb_polymer_entity_align"
	try:
		all_align_info = entity_info[key]
	except KeyError:
		if noAlignmentOkay:
			all_align_info = []
		else:
			raise NoUniprotEntryError("Cannot find '%s' in entity info for %s" % (key, pdbCode))

	sifts = []
	for align_info in all_align_info:
		try:
			if align_info["provenance_source"] == "SIFTS" and align_info["reference_database_name"] == \
			"UniProt" and "reference_database_accession" in align_info and "aligned_regions" in align_info:
				sifts.append(align_info)
		except KeyError:
			continue
	if not sifts and not noAlignmentOkay:
		raise NoUniprotEntryError("Cannot find UniProt alignment info for entry %s" % pdbCode)
	chain_info = { "PDB ID": pdbCode }
	chain_info["title"] = entry_info.get("struct", {}).get("title", "")
	chain_info["citation"] = entry_info.get("rcsb_primary_citation", {}).get("title", "")
	chain_info["pubmed_id"] = entry_info.get("rcsb_primary_citation", {}).get("pdbx_database_id_pub_med", "")
	exptl = entry_info.get("exptl", [])
	for exptl_item in exptl:
		try:
			chain_info["method"] = exptl_item["method"]
			break
		except KeyError:
			pass
	else:
		chain_info["method"] = ""
	chain_info["release"] = entry_info.get("rcsb_accession_info", {}).get("initial_release_date", "")
	src = entity_info.get("rcsb_entity_source_organism", [])
	srcs = set()
	for src_item in src:
		try:
			srcs.add(src_item["ncbi_scientific_name"])
		except KeyError:
			try:
				srcs.add(src_item["scientific_name"])
			except KeyError:
				continue
	chain_info["organism"] = ", ".join(srcs)
	return chain_info, sifts

def grab_url(url):
	from urllib2 import urlopen, URLError
	try:
		f = urlopen(url)
	except URLError, v:
		raise UniprotMappingError('Fetching PDB->Uniprot mapping info using URL:'
			' %s failed: %s\n' % (url, str(v)))
	data = f.read()
	f.close()
	return eval(data)

def showUniprotFeatures(mav, features, seqIndex=-1, hideSS=None, mapping=None,
		sourceID=None):
	# adjust existing regions...
	rb = mav.regionBrowser
	msReg = None
	seq = mav.seqs[seqIndex]
	if hideSS == None:
		hideSS = len(mav.seqs) == 1
	if hideSS:
		mav.showSS(show=False)
	for reg in rb.regions[:]:
		if reg.name in ["structure strands", "structure helices"]:
			rb.lowerRegion(reg, rebuildTable=False)
		if reg.name and reg.name.startswith(mav.GAP_REG_NAME_START):
			msReg = reg
			msReg.borderRGBA = (1.0, 0.376, 0.898, 1.0)
			msReg.interiorRGBA = None
			#msReg.borderRGBA = (1.0, 0.753, 0.796, 1.0)
			#msReg.interiorRGBA = (0.947, 0.824, 0.845, 1.0)
			mav.status("Sequence with no 3D structure outlined in pinkish magenta")
	fNameRemap = {
		"strand": "Uniprot strands",
		"helix": "Uniprot helices",
		"turn": "Uniprot turns"
	}
	fTypeColor = {
		"active site": "deep sky blue",
		"binding site": "medium purple",
		"chain": "dark khaki",
		"disulfide bond": "yellow",
		"domain": "sandy brown",
		"glycosylation site": "white",
		"helix": "gold",
		"modified residue": "plum",
		"mutagenesis site": "coral",
		"propeptide": "gray",
		"region of interest": "hot pink",
		"repeat": "slate gray",
		"sequence conflict": "red",
		"sequence variant": "orange",
		"signal peptide": "dark gray",
		"site": "turquoise",
		"splice variant": "magenta",
		"topological domain": "dark cyan",
		"transmembrane region": "salmon",
		"strand": "chartreuse",
		"turn": "medium purple",
	}
	regionInfo = {}
	featureLookup = {}
	for feature in features:
		locs = [cn for cn in feature.childNodes
					if getattr(cn, 'tagName', None) == "location"]
		if not locs:
			continue
		fType = feature.getAttribute("type")
		name = fNameRemap.get(fType, fType)
		# try to coalesce features with the exact
		# same attributes into one region...
		attrMap = {}
		xmlAttrs = feature.attributes
		for attr in [xmlAttrs.item(i) for i in range(xmlAttrs.length)]:
			if attr.localName == "type":
				continue
			attrMap[attr.localName] = attr.value
		regKey = (fType, tuple(sorted(attrMap.items())))
		featureLookup.setdefault(regKey, []).append(feature)
		for loc in locs:
			begin = end = None
			for cn in loc.childNodes:
				tn = getattr(cn, 'tagName', None)
				if tn == "position":
					begin = end = int(cn.getAttribute("position")) - 1
				elif tn == "begin" and cn.getAttribute("status") != "unknown":
					begin = int(cn.getAttribute("position")) - 1
				elif tn == "end" and cn.getAttribute("status") != "unknown":
					end = int(cn.getAttribute("position")) - 1
			if begin is None or end is None:
				continue
			blocks = regionInfo.setdefault(regKey, [])
			if mapping is not None:
				for b in range(begin, end+1):
					if b in mapping:
						break
				else:
					continue
				for e in range(end, begin-1, -1):
					if e in mapping:
						break
				else:
					continue
				# if the mapped range is larger than the unmapped range,
				# then there are one or more insertions in the sequence
				# and we need to add multiple blocks
				while e  - b < mapping[e] - mapping[b]:
					ne = b
					while ne - b == mapping[ne] - mapping[b]:
						ne += 1
						if ne not in mapping:
							break
					blocks.append((mapping[b], mapping[ne-1]))
					b = ne
					while b not in mapping:
						b += 1
				begin, end = mapping[b], mapping[e]
			blocks.append((begin, end))
	sortableRegKeys = list(reversed(sorted(
		[(fNameRemap.get(rk[0], rk[0]).lower(), rk) for rk in regionInfo.keys()])))
	if sourceID is None:
		source = "UniProt"
	else:
		source = "UniProt (%s)" % sourceID
	for sortKey, regKey in sortableRegKeys:
		fType, attrList = regKey
		attrMap = dict(attrList)
		blocks = regionInfo[regKey]
		if len(blocks) > 2:
			defName = fType + 's'
		else:
			defName = fType
		if 'bond' in fType:
			oldBlocks = blocks[:]
			blocks = []
			for block in oldBlocks:
				blocks.extend([(block[0], block[0]), (block[1], block[1])])
		baseName = fNameRemap.get(fType, defName)
		features = featureLookup[regKey]
		if len(features) == 1:
			feature = features[0]
			origs = [cn for cn in feature.childNodes
						if getattr(cn, 'tagName', None) == "original"]
			if len(origs) == 1:
				vars = [cn for cn in feature.childNodes
							if getattr(cn, 'tagName', None) == "variation"]
				if len(vars) == 1:
					baseName += " " + origs[0].firstChild.nodeValue + \
						u"\N{RIGHTWARDS ARROW}" \
						+ vars[0].firstChild.nodeValue
		if attrMap:
			baseName += ":\n\t"
			if 'description' in attrMap:
				baseName += attrMap.pop('description').replace(
						';', '\n\t  ').strip()
				if attrMap:
					baseName += "\n\t"
			regName = "%s%s" % (baseName, "\n\t".join([
				"%s=%s" % (k,v) for k,v in attrMap.items()]))
		else:
			regName = baseName
		if fType.endswith("-binding region"):
			fill = "cornflower blue"
		else:
			fill = fTypeColor.get(fType, "cyan")
		blocks=[(seq, seq, seq.ungapped2gapped(begin), seq.ungapped2gapped(end))
				for begin,end in blocks]
		isLast = regKey == sortableRegKeys[-1][1]
		reg = mav.getRegion(regName, sequence=seq, source=source)
		if reg:
			reg.addBlocks(blocks, makeCB=isLast)
		else:
			mav.newRegion(name=regName, shown=False, fill=fill, blocks=blocks,
				sequence=seq, source=source, rebuildTable=isLast,
				after=msReg)
	rb.showSeqRegions(seq)
	rb.enter()
	mav.enter() # put the sequence on top

def showUniprotSeq(ident):
	from chimera import UserError, CancelOperation, replyobj, Sequence
	try:
		acc = mapUniprotNameID(ident)
		seqString, fullName, features = uniprotFetch(acc)
	except InvalidAccessionError, v:
		raise UserError(unicode(v))
	except CancelOperation:
		replyobj.status("Fetch of %s cancelled" % ident)
		return
	seq = Sequence.Sequence(ident)
	seq.extend(seqString)
	from MultAlignViewer.MAViewer import MAViewer
	mav = MAViewer([seq], title=fullName)
	showUniprotFeatures(mav, features)

def pdbUniprotCorrespondences(chain, status=None,
								ignoreCache=False, pdbID=None):
	"""can raise CancelOperation"""

	from chimera import LimitationError
	try:
		chain.molecule.pdbHeaders["SEQRES"]
	except (AttributeError, KeyError):
		raise LimitationError("Cannot determine UniProt mapping for"
			" structures without PDB SEQRES records.  [Required by"
			u" RCSB PDB\N{RIGHTWARDS ARROW}UniProt web service]")
	if pdbID is None:
		try:
			header = chain.molecule.pdbHeaders["HEADER"]
		except (AttributeError, KeyError):
			raise LimitationError("Cannot determine PDB ID code"
				" without PDB HEADER record.  [PDB ID code required by"
				u" RCSB PDB\N{RIGHTWARDS ARROW}UniProt web service]")
		pdbID = header[0].split()[-1]
		if not (len(pdbID) == 4 and pdbID[0].isdigit() and pdbID[1:].isalnum()):
			from chimera import UserError
			raise UserError("HEADER record does not end with PDB ID code")
	chainID = chain.chainID
	if status:
		status("Fetching PDB data for %s, chain %s" % (pdbID, chainID))
	try:
		chain_info, align_info = parseUniprotAlignment(pdbID, chainID)
	finally:
		if status:
			status("")
	seqresIndex = makeSeqresIndex(chain)
	chain.uniprotIDs = uniprotIDs(pdbID, chainID, align_info=align_info)
	all_corrs = {}
	for uniprot_align_info in align_info:
		uniprot_id = uniprot_align_info["reference_database_accession"]
		corrs = all_corrs[uniprot_id] = []
		for region in uniprot_align_info["aligned_regions"]:
			entity_index = region["entity_beg_seq_id"] - 1
			uniprot_index = region["ref_beg_seq_id"] - 1
			length = region["length"]
			if entity_index + length > len(chain):
				from chimera import NonChimeraError
				raise NonChimeraError("%s: RCSB reports length greater"
					" than available in currently open structure.\nCheck"
					" to make sure you have the latest version of the PDB"
					" entry." % chain.name)
			corrs.append((entity_index, uniprot_index, length))
	return chain_info, all_corrs

def makeSeqresIndex(chain):
	"""make a lookup table from a (string) residue identifier to
	   an index into the (SEQRES-based) chain.residues"""
	lookup = {}
	midNones = initialNones = 0
	lastKey = None
	for i, r in enumerate(chain.residues):
		if r:
			key = str(r.id)[:-2]
			lookup[key] = i
			if initialNones and not lastKey:
				nonei = i - 1
				if key[-1].isalpha():
					insert = key[-1]
					while insert > 'A' and initialNones:
						insert = char(ord(insert)-1)
						initialNones -= 1
						lookup[key[:-1] + insert] = nonei
						nonei -= 1
					pos = int(key[:-1])
				else:
					pos = int(key)
				while initialNones:
					pos = pos - 1
					initialNones -= 1
					lookup[str(pos)] = nonei
					nonei -= 1
			lookup[key] = i
			if midNones:
				if key[-1].isalpha():
					pos = int(key[:-1])
				else:
					pos = int(key)
				ni = i
				while midNones:
					midNones -= 1
					pos -= 1
					ni -= 1
					lookup[str(pos)] = ni
		else:
			if not lastKey:
				initialNones += 1
				continue
			midNones += 1
			if lastKey[-1].isalpha():
				pos = int(lastKey[:-1]) + 1
			else:
				pos = int(lastKey) + 1
			key = str(pos)
			lookup[key] = i
		lastKey = key
	return lookup

def parseSifts(pdbCode, parser=None):
	"""can raise CancelOperation"""

	url = "http://www.rcsb.org/pdb/files/%s.sifts.xml.gz" % pdbCode.lower()
	from chimera.fetch import fetch_file
	# can raise CancelOperation
	path, headers = fetch_file(url, "%s SIFTS data" % pdbCode, uncompress=True,
		save_dir="SIFTS", save_name="%s.xml" % pdbCode.lower())
	tree = xmlParsePath(path, parser)
	return tree

def printElementTree(tree, depth=0):
	from xml.etree.ElementTree import ElementTree
	if isinstance(tree, ElementTree):
		node = tree.getroot()
	else:
		node = tree
	baseIndent = " " * (4 * depth)
	def printableTag(node):
		if node.tag.startswith('{'):
			return node.tag[node.tag.index('}')+1:]
		return node.tag
	if node.text and node.text.strip():
		textVal = " = " + node.text.strip()
	else:
		textVal = ""
	print baseIndent + printableTag(node) + textVal
	for k, v in node.items():
		print baseIndent, "  ", k, v
	for kid in node.getchildren():
		print baseIndent, "   --CHILD--"
		printTree(kid, depth+1)

def xmlParsePath(path, parser=None):
	if parser == None:
		import xml.dom.minidom
		parser = xml.dom.minidom.parse

	from OpenSave import osOpen
	f = osOpen(path)
	# would like to use 'with', but GzipFiles don't have __exit__
	try:
		tree = parser(f)
	finally:
		f.close()
	return tree
