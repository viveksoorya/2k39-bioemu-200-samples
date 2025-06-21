from chimera.baseDialog import ModelessDialog

name = "Publish Scene"

sketchfabDesc = """\
Sketchfab is a web site where you can upload
Chimera scenes and embed them on any web page.
Visit sketchfab.com for more information."""

import preferences
SKETCHFAB = "sketchfab"
TOKEN = "token"
_sketchfab_options = {
	TOKEN: "",
}
preferences.addCategory(SKETCHFAB, preferences.HiddenCategory,
						optDict=_sketchfab_options)

class PublishDialog(ModelessDialog):
	name = name
	title = name

	def fillInUI(self, parent):
		import Pmw
		self.notebook = Pmw.NoteBook(parent)
		self.notebook.pack(fill="both", expand=True)
		self.pages = {}
		self.pages["Sketchfab"] = self._initSketchfab()

	def _initSketchfab(self):
		import Tkinter, Pmw
		from help import register
		page = self.notebook.add("Sketchfab")
		l = Tkinter.Label(page, text=sketchfabDesc,
						anchor="w", justify="left")
		l.pack(fill="x")
		self.token = Pmw.EntryField(page, labelpos="we",
						label_text="Token:",
						validate=None)
		self.token.pack(fill="x")
		register(self.token,
			balloon="Sketchfab token (see 'Password & API' "
			"under 'My settings' on sketchfab.com)")
		self.name = Pmw.EntryField(page, labelpos="we",
						label_text="Name:",
						validate=None)
		self.name.pack(fill="x")
		register(self.name, balloon="Sketchfab model name")
		self.tags = Pmw.EntryField(page, labelpos="we",
						label_text="Tags:",
						validate=None)
		self.tags.pack(fill="x")
		register(self.tags,
			balloon="Sketchfab model tags (space-separated list)")
		self.desc = Pmw.ScrolledText(page, labelpos="we",
						label_text="Description:")
		self.desc.pack(fill="both", expand=True)
		register(self.desc, balloon="Sketchfab model description")
		Pmw.alignlabels([self.token, self.name, self.desc, self.tags],
								sticky="e")

		# Fill in token if already present
		token = preferences.get(SKETCHFAB, TOKEN)
		if token:
			self.token.setvalue(token)

	def Apply(self):
		token = self.token.getvalue().strip()
		if not token:
			from chimera import UserError
			raise UserError("Sketchfab token is required")
		if token != preferences.get(SKETCHFAB, TOKEN):
			preferences.set(SKETCHFAB, TOKEN, token)
		name = self.name.getvalue().strip()
		tags = self.tags.getvalue().strip()
		desc = self.desc.getvalue().strip()
		#from OpenSave import osTemporaryFile
		#tmpFile = osTemporaryFile()
		#from exports import doExportCommand
		#doExportCommand("COLLADA", tmpFile)
		#with open(tmpFile) as f:
		#	data = f.read()
		import replyobj
		try:
			from cStringIO import StringIO
		except:
			from StringIO import StringIO
		from collada.source import FloatSource
		FloatSource.Precision = "%.3f"
		f = StringIO()
		from ExportCollada import write_collada
		write_collada(f)
		raw_data = f.getvalue()
		replyobj.info("COLLADA output size: %d bytes\n" % len(raw_data))
		from zipfile import ZipFile, ZIP_DEFLATED
		fz = StringIO()
		z = ZipFile(fz, mode="w", compression=ZIP_DEFLATED)
		z.writestr("chimera.dae", raw_data)
		z.close()
		data = fz.getvalue()
		del f, fz, raw_data
		replyobj.info("Upload zip size: %d bytes" % len(data))
		replyobj.status("Uploading %d bytes to Sketchfab..."
								% len(data))
		from threadq import runThread
		runThread(self._upload, token, name, tags, desc, data)

	def _upload(self, q, token, name, tags, desc, data):
		fields = [ ("token", None, token) ]
		if name:
			fields.append(("name", None, name))
		if tags:
			fields.append(("tags", None, tags))
		if desc:
			fields.append(("description", None, desc))
		fields.append(("modelFile", "chimera.zip", data))
		from CGLutil.multipart import post_multipart_formdata as post
		code, msg, headers, content = post("api.sketchfab.com",
							"/v2/models", fields,
							ssl=True)
		import json
		results = json.loads(content)
		import replyobj
		if code == 201:
			msg = "uploaded as model \"%s\"" % results["uid"]
			q.put(lambda s=self, m=msg: s._info(m))
			def f(s=self, token=token, uid=results["uid"]):
				from threadq import runThread
				runThread(s._monitor, token, uid)
			q.put(f)
		elif code == 400:
			msg = "upload failed: %s" % results["detail"]
			q.put(lambda s=self, m=msg: s._error(m))
		else:
			msg = "Bad HTTP code: %s" % repr(code)
			q.put(lambda s=self, m=msg: s._error(m))
		q.put(q)

	def _monitor(self, q, token, uid):
		url = ("https://api.sketchfab.com/v2/models/%s/status?token=%s"
								% (uid, token))
		import urllib2, json, time
		waitTimes = [ 5, 5, 5, 5, 5, 5, 30, 30, 30, 60, 60, 60, 60 ]
		for secs in waitTimes:
			time.sleep(secs)
			f = urllib2.urlopen(url)
			code = f.getcode()
			if code != 200:
				msg = "bad HTTP code: %s" % code
				q.put(lambda s=self, m=msg: s._error(m))
				break
			results = json.loads(f.read())
			status = results["processing"]
			if status == "FAILED":
				msg = ("processing failed: %s"
							% results["error"])
				q.put(lambda s=self, m=msg: s._error(m))
				break
			elif status == "SUCCEEDED":
				msg = ("model available at "
					"\"https://sketchfab.com/models/%s\""
					% uid)
				q.put(lambda s=self, m=msg: s._info(m))
				break
			else:
				q.put(lambda s=self, m=status: s._info(m))
		else:
			msg = "unable to determine processing state"
			q.put(lambda s=self, m=msg: s._error(m))
		q.put(q)

	def _error(self, msg):
		import replyobj
		replyobj.error("Sketchfab upload error: " + msg + "\n")

	def _info(self, msg):
		import replyobj
		msg = "Sketchfab upload: " + msg + "\n"
		replyobj.info(msg)
		replyobj.status(msg)
