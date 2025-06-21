import chimera.extension

class ReadStdinEMO(chimera.extension.EMO):

	def name(self):
		return "Notepad"
	def description(self):
		return "record simple notes"
	def categories(self):
		return ["Utilities"]
	def icon(self):
		return self.path('Notepad.png')
	def activate(self):
		from chimera import dialogs
		dialogs.display(self.module('gui').NotepadDialog.name)
		return None

emo = ReadStdinEMO(__file__)
chimera.extension.manager.registerExtension(emo)
