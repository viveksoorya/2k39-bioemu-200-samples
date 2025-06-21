import httplib, mimetypes, urllib

proxies = urllib.getproxies_environment()

def post_multipart(host, selector, fields, ssl=False, **kw):
	"""
Post fields and files to an http host as multipart/form-data.
fields is a sequence of (name, filename, value) elements for form fields.
If filename is None, the field is treated as a regular field;
otherwise, the field is uploaded as a file.
Return the server's response page.
"""
	return post_multipart_formdata(host, selector, fields, ssl, **kw)[3]

def post_multipart_formdata(host, selector, fields, ssl=False, acceptType=None):
	content_type, body = encode_multipart_formdata(fields)
	try:
		realhost = proxies["http"]
	except KeyError:
		realhost = host
	if ssl:
		h = httplib.HTTPS(realhost)
	else:
		h = httplib.HTTP(realhost)
	h.putrequest('POST', selector)
	h.putheader('content-type', content_type)
	h.putheader('content-length', str(len(body)))
	h.putheader('host', host)
	if acceptType is not None:
		h.putheader('Accept', acceptType)
	h.endheaders()
	h.send(body)
	retcode, retmsg, headers = h.getreply()
	return retcode, retmsg, headers, h.file.read()

def encode_multipart_formdata(fields):
	"""
fields is a sequence of (name, filename, value) elements for data
to be uploaded as files.  If filename is None, the field is not
given a filename.
Return (content_type, body) ready for httplib.HTTP instance
"""
	BOUNDARY = '---------------------------473995594142710163552326102'
	CRLF = '\r\n'
	L = []
	for (key, filename, value) in fields:
		L.append('--' + BOUNDARY)
		if filename is None:
			L.append('Content-Disposition: form-data; name="%s"' % key)
			L.append('Content-Type: text/plain; charset=UTF-8')
		else:
			L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
			L.append('Content-Type: %s' % get_content_type(filename))
		L.append('')
		if isinstance(value, unicode):
			value = value.encode('utf8')
		L.append(value)
	L.append('--' + BOUNDARY + '--')
	L.append('')
	body = CRLF.join(L)
	content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
	return content_type, body

import sys, threading
_lock = None if sys.platform != "win32" else threading.Lock()

def get_content_type(filename):
	if _lock is None:
		return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
	with _lock:
		return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
