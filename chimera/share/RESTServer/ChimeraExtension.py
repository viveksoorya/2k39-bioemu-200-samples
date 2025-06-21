import chimera.extension

class RESTServerEMO(chimera.extension.EMO):

	def name(self):
		return "RESTServer"
	def description(self):
		return "HTTP server for executing Chimera commands"
	def categories(self):
		return ["Utilities"]
	def activate(self):
		self.module().run()
		return None

emo = RESTServerEMO(__file__)
chimera.extension.manager.registerExtension(emo)
